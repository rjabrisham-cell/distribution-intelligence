from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.file_service import FileService
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
        list[UploadFile],
        File(),
    ],
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

    uploaded_count = 0

    for upload_file in files:

        if upload_file is None:
            continue

        if upload_file.filename == "":
            continue

        await file_service.upload(
            entity_type="PROJECT",
            entity_id=project_id,
            category=category,
            upload_file=upload_file,
        )

        uploaded_count += 1

    if uploaded_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No valid files selected.",
        )

    return RedirectResponse(
        url=f"/projects/{project_id}/intake",
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
