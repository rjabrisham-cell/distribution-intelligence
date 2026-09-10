"""
SQLAlchemy Model: City
Table: cities
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    name_en: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    province_id: Mapped[int] = mapped_column(
        ForeignKey("provinces.id"),
        nullable=False,
        index=True,
    )

    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="enable",
        index=True,
    )

    created_by: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    updated_by: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    province: Mapped["Province"] = relationship(
        "Province",
        back_populates="cities",
    )

    regions: Mapped[list["Region"]] = relationship(
        "Region",
        back_populates="city",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return (
            f"<City id={self.id} "
            f"name={self.name!r} "
            f"province_id={self.province_id}>"
        )