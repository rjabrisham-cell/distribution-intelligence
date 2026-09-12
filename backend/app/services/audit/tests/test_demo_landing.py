import asyncio
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.core.templates import templates
from app.routers import home, project
from app.services.audit.tests.test_readiness_routes import page


def test_landing_value_and_cta_destinations():
    request = SimpleNamespace(url_for=lambda *a, **kw: "/static/" + kw.get("path", ""))
    html = templates.env.get_template("index.html").render(request=request)
    assert "داده خام شبکه پخش‌تان را به داده‌ای قابل اعتماد و آماده تصمیم‌گیری تبدیل کنید" in html
    assert 'href="/demo/sample"' in html
    assert html.count('href="/demo/trial"') == 2
    for label in ("دریافت داده", "اعتبارسنجی", "تطبیق", "سنجش آمادگی", "نقشه و گزارش"):
        assert label in html
    assert "چه چیزی تحویل می‌گیرید؟" in html


def test_sample_reuses_readonly_readiness_and_hides_write_actions(page, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_SAMPLE_PROJECT_ID", 23)
    monkeypatch.setattr(home.templates, "TemplateResponse", lambda **kw: kw)
    original = project.readiness_step
    monkeypatch.setattr(project, "readiness_step", lambda *a: SimpleNamespace(context=original(*a)["context"]))
    page.db.no_autoflush = nullcontext()
    response = home.demo_sample(page.request, page.db)
    context = response["context"]
    context["request"] = SimpleNamespace(url_for=lambda *a, **kw: "/static/" + kw.get("path", ""))
    html = templates.env.get_template("projects/readiness.html").render(context)
    assert context["demo_sample"] is True
    assert 'id="readiness-map"' in html
    assert 'method="post"' not in html.lower()
    assert "/matching/rerun" not in html
    assert "/readiness/refresh" not in html
    assert "/projects/23/decision" not in html
    assert "962" in html
    page.matching.assert_not_called()
    page.db.commit.assert_not_called()
    page.db.flush.assert_not_called()


def test_sample_requires_explicit_public_project(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_SAMPLE_PROJECT_ID", 0)
    db = Mock()
    with pytest.raises(HTTPException) as error:
        home.demo_sample(Mock(), db)
    assert error.value.status_code == 503
    assert not db.mock_calls


def test_trial_uses_existing_onboarding_and_preserves_existing_routes():
    response = home.demo_trial()
    assert response.status_code == 303
    assert response.headers["location"] == "/demo/login"
    from app.main import app
    paths = {path.rstrip("/") or "/" for path in app.openapi()["paths"]}
    assert {"/", "/dashboard", "/projects", "/projects/new", "/demo/trial", "/demo/sample"} <= paths
    sample = next(route for route in home.router.routes if route.path == "/demo/sample")
    assert sample.methods == {"GET"}
