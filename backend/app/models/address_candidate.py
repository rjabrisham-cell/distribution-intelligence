"""
AddressCandidate Model — Enterprise Data Model v3.0

AddressCandidate = Every Address Ever Seen

Rules
-----
- هیچ آدرسی حذف نمی‌شود.
- تمام آدرس‌های ورودی از هر منبع در این جدول ذخیره می‌شوند.
- این جدول منبع داده‌ی Matching Engine است.
- خروجی Validation Engine نیز در همین جدول ثبت می‌شود.
- Store حقیقت نهایی است؛ AddressCandidate فقط Evidence است.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
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


class AddressCandidate(BaseModel):
    __tablename__ = "address_candidates"

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
    # Store References
    # ==========================================================

    store_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "stores.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    company_store_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "company_stores.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # ==========================================================
    # Raw Address
    # ==========================================================

    address_text: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    province: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    county: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    district: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    neighborhood: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    village: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    postal_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    # ==========================================================
    # Coordinates
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
    # Source
    # ==========================================================

    source_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    """
    excel
    manual
    api
    fimap
    google
    osm
    ai
    gps
    mysql
    """

    source_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    source_detail: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ==========================================================
    # Matching Result
    # ==========================================================

    match_found: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    matched_store_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    match_score: Mapped[float | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    match_method: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    """
    exact
    fuzzy
    geo
    ai
    manual
    """

    # ==========================================================
    # Validation Result
    # ==========================================================

    validation_provider: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    """
    fimap
    google
    neshan
    osm
    ai
    """

    validation_score: Mapped[float | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    normalized_address: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    normalized_latitude: Mapped[float | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )

    normalized_longitude: Mapped[float | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )

    fimap_token: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # ==========================================================
    # Processing Flags
    # ==========================================================

    is_processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    is_selected: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    """
    اگر این رکورد تبدیل به حقیقت Store شده باشد True می‌شود.
    """

    # ==========================================================
    # Audit
    # ==========================================================

    processed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ==========================================================
    # Relationships
    # ==========================================================

    # ----------------------------------------------------------
    # Master Store
    # ----------------------------------------------------------

    store: Mapped["Store | None"] = relationship(
        "Store",
        back_populates="address_candidates",
        foreign_keys=[store_id],
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Company Store
    # ----------------------------------------------------------

    company_store: Mapped["CompanyStore | None"] = relationship(
        "CompanyStore",
        back_populates="address_candidates",
        foreign_keys=[company_store_id],
        lazy="selectin",
    )

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<AddressCandidate("
            f"id={self.id}, "
            f"source='{self.source_type}', "
            f"matched={self.match_found}"
            f")>"
        )