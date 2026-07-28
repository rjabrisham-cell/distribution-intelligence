"""
VehicleDriver Model — Enterprise Data Model v4.0

Represents the assignment of a Driver to a Vehicle.

Architecture
------------

Company
    |
    +---- Vehicle
    |
    +---- Driver
             |
             +---- VehicleDriver

VehicleDriver represents an operational assignment.

A Driver can be assigned to different Vehicles over time.

A Vehicle can have different Drivers over time.

The assignment itself has a lifecycle and validity period.

This model does NOT represent Project usage.

Project usage is handled by ProjectVehicle and ProjectDriver.
"""

from __future__ import annotations

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
    from app.models.driver import Driver
    from app.models.vehicle import Vehicle


class VehicleDriver(BaseModel):
    """
    Assignment between a Company Vehicle and a Company Driver.

    This model represents the operational relationship between
    a vehicle and its assigned driver.
    """

    __tablename__ = "vehicle_drivers"

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
    # Assignment Information
    # ==========================================================

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PRIMARY",
        index=True,
        comment=(
            "Driver role for the vehicle. "
            "Examples: PRIMARY | SECONDARY | RELIEF"
        ),
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # ==========================================================
    # Validity Period
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
    # Relationships
    # ==========================================================

    # ----------------------------------------------------------
    # Company
    # ----------------------------------------------------------

    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="vehicle_driver_assignments",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Vehicle
    # ----------------------------------------------------------

    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        back_populates="vehicle_drivers",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Driver
    # ----------------------------------------------------------

    driver: Mapped["Driver"] = relationship(
        "Driver",
        back_populates="vehicle_drivers",
        lazy="selectin",
    )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def is_current(self) -> bool:
        """
        Returns True when the assignment is currently active
        within its optional validity period.
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
            f"<VehicleDriver("
            f"id={self.id}, "
            f"company_id={self.company_id}, "
            f"vehicle_id={self.vehicle_id}, "
            f"driver_id={self.driver_id}, "
            f"role={self.role!r}, "
            f"active={self.is_active}"
            f")>"
        )