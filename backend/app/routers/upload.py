from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.request_file_service import RequestFileService

router = APIRouter(
    prefix="/uploads",
    tags=["Uploads"],
)


@router.post("/{request_id}")
async def upload_request_files(
    request_id: int,
    file_type: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File(description="Upload files")],
    db: Session = Depends(get_db),
):
    result = []

    for upload_file in files:
        item = await RequestFileService.upload(
            db=db,
            request_id=request_id,
            file_type=file_type,
            upload_file=upload_file,
        )

        result.append(
            {
                "id": item.id,
                "original_name": item.original_name,
                "stored_name": item.stored_name,
                "file_type": item.file_type,
            }
        )

    return {
        "success": True,
        "files": result,
    }