from sqlalchemy import String, DateTime
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Account(BaseModel):
    __tablename__ = "accounts"
    mobile_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ==========================================================
    # Identity
    # ==========================================================

    mobile: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    # ==========================================================
    # Relationships
    # ==========================================================

    company = relationship(
        "Company",
        back_populates="account",
        uselist=False,
        lazy="selectin",
    )

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<Account("
            f"id={self.id}, "
            "mobile=<redacted>"
            f")>"
        )
