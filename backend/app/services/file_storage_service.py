from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


class FileStorageService:
    BASE_UPLOAD_PATH = Path("uploads")

    @classmethod
    async def save(
        cls,
        request_id: int,
        upload_file: UploadFile,
    ) -> tuple[str, str, int]:
        folder = cls.BASE_UPLOAD_PATH / str(request_id)
        folder.mkdir(parents=True, exist_ok=True)

        extension = Path(upload_file.filename).suffix
        stored_name = f"{uuid4().hex}{extension}"

        destination = folder / stored_name

        content = await upload_file.read()

        destination.write_bytes(content)

        return (
            stored_name,
            str(destination),
            len(content),
        )