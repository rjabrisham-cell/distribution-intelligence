"""Isolated SQL/state tests; heavy services and PostgreSQL lock I/O are mocked.

SQLite tests repository transitions; PostgreSQL locking SQL is compiled separately.
No project database or server is contacted.
"""
import threading
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Column, Index, MetaData, Table, create_engine, event, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, lazyload, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.matching_job import MatchingJob
from app.models.project import Project
from app.repositories.demo_access_repository import now
from app.repositories.matching_job_repository import MatchingJobRepository
from app.routers import project as routes
from app.services import matching_queue_service as queue


@pytest.fixture
def sessions():
    engine = create_engine('sqlite://', poolclass=StaticPool,
                           connect_args={'check_same_thread': False})
    metadata = MetaData()
    for model in (MatchingJob, Project):
        Table(model.__tablename__, metadata, *[
            Column(c.name, c.type, primary_key=c.primary_key, nullable=True,
                   server_default=c.server_default) for c in model.__table__.columns
        ])
    jobs = metadata.tables['matching_jobs']
    for name, fields in [('active_dataset', ['project_id', 'batch_id']),
                         ('active_account', ['account_id'])]:
        Index(name, *(jobs.c[f] for f in fields), unique=True,
              sqlite_where=text("status IN ('QUEUED', 'PROCESSING')"))
    metadata.create_all(engine)
    class QueueTestSession(Session):
        pass
    @event.listens_for(QueueTestSession, 'do_orm_execute')
    def skip_unrelated_relationships(state):
        if state.is_select:
            state.statement = state.statement.options(lazyload('*'))
    yield sessionmaker(bind=engine, class_=QueueTestSession, expire_on_commit=False)
    engine.dispose()


def add_job(db, n, status='QUEUED', result=None):
    db.add(Project(id=n, trial_owner_id=n, active_store_batch_id=n + 100,
                   trial_state='QUEUED'))
    job = MatchingJob(account_id=n, project_id=n, batch_id=n + 100,
                      status=status, attempt_count=0)
    if result is not None:
        job.audit_result = result
    db.add(job)
    db.commit()
    return job


def payload(project_id, batch_id):
    return {'project_id': project_id, 'batch_id': batch_id,
            'results': {'distribution_readiness': {'total_stores': 1, 'ready_stores': 1}},
            'map_geojson': {'type': 'FeatureCollection', 'features': []},
            'missing_coordinate_rows': []}


@pytest.fixture
def worker(monkeypatch, sessions):
    gate = threading.Lock()
    queries = []
    class Connection:
        def scalar(self, sql, params):
            queries.append(str(sql))
            return gate.acquire(blocking=False)
        def execute(self, sql, params):
            queries.append(str(sql))
            gate.release()
    @contextmanager
    def connect():
        yield Connection()
    monkeypatch.setattr(queue, 'engine', SimpleNamespace(connect=connect))
    monkeypatch.setattr(queue, 'SessionLocal', sessions)
    matching = Mock()
    audit = Mock(side_effect=lambda **kw: SimpleNamespace(
        run=lambda: payload(kw['project_id'], kw['batch_id'])))
    monkeypatch.setattr(queue, 'StoreMatchingService', lambda db: matching)
    monkeypatch.setattr(queue, 'AuditRunner', audit)
    instance = queue.MatchingQueueWorker()
    monkeypatch.setattr(instance, '_heartbeat', lambda *_: None)
    return SimpleNamespace(instance=instance, matching=matching, audit=audit,
                           gate=gate, queries=queries)


def test_fifo_positions_once_and_next_job_without_browser(sessions, worker):
    with sessions() as db:
        jobs = [add_job(db, n) for n in (1, 2, 3)]
        ids = [j.id for j in jobs]
    for position, expected in zip((3, 2, 1), ids):
        with sessions() as db:
            assert queue.queue_status(db, db.get(MatchingJob, ids[-1]))['queue_position'] == position
        worker.instance._run_once()
        with sessions() as db:
            completed = db.get(MatchingJob, expected)
            assert completed.status == 'COMPLETED'
            assert completed.attempt_count == 1
            assert completed.audit_result == payload(completed.project_id, completed.batch_id)
    worker.instance._run_once()
    assert [c.kwargs['batch_id'] for c in worker.matching.run_for_batch.call_args_list] == [101, 102, 103]
    assert worker.audit.call_count == 3
    assert all('pg_try_advisory_lock' in q or 'pg_advisory_unlock' in q for q in worker.queries)


