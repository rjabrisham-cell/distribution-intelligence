"""Fail-closed HTTP boundary for public demo and owner-scoped trial routes."""
import hmac
import os
import re
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.trial_policy import policy
from app.repositories.demo_access_repository import DemoAccessRepository, digest
from app.core.demo_logging import trial_request
from app.core.web_errors import error_response, wants_html


PUBLIC = {"/", "/contact", "/about", "/demo/sample", "/demo/trial", "/demo/login", "/demo/access", "/health"}
HISTORY_ASSETS = {
    "/static/data/history/kaleh/history-summary.json",
    "/static/data/history/kaleh/legacy-regions.geojson",
    "/static/data/history/kaleh/planned-routes.geojson",
    "/static/data/history/kaleh/gps-tracks.geojson",
    "/static/data/history/kaleh/smart-regions.geojson",
    "/static/data/history/kaleh/smart-summary.json",
    "/static/data/history/kaleh/municipal-regions.geojson",
    "/static/data/history/kaleh/operation-tracks.geojson",
    "/static/data/history/kaleh/transit-tracks.geojson",
    "/static/data/history/kaleh/access-routes.geojson",
    "/static/data/history/kaleh/gps-continuity.geojson",
    "/static/data/history/kaleh/calendar/index.json",
    "/static/data/history/kaleh/calendar/2010-04-21-regions.geojson",
    "/static/data/history/kaleh/calendar/2010-04-22-regions.geojson",
    "/static/data/history/kaleh/calendar/2010-04-24-regions.geojson",
    "/static/data/history/kaleh/calendar/2010-04-25-regions.geojson",
    "/static/data/history/kaleh/calendar/2010-04-21-operations.geojson",
    "/static/data/history/kaleh/calendar/2010-04-22-operations.geojson",
    "/static/data/history/kaleh/calendar/2010-04-24-operations.geojson",
    "/static/data/history/kaleh/calendar/2010-04-25-operations.geojson",
}
HISTORY_ASSETS.update(
    f"/static/data/history/kaleh/calendar/{day}{suffix}"
    for day in (
        "2010-04-20", "2010-04-21", "2010-04-22", "2010-04-24",
        "2010-04-25", "2010-04-26", "2010-04-28", "2010-04-29",
        "2010-05-02", "2010-05-03", "2010-05-04", "2010-05-05",
        "2010-05-06", "2010-05-08", "2010-05-09", "2010-05-10",
    )
    for suffix in (".geojson", "-access.geojson")
)
SAFE = {"GET", "HEAD"}


def target(path):
    """Every enabled trial operation has an explicit resource boundary."""
    if path in {"/projects", "/projects/grid", "/projects/new", "/projects/api", "/demo/logout"}:
        return "account", None
    for kind, pattern in [
        ("project", r"/projects/(?:api/)?(\d+)(?:/(?:intake|validation|readiness(?:/refresh)?|matching/(?:rerun|status|retry)|decision|distribution|results|profiling|scenario-compare))?"),
        ("project", r"/uploads/project/(\d+)"),
        ("project", r"/demo/result/(\d+)/ack"),
        ("file", r"/(?:files|uploads/file)/(\d+)/(?:download|delete)"),
        ("batch", r"/import/(?:api/)?batches/(\d+)"),
    ]:
        match = re.fullmatch(pattern, path)
        if match:
            return kind, int(match[1])
    if path == "/geography/provinces" or re.fullmatch(r"/geography/cities/\d+", path) or path in {"/import/template/store", "/static/templates/stores_template.xlsx"}:
        return "account", None
    return None, None


