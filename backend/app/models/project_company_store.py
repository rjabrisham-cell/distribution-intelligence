"""
ProjectCompanyStore Model — Enterprise Data Model v3.1

ProjectCompanyStore = Project-specific CompanyStore Usage

Architecture
------------

Company
    |
    | 1:M
    v
CompanyStore
    |
    | M:N
    v
ProjectCompanyStore
    |
    | M:N
    v
Project

Purpose
-------

A Company owns CompanyStore records.

A Project does NOT own CompanyStore records.

ProjectCompanyStore defines which CompanyStore records
are used by a specific Project.

This allows:

    - One CompanyStore to be used by one Project.
    - One CompanyStore to be used by multiple Projects.
    - One CompanyStore to be used by all Projects.
    - Each Project to use a different subset of CompanyStores.

Important
---------

Deleting a ProjectCompanyStore association must NOT delete
the underlying CompanyStore.

Deleting a Project must NOT delete CompanyStore records.

CompanyStore.status represents the global operational
status of the CompanyStore.

ProjectCompanyStore.is_active represents whether the
CompanyStore is currently active in this specific Project.

Therefore:

    CompanyStore.status
        = Global Company-level store status

    ProjectCompanyStore.is_active
        = Project-specific usage status
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.models.base import BaseModel


class ProjectCompanyStore(BaseModel):
    """
    Association model between Project and CompanyStore.

    این مدل مشخص می‌کند که یک CompanyStore در یک Project
    مورد استفاده قرار می‌گیرد یا خیر.

    CompanyStore متعلق به Company است.

    ProjectCompanyStore فقط رابطه استفاده Project از
    CompanyStore را نگهداری می‌کند.

    یک CompanyStore می‌تواند همزمان در چند Project استفاده شود.
    """

    __tablename__ = "project_company_stores"

    # ==========================================================
    # Identity
    # ==========================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    # ==========================================================
    # Foreign Keys
    # ==========================================================

    project_id: Mapped[int] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
        comment="پروژه‌ای که از CompanyStore استفاده می‌کند",
    )

    company_store_id: Mapped[int] = mapped_column(
        ForeignKey(
            "company_stores.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
        comment="CompanyStore مورد استفاده در پروژه",
    )

    # ==========================================================
    # Project-specific Usage Status
    # ==========================================================

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment=(
            "آیا این CompanyStore در این Project "
            "در حال حاضر فعال و قابل استفاده است؟"
        ),
    )

    # ==========================================================
    # Lifecycle
    # ==========================================================

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="زمان اضافه شدن CompanyStore به Project",
    )

    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "زمان غیرفعال شدن CompanyStore در Project. "
            "NULL یعنی هنوز فعال است."
        ),
    )

    # ==========================================================
    # Constraints
    # ==========================================================

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "company_store_id",
            name="uq_project_company_store",
        ),
    )

    # ==========================================================
    # Relationships
    # ==========================================================

    # ----------------------------------------------------------
    # Project
    # ----------------------------------------------------------

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="project_company_stores",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # CompanyStore
    #
    # MUST match:
    #
    # CompanyStore.project_company_stores
    # ----------------------------------------------------------

    company_store: Mapped["CompanyStore"] = relationship(
        "CompanyStore",
        back_populates="project_company_stores",
        lazy="selectin",
    )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def is_currently_active(self) -> bool:
        """
        آیا CompanyStore در این Project فعال است؟

        این وضعیت فقط مربوط به استفاده از Store در Project است
        و ربطی به CompanyStore.status ندارد.
        """

        return (
            self.is_active
            and self.removed_at is None
        )

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<ProjectCompanyStore("
            f"id={self.id}, "
            f"project_id={self.project_id}, "
            f"company_store_id={self.company_store_id}, "
            f"is_active={self.is_active}"
            f")>"
        )