def test_only_one_worker_processes_and_releases_lock(sessions, worker):
    with sessions() as db:
        add_job(db, 1)
        add_job(db, 2)
    entered, release = threading.Event(), threading.Event()
    def matching(**kw):
        entered.set()
        assert release.wait(3)
    worker.matching.run_for_batch.side_effect = matching
    thread = threading.Thread(target=worker.instance._run_once)
    thread.start()
    try:
        assert entered.wait(3)
        worker.instance._run_once()
        with sessions() as db:
            assert [j.status for j in db.scalars(select(MatchingJob).order_by(MatchingJob.id))] == ['PROCESSING', 'QUEUED']
        assert worker.matching.run_for_batch.call_count == 1
    finally:
        release.set()
        thread.join(3)
    assert not thread.is_alive() and not worker.gate.locked()


def test_processing_guard_and_stale_recovery(sessions, worker):
    with sessions() as db:
        active = add_job(db, 1, 'PROCESSING')
        active.heartbeat_at = now()
        add_job(db, 2)
    worker.instance._run_once()
    worker.matching.run_for_batch.assert_not_called()
    with sessions() as db:
        active = db.get(MatchingJob, 1)
        active.heartbeat_at = now() - timedelta(hours=1)
        db.commit()
    worker.instance._run_once()
    with sessions() as db:
        assert db.get(MatchingJob, 1).status == 'FAILED'
        assert db.get(MatchingJob, 2).status == 'COMPLETED'


def test_heartbeat_updates_only_processing_job(monkeypatch, sessions):
    with sessions() as db:
        job = add_job(db, 1, 'PROCESSING')
        job.heartbeat_at = now() - timedelta(hours=1)
        db.commit()
    monkeypatch.setattr(queue, 'SessionLocal', sessions)
    stop = Mock()
    stop.wait.side_effect = [False, True]
    queue.MatchingQueueWorker()._heartbeat(1, stop)
    with sessions() as db:
        job = db.get(MatchingJob, 1)
        assert job.heartbeat_at.replace(tzinfo=now().tzinfo) > now() - timedelta(seconds=5)
        assert MatchingJobRepository(db).fail_stale(90) == 0


def test_retry_deduplicates_and_unique_index(sessions):
    with sessions() as db:
        failed = add_job(db, 1, 'FAILED')
        repo = MatchingJobRepository(db)
        first = repo.enqueue(1, 1, 101)
        assert first.id != failed.id
        assert repo.enqueue(1, 1, 101).id == first.id
        db.commit()
        db.add(MatchingJob(account_id=1, project_id=1, batch_id=101, status='QUEUED', attempt_count=0))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_saved_result_is_scoped_and_never_uses_old_batch(sessions):
    with sessions() as db:
        job = add_job(db, 1, 'COMPLETED', payload(1, 101))
        repo = MatchingJobRepository(db)
        assert repo.readiness_result(1, 1, 101) == payload(1, 101)
        for keys in [(2, 1, 101), (1, 2, 101), (1, 1, 102)]:
            assert repo.readiness_result(*keys) is None
        job.audit_result = payload(1, 102)
        assert repo.readiness_result(1, 1, 101) is None
        job.audit_result = payload(1, 101)
        job.status = 'PROCESSING'
        assert repo.readiness_result(1, 1, 101) is None


def test_legacy_backfill_runs_only_audit_once(sessions, worker):
    with sessions() as db:
        add_job(db, 1, 'COMPLETED')
    worker.instance._run_once()
    worker.instance._run_once()
    worker.matching.run_for_batch.assert_not_called()
    assert worker.audit.call_count == 1
    with sessions() as db:
        assert db.get(MatchingJob, 1).audit_result == payload(1, 101)


@pytest.mark.parametrize('mismatch', ['account', 'batch'])
def test_wrong_owner_or_changed_batch_never_executes(sessions, worker, mismatch):
    with sessions() as db:
        add_job(db, 1)
        project = db.get(Project, 1)
        if mismatch == 'account': project.trial_owner_id = 2
        else: project.active_store_batch_id = 102
        db.commit()
    worker.instance._run_once()
    worker.matching.run_for_batch.assert_not_called()
    worker.audit.assert_not_called()
    with sessions() as db:
        assert db.get(MatchingJob, 1).status == 'FAILED'