class DemoSecurityMiddleware:
    def __init__(self, app, engine=None, raise_errors=False):
        self.app, self.engine, self.raise_errors = app, engine, raise_errors

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"].rstrip("/") or "/"
        method = scope["method"]
        request = Request(scope, receive)

        async def secured_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-content-type-options", b"nosniff"), (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"same-origin"),
                    (b"content-security-policy", b"frame-ancestors 'none'; object-src 'none'; base-uri 'self'"),
                    (b"cache-control", b"no-store"),
                ]
            await send(message)

        async def reject(status, message="دسترسی مجاز نیست."):
            await error_response(request, status, message)(scope, receive, secured_send)

        # Only code assets are public. Raw uploads and arbitrary static files are not.
        static = re.fullmatch(r"/static/(?:css|js|images|fonts)/[\w/.-]+\.(?:css|js|png|svg|jpg|jpeg|ico|woff2?|ttf)", path)
        if (static and ".." not in path or path == "/static/logo/DIPLogo.webp" or path in HISTORY_ASSETS) and method in SAFE:
            return await self.app(scope, receive, secured_send)
        public = path in PUBLIC or (path in {"/demo/otp/request", "/demo/otp/verify"} and settings.APP_ENV == "development" and os.getenv("DEMO_ACCESS_MODE") == "otp")
        if public and method in SAFE:
            return await self.app(scope, receive, secured_send)
        kind, resource_id = target(path)
        if not public and kind is None:
            return await reject(404)
        if method == "DELETE":
            return await reject(403)  # Trial history and consumed entitlement cannot be erased.
        token = request.cookies.get("dip_session", "")
        if not public and not token:
            if method in SAFE:
                return await RedirectResponse("/demo/login", status_code=303)(scope, receive, secured_send)
            return await reject(401)

        # Bound request memory before multipart parsing (including chunked uploads).
        body = b""
        if method not in SAFE:
            async for chunk in request.stream():
                body += chunk
                if len(body) > policy.file_bytes + 65536:
                    return await reject(413, "حجم فایل بیش از حد مجاز است.")
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        # Origin plus synchronizer token for authenticated writes; double-submit
        # pre-auth token prevents login CSRF. Never trust X-Forwarded-For here.
        if method not in SAFE:
            origin = request.headers.get("origin")
            if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
                return await reject(403)
            form_request = Request(scope, replay)
            try:
                form = await form_request.form(max_files=1, max_fields=20)
                csrf = request.headers.get("x-csrf-token") or str(form.get("csrf_token", ""))
                await form.close()
            except Exception:
                return await reject(400, "درخواست نامعتبر است.")
            delivered = False
            if public:
                expected = request.cookies.get("dip_login_csrf", "")
                if not expected or not hmac.compare_digest(expected, csrf):
                    return await reject(403)

        from app.core.database import engine as default_engine
        engine = self.engine or default_engine
        with engine.connect() as connection:
            transaction = connection.begin()
            with Session(bind=connection, join_transaction_mode="create_savepoint", autoflush=False) as db:
                log_token = trial_request.set(True)
                repo = DemoAccessRepository(db)
                scope.setdefault("state", {})["demo_db"] = db
                committed = False
                try:
                    if not public:
                        session = repo.session(token)
                        account = repo.verified_account(session.account_id) if session else None
                        if not account:
                            return await reject(401, "دوباره وارد شوید.")
                        if method not in SAFE:
                            if not hmac.compare_digest(session.csrf_hash, digest(csrf)):
                                return await reject(403)
                            if not repo.lock("trial:" + str(account.id)):
                                return await reject(409, "یک عملیات در حال اجراست.")
                            # Count rejected uploads too, outside the business transaction.
                            with engine.begin() as rate_connection:
                                with Session(bind=rate_connection, join_transaction_mode="create_savepoint") as rate_db:
                                    rate_repo = DemoAccessRepository(rate_db)
                                    allowed = rate_repo.rate("write:" + str(account.id), policy.write_limit, policy.write_window_seconds)
                                    rate_db.commit()
                            if not allowed:
                                return await reject(429, "کمی بعد دوباره تلاش کنید.")
                        scope["state"]["demo_account_id"] = account.id
                        scope["state"]["demo_session"] = session
                        db.info["trial_account_id"] = account.id
                        project_id = resource_id
                        if kind == "file":
                            project_id = repo.file_project_id(resource_id)
                        elif kind == "batch":
                            project_id = repo.batch_project_id(resource_id)
                        if kind != "account":
                            project = repo.owned_project(account.id, project_id)
                            if not project or project.id == settings.DEMO_SAMPLE_PROJECT_ID:
                                return await reject(404)
                            scope["state"]["demo_project"] = project
                    status = 500
                    messages = []

                    async def capture(message):
                        nonlocal status
                        if message["type"] == "http.response.start":
                            status = message["status"]
                        messages.append(message)

                    await self.app(scope, replay if method not in SAFE else receive, capture)
                    if status >= 400 and (wants_html(request) or status >= 500):
                        start = next((m for m in messages if m['type'] == 'http.response.start'), {})
                        headers = dict(start.get('headers', []))
                        if b'application/json' in headers.get(b'content-type', b''):
                            import json
                            try:
                                payload = json.loads(b''.join(m.get('body', b'') for m in messages))
                                detail = payload.get('detail') if isinstance(payload, dict) else None
                            except (ValueError, TypeError):
                                detail = None
                            if status >= 500:
                                detail = "سرویس موقتاً در دسترس نیست."
                            messages.clear()
                            await error_response(request, status, detail)(scope, replay, capture)
                    # OTP attempts/rate counters deliberately survive 4xx. Business
                    # writes are atomic across existing services' internal commits.
                    if method not in SAFE and (status < 400 or path == "/demo/access" or path.startswith("/demo/otp/")):
                        db.commit()
                        transaction.commit()
                        committed = True
                    for message in messages:
                        await secured_send(message)
                except Exception:
                    if transaction.is_active:
                        transaction.rollback()
                    if self.raise_errors:
                        raise
                    import logging
                    logging.getLogger(__name__).exception('Public request failed')
                    return await reject(500, "سرویس موقتاً در دسترس نیست.")
                finally:
                    trial_request.reset(log_token)
                    if transaction.is_active:
                        transaction.rollback()
                    started = db.info.get("trial_processing_started")
                    if started and not committed:
                        from app.services.trial_service import TrialService
                        TrialService.mark_failed(engine, started)
