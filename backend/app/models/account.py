from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Account(BaseModel):
    __tablename__ = "accounts"

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
            f"mobile='{self.mobile}'"
            f")>"
        )