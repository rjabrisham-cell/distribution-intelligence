from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.request_file import RequestFile
from app.repositories.request_file_repository import RequestFileRepository
from app.services.file_storage_service import FileStorageService


class RequestFileService:

    @staticmethod
    async def upload(
        db: Session,
        request_id: int,
        file_type: str,
        upload_file: UploadFile,
    ):

        stored_name, path, size = await FileStorageService.save(
            request_id,
            upload_file,
        )

        entity = RequestFile(
            request_id=request_id,
            file_type=file_type,
            original_name=upload_file.filename,
            stored_name=stored_name,
            file_path=path,
            content_type=upload_file.content_type,
            file_size=size,
        )

        return RequestFileRepository.create(db, entity)