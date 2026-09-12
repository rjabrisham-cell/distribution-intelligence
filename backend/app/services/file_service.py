from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.file import File
from app.repositories.file_repository import FileRepository


class FileService:
    """
    File storage service — handles disk I/O and DB metadata.

    Responsibilities:
        - Store uploaded files on disk
        - Record file metadata in the database
        - Delete files (disk + DB)
        - Query files by entity (polymorphic)
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = FileRepository(db)

        self.upload_root = Path(settings.UPLOAD_DIR)
        self.upload_root.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # Create File  (metadata-only, no disk write)
    # ---------------------------------------------------------

    def create_file(
        self,
        *,
        entity_type: str,
        entity_id: int,
        category: str,
        original_name: str,
        stored_name: str,
        file_path: str,
        content_type: str,
        file_size: int,
        uploaded_by: int | None = None,
    ) -> File:
        """
        Create a File record *without* writing to disk.

        Use this when the file is already on disk or for testing.
        For full upload with disk write, use :meth:`upload`.
        """
        db_file = File(
            entity_type=entity_type,
            entity_id=entity_id,
            category=category,
            original_name=original_name,
            stored_name=stored_name,
            file_path=file_path,
            content_type=content_type,
            file_size=file_size,
            uploaded_by=uploaded_by,
        )
        return self.repository.create(db_file)

    # ---------------------------------------------------------
    # Upload  (async — disk write + DB record)
    # ---------------------------------------------------------

    async def upload(
        self,
        *,
        entity_type: str,
        entity_id: int,
        category: str,
        upload_file: UploadFile,
        uploaded_by: int | None = None,
    ) -> File:
        """
        Store an uploaded file on disk and persist its metadata.

        Returns the created File ORM instance.
        """
        extension = Path(upload_file.filename).suffix.lower()
        stored_name = f"{uuid.uuid4().hex}{extension}"

        category_dir = (
            self.upload_root
            / entity_type.upper()
            / str(entity_id)
            / category
        )
        category_dir.mkdir(parents=True, exist_ok=True)

        destination = category_dir / stored_name

        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        file_size = destination.stat().st_size

        db_file = File(
            entity_type=entity_type,
            entity_id=entity_id,
            category=category,
            original_name=upload_file.filename,
            stored_name=stored_name,
            file_path=str(destination),
            content_type=upload_file.content_type
            or "application/octet-stream",
            file_size=file_size,
            uploaded_by=uploaded_by,
        )

        return self.repository.create(db_file)

    # ---------------------------------------------------------
    # Get File
    # ---------------------------------------------------------

    def get_file(self, file_id: int) -> File | None:
        """Retrieve a single File by its primary key."""
        return self.repository.get(file_id)

    def get(self, file_id: int) -> File | None:
        """Alias for :meth:`get_file`."""
        return self.get_file(file_id)

    # ---------------------------------------------------------
    # Get By Entity
    # ---------------------------------------------------------

    def get_by_entity(
        self,
        *,
        entity_type: str,
        entity_id: int,
    ) -> list[File]:
        """
        Return all files attached to a specific entity.

        This is the primary query method used by routers (e.g. Project Detail).
        """
        return self.repository.get_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
        )

    def get_entity_files(
        self,
        *,
        entity_type: str,
        entity_id: int,
    ) -> list[File]:
        """Alias for :meth:`get_by_entity` (backward-compat)."""
        return self.get_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
        )

    # ---------------------------------------------------------
    # List Files
    # ---------------------------------------------------------

    def list_files(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[File]:
        """Return a paginated list of all files."""
        return self.repository.list(skip=skip, limit=limit)

    # ---------------------------------------------------------
    # Count Files
    # ---------------------------------------------------------

    def count_files(
        self,
        *,
        entity_type: str | None = None,
        entity_id: int | None = None,
    ) -> int:
        """
        Count files, optionally scoped to an entity.

        If both *entity_type* and *entity_id* are provided the count
        is scoped to that entity; otherwise returns the global count.
        """
        if entity_type is not None and entity_id is not None:
            return self.repository.count_by_entity(
                entity_type, entity_id
            )

        return len(self.repository.list(limit=10_000_000))

    # ---------------------------------------------------------
    # Delete File
    # ---------------------------------------------------------

    def delete_file(self, file_id: int) -> bool:
        """
        Delete a file from disk and database.

        Returns True if the file was found and deleted, False otherwise.
        """
        file = self.repository.get(file_id)

        if file is None:
            return False

        if file.entity_type == "PROJECT" and file.category == "stores":
            self.repository.delete(file)
            return True

        path = Path(file.file_path)

        if path.exists():
            path.unlink()

        self.repository.delete(file)

        return True

    def delete(self, file_id: int) -> bool:
        """Alias for :meth:`delete_file` (backward-compat)."""
        return self.delete_file(file_id)
