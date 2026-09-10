"""
Driver Model — Enterprise Data Model v4.0

Driver = Company-Owned Human Resource

## Architecture

A Driver belongs to exactly one Company.

A Driver is NOT owned by a Project.

A Driver is NOT permanently owned by a Vehicle.

Driver-to-Vehicle assignment is represented through
VehicleDriver.

Driver-to-Project assignment is represented through
ProjectDriver.

This allows:

    Driver -> Vehicle A
    Driver -> Vehicle B
    Driver -> Project A
    Driver -> Project B

over different periods of time.

ImportBatch represents the source/import event only.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
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
    from app.models.project_driver import ProjectDriver
    from app.models.vehicle_driver import VehicleDriver

class Driver(BaseModel):
    """
    Company-owned driver.

    A Driver belongs to one Company.

    A Driver may operate different Vehicles over time.

    A Driver may participate in different Projects over time.

    Vehicle assignment:
        VehicleDriver

    Project assignment:
        ProjectDriver
    """

    __tablename__ = "drivers"

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
        comment="Company مالک این Driver",
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
            "آخرین ImportBatch که این Driver از آن وارد شده است"
        ),
    )

    # ==========================================================
    # Business Identity
    # ==========================================================

    driver_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    # ==========================================================
    # Personal Information
    # ==========================================================

    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    # ==========================================================
    # License Information
    # ==========================================================

    license_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    license_expiry: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    experience_years: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # ==========================================================
    # Home / Base Coordinates
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
    # Constraints
    # ==========================================================

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "driver_code",
            name="uq_drivers_company_driver_code",
        ),
    )

    # ==========================================================
    # Relationships
    # ==========================================================

    # ----------------------------------------------------------
    # Company
    # ----------------------------------------------------------

    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="drivers",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Import Batch
    # ----------------------------------------------------------

    import_batch: Mapped["ImportBatch | None"] = relationship(
        "ImportBatch",
        back_populates="drivers",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Vehicle Assignments
    # ----------------------------------------------------------

    vehicle_drivers: Mapped[
        list["VehicleDriver"]
    ] = relationship(
        "VehicleDriver",
        back_populates="driver",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Project Assignments
    # ----------------------------------------------------------

    project_drivers: Mapped[
        list["ProjectDriver"]
    ] = relationship(
        "ProjectDriver",
        back_populates="driver",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def full_name(self) -> str | None:
        """
        نام کامل راننده.
        """

        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"

        return self.first_name or self.last_name

    @property
    def is_active(self) -> bool:
        """
        آیا راننده فعال است؟
        """

        return self.status.lower() == "active"

    @property
    def has_start_coordinates(self) -> bool:
        """
        آیا مختصات محل استقرار ثبت شده است؟
        """

        return (
            self.latitude is not None
            and self.longitude is not None
        )

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<Driver("
            f"id={self.id}, "
            f"company_id={self.company_id}, "
            f"code={self.driver_code!r}, "
            f"name={self.full_name!r}, "
            f"status={self.status!r}"
            f")>"
        )
