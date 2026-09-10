"""
StoreLocation Model — Enterprise Data Model v3.0

Validated Geographic Truth

This table stores the validated geographic location of a Store.

## Rules

• One Store may have multiple validation attempts.
• Only ONE record should have is_current=True.
• Company data NEVER lives here.
• Raw uploaded coordinates NEVER live here.
• This table is the authoritative geographic truth used by AI.

## Region

region_id represents the municipal region of Tehran.

• Region is currently defined for Tehran's 22 municipal regions.
• It is NOT a universal geographic layer for all cities in Iran.
• For Tehran stores, region_id may reference regions.id.
• For stores outside Tehran, region_id may be NULL.
"""

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from geoalchemy2 import Geometry

from app.models.base import BaseModel


class StoreLocation(BaseModel):
    """
    Validated geographic location of a Store.

    StoreLocation keeps the validated/current geographic truth
    and historical validation attempts for a Store.
    """

    __tablename__ = "store_locations"

    # ==========================================================
    # Identity
    # ==========================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # Validated Address
    # ==========================================================

    canonical_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    postal_code: Mapped[str | None] = mapped_column(
        String(10),
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
    # Tehran Municipal Region
    #
    # Region is currently specific to Tehran's
    # 22 municipal regions.
    #
    # For Tehran:
    #     region_id -> regions.id
    #
    # For other cities:
    #     region_id = NULL
    # ==========================================================

    region_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("regions.id"),
        nullable=True,
        index=True,
    )

    # ==========================================================
    # Coordinates
    # ==========================================================

    latitude: Mapped[float] = mapped_column(
        Numeric(10, 7),
        nullable=False,
    )

    longitude: Mapped[float] = mapped_column(
        Numeric(10, 7),
        nullable=False,
    )

    geohash: Mapped[str | None] = mapped_column(
        String(20),
        index=True,
        nullable=True,
    )

    geometry = mapped_column(
        Geometry(
            geometry_type="POINT",
            srid=4326,
            spatial_index=True,
        ),
        nullable=True,
    )

    geometry_type: Mapped[str | None] = mapped_column(
        String(20),
        default="POINT",
        nullable=True,
    )

    srid: Mapped[int] = mapped_column(
        Integer,
        default=4326,
        nullable=False,
    )

    # ==========================================================
    # Validation
    # ==========================================================

    validation_source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Possible values:
    # fimap
    # google
    # neshan
    # osm
    # manual
    # ai

    validation_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    confidence: Mapped[float | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    verified_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ==========================================================
    # Status
    # ==========================================================

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # ==========================================================
    # Relationships
    # ==========================================================

    store = relationship(
        "Store",
        back_populates="store_locations",
        lazy="selectin",
    )

    # NOTE:
    # We intentionally do NOT add a Region relationship here yet.
    #
    # region_id is retained as a nullable FK because Region currently
    # represents Tehran's 22 municipal regions. The existing database
    # architecture does not require a SQLAlchemy Region relationship
    # on StoreLocation at this stage.

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<StoreLocation("
            f"id={self.id}, "
            f"store_id={self.store_id}, "
            f"region_id={self.region_id}, "
            f"source='{self.validation_source}', "
            f"current={self.is_current}"
            f")>"
        )