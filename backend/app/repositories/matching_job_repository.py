from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.matching_job import MatchingJob
from app.repositories.demo_access_repository import now


ACTIVE_STATUSES = ("QUEUED", "PROCESSING")


class MatchingJobRepository:
    def __init__(self, db):
        self.db = db

    def latest(self, account_id: int, project_id: int, batch_id: int | None = None):
        query = select(MatchingJob).where(
            MatchingJob.account_id == account_id,
            MatchingJob.project_id == project_id,
        )
        if batch_id is not None:
            query = query.where(MatchingJob.batch_id == batch_id)
        return self.db.scalar(query.order_by(MatchingJob.id.desc()).limit(1))

    def active(self, account_id: int, project_id: int, batch_id: int):
        return self.db.scalar(
            select(MatchingJob)
            .where(
                MatchingJob.account_id == account_id,
                MatchingJob.project_id == project_id,
                MatchingJob.batch_id == batch_id,
                MatchingJob.status.in_(ACTIVE_STATUSES),
            )
            .order_by(MatchingJob.id.desc())
            .limit(1)
        )

    def active_for_account(self, account_id: int):
        return self.db.scalar(
            select(MatchingJob)
            .where(
                MatchingJob.account_id == account_id,
                MatchingJob.status.in_(ACTIVE_STATUSES),
            )
            .order_by(MatchingJob.id.desc())
            .limit(1)
        )

    def enqueue(self, account_id: int, project_id: int, batch_id: int):
        existing = self.active(account_id, project_id, batch_id)
        if existing:
            return existing
        account_job = self.active_for_account(account_id)
        if account_job:
            return account_job
        job = MatchingJob(
            account_id=account_id,
            project_id=project_id,
            batch_id=batch_id,
            status="QUEUED",
        )
        self.db.add(job)
        try:
            self.db.flush()
            return job
        except IntegrityError:
            self.db.rollback()
            existing = self.active(account_id, project_id, batch_id)
            if existing:
                return existing
            raise

    def jobs_ahead(self, job: MatchingJob) -> int:
        return int(
            self.db.scalar(
                select(func.count(MatchingJob.id)).where(
                    MatchingJob.id < job.id,
                    MatchingJob.status.in_(ACTIVE_STATUSES),
                )
            )
            or 0
        )

    def typical_duration_seconds(self) -> int | None:
        rows = self.db.execute(
            select(MatchingJob.started_at, MatchingJob.finished_at)
            .where(
                MatchingJob.status == "COMPLETED",
                MatchingJob.started_at.is_not(None),
                MatchingJob.finished_at.is_not(None),
            )
            .order_by(MatchingJob.id.desc())
            .limit(20)
        ).all()
        durations = sorted(
            int((finished - started).total_seconds())
            for started, finished in rows
            if finished > started
        )
        if not durations:
            return None
        middle = len(durations) // 2
        return durations[middle] if len(durations) % 2 else (
            durations[middle - 1] + durations[middle]
        ) // 2

    def claim_next(self):
        job = self.db.scalar(
            select(MatchingJob)
            .where(MatchingJob.status == "QUEUED")
            .order_by(MatchingJob.id.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not job:
            return None
        timestamp = now()
        job.status = "PROCESSING"
        job.started_at = timestamp
        job.heartbeat_at = timestamp
        job.finished_at = None
        job.error_message = None
        job.attempt_count += 1
        self.db.flush()
        return job

    def processing_exists(self) -> bool:
        return bool(
            self.db.scalar(
                select(MatchingJob.id)
                .where(MatchingJob.status == "PROCESSING")
                .limit(1)
            )
        )

    def fail_stale(self, seconds: int) -> int:
        cutoff = now() - timedelta(seconds=seconds)
        jobs = self.db.scalars(
            select(MatchingJob)
            .where(
                MatchingJob.status == "PROCESSING",
                MatchingJob.heartbeat_at < cutoff,
            )
            .with_for_update(skip_locked=True)
        ).all()
        for job in jobs:
            job.status = "FAILED"
            job.finished_at = now()
            job.error_message = (
                "پردازش به دلیل توقف سرویس کامل نشد. می‌توانید دوباره تلاش کنید."
            )
        return len(jobs)
