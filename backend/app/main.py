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
    debug=settings.DEBUG,
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
