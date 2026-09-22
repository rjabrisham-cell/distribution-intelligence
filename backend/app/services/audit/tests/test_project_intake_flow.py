"""Project creation/intake HTTP tests with mocked services and no database I/O."""
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.routers import project as routes


SUCCESS = "پروژه با موفقیت ایجاد شد. اکنون فایل فروشگاه‌ها را بارگذاری کنید."


@pytest.fixture
def flow(monkeypatch):
    project = SimpleNamespace(id=73, name='Synthetic project', status='draft')
    db = Mock()
    service = Mock()
    service.create.return_value = project
    monkeypatch.setattr(routes, 'TrialService', lambda _: service)
    monkeypatch.setattr(routes, '_get_project_or_404', lambda *_: project)
    files = Mock()
    files.get_by_entity.return_value = []
    monkeypatch.setattr(routes, 'FileService', lambda _: files)
    app = FastAPI()
    app.include_router(routes.router)
    app.mount('/static', StaticFiles(directory=Path(__file__).resolve().parents[3] / 'static'), name='static')
    app.dependency_overrides[get_db] = lambda: db
    @app.middleware('http')
    async def authenticated_account(request, call_next):
        request.state.demo_account_id = 11
        return await call_next(request)
    with TestClient(app, follow_redirects=False) as client:
        yield client, service
    assert not db.mock_calls


@pytest.mark.parametrize('optional', [{}, {'code': '', 'description': ''},
                                     {'code': 'PRJ-73', 'description': 'Small test'}])
def test_create_redirects_directly_to_intake(flow, optional):
    client, service = flow
    response = client.post('/projects/new', data={'name': 'Synthetic project', **optional})
    assert response.status_code == 303
    assert response.headers['location'] == '/projects/73/intake?created=1'
    service.create.assert_called_once_with(11, 'Synthetic project',
                                            optional.get('description') or None,
                                            optional.get('code') or None)


def test_name_stays_required(flow):
    client, service = flow
    assert client.post('/projects/new', data={'code': 'optional'}).status_code == 422
    service.create.assert_not_called()


@pytest.mark.parametrize('query,visible', [('?created=1', True), ('', False), ('?created=0', False)])
def test_intake_banner_only_on_creation(flow, query, visible):
    response = flow[0].get('/projects/73/intake' + query)
    assert response.status_code == 200
    assert (SUCCESS in response.text) is visible
    assert 'css/intake.css' in response.text
    assert ('id="dip-created-banner"' in response.text) is visible
    if visible:
        assert 'history.replaceState' in response.text
        assert "url.searchParams.delete('created')" in response.text
        assert 'setTimeout(dismiss, 7000)' in response.text


def test_standalone_project_page_remains_available(flow):
    response = flow[0].get('/projects/73')
    assert response.status_code == 200
    assert 'Synthetic project' in response.text
    assert 'href="/projects/73/intake"' in response.text
    assert SUCCESS not in response.text


def test_optional_fields_are_in_closed_native_details(flow):
    class FormParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.details = False
            self.fields = {}
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'details':
                assert 'open' not in attrs
                self.details = True
            if tag in ('input', 'textarea'):
                self.fields[attrs.get('name')] = (attrs, self.details)
        def handle_endtag(self, tag):
            if tag == 'details': self.details = False
    response = flow[0].get('/projects/new')
    assert response.status_code == 200
    parser = FormParser()
    parser.feed(response.text)
    assert 'required' in parser.fields['name'][0]
    assert not parser.fields['name'][1]
    for name in ('code', 'description'):
        attrs, collapsed = parser.fields[name]
        assert collapsed and 'required' not in attrs
    assert 'ایجاد پروژه و دریافت داده' in response.text
    assert 'اطلاعات تکمیلی (اختیاری)' in response.text
