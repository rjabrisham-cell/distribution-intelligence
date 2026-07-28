from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.services.project_service import ProjectService

router = APIRouter(tags=["Dashboard"])

# -------------------------------------------------------
# Shared UI Context Helper
# -------------------------------------------------------
def build_ui_context(
    *,
    company_name: str = "",
    company_code: str = "",
    project_name: str = "",
    project_status: str = "",
    user_name: str = "مدیر سیستم",
    user_role: str = "راهبر ارشد",
    user_initial: str = "م",
):
    return {
        "company_name": company_name,
        "company_code": company_code,
        "project_name": project_name,
        "project_status": project_status,
        "user_name": user_name,
        "user_role": user_role,
        "user_initial": user_initial,
    }

# -------------------------------------------------------
# Dashboard
# -------------------------------------------------------
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    service = ProjectService(db)
    
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "page_title": "داشبورد اصلی",
            "project_count": service.count(),
            **build_ui_context(project_name="پیشخوان مدیریتی")
        },
    )

# -------------------------------------------------------
# Results
# -------------------------------------------------------
@router.get("/results", response_class=HTMLResponse)
async def results_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="results.html",
        context={
            "page_title": "نتایج تحلیل",
            **build_ui_context(project_name="گزارش نهایی")
        },
    )

# -------------------------------------------------------
# Distribution
# -------------------------------------------------------
@router.get("/distribution", response_class=HTMLResponse)
async def distribution_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="distribution.html",
        context={
            "page_title": "مدیریت توزیع",
            **build_ui_context(project_name="عملیات توزیع")
        },
    )

# -------------------------------------------------------
# Dashboard API
# -------------------------------------------------------
@router.get("/api/dashboard")
async def dashboard_stats(db: Session = Depends(get_db)):
    service = ProjectService(db)
    return JSONResponse({
        "projects": service.count(),
        "companies": 0,
        "orders": 0,
        "vehicles": 0,
    })

# -------------------------------------------------------
# Distribution Run (Mock)
# -------------------------------------------------------
@router.post("/distribution/run")
async def run_distribution():
    return JSONResponse({
        "status": "success",
        "message": "عملیات توزیع در محیط دمو با موفقیت شبیه‌سازی شد.",
        "run_id": "mock-run-001",
    })
