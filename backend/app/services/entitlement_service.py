# app/services/entitlement_service.py

from sqlalchemy.orm import Session

from app.repositories.project_repository import ProjectRepository


class EntitlementService:
    def __init__(self, db: Session, max_projects_free: int = 2):
        self.project_repository = ProjectRepository(db)
        self.max_projects_free = max_projects_free

    def assert_can_create_project(self, company_id: int) -> None:
        count = self.project_repository.count_by_company(company_id)
        if count >= self.max_projects_free:
            raise ValueError("Free plan limit reached.")
