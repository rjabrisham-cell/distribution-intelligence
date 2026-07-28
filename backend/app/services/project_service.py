# app/services/project_service.py

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.project import Project, ProjectStatus
from app.services.project_creation_service import ProjectCreationService
from app.services.project_lifecycle_service import ProjectLifecycleService
from app.services.project_query_service import ProjectQueryService


class ProjectService:
    """
    Facade موقت برای حفظ backward compatibility
    """

    def __init__(self, db: Session):
        self.creation_service = ProjectCreationService(db)
        self.query_service = ProjectQueryService(db)
        self.lifecycle_service = ProjectLifecycleService(db)

    def create_project(
        self,
        mobile: str,
        company_name: str,
        project_name: str,
        description: Optional[str] = None,
    ) -> Project:
        return self.creation_service.create_project(
            mobile=mobile,
            company_name=company_name,
            project_name=project_name,
            description=description,
        )

    def get_by_id(self, project_id: int) -> Optional[Project]:
        return self.query_service.get_by_id(project_id)

    def get_all(self) -> List[Project]:
        return self.query_service.get_all()

    def get_by_company(self, company_id: int) -> List[Project]:
        return self.query_service.get_by_company(company_id)

    def update_project(self, project_id: int, **kwargs):
        return self.lifecycle_service.update_project(project_id, **kwargs)

    def update_status(self, project_id: int, status: ProjectStatus):
        return self.lifecycle_service.update_status(project_id, status)

    def delete_project(self, project_id: int):
        return self.lifecycle_service.delete_project(project_id)

    def exists(self, project_id: int) -> bool:
        return self.query_service.exists(project_id)

    def count(self) -> int:
        return self.query_service.count()
