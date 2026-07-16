"""
Driver model for Data Import Engine.

Represents a driver imported from external sources (ERP, Excel, API, etc.).
Each driver belongs to an ImportBatch.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Driver(BaseModel):
    """
    راننده واردشده از فایل Excel در هر Import Batch.

    هر ردیف از فایل Excel به یک رکورد Driver تبدیل می‌شود.
    """

    __tablename__ = "drivers"

    # ── ارتباط با Import Batch ──────────────────────────────
    import_batch_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── کد تجاری راننده ─────────────────────────────────────
    driver_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    # ── اطلاعات هویتی ───────────────────────────────────────
    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    # ── اطلاعات گواهینامه ───────────────────────────────────
    license_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    license_expiry: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    experience_years: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # ── مختصات جغرافیایی (آدرس سکونت / محل استقرار) ─────────
    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )

    # ── وضعیت ───────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="active",
        index=True,
    )

    # ── داده خام ردیف Excel (برای اشکال‌زدایی) ─────────────
    raw_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # ── یادداشت خطا ─────────────────────────────────────────
    error_note: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    # ── محدودیت یکتایی ──────────────────────────────────────
    __table_args__ = (
        UniqueConstraint(
            "import_batch_id",
            "driver_code",
            name="uq_drivers_batch_driver",
        ),
    )

    # ── Relationships ────────────────────────────────────────
    import_batch: Mapped["ImportBatch"] = relationship(
        "ImportBatch",
        back_populates="drivers",
    )

    # ── Properties ──────────────────────────────────────────

    @property
    def full_name(self) -> str | None:
        """نام کامل (ترکیب first_name + last_name)."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name

    @property
    def is_active(self) -> bool:
        """آیا راننده فعال است."""
        return self.status.lower() == "active"

    @property
    def has_start_coordinates(self) -> bool:
        """آیا مختصات محل استقرار ثبت شده."""
        return self.latitude is not None and self.longitude is not None

    def __repr__(self) -> str:
        return (
            f"<Driver(id={self.id}, code={self.driver_code!r}, "
            f"name={self.full_name!r}, status={self.status!r})>"
        )
