# app/services/project_query_service.py

from sqlalchemy.orm import Session

from app.repositories.project_repository import ProjectRepository


class ProjectQueryService:
    def __init__(self, db: Session):
        self.project_repository = ProjectRepository(db)

    def get_all(self):
        return self.project_repository.get_all()

    def get_by_id(self, project_id: int):
        return self.project_repository.get_by_id(project_id)

    def get_by_company(self, company_id: int):
        return self.project_repository.get_by_company(company_id)

    def count(self) -> int:
        return self.project_repository.count()

    def exists(self, project_id: int) -> bool:
        return self.project_repository.exists(project_id)
