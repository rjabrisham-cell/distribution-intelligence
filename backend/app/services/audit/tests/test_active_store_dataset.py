"""Integration tests: run only against the explicitly isolated PostgreSQL database."""
import asyncio
import csv
import io
import os
from pathlib import Path
from uuid import uuid4
from types import SimpleNamespace

import pytest
from fastapi import UploadFile
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.config import settings
from app.models import Base, Account, Company, Project, File, ImportBatch, CompanyStore
from app.models.import_store_row import ImportStoreRow
from app.repositories.store_dataset_repository import StoreDatasetRepository
from app.routers import project as routes
from app.schemas.import_schema import ImportStartRequest, EntityTypeEnum
from app.services.audit.audit_runner import AuditRunner
from app.services.file_service import FileService
from app.services.import_service import ImportService
from app.services.store_matching_service import StoreMatchingService


@pytest.fixture
def db():
    url = os.environ.get("DIP_DATASET_TEST_URL")
    if not url:
        pytest.skip("Requires explicit isolated DIP_DATASET_TEST_URL")
    parsed = make_url(url)
    if parsed.host != "dip-m21-db" or parsed.database != "dip_m21_test":
        pytest.fail("Refusing a database other than the isolated milestone test database")
    engine = create_engine(url, execution_options={"schema_translate_map": {None: "dataset_contract"}})
    # Historical migrations omit existing ORM columns. Exercise the application
    # contract separately; the migration chain is tested in the public schema.
    with engine.begin() as setup:
        setup.execute(text("CREATE SCHEMA IF NOT EXISTS dataset_contract"))
        Base.metadata.create_all(setup)
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()
    engine.dispose()


@pytest.fixture
def project(db, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    account = Account(mobile=uuid4().hex[:20])
    db.add(account)
    db.flush()
    company = Company(account_id=account.id, name="Synthetic company")
    db.add(company)
    db.flush()
    project = Project(company_id=company.id, name="Synthetic dataset regression")
    db.add(project)
    db.commit()
    return project


def import_rows(db, project, rows, name="input.csv"):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    payload = io.BytesIO(stream.getvalue().encode("utf-8"))
    if name.endswith(".xlsx"):
        from openpyxl import Workbook
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(list(rows[0]))
        for item in rows:
            sheet.append(list(item.values()))
        payload = io.BytesIO()
        workbook.save(payload)
        payload.seek(0)
    upload = UploadFile(filename=name, file=payload)
    file = asyncio.run(FileService(db).upload(entity_type="PROJECT", entity_id=project.id,
                                             category="stores", upload_file=upload))
    service = ImportService(db)
    started = service.start_import(ImportStartRequest(entity_type=EntityTypeEnum.STORE,
                                                     file_id=file.id), file.file_path)
    service.process_batch(started.batch_id)
    batch = db.get(ImportBatch, started.batch_id)
    assert batch.imported_rows == len(rows)
    assert StoreDatasetRepository(db).active_batch(project.id).id == batch.id
    return file, batch, service


def row(name="Store B", code="", address="Tehran synthetic street", latitude=35.7, longitude=51.4):
    return dict(name=name, store_code=code, address=address, phone="02112345678",
                latitude=latitude, longitude=longitude)


def audit(db, project, batch):
    return AuditRunner(project.id, batch.id, db).run()


@pytest.mark.parametrize("filename", ["input.csv", "input.xlsx"])
def test_first_upload_has_exactly_1000_rows(db, project, filename):
    _, batch, _ = import_rows(db, project, [row(name=f"Store {i}") for i in range(1000)], filename)
    StoreMatchingService(db).run_for_batch(batch.id, project.id)
    result = audit(db, project, batch)
    assert result["audited_store_count"] == 1000
    assert len(result["map_geojson"]["features"]) == 1000


def test_upload_a_remove_upload_b_preserves_history_and_scopes_all_views(db, project):
    file_a, batch_a, _ = import_rows(db, project, [row("Historical A")])
    StoreMatchingService(db).run_for_batch(batch_a.id, project.id)
    a_ids = {r.company_store_id for r in StoreDatasetRepository(db).rows(batch_a.id)}
    assert FileService(db).delete_file(file_a.id)
    assert Path(file_a.file_path).exists()
    assert db.get(File, file_a.id).removed_at is not None
    assert db.get(ImportBatch, batch_a.id) is not None
    assert StoreDatasetRepository(db).active_batch(project.id) is None
    file_b, batch_b, _ = import_rows(db, project, [row(), row("Missing B", address="", latitude="", longitude="")])
    StoreMatchingService(db).run_for_batch(batch_b.id, project.id)
    result = audit(db, project, batch_b)
    assert result["audited_store_count"] == 2
    assert len(result["map_geojson"]["features"]) == 1
    assert len(result["missing_coordinate_rows"]) == 1
    assert all(f["properties"]["company_store_id"] not in a_ids for f in result["map_geojson"]["features"])
    assert audit(db, project, batch_a)["audited_store_count"] == 0
    assert len(StoreDatasetRepository(db).rows(batch_a.id)) == 1
    assert routes._find_latest_store_batch(db, project.id).id == batch_b.id
    assert [f.id for f in FileService(db).get_by_entity(entity_type="PROJECT", entity_id=project.id)] == [file_b.id]
    with pytest.raises(ValueError, match="active store dataset"):
        StoreMatchingService(db).run_for_batch(batch_a.id, project.id)


def test_shared_store_across_batches_does_not_accumulate_and_keeps_snapshot(db, project):
    _, a, _ = import_rows(db, project, [row("Previous", code="shared")])
    _, b, _ = import_rows(db, project, [row("Current", code="shared", latitude="", longitude="")])
    repo = StoreDatasetRepository(db)
    assert repo.rows(a.id)[0].company_store_id == repo.rows(b.id)[0].company_store_id
    assert repo.rows(a.id)[0].snapshot["name"] == "Previous"
    assert db.get(CompanyStore, repo.rows(a.id)[0].company_store_id).name == "Previous"
    result = audit(db, project, b)
    assert result["audited_store_count"] == 1
    assert result["map_geojson"]["features"] == []
    assert len(result["missing_coordinate_rows"]) == 1


def test_removing_active_does_not_reactivate_previous_batch(db, project):
    _, a, _ = import_rows(db, project, [row("A")])
    file_b, b, service = import_rows(db, project, [row("B")])
    FileService(db).delete_file(file_b.id)
    assert StoreDatasetRepository(db).active_batch(project.id) is None
    assert audit(db, project, a)["audited_store_count"] == 0
    with pytest.raises(Exception, match="not found|available"):
        service.process_batch(b.id)
    assert StoreDatasetRepository(db).active_batch(project.id) is None


def test_missing_address_membership_and_retry_are_idempotent(db, project):
    _, batch, service = import_rows(db, project, [row(address="", latitude="", longitude="")])
    before = db.query(CompanyStore).count()
    completed_at = batch.completed_at
    service.process_batch(batch.id)
    assert db.query(CompanyStore).count() == before
    assert batch.completed_at == completed_at
    rows = StoreDatasetRepository(db).rows(batch.id)
    assert len(rows) == 1
    assert rows[0].row_number == 1
    assert audit(db, project, batch)["missing_coordinate_rows"][0]["source_row"] == 1


@pytest.mark.parametrize("legacy", [True, False])
def test_get_pages_are_read_only_and_null_dataset_renders(db, project, monkeypatch, legacy):
    if not legacy:
        import_rows(db, project, [row()])
    request = Request({"type": "http", "method": "GET", "path": "/", "router": routes.router})
    monkeypatch.setattr(routes.templates, "TemplateResponse", lambda **kw: kw)
    statements = []
    def check(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)
        assert not statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "ALTER", "CREATE"))
    event.listen(db.bind, "before_cursor_execute", check)
    def forbid(*args, **kwargs):
        raise AssertionError("GET must not write or execute Matching")
    monkeypatch.setattr(db, "commit", forbid)
    monkeypatch.setattr(db, "flush", forbid)
    monkeypatch.setattr(routes, "StoreMatchingService", forbid)
    try:
        for endpoint in (routes.validation_step, routes.readiness_step):
            with db.no_autoflush:
                context = endpoint(request, project.id, db)["context"]
            assert (context["batch"] is None) == legacy
            if legacy:
                assert "Dataset" in context["message"]
            context["request"] = SimpleNamespace(url_for=lambda *a, **kw: "/static/" + kw.get("path", ""))
            template = "projects/validation.html" if endpoint is routes.validation_step else "projects/readiness.html"
            html = routes.templates.env.get_template(template).render(context)
            if legacy:
                assert "Dataset" in html
    finally:
        event.remove(db.bind, "before_cursor_execute", check)
    assert statements


