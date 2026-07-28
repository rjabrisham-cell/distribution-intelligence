# app/services/project_lifecycle_service.py

from typing import Optional

from sqlalchemy.orm import Session

from app.models.project import ProjectStatus
from app.repositories.project_repository import ProjectRepository


class ProjectLifecycleService:
    def __init__(self, db: Session):
        self.project_repository = ProjectRepository(db)

    def update_project(self, project_id: int, **kwargs):
        allowed_fields = {"name", "description", "status"}

        clean_data = {
            key: value
            for key, value in kwargs.items()
            if key in allowed_fields and value is not None
        }

        if "status" in clean_data and isinstance(clean_data["status"], str):
            clean_data["status"] = ProjectStatus(clean_data["status"])

        return self.project_repository.update(project_id, **clean_data)

    def update_status(self, project_id: int, status: ProjectStatus):
        return self.project_repository.update(project_id, status=status)

    def delete_project(self, project_id: int):
        return self.project_repository.delete(project_id)
