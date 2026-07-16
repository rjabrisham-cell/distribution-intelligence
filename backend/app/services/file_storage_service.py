from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


class FileStorageService:
    """
    مدیریت ذخیره‌سازی فایل‌ها روی دیسک

    ساختار ذخیره‌سازی:

    uploads/
        PROJECT/
            1/
                orders/
                fleet/

        REQUEST/
            15/
                orders/
                gps/
    """

    BASE_UPLOAD_PATH = Path("uploads")

    @classmethod
    async def save(
        cls,
        entity_type: str,
        entity_id: int,
        category: str,
        upload_file: UploadFile,
    ) -> tuple[str, str, int]:
        """
        ذخیره فایل روی دیسک

        خروجی:
            (
                stored_name,
                file_path,
                file_size,
            )
        """

        folder = (
            cls.BASE_UPLOAD_PATH
            / entity_type.upper()
            / str(entity_id)
            / category
        )

        folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        original_name = upload_file.filename or "file"

        extension = Path(original_name).suffix

        stored_name = f"{uuid4().hex}{extension}"

        destination = folder / stored_name

        content = await upload_file.read()

        destination.write_bytes(content)

        return (
            stored_name,
            str(destination),
            len(content),
        )

    @classmethod
    def delete(
        cls,
        file_path: str,
    ) -> bool:
        """
        حذف فایل از دیسک
        """

        path = Path(file_path)

        if not path.exists():
            return False

        path.unlink()

        return True

    @classmethod
    def exists(
        cls,
        file_path: str,
    ) -> bool:
        """
        بررسی وجود فایل
        """

        return Path(file_path).exists()