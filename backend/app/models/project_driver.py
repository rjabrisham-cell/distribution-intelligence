"""
ProjectDriver Model — Enterprise Data Model v4.0

Represents the participation of a Company Driver
inside a Project.

Architecture
------------

Company owns Driver.

Project belongs to Company.

ProjectDriver connects a Company's Driver
to a Project.

ProjectDriver does NOT own the Driver.

Deleting a ProjectDriver record does NOT delete
the underlying Driver.

Deleting a Project deletes its ProjectDriver
association records.

The Driver remains part of the Company's
Enterprise Driver Pool.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
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
    from app.models.driver import Driver
    from app.models.project import Project


class ProjectDriver(BaseModel):
    """
    Project-specific participation of a Company Driver.
    """

    __tablename__ = "project_drivers"

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
    # Driver
    # ==========================================================

    driver_id: Mapped[int] = mapped_column(
        ForeignKey(
            "drivers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # Project-Specific Role
    # ==========================================================

    role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment=(
            "Project-specific driver role. "
            "Examples: DRIVER | SUPERVISOR | RELIEF"
        ),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
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
            "driver_id",
            name="uq_project_driver",
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
        back_populates="project_drivers",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Driver
    # ----------------------------------------------------------

    driver: Mapped["Driver"] = relationship(
        "Driver",
        back_populates="project_drivers",
        lazy="selectin",
    )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def is_current(self) -> bool:
        """
        Returns True when the driver is currently active
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
            f"<ProjectDriver("
            f"id={self.id}, "
            f"project_id={self.project_id}, "
            f"driver_id={self.driver_id}, "
            f"active={self.is_active}"
            f")>"
        )