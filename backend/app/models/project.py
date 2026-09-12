"""
Project Model — Enterprise Data Model v4.0

Project = Business Workspace

Architecture
------------

Every Project belongs to exactly one Company.

A Company may own multiple Projects.

A Project may use zero, one, or many CompanyStores.

A CompanyStore may be used in one, multiple, or all Projects.

Project <-> CompanyStore is MANY-TO-MANY through
ProjectCompanyStore.

Vehicles and Drivers are NOT owned by Project.

Vehicles and Drivers belong to Company.

Project-specific resource allocation is handled through:

    ProjectVehicle
    ProjectDriver

This separation allows the same company vehicle or driver to
participate in different projects over time.

Ownership Rules
---------------

Company
    Owns Vehicles and Drivers.

Project
    Belongs to one Company.

ProjectCompanyStore
    Associates CompanyStore with Project.

ProjectVehicle
    Associates a Company-owned Vehicle with Project.

ProjectDriver
    Associates a Company-owned Driver with Project.

Project NEVER owns Vehicle directly.

Project NEVER owns Driver directly.

Deleting a Project must only remove its association records.

Underlying Company, Vehicle, Driver and CompanyStore records
must remain independent.
"""

from __future__ import annotations

from enum import Enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.models.base import BaseModel


if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.company_store import CompanyStore
    from app.models.order import Order
    from app.models.project_company_store import ProjectCompanyStore
    from app.models.project_driver import ProjectDriver
    from app.models.project_vehicle import ProjectVehicle
    from app.models.request import Request


class ProjectStatus(str, Enum):
    """
    Lifecycle status of a Project.
    """

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    CLOSED = "CLOSED"


class Project(BaseModel):
    """
    Business workspace belonging to exactly one Company.

    A Project is the operational boundary for:

        - CompanyStore participation
        - Vehicle allocation
        - Driver allocation
        - Orders
        - Requests

    Project does not own Vehicles or Drivers directly.
    """

    __tablename__ = "projects"
    trial_owner_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True, index=True)
    trial_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trial_result_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    trial_consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    active_store_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="RESTRICT", name="fk_projects_active_store_batch"),
        nullable=True,
        index=True,
    )

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
    # Company Ownership
    # ==========================================================

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "companies.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
        comment="Company مالک این Project",
    )

    # ==========================================================
    # Business Identity
    # ==========================================================

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ==========================================================
    # Project Status
    # ==========================================================

    status: Mapped[ProjectStatus] = mapped_column(
        String(30),
        nullable=False,
        default=ProjectStatus.DRAFT,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # ==========================================================
    # Relationships
    # ==========================================================

    # ----------------------------------------------------------
    # Company
    # ----------------------------------------------------------

    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="projects",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Company Store Associations
    # ----------------------------------------------------------

    project_company_stores: Mapped[
        list["ProjectCompanyStore"]
    ] = relationship(
        "ProjectCompanyStore",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Vehicle Allocations
    # ----------------------------------------------------------

    project_vehicles: Mapped[
        list["ProjectVehicle"]
    ] = relationship(
        "ProjectVehicle",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Driver Allocations
    # ----------------------------------------------------------

    project_drivers: Mapped[
        list["ProjectDriver"]
    ] = relationship(
        "ProjectDriver",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Requests
    # ----------------------------------------------------------

    requests: Mapped[
        list["Request"]
    ] = relationship(
        "Request",
        back_populates="project",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Orders
    # ----------------------------------------------------------

    orders: Mapped[
        list["Order"]
    ] = relationship(
        "Order",
        back_populates="project",
        lazy="selectin",
    )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def is_draft(self) -> bool:
        """
        Returns True when the project is in DRAFT state.
        """

        return self.status == ProjectStatus.DRAFT

    @property
    def is_operational(self) -> bool:
        """
        Returns True when the project is active and operational.
        """

        return (
            self.is_active
            and self.status == ProjectStatus.ACTIVE
        )

    @property
    def is_closed(self) -> bool:
        """
        Returns True when the project is closed.
        """

        return self.status == ProjectStatus.CLOSED

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<Project("
            f"id={self.id}, "
            f"company_id={self.company_id}, "
            f"name={self.name!r}, "
            f"code={self.code!r}, "
            f"status={self.status!r}, "
            f"active={self.is_active}"
            f")>"
        )
