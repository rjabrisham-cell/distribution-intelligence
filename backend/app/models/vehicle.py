"""
Vehicle Model — Enterprise Data Model v4.0

Vehicle = Company-Owned Fleet Asset

## Architecture

A Vehicle belongs to exactly one Company.

A Vehicle is NOT owned by a Project.

A Vehicle may participate in zero, one or many Projects
over its lifecycle.

Project-specific usage is represented by ProjectVehicle.

ImportBatch represents the source/import event only.
It does NOT define the ownership of the Vehicle.

## Ownership

Company
Owns Vehicle.

ImportBatch
Records how Vehicle data entered the system.

ProjectVehicle
Records the participation/allocation of a Vehicle
in a Project.

Project
Does not directly own Vehicle.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.import_batch import ImportBatch
    from app.models.project_vehicle import ProjectVehicle
    from app.models.vehicle_driver import VehicleDriver

class Vehicle(BaseModel):
    """
    Company-owned vehicle / fleet asset.

    A Vehicle belongs to one Company.

    It may be used in multiple Projects over time.

    Project-specific allocation is handled through
    ProjectVehicle.

    Driver assignment is handled through VehicleDriver.
    """

    __tablename__ = "vehicles"

    # ==========================================================
    # Company Ownership
    # ==========================================================

    company_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "companies.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
        comment="Company مالک این Vehicle",
    )

    # ==========================================================
    # Import Source
    # ==========================================================

    import_batch_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "import_batches.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
        comment=(
            "آخرین ImportBatch که این Vehicle از آن وارد شده است"
        ),
    )

    # ==========================================================
    # Vehicle Identity
    # ==========================================================

    vehicle_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    plate_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # Vehicle Type
    # ==========================================================

    vehicle_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ==========================================================
    # Capacity
    # ==========================================================

    capacity_kg: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    capacity_m3: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ==========================================================
    # Cost
    # ==========================================================

    cost_per_km: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    fixed_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    # ==========================================================
    # Depot / Base Coordinates
    # ==========================================================

    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )

    # ==========================================================
    # Status
    # ==========================================================

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="active",
        index=True,
    )

    # ==========================================================
    # Operational Availability
    # ==========================================================

    available_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    available_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ==========================================================
    # Raw Import Data
    # ==========================================================

    raw_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    error_note: Mapped[str | None] = mapped_column(
        String(1000),
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
        back_populates="vehicles",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Import Batch
    # ----------------------------------------------------------

    import_batch: Mapped["ImportBatch | None"] = relationship(
        "ImportBatch",
        back_populates="vehicles",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Project Allocations
    # ----------------------------------------------------------

    project_vehicles: Mapped[
        list["ProjectVehicle"]
    ] = relationship(
        "ProjectVehicle",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Driver Assignments
    # ----------------------------------------------------------

    vehicle_drivers: Mapped[
        list["VehicleDriver"]
    ] = relationship(
        "VehicleDriver",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def has_capacity(self) -> bool:
        """
        آیا حداقل یکی از ظرفیت‌ها ثبت شده است؟
        """

        return (
            self.capacity_kg is not None
            or self.capacity_m3 is not None
        )

    @property
    def has_coordinates(self) -> bool:
        """
        آیا مختصات دپو ثبت شده است؟
        """

        return (
            self.latitude is not None
            and self.longitude is not None
        )

    @property
    def is_available_now(self) -> bool:
        """
        آیا خودرو در بازه زمانی فعلی در دسترس است؟
        """

        if self.status != "active":
            return False

        now = datetime.now().astimezone()

        if (
            self.available_from
            and now < self.available_from
        ):
            return False

        if (
            self.available_until
            and now > self.available_until
        ):
            return False

        return True

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<Vehicle("
            f"id={self.id}, "
            f"company_id={self.company_id}, "
            f"code={self.vehicle_code!r}, "
            f"plate={self.plate_number!r}"
            f")>"
        )
