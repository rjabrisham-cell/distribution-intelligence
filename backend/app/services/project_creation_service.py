# app/services/project_creation_service.py

from typing import Optional

from sqlalchemy.orm import Session

from app.models.project import Project, ProjectStatus
from app.repositories.project_repository import ProjectRepository
from app.services.entitlement_service import EntitlementService
from app.services.onboarding_service import OnboardingService


class ProjectCreationService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repository = ProjectRepository(db)
        self.onboarding_service = OnboardingService(db)
        self.entitlement_service = EntitlementService(db)

    def create_project(
        self,
        mobile: str,
        company_name: str,
        project_name: str,
        description: Optional[str] = None,
    ) -> Project:
        _, company = self.onboarding_service.get_or_create_account_and_company(
            mobile=mobile,
            company_name=company_name,
        )

        self.entitlement_service.assert_can_create_project(company.id)

        existing = self.project_repository.get_by_company_and_name(
            company_id=company.id,
            name=project_name,
        )
        if existing:
            raise ValueError("Project with this name already exists.")

        project = Project(
            company_id=company.id,
            name=project_name,
            description=description,
            status=ProjectStatus.DRAFT,
        )

        return self.project_repository.create(project)
