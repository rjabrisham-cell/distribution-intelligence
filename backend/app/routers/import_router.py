"""
Router for Data Import Engine.

MVP scope:
    Store / Supermarket data import and readiness preparation.

Flow:

Upload
  |
FileStorageService
  |
File Model
  |
ImportService.start_import()
  |
ImportService.process_batch()
  |
Batch Detail / Validation / Readiness
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    FileResponse,
)

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import EntityType
from app.core.templates import templates

from app.models.file import File as FileModel

from app.schemas.import_schema import (
    ImportStartRequest,
    EntityTypeEnum,
)

from app.services.file_storage_service import (
    FileStorageService,
)

from app.services.import_service import (
    ImportService,
)


router = APIRouter(
    prefix="/import",
    tags=["Data Import"],
)


# ==========================================================
# Helpers
# ==========================================================


def _enum_value(value):
    """
    Safely return enum.value or the raw value.
    """
    return (
        value.value
        if hasattr(value, "value")
        else value
    )


# ==========================================================
# HTML PAGES
# ==========================================================


@router.get(
    "",
    response_class=HTMLResponse,
)
async def import_page(
    request: Request,
):
    """
    Main data import page.
    """

    return templates.TemplateResponse(
        request=request,
        name="import.html",
        context={},
    )


@router.get(
    "/batches",
    response_class=HTMLResponse,
)
async def list_batches(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Display all import batches.
    """

    service = ImportService(db)

    batches = service.get_all_batches()

    return templates.TemplateResponse(
        request=request,
        name="import/batches.html",
        context={
            "batches": batches,
        },
    )


@router.get(
    "/batches/{batch_id}",
    response_class=HTMLResponse,
)
async def batch_detail(
    request: Request,
    batch_id: int,
    db: Session = Depends(get_db),
):
    """
    Display details of a single import batch.
    """

    service = ImportService(db)

    batch = service.get_batch(
        batch_id
    )

    if not batch:
        return templates.TemplateResponse(
            request=request,
            name="import/batch_detail.html",
            context={
                "error": f"Batch #{batch_id} not found.",
            },
            status_code=404,
        )

    summary = service.get_batch_summary(
        batch_id
    )

    return templates.TemplateResponse(
        request=request,
        name="import/batch_detail.html",
        context={
            "batch": batch,
            "summary": summary,
        },
    )


# ==========================================================
# STORE TEMPLATE
# ==========================================================


@router.get(
    "/template/store"
)
async def download_store_template():
    """
    Download the Store Excel template.
    """

    path = Path(
        "app/static/templates/store_template.xlsx"
    )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Template not found",
        )

    return FileResponse(
        path=str(path),
        filename="store_template.xlsx",
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )


# ==========================================================
# UPLOAD / IMPORT
# ==========================================================


@router.post(
    "/upload"
)
async def upload_import_file(
    request: Request,
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload and process an import file.

    MVP currently supports Store / Supermarket data only.
    """

    # ------------------------------------------------------
    # Normalize entity type
    # ------------------------------------------------------

    normalized_entity_type = (
        entity_type.strip().lower()
    )

    # ------------------------------------------------------
    # MVP restriction
    # ------------------------------------------------------

    if normalized_entity_type != EntityType.STORE.value:
        return templates.TemplateResponse(
            request=request,
            name="import.html",
            context={
                "error_message": (
                    "در نسخه MVP فقط ورود اطلاعات "
                    "فروشگاه‌ها فعال است."
                ),
            },
            status_code=400,
        )

    # ------------------------------------------------------
    # Save physical file
    # ------------------------------------------------------

    try:

        stored_name, file_path, file_size = (
            await FileStorageService.save(
                entity_type="REQUEST",
                entity_id=0,
                category="stores",
                upload_file=file,
            )
        )

    except Exception as exc:

        return templates.TemplateResponse(
            request=request,
            name="import.html",
            context={
                "error_message": (
                    f"خطا در ذخیره فایل: {exc}"
                ),
            },
            status_code=400,
        )

    # ------------------------------------------------------
    # Create File record
    # ------------------------------------------------------

    try:

        file_record = FileModel(
            entity_type="REQUEST",
            entity_id=0,
            category="stores",
            original_name=(
                file.filename
                or "upload.xlsx"
            ),
            stored_name=stored_name,
            file_path=file_path,
            content_type=(
                file.content_type
                or "application/octet-stream"
            ),
            file_size=file_size,
        )

        db.add(file_record)
        db.commit()
        db.refresh(file_record)

    except Exception as exc:

        db.rollback()

        return templates.TemplateResponse(
            request=request,
            name="import.html",
            context={
                "error_message": (
                    f"خطا در ثبت فایل در دیتابیس: {exc}"
                ),
            },
            status_code=400,
        )

    # ------------------------------------------------------
    # Start Import
    # ------------------------------------------------------

    try:

        service = ImportService(db)

        start_request = ImportStartRequest(
            entity_type=EntityTypeEnum.STORE,
            file_id=file_record.id,
            skip_validation=False,
        )

        result = service.start_import(
            request=start_request,
            file_path=file_path,
        )

        # --------------------------------------------------
        # Process Batch
        # --------------------------------------------------

        service.process_batch(
            result.batch_id
        )

    except Exception as exc:

        db.rollback()

        return templates.TemplateResponse(
            request=request,
            name="import.html",
            context={
                "error_message": (
                    f"خطا در پردازش فایل: {exc}"
                ),
            },
            status_code=400,
        )

    # ------------------------------------------------------
    # Continue existing workflow
    # ------------------------------------------------------

    return RedirectResponse(
        url=router.url_path_for(
            "batch_detail",
            batch_id=result.batch_id,
        ),
        status_code=303,
    )


# ==========================================================
# BATCH STATUS API
# ==========================================================


@router.get(
    "/api/batches/{batch_id}"
)
async def batch_status_api(
    batch_id: int,
    db: Session = Depends(get_db),
):
    """
    Return current processing status of an ImportBatch.
    """

    service = ImportService(db)

    progress = service.get_batch_progress(
        batch_id
    )

    return {
        "batch_id": progress.batch_id,
        "status": _enum_value(
            progress.status
        ),
        "total_rows": progress.total_rows,
        "processed_rows": progress.processed_rows,
        "error_count": progress.error_count,
        "progress_percent": progress.progress_percent,
        "elapsed_seconds": progress.elapsed_seconds,
        "estimated_remaining_seconds": (
            progress.estimated_remaining_seconds
        ),
    }