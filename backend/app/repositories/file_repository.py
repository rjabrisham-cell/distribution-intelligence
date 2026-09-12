from __future__ import annotations          # 🆕 اضافه شد

from typing import Optional

from sqlalchemy.orm import Session

from app.models.file import File


class FileRepository:
    """Repository for File model — polymorphic file attachments."""

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------
    # Create
    # -------------------------------------------------------

    def create(self, file: File) -> File:
        """Persist a new File record."""
        self.db.add(file)
        self.db.commit()
        self.db.refresh(file)
        return file

    # -------------------------------------------------------
    # Get By ID
    # -------------------------------------------------------

    def get(self, file_id: int) -> Optional[File]:
        """Retrieve a single File by its primary key."""
        return self.db.query(File).filter(File.removed_at.is_(None)).filter(File.id == file_id).first()

    def get_by_id(self, file_id: int) -> Optional[File]:
        """Alias for get()."""
        return self.get(file_id)

    # -------------------------------------------------------
    # List
    # -------------------------------------------------------

    def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[File]:
        """Return a paginated list of all files."""
        return (
            self.db.query(File).filter(File.removed_at.is_(None))
            .order_by(File.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    # -------------------------------------------------------
    # Get Files By Entity  (polymorphic — any entity type)
    # -------------------------------------------------------

    def get_by_entity(
        self,
        entity_type: str,
        entity_id: int,
    ) -> list[File]:
        """Return all files attached to a specific entity."""
        return (
            self.db.query(File).filter(File.removed_at.is_(None))
            .filter(
                File.entity_type == entity_type,
                File.entity_id == entity_id,
            )
            .order_by(File.created_at.desc())
            .all()
        )

    # -------------------------------------------------------
    # Count By Entity
    # -------------------------------------------------------

    def count_by_entity(
        self,
        entity_type: str,
        entity_id: int,
    ) -> int:
        """Return the number of files attached to an entity."""
        return (
            self.db.query(File).filter(File.removed_at.is_(None))
            .filter(
                File.entity_type == entity_type,
                File.entity_id == entity_id,
            )
            .count()
        )

    # -------------------------------------------------------
    # Get By Project  (convenience — delegates to get_by_entity)
    # -------------------------------------------------------

    def get_by_project(self, project_id: int) -> list[File]:
        """Return all files attached to a project."""
        return self.get_by_entity("PROJECT", project_id)

    # -------------------------------------------------------
    # Get By Category
    # -------------------------------------------------------

    def get_by_category(
        self,
        project_id: int,
        category: str,
    ) -> list[File]:
        """Return project files filtered by category."""
        return (
            self.db.query(File).filter(File.removed_at.is_(None))
            .filter(
                File.entity_type == "PROJECT",
                File.entity_id == project_id,
                File.category == category,
            )
            .order_by(File.created_at.desc())
            .all()
        )

    # -------------------------------------------------------
    # Count By Project
    # -------------------------------------------------------

    def count_by_project(self, project_id: int) -> int:
        """Return the number of files attached to a project."""
        return self.count_by_entity("PROJECT", project_id)

    # -------------------------------------------------------
    # Delete
    # -------------------------------------------------------

    def delete(self, file: File) -> None:
        """Remove a File record from the database."""
        if file.entity_type == "PROJECT" and file.category == "stores":
            from app.repositories.store_dataset_repository import StoreDatasetRepository
            StoreDatasetRepository(self.db).remove_file(file)
            return
        self.db.delete(file)
        self.db.commit()