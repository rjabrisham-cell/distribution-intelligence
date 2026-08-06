"""
Project Management Router - Vertical Slice aligned with Journey Stepper
(Intake → Validation → Readiness → Decision → Distribution → Results → Profiling → Scenario Compare)
"""

from fastapi import APIRouter, Depends, Request, HTTPException, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.project import Project
from app.services.file_service import FileService
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter(prefix="/projects", tags=["projects"])

templates = Jinja2Templates(directory="app/templates")

# =============================================================================
# Data Contract Helpers
# =============================================================================

ALL_STAGES = [
    {"id": "intake",           "label": "دریافت داده"},
    {"id": "validation",       "label": "اعتبارسنجی"},
    {"id": "readiness",        "label": "آمادگی"},
    {"id": "decision",         "label": "تصمیم‌گیری"},
    {"id": "distribution",     "label": "توزیع"},
    {"id": "results",          "label": "نتایج"},
    {"id": "profiling",        "label": "پروفایلینگ"},
    {"id": "scenario_compare", "label": "مقایسه سناریو"},
]

TOTAL_STEPS = len(ALL_STAGES)


def _build_project_context(project) -> dict:
    """Build project_context dict from ORM model — null-safe."""
    return {
        "id": project.id,
        "name": getattr(project, "name", "بدون نام") or "بدون نام",
        "status": getattr(project, "status", "draft") or "draft",
        "company": getattr(project, "company", "") or "",
        "description": getattr(project, "description", "") or "",
        "created_at": str(getattr(project, "created_at", "") or ""),
        "updated_at": str(getattr(project, "updated_at", "") or ""),
    }


def _build_journey_state(current_stage_id: str, project_id: int) -> dict:
    """Build journey_state dict with correct completed/current/locked."""
    current_index = next(
        (i for i, s in enumerate(ALL_STAGES) if s["id"] == current_stage_id),
        0,
    )

    stages = []
    for i, stage in enumerate(ALL_STAGES):
        if i < current_index:
            state = "completed"
        elif i == current_index:
            state = "current"
        else:
            state = "locked"

        url = f"/projects/{project_id}/{stage['id']}" if state != "locked" else None
        stages.append({
            "id": stage["id"],
            "label": stage["label"],
            "state": state,
            "url": url,
        })

    return {
        "current": current_stage_id,
        "current_index": current_index + 1,
        "current_step_number": current_index + 1,
        "total_steps": TOTAL_STEPS,
        "current_stage_label": ALL_STAGES[current_index]["label"],
        "stages": stages,
    }


def _build_breadcrumb_items(project_name: str, project_id: int, stage_label: str | None = None) -> list:
    """Build breadcrumb items — always 3 levels for journey pages."""
    items = [
        {"label": "پروژه‌ها", "url": "/projects"},
        {"label": project_name or "پروژه", "url": f"/projects/{project_id}"},
    ]
    if stage_label:
        items.append({"label": stage_label, "url": None})
    return items


def _build_context(
    request: Request,
    project,
    current_stage_id: str,
    activity: list | None = None,
    extra: dict | None = None,
) -> dict:
    """Assemble the full shared Data Contract context."""
    pc = _build_project_context(project)
    js = _build_journey_state(current_stage_id, project.id)

    ctx = {
        "request": request,
        "project": project,
        "project_context": pc,
        "journey_state": js,
        "activity": activity or [],
        "recent_activity": activity or [],
        "breadcrumb_items": _build_breadcrumb_items(
            pc["name"],
            project.id,
            js["current_stage_label"]
        ),
    }

    if extra:
        ctx.update(extra)

    return ctx


def _get_project_or_404(db: Session, project_id: int):
    project = db.query(Project).filter(Project.id == project_id).first()
    return project


# =============================================================================
# Main Project Dashboard (List/Grid View)
# =============================================================================

@router.get("/", response_class=HTMLResponse)
def list_projects(request: Request, db: Session = Depends(get_db)):
    """Project dashboard - list view"""
    projects = db.query(Project).all()
    return templates.TemplateResponse(
        request=request,
        name="projects.html",
        context={
            "request": request,
            "projects": projects,
        }
    )


@router.get("/grid", response_class=HTMLResponse)
def grid_projects(request: Request, db: Session = Depends(get_db)):
    """Project dashboard - grid/card view"""
    projects = db.query(Project).all()
    return templates.TemplateResponse(
        request=request,
        name="projects_grid.html",
        context={
            "request": request,
            "projects": projects,
        }
    )


