from __future__ import annotations

import logging
import math
import threading

from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models.matching_job import MatchingJob
from app.models.project import Project
from app.repositories.demo_access_repository import now
from app.repositories.matching_job_repository import MatchingJobRepository
from app.services.audit.audit_runner import AuditRunner
from app.services.store_matching_service import StoreMatchingService


logger = logging.getLogger(__name__)
GLOBAL_MATCHING_LOCK_ID = 849204820194821


def queue_status(db, job: MatchingJob) -> dict:
    repo = MatchingJobRepository(db)
    jobs_ahead = repo.jobs_ahead(job) if job.status in ("QUEUED", "PROCESSING") else 0
    typical = repo.typical_duration_seconds()
    eta_minutes = None
    if typical:
        if job.status == "QUEUED":
            eta_minutes = max(1, math.ceil((jobs_ahead + 1) * typical / 60))
        elif job.status == "PROCESSING":
            elapsed = max(0, int((now() - job.started_at).total_seconds())) if job.started_at else 0
            eta_minutes = max(1, math.ceil(max(0, typical - elapsed) / 60))
    if job.status == "QUEUED":
        position = jobs_ahead + 1
        message = f"درخواست شما در صف قرار گرفت. جایگاه فعلی: {position}."
    elif job.status == "PROCESSING":
        message = "پردازش درخواست شما آغاز شده است."
    elif job.status == "COMPLETED":
        message = "پردازش کامل شد؛ در حال انتقال به نتیجه هستید."
    else:
        message = job.error_message or "پردازش کامل نشد. می‌توانید دوباره تلاش کنید."
    return {
        "status": job.status,
        "jobs_ahead": jobs_ahead,
        "eta_minutes": eta_minutes,
        "message": message,
        "error_message": job.error_message,
        "redirect_url": f"/projects/{job.project_id}/readiness",
    }


class MatchingQueueWorker:
    def __init__(self):
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self._loop, name="matching-queue-worker", daemon=True
        )
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)

    def _loop(self):
        while not self.stop_event.is_set():
            try:
                self._run_once()
            except Exception:
                logger.exception("Matching queue worker cycle failed")
            self.stop_event.wait(settings.MATCHING_QUEUE_POLL_SECONDS)

    def _run_once(self):
        with engine.connect() as lock_connection:
            acquired = bool(
                lock_connection.scalar(
                    text("SELECT pg_try_advisory_lock(:key)"),
                    {"key": GLOBAL_MATCHING_LOCK_ID},
                )
            )
            if not acquired:
                return
            try:
                with SessionLocal() as db:
                    repo = MatchingJobRepository(db)
                    recovered = repo.fail_stale(settings.MATCHING_QUEUE_STALE_SECONDS)
                    if recovered:
                        db.commit()
                    if repo.processing_exists():
                        db.rollback()
                        return
                    job = repo.claim_next()
                    if not job:
                        db.rollback()
                        return
                    job_id = job.id
                    db.commit()
                self._process(job_id)
            finally:
                lock_connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": GLOBAL_MATCHING_LOCK_ID},
                )

    def _process(self, job_id: int):
        heartbeat_stop = threading.Event()
        heartbeat = threading.Thread(
            target=self._heartbeat,
            args=(job_id, heartbeat_stop),
            name=f"matching-heartbeat-{job_id}",
            daemon=True,
        )
        heartbeat.start()
        try:
            with SessionLocal() as db:
                job = db.get(MatchingJob, job_id)
                if not job or job.status != "PROCESSING":
                    return
                StoreMatchingService(db).run_for_batch(
                    batch_id=job.batch_id,
                    project_id=job.project_id,
                    persist=True,
                )
                audit = AuditRunner(
                    project_id=job.project_id, batch_id=job.batch_id, db=db
                ).run()
                readiness = audit.get("results", {}).get("distribution_readiness")
                if not readiness:
                    raise RuntimeError("Readiness result was not generated")
                project = db.get(Project, job.project_id)
                if project and project.active_store_batch_id == job.batch_id:
                    project.trial_state = "COMPLETED"
                    project.trial_result_batch_id = job.batch_id
                job.status = "COMPLETED"
                job.finished_at = now()
                job.heartbeat_at = now()
                job.error_message = None
                db.commit()
        except Exception:
            logger.exception("Matching job %s failed", job_id)
            with SessionLocal() as db:
                job = db.get(MatchingJob, job_id)
                if job and job.status == "PROCESSING":
                    job.status = "FAILED"
                    job.finished_at = now()
                    job.error_message = "پردازش کامل نشد. لطفاً دوباره تلاش کنید."
                    project = db.get(Project, job.project_id)
                    if project and project.active_store_batch_id == job.batch_id:
                        project.trial_state = "FAILED"
                    db.commit()
        finally:
            heartbeat_stop.set()
            heartbeat.join(timeout=2)

    def _heartbeat(self, job_id: int, stop_event: threading.Event):
        while not stop_event.wait(settings.MATCHING_QUEUE_HEARTBEAT_SECONDS):
            try:
                with SessionLocal() as db:
                    job = db.scalar(
                        select(MatchingJob).where(
                            MatchingJob.id == job_id,
                            MatchingJob.status == "PROCESSING",
                        )
                    )
                    if not job:
                        return
                    job.heartbeat_at = now()
                    db.commit()
            except Exception:
                logger.exception("Matching job %s heartbeat failed", job_id)


matching_queue_worker = MatchingQueueWorker()
