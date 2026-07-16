from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Form,
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)
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
# Projects List
# -------------------------------------------------------

@router.get(
    "",
    response_class=HTMLResponse,
)
async def projects_page(
    request: Request,
    db: Session = Depends(get_db),
):
    service = ProjectService(db)

    projects = service.get_all()

    return templates.TemplateResponse(
        request=request,
        name="projects.html",
        context={
            "projects": projects,
        },
    )


# -------------------------------------------------------
# New Project
# -------------------------------------------------------

@router.get(
    "/new",
    response_class=HTMLResponse,
)
async def new_project_page(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="projects/new.html",
        context={
            "status_list": list(ProjectStatus),
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
            mobile=mobile,
            company_name=company_name,
            project_name=project_name,
            description=description,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return RedirectResponse(
        url=f"/projects/{project.id}",
        status_code=303,
    )


# -------------------------------------------------------
# Demo Page
# IMPORTANT:
# MUST be BEFORE /{project_id}
# -------------------------------------------------------

@router.get(
    "/demo",
    response_class=HTMLResponse,
)
async def project_demo(
    request: Request,
):

    class DummyCompany:
        id = 1
        name = "RJA Distribution"

    class DummyProject:
        id = 1
        name = "Distribution Intelligence Assessment"
        description = "Production UI Preview"
        status = ProjectStatus.DRAFT
        company = DummyCompany()
        created_at = datetime.now()
        updated_at = datetime.now()

    return templates.TemplateResponse(
        request=request,
        name="project_detail.html",
        context={
            "project": DummyProject(),
            "files": [],
        },
    )


# -------------------------------------------------------
# Project Detail
# IMPORTANT:
# MUST stay AFTER /demo
# -------------------------------------------------------

@router.get(
    "/{project_id}",
    response_class=HTMLResponse,
)
async def project_detail(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    project_service = ProjectService(db)

    project = project_service.get_by_id(project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    file_service = FileService(db)
    files = file_service.get_by_entity(
        entity_type="PROJECT",
        entity_id=project.id,
    )

    return templates.TemplateResponse(
        request=request,
        name="project_detail.html",
        context={
            "project": project,
            "files": files,
        },
    )


# -------------------------------------------------------
# Update Status
# -------------------------------------------------------

@router.post(
    "/{project_id}/status",
)
async def update_project_status(
    project_id: int,
    status: ProjectStatus = Form(...),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)

    project = service.update_status(
        project_id=project_id,
        status=status,
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    return RedirectResponse(
        url=f"/projects/{project_id}",
        status_code=303,
    )


# -------------------------------------------------------
# Delete Project
# -------------------------------------------------------

@router.post(
    "/{project_id}/delete",
)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    service = ProjectService(db)

    deleted = service.delete_project(project_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    return RedirectResponse(
        url="/projects",
        status_code=303,
    )