# =============================================================================
# Static Routes — MUST come before /{project_id}
# =============================================================================

@router.get("/new", response_class=HTMLResponse)
def new_project_form(request: Request):
    """
    New project creation form.
    Static route must be declared before /{project_id}
    to prevent 'new' from being parsed as project_id:int.
    """
    return templates.TemplateResponse(
        request=request,
        name="projects/new.html",
        context={
            "request": request,
        }
    )


@router.post("/new", response_class=HTMLResponse)
def create_project_from_form(
    name: str = Form(...),
    description: str | None = Form(None),
    code: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    Create project from the canonical HTML form contract.

    Development:
        All current projects belong to Company #1.

    Production:
        company_id must be obtained from the authenticated user's
        company/session context.
    """
    clean_name = name.strip()

    db_project = Project(
        company_id=1,
        name=clean_name,
        description=description.strip() if description and description.strip() else None,
        code=code.strip() if code and code.strip() else None,
    )

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return RedirectResponse(
        url=f"/projects/{db_project.id}",
        status_code=303,
    )



# =============================================================================
# Project Detail & Journey Stepper
# =============================================================================

@router.get("/{project_id}", response_class=HTMLResponse)
def project_detail(request: Request, project_id: int, db: Session = Depends(get_db)):
    """Project detail page with journey stepper"""
    project = _get_project_or_404(db, project_id)
    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": f"Project with ID {project_id} not found",
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="project_detail.html",
        context={
            "request": request,
            "project": project,
            "project_context": _build_project_context(project),
            "journey_state": _build_journey_state("intake", project.id),
            "breadcrumb_items": [
                {"label": "پروژه‌ها", "url": "/projects"},
                {"label": getattr(project, "name", "پروژه"), "url": None},
            ],
            "recent_activity": [],
        }
    )


# =============================================================================
# Journey Steps — 8 Route Handlers with Unified Data Contract
# =============================================================================

# ---------------------------------------------------------------------------
# 1. Intake
# ---------------------------------------------------------------------------

@router.get("/{project_id}/intake", response_class=HTMLResponse)
def intake_step(request: Request, project_id: int, db: Session = Depends(get_db)):
    """Intake step — displays uploaded files for this project."""
    project = _get_project_or_404(db, project_id)
    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": f"Project with ID {project_id} not found",
            }
        )

    file_service = FileService(db)
    files = file_service.get_by_entity(entity_type="PROJECT", entity_id=project_id)

    return templates.TemplateResponse(
        request=request,
        name="projects/intake.html",
        context=_build_context(request, project, "intake", extra={"files": files}),
    )


@router.post("/{project_id}/intake")
async def process_intake(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db)
):
    """Reserved for future Intake metadata submission."""
    return {"message": "Intake endpoint reserved", "project_id": project_id}


# ---------------------------------------------------------------------------
# 2. Validation
# ---------------------------------------------------------------------------

@router.get("/{project_id}/validation", response_class=HTMLResponse)
def validation_step(request: Request, project_id: int, db: Session = Depends(get_db)):
    """Validation step view."""
    project = _get_project_or_404(db, project_id)
    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": f"Project with ID {project_id} not found",
            }
        )
    return templates.TemplateResponse(
        request=request,
        name="projects/validation.html",
        context=_build_context(request, project, "validation"),
    )


@router.post("/{project_id}/validation")
async def process_validation(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db)
):
    """Process validation form submission."""
    await request.form()
    return {"message": "Validation processed", "next_step": "readiness"}


# ---------------------------------------------------------------------------
# 3. Readiness
# ---------------------------------------------------------------------------

@router.get("/{project_id}/readiness", response_class=HTMLResponse)
def readiness_step(request: Request, project_id: int, db: Session = Depends(get_db)):
    """Readiness step view."""
    project = _get_project_or_404(db, project_id)
    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": f"Project with ID {project_id} not found",
            }
        )
    return templates.TemplateResponse(
        request=request,
        name="projects/readiness.html",
        context=_build_context(request, project, "readiness"),
    )


@router.post("/{project_id}/readiness")
async def process_readiness(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db)
):
    """Process readiness form submission."""
    await request.form()
    return {"message": "Readiness processed", "next_step": "decision"}


# ---------------------------------------------------------------------------
# 4. Decision
# ---------------------------------------------------------------------------

@router.get("/{project_id}/decision", response_class=HTMLResponse)
def decision_step(request: Request, project_id: int, db: Session = Depends(get_db)):
    """Decision step view."""
    project = _get_project_or_404(db, project_id)
    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": f"Project with ID {project_id} not found",
            }
        )
    return templates.TemplateResponse(
        request=request,
        name="projects/decision.html",
        context=_build_context(request, project, "decision"),
    )


@router.post("/{project_id}/decision")
async def process_decision(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db)
):
    """Process decision form submission."""
    await request.form()
    return {"message": "Decision processed", "next_step": "distribution"}


# ---------------------------------------------------------------------------
# 5. Distribution
# ---------------------------------------------------------------------------

@router.get("/{project_id}/distribution", response_class=HTMLResponse)
def distribution_step(request: Request, project_id: int, db: Session = Depends(get_db)):
    """Distribution step view."""
    project = _get_project_or_404(db, project_id)
    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": f"Project with ID {project_id} not found",
            }
        )
    return templates.TemplateResponse(
        request=request,
        name="projects/distribution.html",
        context=_build_context(request, project, "distribution"),
    )


@router.post("/{project_id}/distribution")
async def process_distribution(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db)
):
    """Process distribution form submission."""
    await request.form()
    return {"message": "Distribution processed", "next_step": "results"}


# ---------------------------------------------------------------------------
# 6. Results
# ---------------------------------------------------------------------------

@router.get("/{project_id}/results", response_class=HTMLResponse)
def results_step(request: Request, project_id: int, db: Session = Depends(get_db)):
    """Results step view."""
    project = _get_project_or_404(db, project_id)
    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": f"Project with ID {project_id} not found",
            }
        )
    return templates.TemplateResponse(
        request=request,
        name="projects/results.html",
        context=_build_context(request, project, "results"),
    )


@router.post("/{project_id}/results")
async def process_results(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db)
):
    """Process results form submission."""
    await request.form()
    return {"message": "Results processed", "next_step": "profiling"}


# ---------------------------------------------------------------------------
# 7. Profiling
# ---------------------------------------------------------------------------

@router.get("/{project_id}/profiling", response_class=HTMLResponse)
def profiling_step(request: Request, project_id: int, db: Session = Depends(get_db)):
    """Profiling step view."""
    project = _get_project_or_404(db, project_id)
    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": f"Project with ID {project_id} not found",
            }
        )
    return templates.TemplateResponse(
        request=request,
        name="projects/profiling.html",
        context=_build_context(request, project, "profiling"),
    )


@router.post("/{project_id}/profiling")
async def process_profiling(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db)
):
    """Process profiling form submission."""
    await request.form()
    return {"message": "Profiling processed", "next_step": "scenario_compare"}


# ---------------------------------------------------------------------------
# 8. Scenario Compare
# ---------------------------------------------------------------------------

@router.get("/{project_id}/scenario_compare", response_class=HTMLResponse)
def scenario_compare_step(request: Request, project_id: int, db: Session = Depends(get_db)):
    """Scenario Compare step view."""
    project = _get_project_or_404(db, project_id)
    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": f"Project with ID {project_id} not found",
            }
        )
    return templates.TemplateResponse(
        request=request,
        name="projects/scenario_compare.html",
        context=_build_context(request, project, "scenario_compare"),
    )


@router.post("/{project_id}/scenario_compare")
async def process_scenario_compare(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db)
):
    """Process scenario compare form submission."""
    await request.form()
    return {"message": "Scenario compare processed", "next_step": "complete"}


# =============================================================================
# CRUD API Endpoints
# =============================================================================

@router.get("/api/")
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Read projects list (API)"""
    projects = db.query(Project).offset(skip).limit(limit).all()
    return projects


@router.get("/api/{project_id}")
def read_project(project_id: int, db: Session = Depends(get_db)):
    """Read a specific project (API)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/api/")
def create_project(
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    """Create a new project (via form/JSON)"""
    db_project = Project(name=name, description=description)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.post("/api/")
def create_project(
    name: str = Form(...),
    description: str | None = Form(None),
    code: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    Create project through the current Development API contract.

    Production:
        company_id must be obtained from the authenticated user's
        company/session context.
    """
    clean_name = name.strip()

    db_project = Project(
        company_id=1,
        name=clean_name,
        description=description.strip() if description and description.strip() else None,
        code=code.strip() if code and code.strip() else None,
    )

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return db_project

@router.delete("/api/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete a project"""
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(db_project)
    db.commit()
    return {"message": "Project deleted"}
