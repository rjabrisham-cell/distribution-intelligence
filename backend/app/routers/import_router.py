"""
Router for Data Import Engine.
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.services.import_service import ImportService

router = APIRouter(
    prefix="/import",
    tags=["Data Import"],
)


# --------------------------------------------------------------------------- #
#  HTML pages
# --------------------------------------------------------------------------- #

@router.get("", response_class=HTMLResponse)
async def import_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="import.html",
        context={},
    )


@router.get("/batches", response_class=HTMLResponse)
async def list_batches(request: Request, db: Session = Depends(get_db)):
    import_service = ImportService(db)
    batches = import_service.get_all_batches()
    return templates.TemplateResponse(
        request=request,
        name="import/batches.html",
        context={"batches": batches},
    )


@router.get("/batches/{batch_id}", response_class=HTMLResponse)
async def batch_detail(
    request: Request,
    batch_id: int,
    db: Session = Depends(get_db),
):
    import_service = ImportService(db)
    batch = import_service.get_batch(batch_id)
    if not batch:
        return templates.TemplateResponse(
            request=request,
            name="import/batch_detail.html",
            context={"error": f"Batch #{batch_id} not found."},
            status_code=404,
        )

    summary = import_service.get_batch_summary(batch_id)
    return templates.TemplateResponse(
        request=request,
        name="import/batch_detail.html",
        context={"batch": batch, "summary": summary},
    )


# --------------------------------------------------------------------------- #
#  Actions
# --------------------------------------------------------------------------- #

@router.post("/upload")
async def upload_import_file(
    request: Request,
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    import_service = ImportService(db)

    try:
        batch = await import_service.import_file(
            upload_file=file,
            entity_type=entity_type,
            description=description,
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request=request,
            name="import.html",
            context={"error_message": f"خطا در پردازش فایل: {exc}"},
            status_code=400,
        )

    return RedirectResponse(
        url=router.url_path_for("batch_detail", batch_id=batch.id),
        status_code=303,
    )


# --------------------------------------------------------------------------- #
#  JSON endpoints
# --------------------------------------------------------------------------- #

@router.get("/api/batches/{batch_id}")
async def batch_status_api(batch_id: int, db: Session = Depends(get_db)):
    import_service = ImportService(db)
    batch = import_service.get_batch(batch_id)
    if not batch:
        return JSONResponse(content={"error": "Not found"}, status_code=404)

    return JSONResponse(
        content={
            "id": batch.id,
            "entity_type": batch.entity_type,
            "status": batch.status,
            "total_rows": batch.total_rows,
            "success_rows": batch.success_rows,
            "error_rows": batch.error_rows,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
        }
    )


@router.get("/api/batches/recent")
async def recent_batches(db: Session = Depends(get_db)):
    import_service = ImportService(db)
    batches = import_service.get_recent_batches(limit=5)

    return JSONResponse(
        content=[
            {
                "id": b.id,
                "entity_type": b.entity_type,
                "status": b.status,
                "description": b.description,
                "total_rows": b.total_rows,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in batches
        ]
    )
