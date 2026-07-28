from typing import List, Optional, Union

from sqlalchemy.orm import Session

from app.models.project import Project, ProjectStatus


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    # --------------------------------------------------
    # Create
    # --------------------------------------------------

    def create(self, project: Project) -> Project:
        try:
            self.db.add(project)
            self.db.commit()
            self.db.refresh(project)
            return project
        except Exception:
            self.db.rollback()
            raise

    # --------------------------------------------------
    # Read
    # --------------------------------------------------

    def get_by_id(self, project_id: int) -> Optional[Project]:
        return (
            self.db.query(Project)
            .filter(Project.id == project_id)
            .first()
        )

    def get_all(self) -> List[Project]:
        return (
            self.db.query(Project)
            .order_by(Project.created_at.desc())
            .all()
        )

    def get_by_company(self, company_id: int) -> List[Project]:
        return (
            self.db.query(Project)
            .filter(Project.company_id == company_id)
            .order_by(Project.created_at.desc())
            .all()
        )

    def get_by_status(self, status: ProjectStatus) -> List[Project]:
        return (
            self.db.query(Project)
            .filter(Project.status == status)
            .order_by(Project.created_at.desc())
            .all()
        )

    def get_by_name(
        self,
        company_id: int,
        name: str,
    ) -> Optional[Project]:
        return (
            self.db.query(Project)
            .filter(
                Project.company_id == company_id,
                Project.name == name,
            )
            .first()
        )

    def get_by_company_and_name(
        self,
        company_id: int,
        name: str,
    ) -> Optional[Project]:
        return self.get_by_name(company_id=company_id, name=name)

    # --------------------------------------------------
    # Update
    # --------------------------------------------------

    def update(
        self,
        project_or_id: Union[Project, int],
        **kwargs,
    ) -> Optional[Project]:
        if isinstance(project_or_id, Project):
            project = project_or_id
        else:
            project = self.get_by_id(project_or_id)
            if project is None:
                return None

            for key, value in kwargs.items():
                setattr(project, key, value)

        try:
            self.db.commit()
            self.db.refresh(project)
            return project
        except Exception:
            self.db.rollback()
            raise

    def update_status(
        self,
        project_or_id: Union[Project, int],
        status: ProjectStatus,
    ) -> Optional[Project]:
        if isinstance(project_or_id, Project):
            project = project_or_id
        else:
            project = self.get_by_id(project_or_id)
            if project is None:
                return None

        project.status = status
        return self.update(project)

    def save(self, project: Project) -> Project:
        updated = self.update(project)
        if updated is None:
            raise ValueError("Project not found.")
        return updated

    # --------------------------------------------------
    # Delete
    # --------------------------------------------------

    def delete(
        self,
        project_or_id: Union[Project, int],
    ) -> bool:
        if isinstance(project_or_id, Project):
            project = project_or_id
        else:
            project = self.get_by_id(project_or_id)
            if project is None:
                return False

        try:
            self.db.delete(project)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    # --------------------------------------------------
    # Utility
    # --------------------------------------------------

    def exists(self, project_id: int) -> bool:
        return self.get_by_id(project_id) is not None

    def count(self) -> int:
        return self.db.query(Project).count()

    def count_by_company(self, company_id: int) -> int:
        return (
            self.db.query(Project)
            .filter(Project.company_id == company_id)
            .count()
        )
