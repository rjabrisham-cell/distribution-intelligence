from typing import Annotated, Union

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile as FastAPIUploadFile
)
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.core.database import get_db
from app.models.file import File
from app.schemas.import_schema import (
    EntityTypeEnum,
    ImportStartRequest,
)
from app.services.file_service import FileService
from app.services.import_service import ImportService
from app.services.project_service import ProjectService

router = APIRouter(
    prefix="/uploads",
    tags=["Uploads"],
)

# -------------------------------------------------------
# Upload Files To Project
# -------------------------------------------------------

@router.post(
    "/project/{project_id}",
)
async def upload_project_files(
    project_id: int,
    category: Annotated[
        str,
        Form(),
    ],
    files: Annotated[
        Union[FastAPIUploadFile, list[FastAPIUploadFile], None],
        File(),
    ] = None,
    province_id: Annotated[
        int | None,
        Form(),
    ] = None,
    city_id: Annotated[
        int | None,
        Form(),
    ] = None,
    db: Session = Depends(get_db),
):

    # ── Normalize: any form → list[StarletteUploadFile] ──
    if files is None:
        files = []
    elif isinstance(files, StarletteUploadFile):
        files = [files]
    elif not isinstance(files, list):
        files = list(files)

    # ── Debug (temporary) ──────────────────────────
    print(f"[DEBUG] files type: {type(files).__name__}")
    print(f"[DEBUG] files count: {len(files)}")

    project_service = ProjectService(db)

    project = project_service.get_by_id(project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    file_service = FileService(db)

    trial_account = db.info.get("trial_account_id")
    trial_hash = None
    if trial_account:
        from hashlib import sha256
        from app.core.trial_policy import policy
        from app.services.entitlement_service import EntitlementService
        from app.services.trial_file_service import validate_trial_xlsx
        EntitlementService(db).assert_trial(trial_account, project_id)
        if category != "stores" or len(files) != 1:
            raise HTTPException(400, "فقط یک فایل فروشگاه بارگذاری کنید.")
        payload = await files[0].read(policy.file_bytes + 1)
        validate_trial_xlsx(files[0].filename or "", payload)
        await files[0].seek(0)
        trial_hash = sha256(payload).hexdigest()
        if project.trial_file_hash == trial_hash and project.active_store_batch_id:
            return RedirectResponse(url=f"/projects/{project_id}/validation", status_code=303)

    uploaded_files: list[File] = []

    for upload_file in files:

        if upload_file is None:
            continue

        if upload_file.filename == "":
            continue

        file_record = await file_service.upload(
            entity_type="PROJECT",
            entity_id=project_id,
            category=category,
            upload_file=upload_file,
        )

        uploaded_files.append(file_record)

    if not uploaded_files:
        raise HTTPException(
            status_code=400,
            detail="No valid files selected.",
        )

    # ---------------------------------------------------
    # Build ImportBatch for Store category.
    # ---------------------------------------------------

    if category == "stores":

        import_service = ImportService(db)

        for file_record in uploaded_files:

            request = ImportStartRequest(
                entity_type=EntityTypeEnum.STORE,
                file_id=file_record.id,
                column_mapping={},       # ← دیکشنری خالی، نه None
                skip_validation=False,
            )

            start_response = import_service.start_import(
                request=request,
                file_path=file_record.file_path,
            )

            import_service.process_batch(
                batch_id=start_response.batch_id,
                province_id=province_id,
                city_id=city_id,
            )
            if trial_account:
                from app.models.import_batch import ImportBatch
                batch = db.get(ImportBatch, start_response.batch_id)
                status = getattr(batch.status, "value", batch.status)
                if str(status).lower() != "completed" or not batch.imported_rows:
                    raise HTTPException(400, "پردازش فایل کامل نشد؛ فایل را اصلاح کنید. سهمیه مصرف نشده است.")
                project.trial_file_hash = trial_hash
                project.trial_state = "UPLOADED"
                project.trial_result_batch_id = None
                db.commit()

    # ---------------------------------------------------
    # Redirect to Validation step
    # ---------------------------------------------------

    return RedirectResponse(
        url=f"/projects/{project_id}/validation",
        status_code=303,
    )

# -------------------------------------------------------
# Download File
# -------------------------------------------------------

@router.get(
    "/file/{file_id}/download",
)
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
):
    """
    Download a file by its ID.
    """
    file_service = FileService(db)

    file = file_service.get(file_id)

    if file is None:
        raise HTTPException(
            status_code=404,
            detail="File not found.",
        )

    path = Path(file.file_path)

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="File not found on disk.",
        )

    return FileResponse(
        path=path,
        filename=file.original_name,
        media_type=file.content_type,
    )

# -------------------------------------------------------
# Delete File
# -------------------------------------------------------

@router.post(
    "/file/{file_id}/delete",
)
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a file from disk and database.
    Redirects back to the project Intake step.
    """
    file_service = FileService(db)

    file = file_service.get(file_id)

    if file is None:
        raise HTTPException(
            status_code=404,
            detail="File not found.",
        )

    entity_id = file.entity_id

    file_service.delete(file_id)

    return RedirectResponse(
        url=f"/projects/{entity_id}/intake",
        status_code=303,
    )
