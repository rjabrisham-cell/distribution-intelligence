from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.core.templates import templates

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "page_title": "داشبورد"
        }
    )


@router.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="projects.html",
        context={
            "page_title": "پروژه‌ها"
        }
    )


@router.get("/projects/new", response_class=HTMLResponse)
async def new_project_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="project_new.html",
        context={
            "page_title": "ایجاد پروژه جدید"
        }
    )


@router.get("/results", response_class=HTMLResponse)
async def results_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="results.html",
        context={
            "page_title": "نتایج تحلیل"
        }
    )


@router.get("/distribution", response_class=HTMLResponse)
async def distribution_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="distribution.html",
        context={
            "page_title": "اجرای توزیع"
        }
    )


@router.get("/api/dashboard")
async def dashboard_stats():
    return JSONResponse(
        {
            "projects": 12,
            "companies": 8,
            "orders": 1540,
            "vehicles": 47,
        }
    )


@router.post("/distribution/run")
async def run_distribution():
    return JSONResponse(
        {
            "status": "success",
            "message": "اجرای توزیع آزمایشی با موفقیت انجام شد.",
            "run_id": "mock-run-001",
        }
    )
