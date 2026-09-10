"""
Store Model (Enterprise v3.1)
----------------------------

Canonical physical location with life-cycle management.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Enum as SQLAlchemyEnum,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    DataQualityStatus,
    DuplicateStatus,
    GeoStatus,
)
from app.models.base import BaseModel


class Store(BaseModel):
    """
    Canonical physical location (store, pharmacy, outlet, etc.).

    Lifecycle:
        Intake → Validation → Matching → Resolution → Readiness → Complete

    Relationships:
        • One-to-many: Store → CompanyStore (via master_store_id)
        • One-to-many: Store → StoreLocation (location history)
        • One-to-many: Store → AddressCandidate (geocoding candidates)
    """

    __tablename__ = "stores"

    __table_args__ = (
        Index(
            "ux_stores_legacy_mysql_id",
            "legacy_mysql_id",
            unique=True,
        ),
    )

    # ==========================================================
    # Primary Key & Audit Fields
    # ==========================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    # ==========================================================
    # Legacy MySQL Migration Support
    # ==========================================================

    legacy_mysql_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="ID from legacy MySQL system for migration tracking",
    )

    # ==========================================================
    # Canonical Identity
    # ==========================================================

    canonical_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    canonical_phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    # ==========================================================
    # Contact Information
    # ==========================================================

    manager_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    mobile: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # ==========================================================
    # Canonical Address
    # ==========================================================

    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    postal_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    plaque: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    unit: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    floor: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # ==========================================================
    # Administrative Divisions
    #
    # MVP — Base Geography Only:
    #     province_id / city_id
    #     + denormalized province_name / city_name
    #
    # Deep geography removed from MVP readiness pipeline.
    # ==========================================================

    province_id: Mapped[int | None] = mapped_column(
        Integer,
        index=True,
        nullable=True,
    )

    city_id: Mapped[int | None] = mapped_column(
        Integer,
        index=True,
        nullable=True,
    )

    # ==========================================================
    # Denormalized Administrative Names
    # ==========================================================

    province_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    city_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ==========================================================
    # Current Canonical Coordinates
    #
    # Authoritative location history:
    #     StoreLocation
    #
    # These fields store the current canonical coordinates
    # for fast access and search.
    # ==========================================================

    latitude: Mapped[float | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )

    longitude: Mapped[float | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )

    # ==========================================================
    # Data Readiness MVP
    # ==========================================================

    data_quality_status: Mapped[DataQualityStatus | None] = mapped_column(
        SQLAlchemyEnum(
            DataQualityStatus,
            native_enum=False,
            length=50,
        ),
        nullable=True,
        default=DataQualityStatus.PENDING,
        comment="وضعیت کیفیت داده‌های فروشگاه",
    )

    geo_status: Mapped[GeoStatus | None] = mapped_column(
        SQLAlchemyEnum(
            GeoStatus,
            native_enum=False,
            length=50,
        ),
        nullable=True,
        default=GeoStatus.PENDING,
        comment="وضعیت اعتبارسنجی جغرافیایی",
    )

    duplicate_status: Mapped[DuplicateStatus | None] = mapped_column(
        SQLAlchemyEnum(
            DuplicateStatus,
            native_enum=False,
            length=50,
        ),
        nullable=True,
        default=DuplicateStatus.UNKNOWN,
        comment="وضعیت شناسایی تکراری بودن",
    )

    readiness_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="امتیاز آمادگی داده‌های فروشگاه (مثلاً 95.50)",
    )

    # ==========================================================
    # AI Matching
    # ==========================================================

    confidence_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    matching_status: Mapped[str | None] = mapped_column(
        String(20),
        default="PENDING",
        nullable=True,
        index=True,
    )

    # Possible values:
    # PENDING
    # MATCHED
    # CONFLICT
    # REVIEW
    # VERIFIED

    master_source: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # ==========================================================
    # Fimap Integration
    # ==========================================================

    fimap_token: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
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

    # ==========================================================
    # Relationships
    # ==========================================================

    company_stores: Mapped[list["CompanyStore"]] = relationship(
        "CompanyStore",
        back_populates="master_store",
        foreign_keys="CompanyStore.master_store_id",
        lazy="selectin",
    )

    store_locations: Mapped[list["StoreLocation"]] = relationship(
        "StoreLocation",
        back_populates="store",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    address_candidates: Mapped[list["AddressCandidate"]] = relationship(
        "AddressCandidate",
        back_populates="store",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def has_coordinates(self) -> bool:
        """
        Returns True when both canonical coordinates exist.
        """
        return (
            self.latitude is not None
            and self.longitude is not None
        )

    @property
    def is_geo_ready(self) -> bool:
        """
        Returns True when the Store has valid geographic data.
        """
        return (
            self.geo_status == GeoStatus.VALID
            and self.latitude is not None
            and self.longitude is not None
        )

    @property
    def is_ready(self) -> bool:
        """
        Returns True when the Store readiness score is at least 90.
        """
        return (
            self.readiness_score is not None
            and self.readiness_score >= 90
        )

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        geo_display = (
            self.geo_status.value
            if self.geo_status is not None
            else "N/A"
        )

        readiness_display = (
            f"{self.readiness_score}"
            if self.readiness_score is not None
            else "N/A"
        )

        return (
            f"<Store("
            f"id={self.id!r}, "
            f"name={self.canonical_name!r}, "
            f"city={self.city_name!r}, "
            f"geo={geo_display!r}, "
            f"readiness={readiness_display}"
            f")>"
        )