from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

class Request(BaseModel):
    __tablename__ = "requests"

    company_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    contact_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    mobile: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    industry: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    goal: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="SUBMITTED",
        nullable=False,
        index=True,
    )

    files: Mapped[list["RequestFile"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
    )