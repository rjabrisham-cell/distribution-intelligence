"""
Project Management Router - Vertical Slice aligned with Journey Stepper
(Intake → Validation → Readiness → Decision → Distribution → Results → Profiling → Scenario Compare)
"""

from __future__ import annotations

import json
import time

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import EntityType
from app.models.address_candidate import AddressCandidate
from app.models.file import File
from app.models.import_batch import ImportBatch
from app.models.project import Project
from app.models.row_error import RowError
from app.services.file_service import FileService
from app.services.audit.audit_runner import AuditRunner
from app.services.audit.report_builder import ReportBuilder
from app.services.store_matching_service import StoreMatchingService


router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)

templates = Jinja2Templates(
    directory="app/templates",
)


# =============================================================================
# Data Contract Helpers
# =============================================================================


ALL_STAGES = [
    {"id": "intake", "label": "دریافت داده"},
    {"id": "validation", "label": "اعتبارسنجی"},
    {"id": "readiness", "label": "آمادگی"},
    {"id": "decision", "label": "تصمیم‌گیری"},
    {"id": "distribution", "label": "توزیع"},
    {"id": "results", "label": "نتایج"},
    {"id": "profiling", "label": "پروفایلینگ"},
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


def _build_journey_state(
    current_stage_id: str,
    project_id: int,
) -> dict:
    """Build journey_state dict with correct completed/current/locked."""

    current_index = next(
        (
            i
            for i, stage in enumerate(ALL_STAGES)
            if stage["id"] == current_stage_id
        ),
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

        url = (
            f"/projects/{project_id}/{stage['id']}"
            if state != "locked"
            else None
        )

        stages.append(
            {
                "id": stage["id"],
                "label": stage["label"],
                "state": state,
                "url": url,
            }
        )

    return {
        "current": current_stage_id,
        "current_index": current_index + 1,
        "current_step_number": current_index + 1,
        "total_steps": TOTAL_STEPS,
        "current_stage_label": ALL_STAGES[current_index]["label"],
        "stages": stages,
    }


def _build_breadcrumb_items(
    project_name: str,
    project_id: int,
    stage_label: str | None = None,
) -> list:
    """Build breadcrumb items."""

    items = [
        {
            "label": "پروژه‌ها",
            "url": "/projects",
        },
        {
            "label": project_name or "پروژه",
            "url": f"/projects/{project_id}",
        },
    ]

    if stage_label:
        items.append(
            {
                "label": stage_label,
                "url": None,
            }
        )

    return items


def _build_context(
    request: Request,
    project,
    current_stage_id: str,
    activity: list | None = None,
    extra: dict | None = None,
) -> dict:
    """Assemble the shared Journey context."""

    project_context = _build_project_context(
        project
    )

    journey_state = _build_journey_state(
        current_stage_id,
        project.id,
    )

    context = {
        "request": request,
        "project": project,
        "project_context": project_context,
        "journey_state": journey_state,
        "activity": activity or [],
        "recent_activity": activity or [],
        "breadcrumb_items": _build_breadcrumb_items(
            project_context["name"],
            project.id,
            journey_state["current_stage_label"],
        ),
    }

    if extra:
        context.update(extra)

    return context


def _get_project_or_404(
    db: Session,
    project_id: int,
):
    """Return project or None."""

    return (
        db.query(Project)
        .filter(
            Project.id == project_id
        )
        .first()
    )


# =============================================================================
# Store Batch Resolver
# =============================================================================


def _find_latest_store_batch(
    db: Session,
    project_id: int,
) -> ImportBatch | None:
    """
    Find latest STORE ImportBatch belonging to exactly this Project.

    Join:

        ImportBatch.file_id
            -> File.id

        File.entity_type = PROJECT
        File.entity_id   = project_id
        File.category    = stores

        ImportBatch.entity_type = STORE
    """

    return (
        db.query(ImportBatch)
        .join(
            File,
            ImportBatch.file_id == File.id,
        )
        .filter(
            File.entity_type == "PROJECT",
            File.entity_id == project_id,
            File.category == "stores",
            ImportBatch.entity_type == EntityType.STORE,
        )
        .order_by(
            ImportBatch.id.desc()
        )
        .first()
    )


# =============================================================================
# Batch Candidate Query
# =============================================================================


def _batch_candidate_query(
    db: Session,
    batch_id: int,
):
    """Return AddressCandidate query scoped to one ImportBatch."""

    source_pattern = (
        f"import_batch:{batch_id}:row:%"
    )

    return (
        db.query(AddressCandidate)
        .filter(
            AddressCandidate.source_type == "excel",
            AddressCandidate.source_id.like(
                source_pattern
            ),
        )
    )


# =============================================================================
# Validation Evidence Summary
# =============================================================================


def _build_validation_evidence_summary(
    db: Session,
    batch: ImportBatch,
) -> dict:
    """
    Build Batch-scoped evidence metrics for Validation.
    """

    candidate_query = _batch_candidate_query(
        db,
        batch.id,
    )

    address_evidence = (
        candidate_query.count()
    )

    linked_company_store = (
        candidate_query
        .filter(
            AddressCandidate.company_store_id.isnot(
                None
            )
        )
        .count()
    )

    coordinates_available = (
        candidate_query
        .filter(
            AddressCandidate.latitude.isnot(
                None
            ),
            AddressCandidate.longitude.isnot(
                None
            ),
        )
        .count()
    )

    coordinates_missing = max(
        address_evidence - coordinates_available,
        0,
    )

    processed_candidates = (
        candidate_query
        .filter(
            AddressCandidate.is_processed.is_(
                True
            )
        )
        .count()
    )

    matched_candidates = (
        candidate_query
        .filter(
            AddressCandidate.match_found.is_(
                True
            ),
            AddressCandidate.matched_store_id.isnot(
                None
            ),
        )
        .count()
    )

    imported_stores = int(
        batch.imported_rows or 0
    )

    missing_address = max(
        imported_stores - address_evidence,
        0,
    )

    if imported_stores <= 0:
        matching_status = "NOT_READY"

    elif address_evidence <= 0:
        matching_status = "NOT_READY"

    elif processed_candidates == 0:
        matching_status = "PENDING"

    elif processed_candidates < address_evidence:
        matching_status = "IN_PROGRESS"

    else:
        matching_status = "PROCESSED"

    return {
        "batch_id": batch.id,
        "imported_stores": imported_stores,
        "address_evidence": address_evidence,
        "linked_company_store": linked_company_store,
        "coordinates_available": coordinates_available,
        "coordinates_missing": coordinates_missing,
        "missing_address": missing_address,
        "ready_for_matching": imported_stores,
        "processed_candidates": processed_candidates,
        "matched_candidates": matched_candidates,
        "matching_status": matching_status,
    }


# =============================================================================
# Persisted Matching Summary
# =============================================================================


def _build_matching_database_summary(
    db: Session,
    batch: ImportBatch,
) -> dict:
    """
    Read Matching state directly from AddressCandidate.

    This allows Readiness GET to display already-persisted Matching
    without running the engine again.
    """

    query = _batch_candidate_query(
        db,
        batch.id,
    )

    total_candidates = (
        query.count()
    )

    processed = (
        query
        .filter(
            AddressCandidate.is_processed.is_(
                True
            )
        )
        .count()
    )

    confirmed_matches = (
        query
        .filter(
            AddressCandidate.is_processed.is_(
                True
            ),
            AddressCandidate.match_found.is_(
                True
            ),
            AddressCandidate.store_id.isnot(
                None
            ),
            AddressCandidate.matched_store_id.isnot(
                None
            ),
        )
        .count()
    )

    precise = (
        query
        .filter(
            AddressCandidate.is_processed.is_(
                True
            ),
            AddressCandidate.match_method.like(
                "precise:%"
            ),
        )
        .count()
    )

    suggested = (
        query
        .filter(
            AddressCandidate.is_processed.is_(
                True
            ),
            AddressCandidate.match_method.like(
                "suggested:%"
            ),
        )
        .count()
    )

    existing_link = (
        query
        .filter(
            AddressCandidate.is_processed.is_(
                True
            ),
            AddressCandidate.match_method
            == "existing_master_link",
        )
        .count()
    )

    unresolved = (
        query
        .filter(
            AddressCandidate.is_processed.is_(
                True
            ),
            AddressCandidate.match_found.is_(
                False
            ),
            ~AddressCandidate.match_method.like(
                "suggested:%"
            ),
        )
        .count()
    )

    no_candidate_pool = (
        query
        .filter(
            AddressCandidate.is_processed.is_(
                True
            ),
            AddressCandidate.match_method
            == "no_candidate_pool",
        )
        .count()
    )

    geo_unresolved = (
        query
        .filter(
            AddressCandidate.is_processed.is_(
                True
            ),
            AddressCandidate.match_method
            == "geo_unresolved",
        )
        .count()
    )

    pending = max(
        total_candidates - processed,
        0,
    )

    processed_without_confirmed_match = max(
        processed - confirmed_matches,
        0,
    )

    processed_rate = (
        round(
            (processed / total_candidates) * 100,
            2,
        )
        if total_candidates > 0
        else 0.0
    )

    match_rate = (
        round(
            (confirmed_matches / total_candidates) * 100,
            2,
        )
        if total_candidates > 0
        else 0.0
    )

    if total_candidates <= 0:
        status = "NOT_READY"

    elif processed <= 0:
        status = "PENDING"

    elif processed < total_candidates:
        status = "IN_PROGRESS"

    else:
        status = "PROCESSED"

    return {
        "batch_id": batch.id,
        "total_candidates": total_candidates,
        "processed": processed,
        "pending": pending,

        "confirmed_matches": confirmed_matches,
        "precise": precise,
        "suggested": suggested,
        "unresolved": unresolved,
        "existing_link": existing_link,

        "processed_without_confirmed_match": (
            processed_without_confirmed_match
        ),

        "no_candidate_pool": no_candidate_pool,
        "geo_unresolved": geo_unresolved,

        "processed_rate": processed_rate,
        "match_rate": match_rate,

        "status": status,
    }


# =============================================================================
# Matching Report Adapter
# =============================================================================


def _build_matching_report(
    *,
    batch: ImportBatch,
    database_summary: dict,
    elapsed_sec: float | None = None,
    execution_error: str | None = None,
) -> dict:
    """
    Adapt Matching results to the existing readiness.html report contract.

    Important:

    readiness.html expects:

        report["summary"] -> string

        report["sections"] -> list[dict]

        report["totals"] -> list[dict]

    This is a Matching Gate report only.
    It is NOT yet the final Audit / Readiness Score.
    """

    total = int(
        database_summary.get(
            "total_candidates",
            0,
        )
        or 0
    )

    processed = int(
        database_summary.get(
            "processed",
            0,
        )
        or 0
    )

    precise = int(
        database_summary.get(
            "precise",
            0,
        )
        or 0
    )

    suggested = int(
        database_summary.get(
            "suggested",
            0,
        )
        or 0
    )

    unresolved = int(
        database_summary.get(
            "unresolved",
            0,
        )
        or 0
    )

    confirmed_matches = int(
        database_summary.get(
            "confirmed_matches",
            0,
        )
        or 0
    )

    existing_link = int(
        database_summary.get(
            "existing_link",
            0,
        )
        or 0
    )

    pending = int(
        database_summary.get(
            "pending",
            0,
        )
        or 0
    )

    no_candidate_pool = int(
        database_summary.get(
            "no_candidate_pool",
            0,
        )
        or 0
    )

    geo_unresolved = int(
        database_summary.get(
            "geo_unresolved",
            0,
        )
        or 0
    )

    processed_rate = float(
        database_summary.get(
            "processed_rate",
            0.0,
        )
        or 0.0
    )

    match_rate = float(
        database_summary.get(
            "match_rate",
            0.0,
        )
        or 0.0
    )

    if execution_error:
        summary_text = (
            "اجرای مرحله تطبیق هوشمند با خطا مواجه شد. "
            "نتایج زیر وضعیت ثبت‌شده در پایگاه داده را نشان می‌دهند."
        )

    elif total <= 0:
        summary_text = (
            "برای این Batch شواهد آدرس قابل ارسال به موتور "
            "Matching وجود ندارد."
        )

    elif processed < total:
        summary_text = (
            f"از {total} رکورد قابل تطبیق، "
            f"{processed} رکورد پردازش شده و "
            f"{pending} رکورد هنوز در انتظار Matching است. "
            "ارزیابی نهایی آمادگی هنوز اجرا نشده است."
        )

    else:
        summary_text = (
            f"مرحله تطبیق هوشمند برای هر {total} رکورد دارای "
            f"شواهد آدرس تکمیل شده است. "
            f"{confirmed_matches} رکورد به Master Store موجود "
            f"متصل شده، {suggested} رکورد در وضعیت پیشنهادی و "
            f"{unresolved} رکورد بدون تطبیق قطعی باقی مانده است. "
            "این گزارش فقط نتیجه Matching است و ارزیابی نهایی "
            "کیفیت و Readiness هنوز اجرا نشده است."
        )

    #
    # Do not claim final readiness PASS/FAIL yet.
    #
    overall_status = "unknown"

    matching_section_status = (
        "fail"
        if execution_error
        else "unknown"
    )

    sections = [
        {
            "name": "matching",
            "status": matching_section_status,
            "percentage": processed_rate,
            "score": None,
            "passed": confirmed_matches,
            "failed": unresolved,
            "unknown": suggested + pending,
            "summary": (
                f"{processed}/{total} رکورد پردازش شده؛ "
                f"{confirmed_matches} تطبیق قطعی، "
                f"{suggested} پیشنهادی و "
                f"{unresolved} بدون تطبیق قطعی."
            ),
            "metrics": [
                {
                    "key": "processed",
                    "label": "پردازش‌شده",
                    "value": processed,
                },
                {
                    "key": "confirmed_matches",
                    "label": "تطبیق قطعی",
                    "value": confirmed_matches,
                },
                {
                    "key": "precise",
                    "label": "PRECISE",
                    "value": precise,
                },
                {
                    "key": "suggested",
                    "label": "SUGGESTED",
                    "value": suggested,
                },
                {
                    "key": "unresolved",
                    "label": "UNRESOLVED",
                    "value": unresolved,
                },
                {
                    "key": "existing_link",
                    "label": "Existing Master Link",
                    "value": existing_link,
                },
                {
                    "key": "no_candidate_pool",
                    "label": "No Candidate Pool",
                    "value": no_candidate_pool,
                },
                {
                    "key": "geo_unresolved",
                    "label": "Geography Unresolved",
                    "value": geo_unresolved,
                },
                {
                    "key": "match_rate",
                    "label": "نرخ تطبیق قطعی",
                    "value": f"{match_rate:.2f}%",
                },
            ],
            "raw": database_summary,
        }
    ]

    totals = [
        {
            "key": "total_candidates",
            "label": "کل شواهد Matching",
            "value": total,
        },
        {
            "key": "processed",
            "label": "پردازش‌شده",
            "value": processed,
        },
        {
            "key": "confirmed_matches",
            "label": "تطبیق قطعی",
            "value": confirmed_matches,
        },
        {
            "key": "suggested",
            "label": "پیشنهادی",
            "value": suggested,
        },
        {
            "key": "unresolved",
            "label": "حل‌نشده",
            "value": unresolved,
        },
        {
            "key": "pending",
            "label": "در انتظار",
            "value": pending,
        },
    ]

    return {
        "audit_run_id": (
            f"matching-batch-{batch.id}"
        ),
        "elapsed_sec": elapsed_sec,
        "overall_status": overall_status,
        "summary": summary_text,
        "sections": sections,
        "totals": totals,

        #
        # Extra Matching-specific contract for future UI use.
        #
        "phase": "matching",
        "batch_id": batch.id,
        "matching": database_summary,
        "execution_error": execution_error,
    }


# =============================================================================
# Main Project Dashboard
# =============================================================================


@router.get(
    "/",
    response_class=HTMLResponse,
)
def list_projects(
    request: Request,
    db: Session = Depends(get_db),
):
    """Project dashboard - list view."""

    projects = (
        db.query(Project)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="projects.html",
        context={
            "request": request,
            "projects": projects,
        },
    )


@router.get(
    "/grid",
    response_class=HTMLResponse,
)
def grid_projects(
    request: Request,
    db: Session = Depends(get_db),
):
    """Project dashboard - grid/card view."""

    projects = (
        db.query(Project)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="projects_grid.html",
        context={
            "request": request,
            "projects": projects,
        },
    )


# =============================================================================
# Static Routes — MUST come before /{project_id}
# =============================================================================


@router.get(
    "/new",
    response_class=HTMLResponse,
)
def new_project_form(
    request: Request,
):
    """New project creation form."""

    return templates.TemplateResponse(
        request=request,
        name="projects/new.html",
        context={
            "request": request,
        },
    )


@router.post(
    "/new",
    response_class=HTMLResponse,
)
def create_project_from_form(
    name: str = Form(...),
    description: str | None = Form(None),
    code: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    Create project from HTML form.

    Development:
        current projects belong to Company #1.

    Production:
        company_id must come from authenticated context.
    """

    clean_name = (
        name.strip()
    )

    db_project = Project(
        company_id=1,
        name=clean_name,
        description=(
            description.strip()
            if description and description.strip()
            else None
        ),
        code=(
            code.strip()
            if code and code.strip()
            else None
        ),
    )

    db.add(
        db_project
    )

    db.commit()

    db.refresh(
        db_project
    )

    return RedirectResponse(
        url=f"/projects/{db_project.id}",
        status_code=303,
    )


# =============================================================================
# Project Detail
# =============================================================================


@router.get(
    "/{project_id}",
    response_class=HTMLResponse,
)
def project_detail(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """Project detail page."""

    project = _get_project_or_404(
        db,
        project_id,
    )

    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": (
                    f"Project with ID {project_id} not found"
                ),
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="project_detail.html",
        context={
            "request": request,
            "project": project,
            "project_context": _build_project_context(
                project
            ),
            "journey_state": _build_journey_state(
                "intake",
                project.id,
            ),
            "breadcrumb_items": [
                {
                    "label": "پروژه‌ها",
                    "url": "/projects",
                },
                {
                    "label": getattr(
                        project,
                        "name",
                        "پروژه",
                    ),
                    "url": None,
                },
            ],
            "recent_activity": [],
        },
    )


# =============================================================================
# 1. Intake
# =============================================================================


@router.get(
    "/{project_id}/intake",
    response_class=HTMLResponse,
)
def intake_step(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """Intake step."""

    project = _get_project_or_404(
        db,
        project_id,
    )

    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": (
                    f"Project with ID {project_id} not found"
                ),
            },
        )

    file_service = FileService(
        db
    )

    files = file_service.get_by_entity(
        entity_type="PROJECT",
        entity_id=project_id,
    )

    return templates.TemplateResponse(
        request=request,
        name="projects/intake.html",
        context=_build_context(
            request,
            project,
            "intake",
            extra={
                "files": files,
            },
        ),
    )


@router.post(
    "/{project_id}/intake"
)
async def process_intake(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """Reserved for future Intake metadata submission."""

    return {
        "message": "Intake endpoint reserved",
        "project_id": project_id,
    }


# =============================================================================
# 2. Validation
# =============================================================================


@router.get(
    "/{project_id}/validation",
    response_class=HTMLResponse,
)
def validation_step(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """
    Validation step.

    Displays:
        - Import counters
        - Row errors
        - AddressCandidate evidence
        - Matching eligibility

    Read-only.
    """

    project = _get_project_or_404(
        db,
        project_id,
    )

    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": (
                    f"Project with ID {project_id} not found"
                ),
            },
        )

    batch = _find_latest_store_batch(
        db,
        project_id,
    )

    if batch is None:
        return templates.TemplateResponse(
            request=request,
            name="projects/validation.html",
            context=_build_context(
                request,
                project,
                "validation",
                extra={
                    "batch": None,
                    "summary": None,
                    "evidence_summary": None,
                    "row_errors": [],
                    "message": (
                        "هیچ فایل Store برای این پروژه یافت نشد."
                    ),
                },
            ),
        )

    row_errors = (
        db.query(RowError)
        .filter(
            RowError.import_batch_id == batch.id
        )
        .order_by(
            RowError.row_number.asc()
        )
        .all()
    )

    summary = {
        "total_rows": batch.total_rows,
        "valid_rows": batch.valid_rows,
        "error_rows": batch.error_rows,
        "imported_rows": batch.imported_rows,
        "status": (
            batch.status.value
            if batch.status
            else None
        ),
        "progress_percent": batch.progress_percent,
        "has_errors": batch.has_errors,
        "success_rate": batch.success_rate,
        "is_finished": batch.is_finished,
    }

    evidence_summary = (
        _build_validation_evidence_summary(
            db=db,
            batch=batch,
        )
    )

    message = None

    if not batch.is_finished:
        message = (
            "پردازش این Batch هنوز کامل نشده است."
        )

    return templates.TemplateResponse(
        request=request,
        name="projects/validation.html",
        context=_build_context(
            request,
            project,
            "validation",
            extra={
                "batch": batch,
                "summary": summary,
                "evidence_summary": evidence_summary,
                "row_errors": row_errors,
                "message": message,
            },
        ),
    )


@router.post(
    "/{project_id}/validation"
)
async def process_validation(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """
    Validation submission.

    Matching intentionally happens in Readiness.
    """

    await request.form()

    return {
        "message": "Validation processed",
        "next_step": "readiness",
    }


# =============================================================================
# 3. Readiness
# =============================================================================


@router.get(
    "/{project_id}/readiness",
    response_class=HTMLResponse,
)
def readiness_step(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """
    Readiness GET.

    Behaviour:

    1. Resolve latest STORE Batch for this Project.
    2. Read persisted Matching state.
    3. If all AddressCandidates are already processed:
           DO NOT run Matching again.
    4. If Matching is still pending:
           run StoreMatchingService once.
    5. Read persisted state again.
    6. Run the project-scoped AuditRunner for every active project store.
    7. Build the normalized audit report and GeoJSON map payload.
    8. Render the final distribution-readiness view.
    """

    project = _get_project_or_404(
        db,
        project_id,
    )

    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": (
                    f"Project with ID {project_id} not found"
                ),
            },
        )

    batch = _find_latest_store_batch(
        db,
        project_id,
    )

    # -------------------------------------------------------------------------
    # No STORE Batch
    # -------------------------------------------------------------------------

    if batch is None:
        return templates.TemplateResponse(
            request=request,
            name="projects/readiness.html",
            context=_build_context(
                request,
                project,
                "readiness",
                extra={
                    "batch": None,
                    "matching_summary": None,
                    "matching_runtime": None,
                    "report": None,
                    "matching_error": None,
                    "message": (
                        "هیچ STORE Batch برای این پروژه یافت نشد."
                    ),
                },
            ),
        )

    # -------------------------------------------------------------------------
    # No imported rows
    # -------------------------------------------------------------------------

    imported_rows = int(
        batch.imported_rows or 0
    )

    if imported_rows <= 0:
        return templates.TemplateResponse(
            request=request,
            name="projects/readiness.html",
            context=_build_context(
                request,
                project,
                "readiness",
                extra={
                    "batch": batch,
                    "matching_summary": None,
                    "matching_runtime": None,
                    "report": None,
                    "matching_error": None,
                    "message": (
                        "این Batch هیچ ردیف پذیرفته‌شده‌ای "
                        "برای ورود به Matching ندارد."
                    ),
                },
            ),
        )

    # -------------------------------------------------------------------------
    # Read existing Matching state BEFORE deciding whether to run engine
    # -------------------------------------------------------------------------

    before_summary = (
        _build_matching_database_summary(
            db,
            batch,
        )
    )

    total_candidates = int(
        before_summary.get(
            "total_candidates",
            0,
        )
        or 0
    )

    processed_candidates = int(
        before_summary.get(
            "processed",
            0,
        )
        or 0
    )

    matching_runtime: dict | None = None
    matching_error: str | None = None
    elapsed_sec: float | None = None

    # -------------------------------------------------------------------------
    # Run Matching only if actual pending evidence exists
    # -------------------------------------------------------------------------

    should_run_matching = (
        total_candidates > 0
        and processed_candidates < total_candidates
    )

    if should_run_matching:
        started_at = time.perf_counter()

        try:
            matching_service = (
                StoreMatchingService(
                    db
                )
            )

            matching_runtime = (
                matching_service.run_for_batch(
                    batch_id=batch.id,
                    project_id=project_id,
                    persist=True,
                )
            )

        except Exception as exc:
            db.rollback()

            matching_error = (
                f"{type(exc).__name__}: {exc}"
            )

        finally:
            elapsed_sec = round(
                time.perf_counter() - started_at,
                3,
            )

    # -------------------------------------------------------------------------
    # Always rebuild from persisted DB state
    # -------------------------------------------------------------------------

    matching_summary = (
        _build_matching_database_summary(
            db,
            batch,
        )
    )

    audit_run: dict | None = None
    audit_report: dict | None = None
    readiness_summary: dict | None = None
    map_geojson: dict = {
        "type": "FeatureCollection",
        "features": [],
    }
    audit_error: str | None = None

    if not matching_error:
        try:
            audit_run = AuditRunner(
                project_id=project_id,
                batch_id=batch.id,
                db=db,
            ).run()
            audit_report = ReportBuilder().build(audit_run)
            readiness_summary = (
                audit_run.get("results", {})
                .get("distribution_readiness")
            )
            map_geojson = audit_run.get("map_geojson") or map_geojson
        except Exception as exc:
            db.rollback()
            audit_error = f"{type(exc).__name__}: {exc}"

    report = audit_report

    # -------------------------------------------------------------------------
    # Message
    # -------------------------------------------------------------------------

    if matching_error:
        message = (
            "اجرای Matching با خطا مواجه شد. "
            "وضعیت ثبت‌شده در پایگاه داده نمایش داده شده است."
        )

    elif audit_error:
        message = (
            "Matching تکمیل شده است، اما اجرای ارزیابی آمادگی "
            "با خطا مواجه شد."
        )

    elif readiness_summary:
        ready_count = int(readiness_summary.get("ready_stores") or 0)
        total_count = int(readiness_summary.get("total_stores") or 0)
        message = (
            f"ارزیابی آمادگی توزیع برای {total_count} فروشگاه انجام شد؛ "
            f"{ready_count} فروشگاه آماده ورود به مرحله تصمیم‌گیری است."
        )

    elif matching_summary["total_candidates"] <= 0:
        message = (
            "برای این Batch هیچ AddressCandidate "
            "قابل پردازشی یافت نشد."
        )

    elif matching_summary["pending"] > 0:
        message = (
            "Matching هنوز برای تمام شواهد این Batch "
            "تکمیل نشده است."
        )

    elif should_run_matching:
        message = (
            "Matching اجرا و نتایج آن در پایگاه داده ثبت شد."
        )

    else:
        message = (
            "Matching این Batch قبلاً تکمیل شده است؛ "
            "نتایج ثبت‌شده بدون اجرای مجدد موتور نمایش داده می‌شوند."
        )

    return templates.TemplateResponse(
        request=request,
        name="projects/readiness.html",
        context=_build_context(
            request,
            project,
            "readiness",
            extra={
                "batch": batch,
                "matching_runtime": matching_runtime,
                "matching_summary": matching_summary,
                "matching_error": matching_error,
                "audit_error": audit_error,
                "matching_was_executed": should_run_matching,
                "report": report,
                "audit_run": audit_run,
                "readiness_summary": readiness_summary,
                "map_geojson_json": json.dumps(
                    map_geojson,
                    ensure_ascii=False,
                    default=str,
                ),
                "message": message,
            },
        ),
    )


@router.post(
    "/{project_id}/readiness",
    response_class=HTMLResponse,
)
async def process_readiness(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """
    Explicit Matching re-run endpoint.

    POST intentionally performs Matching again.
    GET normally only reads persisted state when already complete.

    Future UI can use this endpoint for a
    "Re-run Matching" button.
    """

    await request.form()

    project = _get_project_or_404(
        db,
        project_id,
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    batch = _find_latest_store_batch(
        db,
        project_id,
    )

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No STORE ImportBatch found "
                "for this project."
            ),
        )

    matching_service = (
        StoreMatchingService(
            db
        )
    )

    matching_service.run_for_batch(
        batch_id=batch.id,
        project_id=project_id,
        persist=True,
    )

    return RedirectResponse(
        url=f"/projects/{project_id}/readiness",
        status_code=303,
    )


# =============================================================================
# 4. Decision
# =============================================================================


@router.get(
    "/{project_id}/decision",
    response_class=HTMLResponse,
)
def decision_step(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """Decision step view."""

    project = _get_project_or_404(
        db,
        project_id,
    )

    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": (
                    f"Project with ID {project_id} not found"
                ),
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="projects/decision.html",
        context=_build_context(
            request,
            project,
            "decision",
        ),
    )


@router.post(
    "/{project_id}/decision"
)
async def process_decision(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """Process Decision submission."""

    await request.form()

    return {
        "message": "Decision processed",
        "next_step": "distribution",
    }


# =============================================================================
# 5. Distribution
# =============================================================================


@router.get(
    "/{project_id}/distribution",
    response_class=HTMLResponse,
)
def distribution_step(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """Distribution step view."""

    project = _get_project_or_404(
        db,
        project_id,
    )

    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": (
                    f"Project with ID {project_id} not found"
                ),
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="projects/distribution.html",
        context=_build_context(
            request,
            project,
            "distribution",
        ),
    )


@router.post(
    "/{project_id}/distribution"
)
async def process_distribution(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """Process Distribution submission."""

    await request.form()

    return {
        "message": "Distribution processed",
        "next_step": "results",
    }


# =============================================================================
# 6. Results
# =============================================================================


@router.get(
    "/{project_id}/results",
    response_class=HTMLResponse,
)
def results_step(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """Results step view."""

    project = _get_project_or_404(
        db,
        project_id,
    )

    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": (
                    f"Project with ID {project_id} not found"
                ),
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="projects/results.html",
        context=_build_context(
            request,
            project,
            "results",
        ),
    )


@router.post(
    "/{project_id}/results"
)
async def process_results(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """Process Results submission."""

    await request.form()

    return {
        "message": "Results processed",
        "next_step": "profiling",
    }


# =============================================================================
# 7. Profiling
# =============================================================================


@router.get(
    "/{project_id}/profiling",
    response_class=HTMLResponse,
)
def profiling_step(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """Profiling step view."""

    project = _get_project_or_404(
        db,
        project_id,
    )

    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": (
                    f"Project with ID {project_id} not found"
                ),
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="projects/profiling.html",
        context=_build_context(
            request,
            project,
            "profiling",
        ),
    )


@router.post(
    "/{project_id}/profiling"
)
async def process_profiling(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """Process Profiling submission."""

    await request.form()

    return {
        "message": "Profiling processed",
        "next_step": "scenario_compare",
    }


# =============================================================================
# 8. Scenario Compare
# =============================================================================


@router.get(
    "/{project_id}/scenario_compare",
    response_class=HTMLResponse,
)
def scenario_compare_step(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """Scenario Compare step view."""

    project = _get_project_or_404(
        db,
        project_id,
    )

    if not project:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "request": request,
                "message": (
                    f"Project with ID {project_id} not found"
                ),
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="projects/scenario_compare.html",
        context=_build_context(
            request,
            project,
            "scenario_compare",
        ),
    )


@router.post(
    "/{project_id}/scenario_compare"
)
async def process_scenario_compare(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    """Process Scenario Compare submission."""

    await request.form()

    return {
        "message": "Scenario compare processed",
        "next_step": "complete",
    }


# =============================================================================
# CRUD API Endpoints
# =============================================================================


@router.get(
    "/api/"
)
def read_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Read projects list."""

    projects = (
        db.query(Project)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return projects


@router.get(
    "/api/{project_id}"
)
def read_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    """Read one project."""

    project = (
        db.query(Project)
        .filter(
            Project.id == project_id
        )
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return project


@router.post(
    "/api/"
)
def create_project(
    name: str = Form(...),
    description: str | None = Form(None),
    code: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Create project through current development API."""

    clean_name = (
        name.strip()
    )

    db_project = Project(
        company_id=1,
        name=clean_name,
        description=(
            description.strip()
            if description and description.strip()
            else None
        ),
        code=(
            code.strip()
            if code and code.strip()
            else None
        ),
    )

    db.add(
        db_project
    )

    db.commit()

    db.refresh(
        db_project
    )

    return db_project


@router.delete(
    "/api/{project_id}"
)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    """Delete project."""

    db_project = (
        db.query(Project)
        .filter(
            Project.id == project_id
        )
        .first()
    )

    if db_project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    db.delete(
        db_project
    )

    db.commit()

    return {
        "message": "Project deleted",
    }
