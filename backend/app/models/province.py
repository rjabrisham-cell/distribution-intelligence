"""
SQLAlchemy Model: Province
Table: provinces
"""

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Province(Base):
    __tablename__ = "provinces"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    file_id: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    name_en: Mapped[str] = mapped_column(
        String(80),
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

    cities: Mapped[list["City"]] = relationship(
        "City",
        back_populates="province",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<Province id={self.id} name={self.name!r}>"
