from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import admin, dashboard, home, request, upload

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(home.router)
app.include_router(request.router)
app.include_router(admin.router)
app.include_router(upload.router)
app.include_router(dashboard.router)
