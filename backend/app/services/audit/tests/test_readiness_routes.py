"""Readiness must never mutate matching state while viewing/recalculating."""

import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from starlette.requests import Request

from app.routers import project as routes
from app.services.audit.audit_runner import AuditRunner
from app.services.audit.tests.test_matching_readiness_contract import (
    _company, _evidence, _master,
)


@pytest.fixture
def page(monkeypatch):
    project = SimpleNamespace(id=23, name="Regression project")
    batch = SimpleNamespace(id=24, imported_rows=1000)
    summary = dict(total_candidates=999, processed=998, pending=1,
                   confirmed_matches=998)
    result = {
        "results": {"distribution_readiness": {
            "total_stores": 1000, "ready_stores": 962,
            "stores_with_coordinates": 970, "matched_to_master": 999,
            "stores_without_coordinates": 30,
        }},
        "map_geojson": {"type": "FeatureCollection", "features": []},
        "missing_coordinate_rows": [{"source_row": i} for i in range(30)],
    }
    db = Mock()
    for name in ("commit", "flush", "add", "add_all", "delete", "execute"):
        getattr(db, name).side_effect = AssertionError("Unexpected database write")
    matching = Mock(side_effect=AssertionError("Unexpected matching execution"))
    audit = Mock(return_value=SimpleNamespace(run=Mock(return_value=result)))
    monkeypatch.setattr(routes, "_get_project_or_404", lambda *_: project)
    monkeypatch.setattr(routes, "_find_latest_store_batch", lambda *_: batch)
    monkeypatch.setattr(routes, "_build_matching_database_summary", lambda *_: summary)
    monkeypatch.setattr(routes, "StoreMatchingService", matching)
    monkeypatch.setattr(routes, "AuditRunner", audit)
    monkeypatch.setattr(routes, "ReportBuilder", lambda: SimpleNamespace(build=lambda _: {}))
    monkeypatch.setattr(routes.templates, "TemplateResponse", lambda **kwargs: kwargs)
    request = Request({"type": "http", "method": "GET", "path": "/projects/23/readiness"})
    return SimpleNamespace(db=db, matching=matching, audit=audit, result=result,
                           summary=summary, batch=batch, request=request)


@pytest.mark.parametrize("processed", [0, 998, 999])
def test_get_never_runs_matching_or_writes_and_preserves_payload(page, processed):
    page.summary.update(processed=processed, pending=999 - processed)
    before = copy.deepcopy(page.result)
    for _ in range(2):
        response = routes.readiness_step(page.request, 23, page.db)
        context = response["context"]
        assert response["name"] == "projects/readiness.html"
        assert context["readiness_summary"] == before["results"]["distribution_readiness"]
        assert json.loads(context["map_geojson_json"]) == before["map_geojson"]
        assert context["audit_run"]["missing_coordinate_rows"] == before["missing_coordinate_rows"]
        assert context["matching_was_executed"] is False
    page.matching.assert_not_called()
    assert page.result == before
    assert not page.db.mock_calls


def test_refresh_recalculates_without_matching_or_writes(page):
    response = asyncio.run(routes.refresh_readiness(page.request, 23, page.db))
    assert response["context"]["readiness_summary"]["ready_stores"] == 962
    page.audit.assert_called_once_with(project_id=23, batch_id=24, db=page.db)
    page.matching.assert_not_called()
    assert not page.db.mock_calls


@pytest.mark.parametrize("empty_batch", [True, False])
def test_get_empty_batch_never_runs_matching(page, monkeypatch, empty_batch):
    if empty_batch:
        monkeypatch.setattr(routes, "_find_latest_store_batch", lambda *_: None)
    else:
        page.batch.imported_rows = 0
    response = routes.readiness_step(page.request, 23, page.db)
    assert response["context"]["report"] is None
    page.matching.assert_not_called()
    page.audit.assert_not_called()
    assert not page.db.mock_calls


def test_explicit_matching_keeps_legacy_post_and_redirect(page, monkeypatch):
    service = Mock()
    monkeypatch.setattr(routes, "StoreMatchingService", lambda db: service)
    async def form():
        return {}
    request = SimpleNamespace(form=form)
    response = asyncio.run(routes.process_readiness(request, 23, page.db))
    service.run_for_batch.assert_called_once_with(batch_id=24, project_id=23, persist=True)
    page.audit.assert_not_called()
    assert response.status_code == 303
    assert response.headers["location"] == "/projects/23/readiness"
    for path in ("/projects/{project_id}/readiness", "/projects/{project_id}/matching/rerun"):
        assert any(route.path == path and "POST" in route.methods
                   and route.endpoint is routes.process_readiness for route in routes.router.routes)


def test_audit_error_does_not_fall_back_to_matching(page):
    page.audit.return_value.run.side_effect = ValueError("audit failed")
    response = routes.readiness_step(page.request, 23, page.db)
    assert "audit failed" in response["context"]["audit_error"]
    page.matching.assert_not_called()
    page.db.commit.assert_not_called()


def test_real_audit_preserves_confirmed_master_and_selected_evidence(page, monkeypatch):
    company = _company(master_store_id=9001)
    company.match_status = "PRECISE"
    evidence = _evidence()
    evidence.is_selected = True
    evidence.matched_store_id = 9001
    evidence.is_processed = True
    master = _master()
    objects = (company, master, evidence)
    before = copy.deepcopy([vars(obj) for obj in objects])
    query = page.db.query.return_value
    for method in ("join", "outerjoin", "filter", "order_by"):
        getattr(query, method).return_value = query
    from app.repositories.store_dataset_repository import StoreDatasetRepository
    row = SimpleNamespace(id=1, row_number=1, snapshot=vars(company).copy())
    monkeypatch.setattr(StoreDatasetRepository, "audit_rows",
                        lambda *_: [(row, company, master, evidence)])
    monkeypatch.setattr(routes, "AuditRunner", AuditRunner)
    for action in (lambda: routes.readiness_step(page.request, 23, page.db),
                   lambda: asyncio.run(routes.refresh_readiness(page.request, 23, page.db))):
        response = action()
        assert response["context"]["audit_error"] is None
        assert response["context"]["readiness_summary"]["total_stores"] == 1
        assert [vars(obj) for obj in objects] == before
    page.matching.assert_not_called()
    for method in ("commit", "flush", "add", "add_all", "delete", "execute"):
        getattr(page.db, method).assert_not_called()


def test_readiness_template_keeps_map_missing_rows_and_distinct_forms(page):
    context = routes.readiness_step(page.request, 23, page.db)["context"]
    context["request"] = SimpleNamespace(url_for=lambda name, **kwargs: "/static/" + kwargs.get("path", ""))
    html = routes.templates.env.get_template("projects/readiness.html").render(context)
    assert 'id="readiness-map"' in html
    assert "فروشگاه‌های فاقد مختصات" in html
    assert "962" in html and "970" in html and "999" in html
    assert 'action="/projects/23/readiness/refresh"' in html
    assert 'action="/projects/23/matching/rerun"' in html
    assert 'href="/projects/23/decision"' in html
    assert any(route.path == "/projects/{project_id}/readiness/refresh"
               and route.methods == {"POST"} for route in routes.router.routes)


def test_matching_missing_batch_does_not_execute(page, monkeypatch):
    monkeypatch.setattr(routes, "_find_latest_store_batch", lambda *_: None)
    async def form():
        return {}
    with pytest.raises(routes.HTTPException) as error:
        asyncio.run(routes.process_readiness(SimpleNamespace(form=form), 23, page.db))
    assert error.value.status_code == 404
    page.matching.assert_not_called()
