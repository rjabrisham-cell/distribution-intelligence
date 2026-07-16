from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.project import (
    Project,
    ProjectStatus,
)
from app.repositories.account_repository import AccountRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.project_repository import (
    ProjectRepository,
)


class ProjectService:

    def __init__(self, db: Session):
        self.repository = ProjectRepository(db)
        self.account_repository = AccountRepository(db)
        self.company_repository = CompanyRepository(db)

    # --------------------------------------------------
    # Create
    # --------------------------------------------------

    def create_project(
        self,
        mobile: str,
        company_name: str,
        project_name: str,
        description: Optional[str] = None,
    ) -> Project:

        # ── Account: find or create ──────────────────────
        account = self.account_repository.get_by_mobile(mobile)

        if not account:
            account = self.account_repository.create(mobile)

        # ── Company: find or create ──────────────────────
        company = self.company_repository.get_by_account(account.id)

        if not company:
            company = self.company_repository.create(
                account_id=account.id,
                name=company_name,
            )

        # ── Free plan limit ──────────────────────────────
        count = self.repository.count_by_company(company.id)

        if count >= 2:
            raise ValueError(
                "Free plan limit reached."
            )

        # ── Check duplicate name ─────────────────────────
        existing = self.repository.get_by_name(
            company_id=company.id,
            name=project_name,
        )

        if existing:
            raise ValueError(
                f"Project '{project_name}' already exists."
            )

        # ── Create project ───────────────────────────────
        project = Project(
            company_id=company.id,
            name=project_name,
            description=description,
            status=ProjectStatus.DRAFT,
        )

        return self.repository.create(project)

    # --------------------------------------------------
    # Read
    # --------------------------------------------------

    def get_by_id(
        self,
        project_id: str,
    ) -> Optional[Project]:

        return self.repository.get_by_id(project_id)

    def get_all(
        self,
    ) -> List[Project]:

        return self.repository.get_all()

    def get_by_company(
        self,
        company_id: str,
    ) -> List[Project]:

        return self.repository.get_by_company(company_id)

    # --------------------------------------------------
    # Update
    # --------------------------------------------------

    def update_project(
        self,
        project_id: str,
        **kwargs,
    ) -> Optional[Project]:

        project = self.repository.get_by_id(project_id)

        if project is None:
            return None

        allowed_fields = {
            "name",
            "description",
            "status",
        }

        for key, value in kwargs.items():

            if key not in allowed_fields:
                continue

            if value is None:
                continue

            if (
                key == "status"
                and isinstance(value, str)
            ):
                value = ProjectStatus(value)

            setattr(
                project,
                key,
                value,
            )

        return self.repository.update(project)

    def update_status(
        self,
        project_id: str,
        status: ProjectStatus,
    ) -> Optional[Project]:

        project = self.repository.get_by_id(project_id)

        if project is None:
            return None

        project.status = status

        return self.repository.update(project)

    # --------------------------------------------------
    # Delete
    # --------------------------------------------------

    def delete_project(
        self,
        project_id: str,
    ) -> bool:

        project = self.repository.get_by_id(project_id)

        if project is None:
            return False

        self.repository.delete(project)

        return True

    # --------------------------------------------------
    # Utility
    # --------------------------------------------------

    def exists(
        self,
        project_id: str,
    ) -> bool:

        return self.repository.exists(project_id)

    def count(
        self,
    ) -> int:

        return self.repository.count()
