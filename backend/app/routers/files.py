from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import (
    FileResponse,
    RedirectResponse,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.file_service import FileService
from app.services.file_storage_service import FileStorageService


router = APIRouter(
    prefix="/files",
    tags=["Files"],
)


# -------------------------------------------------------
# Download File
# -------------------------------------------------------

@router.get(
    "/{file_id}/download",
)
async def download_file(
    file_id: int,
    db: Session = Depends(get_db),
):

    file_service = FileService(db)

    file_record = file_service.get_by_id(file_id)

    if file_record is None:
        raise HTTPException(
            status_code=404,
            detail="File not found.",
        )

    if not FileStorageService.exists(file_record.file_path):
        raise HTTPException(
            status_code=404,
            detail="File not found on disk.",
        )

    return FileResponse(
        path=file_record.file_path,
        filename=file_record.original_name,
        media_type=file_record.content_type,
    )


# -------------------------------------------------------
# Delete File
# -------------------------------------------------------

@router.post(
    "/{file_id}/delete",
)
async def delete_file(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db),
):

    file_service = FileService(db)

    file_record = file_service.get_by_id(file_id)

    if file_record is None:
        raise HTTPException(
            status_code=404,
            detail="File not found.",
        )

    referer = request.headers.get(
        "referer",
        "/projects",
    )

    file_service.delete(file_id)

    return RedirectResponse(
        url=referer,
        status_code=303,
    )