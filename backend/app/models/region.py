"""
SQLAlchemy Model: Region
Table: regions
"""

from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id"),
        nullable=False,
        index=True,
    )
    latitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 7),
        nullable=False,
    )
    longitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 7),
        nullable=False,
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

    city: Mapped["City"] = relationship(
        "City",
        back_populates="regions",
    )

    def __repr__(self) -> str:
        return f"<Region id={self.id} name={self.name!r} city_id={self.city_id}>"
