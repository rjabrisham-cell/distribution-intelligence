from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Account(BaseModel):
    __tablename__ = "accounts"

    mobile: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    company = relationship(
        "Company",
        back_populates="account",
        uselist=False,
    )
