from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Vehicle(BaseModel):
    """
    خودروی واردشده از فایل Excel در هر Import Batch.

    هر ردیف از فایل Excel (یا Sheet خودروها) به یک رکورد Vehicle تبدیل می‌شود.
    """

    __tablename__ = "vehicles"

    # ── ارتباط با Import Batch ──────────────────────────────
    import_batch_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── شناسه خودرو ─────────────────────────────────────────
    vehicle_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # ── پلاک ────────────────────────────────────────────────
    plate_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # ── نوع خودرو ───────────────────────────────────────────
    vehicle_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ── ظرفیت ───────────────────────────────────────────────
    capacity_kg: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    capacity_m3: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ── هزینه‌ها ────────────────────────────────────────────
    cost_per_km: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    fixed_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    # ── مختصات پایگاه (Depot) ───────────────────────────────
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

    # ── زمان‌های عملیاتی ────────────────────────────────────
    available_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    available_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    # ── Relationships ────────────────────────────────────────
    import_batch: Mapped["ImportBatch"] = relationship(
        "ImportBatch",
        back_populates="vehicles",
    )

    # ── Properties ──────────────────────────────────────────

    @property
    def has_capacity(self) -> bool:
        """آیا حداقل یکی از ظرفیت‌ها (کیلوگرم / مترمکعب) ثبت شده."""
        return self.capacity_kg is not None or self.capacity_m3 is not None

    @property
    def has_coordinates(self) -> bool:
        """آیا مختصات دپو ثبت شده."""
        return self.latitude is not None and self.longitude is not None

    @property
    def is_available_now(self) -> bool:
        """آیا خودرو در بازه زمانی فعلی در دسترس است."""
        if self.status != "active":
            return False
        now = datetime.now().astimezone()
        if self.available_from and now < self.available_from:
            return False
        if self.available_until and now > self.available_until:
            return False
        return True

    def __repr__(self) -> str:
        return (
            f"<Vehicle(id={self.id}, code={self.vehicle_code!r}, "
            f"plate={self.plate_number!r})>"
        )
