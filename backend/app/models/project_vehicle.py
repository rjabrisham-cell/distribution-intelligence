"""
ProjectVehicle Model — Enterprise Data Model v4.0

Represents the participation of a Company Vehicle
inside a Project.

Architecture
------------

Company owns Vehicle.

Project belongs to Company.

ProjectVehicle connects a Company's Vehicle
to a Project.

ProjectVehicle does NOT own the Vehicle.

Deleting a ProjectVehicle record does NOT delete
the underlying Vehicle.

Deleting a Project deletes its ProjectVehicle
association records.

The Vehicle remains part of the Company's
Enterprise Fleet.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.models.base import BaseModel


if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.vehicle import Vehicle


class ProjectVehicle(BaseModel):
    """
    Project-specific participation of a Company Vehicle.
    """

    __tablename__ = "project_vehicles"

    # ==========================================================
    # Project
    # ==========================================================

    project_id: Mapped[int] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # Vehicle
    # ==========================================================

    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey(
            "vehicles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # Project-Specific Operational Configuration
    # ==========================================================

    role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment=(
            "Project-specific vehicle role. "
            "Examples: DELIVERY | BACKUP | SUPPORT"
        ),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # ==========================================================
    # Project-Specific Cost Overrides
    # ==========================================================

    cost_per_km_override: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment=(
            "Optional project-specific cost per kilometer. "
            "If null, Vehicle default cost is used."
        ),
    )

    fixed_cost_override: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment=(
            "Optional project-specific fixed cost. "
            "If null, Vehicle default fixed cost is used."
        ),
    )

    # ==========================================================
    # Project Participation Period
    # ==========================================================

    assigned_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    assigned_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ==========================================================
    # Notes
    # ==========================================================

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ==========================================================
    # Constraints
    # ==========================================================

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "vehicle_id",
            name="uq_project_vehicle",
        ),
    )

    # ==========================================================
    # Relationships
    # ==========================================================

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="project_vehicles",
        lazy="selectin",
    )

    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        back_populates="project_vehicles",
        lazy="selectin",
    )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def is_current(self) -> bool:
        """
        Returns True when the vehicle is currently active
        in this Project.
        """

        if not self.is_active:
            return False

        now = datetime.now().astimezone()

        if self.assigned_from and now < self.assigned_from:
            return False

        if self.assigned_until and now > self.assigned_until:
            return False

        return True

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<ProjectVehicle("
            f"id={self.id}, "
            f"project_id={self.project_id}, "
            f"vehicle_id={self.vehicle_id}, "
            f"active={self.is_active}"
            f")>"
        )