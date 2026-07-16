from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.services.project_service import ProjectService


router = APIRouter(
    tags=["Dashboard"],
)


# -------------------------------------------------------
# Dashboard
# -------------------------------------------------------

@router.get(
    "/dashboard",
    response_class=HTMLResponse,
)
async def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
):
    service = ProjectService(db)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "page_title": "داشبورد",
            "project_count": service.count(),
        },
    )


# -------------------------------------------------------
# Results
# -------------------------------------------------------

@router.get(
    "/results",
    response_class=HTMLResponse,
)
async def results_page(
    request: Request,
):
    return templates.TemplateResponse(
        request,
        "results.html",
        {
            "page_title": "نتایج تحلیل",
        },
    )


# -------------------------------------------------------
# Distribution
# -------------------------------------------------------

@router.get(
    "/distribution",
    response_class=HTMLResponse,
)
async def distribution_page(
    request: Request,
):
    return templates.TemplateResponse(
        request,
        "distribution.html",
        {
            "page_title": "اجرای توزیع",
        },
    )


# -------------------------------------------------------
# Dashboard API
# -------------------------------------------------------

@router.get(
    "/api/dashboard",
)
async def dashboard_stats(
    db: Session = Depends(get_db),
):
    service = ProjectService(db)

    return JSONResponse(
        {
            "projects": service.count(),
            "companies": 0,
            "orders": 0,
            "vehicles": 0,
        }
    )


# -------------------------------------------------------
# Distribution Run (Mock)
# -------------------------------------------------------

@router.post(
    "/distribution/run",
)
async def run_distribution():

    return JSONResponse(
        {
            "status": "success",
            "message": "اجرای آزمایشی با موفقیت انجام شد.",
            "run_id": "mock-run-001",
        }
    )