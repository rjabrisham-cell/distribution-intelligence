from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Company(BaseModel):
    __tablename__ = "companies"

    # --------------------------------------------------
    # Account
    # --------------------------------------------------

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
    )

    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="company",
    )

    # --------------------------------------------------
    # Basic Information
    # --------------------------------------------------

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    economic_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    national_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    address: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # --------------------------------------------------
    # Projects
    # --------------------------------------------------

    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="company",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # --------------------------------------------------
    # Representation (Session-safe — no lazy-load)
    # --------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<Company("
            f"name={self.name!r}"
            f")>"
        )
