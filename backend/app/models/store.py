"""
Store Model — Enterprise Data Model v3.1

Store = Canonical Physical Place

Architecture
------------

Store represents ONE canonical real-world physical location.

Rules
-----

* Store is Company-independent.
* Store is the canonical geographic identity.
* Company-specific business data belongs to CompanyStore.
* CompanyStore may optionally link to one Store through master_store_id.
* A Store may be referenced by many CompanyStore records.
* Store does not belong directly to a Project.
* Project usage is handled through CompanyStore -> ProjectCompanyStore.

AI Matching
-----------

AI Matching resolves:

    CompanyStore -> Store

The relationship is:

    Company
        |
        | 1:M
        v
    CompanyStore
        |
        | M:1
        v
    Store

Store is the Enterprise Truth Layer for the physical location.

Location History
----------------

StoreLocation contains historical or validated geographic coordinates.

The Store.latitude and Store.longitude fields represent the
current canonical coordinates used for fast access and search.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Integer,
    Numeric,
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
    from app.models.address_candidate import AddressCandidate
    from app.models.company_store import CompanyStore
    from app.models.store_location import StoreLocation


class Store(BaseModel):
    """
    Canonical physical location.

    Store is independent of Company and Project.

    A CompanyStore may be linked to this Store as its
    canonical/master physical location.
    """

    __tablename__ = "stores"

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
    )

    canonical_category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    shop_type: Mapped[str | None] = mapped_column(
        String(50),
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
    # ==========================================================

    province_id: Mapped[int | None] = mapped_column(
        Integer,
        index=True,
        nullable=True,
    )

    county_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    city_id: Mapped[int | None] = mapped_column(
        Integer,
        index=True,
        nullable=True,
    )

    district_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    neighborhood_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    village_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # ==========================================================
    # Denormalized Administrative Names
    # ==========================================================

    province_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    county_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    city_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    district_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    neighborhood_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    village_name: Mapped[str | None] = mapped_column(
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
    #
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

    # ----------------------------------------------------------
    # CompanyStore References
    #
    # One Store can be referenced by many CompanyStores.
    #
    # IMPORTANT:
    #
    # This matches:
    #
    # CompanyStore.master_store
    #
    # through:
    #
    # back_populates="master_store"
    # ----------------------------------------------------------

    company_stores: Mapped[
        list["CompanyStore"]
    ] = relationship(
        "CompanyStore",
        back_populates="master_store",
        foreign_keys="CompanyStore.master_store_id",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Store Location History
    # ----------------------------------------------------------

    store_locations: Mapped[
        list["StoreLocation"]
    ] = relationship(
        "StoreLocation",
        back_populates="store",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # ----------------------------------------------------------
    # Address Candidates
    # ----------------------------------------------------------

    address_candidates: Mapped[
        list["AddressCandidate"]
    ] = relationship(
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

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<Store("
            f"id={self.id}, "
            f"name={self.canonical_name!r}, "
            f"city={self.city_name!r}, "
            f"active={self.is_active}"
            f")>"
        )