def test_completed_api_redirect_and_repeated_http_views(sessions, worker, monkeypatch):
    with sessions() as db:
        add_job(db, 1)
    worker.instance._run_once()
    app = FastAPI()
    app.mount('/static', StaticFiles(directory=Path(__file__).resolve().parents[3] / 'static'), name='static')
    app.include_router(routes.router)
    def database():
        with sessions() as db:
            db.info['trial_account_id'] = 1
            yield db
    app.dependency_overrides[get_db] = database
    monkeypatch.setattr(routes, '_get_project_or_404', lambda db, pid: db.get(Project, pid))
    monkeypatch.setattr(routes, '_find_latest_store_batch', lambda db, pid: SimpleNamespace(id=db.get(Project, pid).active_store_batch_id, imported_rows=1))
    monkeypatch.setattr(routes, '_build_matching_database_summary', lambda *_: {'total_candidates': 1, 'pending': 0})
    monkeypatch.setattr(routes, 'AuditRunner', Mock(side_effect=AssertionError('HTTP must not audit')))
    monkeypatch.setattr(routes, 'StoreMatchingService', Mock(side_effect=AssertionError('HTTP must not match')))
    client = TestClient(app, follow_redirects=False)
    response = client.get('/projects/api/1/matching/status')
    assert response.status_code == 200
    assert response.json()['redirect_url'] == '/projects/1/readiness'
    assert response.json()['queue_position'] is None
    response = client.get('/projects/1/matching/status')
    assert response.status_code == 303 and response.headers['location'] == '/projects/1/readiness'
    for _ in range(3):
        response = client.get('/projects/1/readiness')
        assert response.status_code == 200 and 'readiness-map' in response.text
        assert client.post('/projects/1/readiness/refresh').status_code == 200
    assert worker.audit.call_count == worker.matching.run_for_batch.call_count == 1
    with sessions() as db:
        db.get(Project, 1).active_store_batch_id = 102
        db.commit()
    response = client.get('/projects/1/readiness')
    assert response.status_code == 200
    assert worker.audit.call_count == 1


@pytest.mark.parametrize('status', ['QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED'])
def test_queue_template_and_no_script_fallback(status, sessions):
    from html.parser import HTMLParser
    class Tags(HTMLParser):
        def __init__(self): super().__init__(); self.tags = []
        def handle_starttag(self, tag, attrs): self.tags.append((tag, dict(attrs)))
    with sessions() as db:
        job = add_job(db, 1, status)
        data = queue.queue_status(db, job)
    html = routes.templates.env.get_template('projects/matching_status.html').render(
        public_demo=True, project_context={'id': 1}, queue=data)
    tags = Tags(); tags.feed(html)
    position = next(a for t, a in tags.tags if a.get('id') == 'mq-position-card')
    assert ('hidden' not in position) == (status == 'QUEUED')
    assert (data['queue_position'] is not None) == (status == 'QUEUED')
    assert data['eta_minutes'] is None
    assert any(t == 'meta' and a.get('http-equiv') == 'refresh' for t, a in tags.tags) == (status in ['QUEUED', 'PROCESSING'])
    assert 'در حال پردازش' in html
    assert 'معمولاً چند دقیقه' not in html
    retry = next(a for t, a in tags.tags if a.get('id') == 'mq-retry')
    assert ('hidden' not in retry) == (status == 'FAILED')


def test_postgresql_claim_sql_preserves_skip_locked_and_fifo():
    db = Mock()
    db.scalar.return_value = None
    MatchingJobRepository(db).claim_next()
    sql = str(db.scalar.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert 'ORDER BY matching_jobs.id ASC' in sql and 'FOR UPDATE SKIP LOCKED' in sql


def test_audit_failure_never_publishes_and_next_job_runs(sessions, worker):
    with sessions() as db:
        add_job(db, 1)
        add_job(db, 2)
    worker.audit.side_effect = [ValueError('synthetic failure'),
                               SimpleNamespace(run=lambda: payload(2, 102))]
    worker.instance._run_once()
    worker.instance._run_once()
    with sessions() as db:
        failed = db.get(MatchingJob, 1)
        assert failed.status == 'FAILED' and failed.audit_result is None
        assert db.get(MatchingJob, 2).status == 'COMPLETED'
    assert worker.matching.run_for_batch.call_count == 2


def test_legacy_backfill_skips_obsolete_batch_and_preserves_fifo(sessions, worker):
    with sessions() as db:
        add_job(db, 1, 'COMPLETED')
        db.get(Project, 1).active_store_batch_id = 999
        add_job(db, 2, 'COMPLETED')
        add_job(db, 3)
    worker.instance._run_once()
    assert worker.audit.call_args.kwargs['project_id'] == 3
    worker.instance._run_once()
    assert worker.audit.call_args.kwargs['project_id'] == 2
    worker.instance._run_once()
    assert worker.audit.call_count == 2
    assert worker.matching.run_for_batch.call_count == 1


def test_batch_change_during_audit_does_not_publish(sessions, worker):
    with sessions() as db:
        add_job(db, 1)
    def audit(**kwargs):
        def run():
            with sessions() as other:
                other.get(Project, 1).active_store_batch_id = 102
                other.commit()
            return payload(1, 101)
        return SimpleNamespace(run=run)
    worker.audit.side_effect = audit
    worker.instance._run_once()
    with sessions() as db:
        job = db.get(MatchingJob, 1)
        assert job.status == 'FAILED' and job.audit_result is None
