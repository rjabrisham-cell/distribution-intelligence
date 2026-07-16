from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Request(BaseModel):
    __tablename__ = "requests"

    # --------------------------------------------------
    # Company Information
    # --------------------------------------------------

    company_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
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

    # --------------------------------------------------
    # Workflow
    # --------------------------------------------------

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="SUBMITTED",
        index=True,
    )

    # --------------------------------------------------
    # Files
    # --------------------------------------------------

    files: Mapped[list["RequestFile"]] = relationship(
        "RequestFile",
        back_populates="request",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # --------------------------------------------------
    # Representation
    # --------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<Request("
            f"id={self.id}, "
            f"company='{self.company_name}', "
            f"status='{self.status}'"
            f")>"
        )