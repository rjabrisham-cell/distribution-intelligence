from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.project import Project, ProjectStatus


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, project: Project) -> Project:
        try:
            self.db.add(project)
            self.db.commit()
            self.db.refresh(project)
            return project
        except Exception:
            self.db.rollback()
            raise

    def get_by_id(self, project_id: str) -> Optional[Project]:
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

    def get_by_company(self, company_id: str) -> List[Project]:
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

    def update(self, project: Project) -> Project:
        try:
            self.db.commit()
            self.db.refresh(project)
            return project
        except Exception:
            self.db.rollback()
            raise

    def delete(self, project: Project) -> None:
        try:
            self.db.delete(project)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def exists(self, project_id: str) -> bool:
        return (
            self.db.query(Project)
            .filter(Project.id == project_id)
            .first()
            is not None
        )

    def count(self) -> int:
        return self.db.query(Project).count()

    def count_by_company(self, company_id: int) -> int:
        return (
            self.db.query(Project)
            .filter(Project.company_id == company_id)
            .count()
        )

    def update_status(
        self,
        project: Project,
        status: ProjectStatus,
    ) -> Project:
        project.status = status
        return self.update(project)

    def save(self, project: Project) -> Project:
        return self.update(project)

    def get_by_name(
        self,
        company_id: str,
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
