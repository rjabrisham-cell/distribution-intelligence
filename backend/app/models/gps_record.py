"""
GPSRecord model for Data Import Engine.

Represents a single GPS data point imported from external sources (Excel, API, etc.).
Each record is linked to a vehicle plate and belongs to an ImportBatch.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

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

if TYPE_CHECKING:
    from app.models.import_batch import ImportBatch

class GPSRecord(BaseModel):
    """
    رکورد GPS واردشده از فایل Excel در هر Import Batch.

    هر ردیف از فایل Excel به یک رکورد GPSRecord تبدیل می‌شود.
    """

    __tablename__ = "gps_records"

    # ── ارتباط با Import Batch ──────────────────────────────
    import_batch_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("import_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── وسیله نقلیه مرتبط ───────────────────────────────────
    vehicle_plate: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # ── مختصات ──────────────────────────────────────────────
    latitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 7),
        nullable=False,
    )

    longitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 7),
        nullable=False,
    )

    # ── زمان ثبت ────────────────────────────────────────────
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # ── سرعت و جهت ──────────────────────────────────────────
    speed_kmh: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    heading: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ── دقت ────────────────────────────────────────────────
    accuracy_m: Mapped[float | None] = mapped_column(
        Float,
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
    import_batch: Mapped["ImportBatch | None"] = relationship(
        "ImportBatch",
        back_populates="gps_records",
        lazy="selectin",
    )

    # ── Properties ──────────────────────────────────────────

    @property
    def is_high_accuracy(self) -> bool:
        """آیا دقت GPS بالا (≤ ۱۰ متر) است."""
        return self.accuracy_m is not None and self.accuracy_m <= 10.0

    @property
    def is_moving(self) -> bool:
        """آیا وسیله نقلیه در حال حرکت است (سرعت > ۱ km/h)."""
        return self.speed_kmh is not None and self.speed_kmh > 1.0

    def __repr__(self) -> str:
        return (
            f"<GPSRecord(id={self.id}, plate={self.vehicle_plate!r}, "
            f"at={self.timestamp})>"
        )
