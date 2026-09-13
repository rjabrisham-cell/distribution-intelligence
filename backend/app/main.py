from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.templates import templates

# ----------------------------------------------------
# Register SQLAlchemy Models
# ----------------------------------------------------

import app.models

# ----------------------------------------------------
# Routers
# ----------------------------------------------------

from app.routers.home import router as home_router
from app.routers.dashboard import router as dashboard_router
from app.routers.request import router as request_router
from app.routers.upload import router as upload_router
from app.routers.files import router as files_router
from app.routers.admin import router as admin_router
from app.routers.project import router as project_router
from app.routers.import_router import router as import_router
from app.routers.geographic_router import router as geographic_router  # ← جدید

# ----------------------------------------------------
# FastAPI
# ----------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=False,
)

# ----------------------------------------------------
# Static
# ----------------------------------------------------

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)

# ----------------------------------------------------
# Shared Templates
# ----------------------------------------------------

app.state.templates = templates

# ----------------------------------------------------
# Routers
# ----------------------------------------------------

app.include_router(home_router)
app.include_router(dashboard_router)
app.include_router(request_router)
app.include_router(upload_router)
app.include_router(files_router)
app.include_router(admin_router)
app.include_router(project_router)
app.include_router(import_router)
app.include_router(geographic_router)  # ← جدید

from app.routers.demo_access import router as demo_access_router
from app.core.demo_security import DemoSecurityMiddleware
from fastapi.responses import JSONResponse
app.include_router(demo_access_router)
app.add_middleware(DemoSecurityMiddleware)
from app.core.demo_logging import install as install_demo_log_filter
install_demo_log_filter()

from starlette.exceptions import HTTPException as StarletteHTTPException


@app.exception_handler(StarletteHTTPException)
async def public_http_error(request, exc):
    from app.core.web_errors import error_response
    detail = "سرویس موقتاً در دسترس نیست." if exc.status_code >= 500 else exc.detail
    response = error_response(request, exc.status_code, detail)
    if exc.headers:
        response.headers.update(exc.headers)
    return response


@app.exception_handler(Exception)
async def public_error(request, exc):
    from app.core.web_errors import error_response
    return error_response(request, 500, "سرویس موقتاً در دسترس نیست.")

# ----------------------------------------------------
# Health
# ----------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
