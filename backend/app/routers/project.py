from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.models.project import ProjectStatus
from app.services.file_service import FileService
from app.services.project_service import ProjectService

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)

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
# Projects List
# -------------------------------------------------------
@router.get("", response_class=HTMLResponse)
async def projects_page(request: Request, db: Session = Depends(get_db)):
    service = ProjectService(db)
    projects = service.get_all()

    return templates.TemplateResponse(
        request=request,
        name="projects.html",
        context={
            "projects": projects,
            **build_ui_context(project_name="لیست پروژه‌ها")
        },
    )

# -------------------------------------------------------
# New Project
# -------------------------------------------------------
@router.get("/new", response_class=HTMLResponse)
async def new_project_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="projects/new.html",
        context={
            "status_list": list(ProjectStatus),
            **build_ui_context(project_name="تعریف پروژه جدید", project_status="Draft")
        },
    )

# -------------------------------------------------------
# Create Project
# -------------------------------------------------------
@router.post("")
async def create_project(
    mobile: str = Form(...),
    company_name: str = Form(...),
    project_name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    try:
        project = service.create_project(
            mobile=mobile.strip(),
            company_name=company_name.strip(),
            project_name=project_name.strip(),
            description=description.strip() or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return RedirectResponse(url=f"/projects/{project.id}", status_code=303)

# -------------------------------------------------------
# Demo Page
# -------------------------------------------------------
@router.get("/demo", response_class=HTMLResponse)
async def project_demo(request: Request):
    class DummyCompany:
        id = 1
        name = "توزیع نمونه RJA"
        code = "RJA-DEMO"

    class DummyProject:
        id = 1
        name = "ارزیابی هوشمندی توزیع"
        description = "پیش‌نمایش رابط کاربری جدید"
        status = ProjectStatus.DRAFT
        company = DummyCompany()
        created_at = datetime.now()
        updated_at = datetime.now()

    dummy = DummyProject()
    return templates.TemplateResponse(
        request=request,
        name="project_detail.html",
        context={
            "project": dummy,
            "files": [],
            **build_ui_context(
                company_name=dummy.company.name,
                company_code=dummy.company.code,
                project_name=dummy.name,
                project_status=dummy.status.value
            )
        },
    )

# -------------------------------------------------------
# Project Detail
# -------------------------------------------------------
@router.get("/{project_id}", response_class=HTMLResponse)
async def project_detail(project_id: int, request: Request, db: Session = Depends(get_db)):
    project_service = ProjectService(db)
    project = project_service.get_by_id(project_id)

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    file_service = FileService(db)
    files = file_service.get_by_entity(entity_type="PROJECT", entity_id=project.id)

    # استخراج نام شرکت در صورت وجود رابطه در مدل
    c_name = project.company.name if hasattr(project, 'company') and project.company else "نامشخص"
    c_code = project.company.code if hasattr(project, 'company') and project.company else ""

    return templates.TemplateResponse(
        request=request,
        name="project_detail.html",
        context={
            "project": project,
            "files": files,
            **build_ui_context(
                company_name=c_name,
                company_code=c_code,
                project_name=project.name,
                project_status=project.status.value if hasattr(project.status, 'value') else str(project.status)
            )
        },
    )

# -------------------------------------------------------
# Update Status & Delete
# -------------------------------------------------------
@router.post("/{project_id}/status")
async def update_project_status(project_id: int, status: ProjectStatus = Form(...), db: Session = Depends(get_db)):
    service = ProjectService(db)
    project = service.update_status(project_id=project_id, status=status)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@router.post("/{project_id}/delete")
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    service = ProjectService(db)
    if not service.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    return RedirectResponse(url="/projects", status_code=303)
