"""
Company Model — Enterprise Data Model v4.0

Company = Legal Business Entity

Architecture
------------

Company is the legal owner of:

    - Projects
    - CompanyStores
    - Vehicles
    - Drivers

Ownership Rules
---------------

Company owns Vehicles.

Company owns Drivers.

Vehicle does NOT belong to a Project.

Driver does NOT belong to a Project.

Project-specific vehicle usage is managed through:

    ProjectVehicle

Project-specific driver usage is managed through:

    ProjectDriver

Vehicle-driver assignment is managed through:

    VehicleDriver

This keeps the Enterprise Truth Layer separate from
Project Operational Usage.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
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


class Company(BaseModel):
    __tablename__ = "companies"

    # ==========================================================
    # Identity
    # ==========================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey(
            "accounts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    slug: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
    )

    code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    # ==========================================================
    # Legal Information
    # ==========================================================

    national_id: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
    )

    economic_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    registration_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # ==========================================================
    # Contact
    # ==========================================================

    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    mobile: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    website: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # ==========================================================
    # Head Office Address
    # ==========================================================

    province: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    postal_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    # ==========================================================
    # Configuration
    # ==========================================================

    max_projects: Mapped[int] = mapped_column(
        Integer,
        default=2,
        nullable=False,
    )

    max_users: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )

    # ==========================================================
    # Status
    # ==========================================================

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # ==========================================================
    # Relationships
    # ==========================================================

    # ----------------------------------------------------------
    # Account
    # ----------------------------------------------------------

    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="company",
        uselist=False,
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Projects
    # ----------------------------------------------------------

    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="company",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # ----------------------------------------------------------
    # Company Stores
    # ----------------------------------------------------------

    company_stores: Mapped[list["CompanyStore"]] = relationship(
        "CompanyStore",
        back_populates="company",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # ----------------------------------------------------------
    # Vehicles
    # ----------------------------------------------------------

    vehicles: Mapped[list["Vehicle"]] = relationship(
        "Vehicle",
        back_populates="company",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # ----------------------------------------------------------
    # Drivers
    # ----------------------------------------------------------

    drivers: Mapped[list["Driver"]] = relationship(
        "Driver",
        back_populates="company",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # ----------------------------------------------------------
    # Vehicle-Driver Assignments
    # ----------------------------------------------------------

    vehicle_driver_assignments: Mapped[
        list["VehicleDriver"]
    ] = relationship(
        "VehicleDriver",
        back_populates="company",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<Company("
            f"id={self.id}, "
            f"name={self.name!r}, "
            f"account_id={self.account_id}, "
            f"active={self.is_active}"
            f")>"
        )