def test_completed_historical_import_cannot_reactivate_after_removal(db, project):
    _, a, service_a = import_rows(db, project, [row("A")])
    file_b, b, _ = import_rows(db, project, [row("B")])
    FileService(db).delete_file(file_b.id)
    completed_at = a.completed_at
    service_a.process_batch(a.id)
    assert a.completed_at == completed_at
    assert StoreDatasetRepository(db).active_batch(project.id) is None


def test_unrelated_file_deletion_retains_existing_behavior(db, project):
    service = FileService(db)
    file = asyncio.run(service.upload(entity_type="PROJECT", entity_id=project.id,
                                     category="other", upload_file=UploadFile(
                                         filename="synthetic.txt", file=io.BytesIO(b"test"))))
    path = Path(file.file_path)
    assert service.delete_file(file.id)
    assert not path.exists()
    assert db.get(File, file.id) is None


def test_batch_row_uniqueness_rejects_duplicate_membership(db, project):
    from sqlalchemy.exc import IntegrityError
    _, batch, _ = import_rows(db, project, [row()])
    repo = StoreDatasetRepository(db)
    original = repo.rows(batch.id)[0]
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            repo.record(batch.id, original.company_store_id, original.row_number, {})
    assert len(repo.rows(batch.id)) == 1


def test_matching_and_summary_exclude_evidence_without_exact_membership(db, project):
    from app.models.address_candidate import AddressCandidate
    _, a, _ = import_rows(db, project, [row("Old A")])
    _, b, _ = import_rows(db, project, [row("Current B")])
    repo = StoreDatasetRepository(db)
    orphan = AddressCandidate(company_store_id=repo.rows(a.id)[0].company_store_id,
                              source_type="excel", source_id=f"import_batch:{b.id}:row:999",
                              address_text="Synthetic orphan")
    db.add(orphan)
    db.commit()
    assert repo.candidate_query(b.id).count() == 1
    StoreMatchingService(db).run_for_batch(b.id, project.id)
    assert not orphan.is_processed
    assert audit(db, project, b)["audited_store_count"] == 1
