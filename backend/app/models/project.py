import enum

from sqlalchemy import (
    Enum,
    ForeignKey,
    String,
    Text,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.models.base import BaseModel


class ProjectStatus(str, enum.Enum):

    DRAFT = "draft"

    IN_PROGRESS = "in_progress"

    COMPLETED = "completed"

    CANCELLED = "cancelled"


class Project(BaseModel):

    __tablename__ = "projects"

    # ------------------------------------
    # Company
    # ------------------------------------

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "companies.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="projects",
    )

    # ------------------------------------
    # Basic Information
    # ------------------------------------

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus),
        nullable=False,
        default=ProjectStatus.DRAFT,
    )

    # ------------------------------------
    # 🆕 Files (polymorphic)
    # ------------------------------------

    files: Mapped[list["File"]] = relationship(
        "File",
        primaryjoin=(
            "and_(foreign(File.entity_id) == Project.id, "
            "File.entity_type == 'PROJECT')"
        ),
        viewonly=True,
        lazy="selectin",
        doc="Files attached to this project (viewonly, entity_type='PROJECT').",
    )

    # ------------------------------------
    # Representation
    # ------------------------------------

    def __repr__(self):

        return (
            f"<Project("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"status='{self.status.value}'"
            f")>"
        )
