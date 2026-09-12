"""
CompanyStore Model — Enterprise Data Model v3.1

CompanyStore = Company-Owned Store Instance

Architecture
------------

CompanyStore represents the canonical store record owned by a Company have many CompanyStores.

A CompanyStore:

    - belongs to exactly - belongs to exactly one Company
    - may optionally link to one Master Store
    - can be reused by multiple Projects
    - does NOT belong exclusively to one Project

Project Usage
-------------

Project ↔ CompanyStore is a MANY-TO-MANY relationship.

The relationship is managed through:

    ProjectCompanyStore

Therefore:

    Company
       │
       │ 1:M
       ▼
    CompanyStore
       │
       │ 1:M
       ▼
    ProjectCompanyStore
       ▲
       │ M:1
       │
    Project

CompanyStore lifecycle is independent from Project usage.

Master Store
------------

CompanyStore may be matched to the Enterprise Truth Layer master Store.

Relationship:

    Company (1:M) ──< CompanyStore >── (M:1) Store

Project Usage:

    Project (M:N) ──< ProjectCompanyStore >── (M:N) CompanyStore

Contract v1.2
-------------

DB enum = 7-state MatchStatus

Business logic = 3-state:

    MATCHED
    LOCATED
    UNRESOLVED

Properties:

    is_matched
    is_located
    is_unresolved
"""

from __future__ import annotations

from sqlalchemy import (
    Enum as SAEnum,
    Float,
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

from app.core.enums import (
    CoordinateSource,
    LocationConfidence,
    LocationSource,
    MatchStatus,
    StoreStatus,
)
from app.models.base import BaseModel


class CompanyStore(BaseModel):
    """
    Company-owned store instance.

    CompanyStore belongs to exactly one Company and may optionally
    be linked to one canonical Master Store.

    CompanyStore is independent from Project.

    Project-specific usage is managed through ProjectCompanyStore.
    """

    __tablename__ = "company_stores"

    # ==========================================================
    # Foreign Keys
    # ==========================================================

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "companies.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
        comment="مالک اصلی CompanyStore",
    )

    master_store_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "stores.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
        comment=(
            "لینک به Master Store در Enterprise Truth Layer. "
            "NULL یعنی هنوز به Master Store متصل نشده است."
        ),
    )

    # ==========================================================
    # Identity
    # ==========================================================

    store_code: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment=(
            "کد فروشگاه در سیستم شرکت "
            "(Company-provided Store Code)"
        ),
    )

    name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    # ==========================================================
    # Contact & Address
    # ==========================================================

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    address: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    # ==========================================================
    # Geography
    #
    # MVP — Base Geography Only:
    #     province / city
    #
    # Deep geography (district) removed from the readiness
    # pipeline per the MVP decision.
    # ==========================================================

    province: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # ==========================================================
    # Coordinates
    # ==========================================================

    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ==========================================================
    # Location Intelligence
    # ==========================================================

    location_confidence: Mapped[
        LocationConfidence | None
    ] = mapped_column(
        SAEnum(LocationConfidence),
        nullable=True,
        index=True,
    )

    coordinate_source: Mapped[
        CoordinateSource | None
    ] = mapped_column(
        SAEnum(CoordinateSource),
        nullable=True,
        index=True,
    )

    location_source: Mapped[
        LocationSource | None
    ] = mapped_column(
        SAEnum(LocationSource),
        nullable=True,
        index=True,
        comment=(
            "MASTER = inherited from master_store; "
            "MANUAL = manually assigned; "
            "other values according to LocationSource enum"
        ),
    )

    # ==========================================================
    # Match Status
    # ==========================================================

    match_status: Mapped[MatchStatus] = mapped_column(
        SAEnum(MatchStatus),
        default=MatchStatus.UNRESOLVED,
        nullable=False,
        index=True,
        comment=(
            "7-value DB enum. "
            "Business logic exposed through "
            "is_matched / is_located / is_unresolved."
        ),
    )

    # ==========================================================
    # CompanyStore Operational Status
    # ==========================================================

    status: Mapped[StoreStatus] = mapped_column(
        SAEnum(StoreStatus),
        default=StoreStatus.ENABLE,
        nullable=False,
        index=True,
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
            "company_id",
            "store_code",
            name="uq_company_store_code",
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
        back_populates="company_stores",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Master Store
    # ----------------------------------------------------------

    master_store: Mapped["Store | None"] = relationship(
        "Store",
        back_populates="company_stores",
        foreign_keys=[master_store_id],
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Address Candidates
    # ----------------------------------------------------------

    address_candidates: Mapped[
        list["AddressCandidate"]
    ] = relationship(
        "AddressCandidate",
        back_populates="company_store",
        foreign_keys="AddressCandidate.company_store_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # ----------------------------------------------------------
    # Project Usage
    # ----------------------------------------------------------

    project_company_stores: Mapped[
        list["ProjectCompanyStore"]
    ] = relationship(
        "ProjectCompanyStore",
        back_populates="company_store",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def has_coordinates(self) -> bool:
        """
        آیا مختصات جغرافیایی ثبت شده است؟
        """

        return (
            self.latitude is not None
            and self.longitude is not None
        )

    @property
    def is_matched(self) -> bool:
        """
        آیا CompanyStore به یک Master Store متصل شده است؟

        اتصال واقعی به Master Store با master_store_id مشخص می‌شود.
        همچنین اگر MatchStatus برابر MATCHED باشد، رکورد در منطق
        کسب‌وکار Match شده در نظر گرفته می‌شود.
        """

        return (
            self.master_store_id is not None
            or self.match_status == MatchStatus.MATCHED
        )

    @property
    def is_located(self) -> bool:
        """
        آیا موقعیت مکانی فروشگاه مشخص شده است؟

        این وضعیت بر اساس match_status تعیین می‌شود،
        نه صرفاً وجود latitude و longitude.
        """

        return self.match_status == MatchStatus.LOCATED

    @property
    def is_unresolved(self) -> bool:
        """
        آیا فروشگاه هنوز نه Match شده و نه Locate شده است؟
        """

        return self.match_status == MatchStatus.UNRESOLVED

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<CompanyStore("
            f"id={self.id}, "
            f"company_id={self.company_id}, "
            f"store_code={self.store_code!r}, "
            f"status={self.status.value!r}, "
            f"match_status={self.match_status.value!r}"
            f")>"
        )
