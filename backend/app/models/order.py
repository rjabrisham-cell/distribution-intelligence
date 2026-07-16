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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Order(BaseModel):
    """
    سفارش واردشده از فایل Excel در هر Import Batch.

    هر ردیف از فایل Excel به یک رکورد Order تبدیل می‌شود.
    """

    __tablename__ = "orders"

    # ── ارتباط با Import Batch ──────────────────────────────
    import_batch_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── کلید تجاری سفارش ────────────────────────────────────
    order_code: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    # ── اطلاعات فروشگاه (Store) ─────────────────────────────
    store_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    store_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # ── آدرس مقصد ───────────────────────────────────────────
    address: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    # ── مختصات جغرافیایی ────────────────────────────────────
    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )

    # ── وزن و حجم ───────────────────────────────────────────
    weight_kg: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    volume_m3: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ── اطلاعات زمانی تحویل ─────────────────────────────────
    delivery_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivery_time_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivery_time_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── وضعیت پردازش ────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="NEW",
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
            "order_code",
            name="uq_orders_batch_order",
        ),
    )

    # ── Relationships ────────────────────────────────────────
    import_batch: Mapped["ImportBatch"] = relationship(
        "ImportBatch",
        back_populates="orders",
    )

    # ── Properties ──────────────────────────────────────────

    @property
    def has_coordinates(self) -> bool:
        """آیا مختصات دارد (حتی اگر صفر باشد)."""
        return self.latitude is not None and self.longitude is not None

    @property
    def is_geocoded(self) -> bool:
        """آیا مختصات معتبر دارد (نه صفر مطلق)."""
        return (
            self.latitude is not None
            and self.longitude is not None
            and not (self.latitude == 0 and self.longitude == 0)
        )

    def __repr__(self) -> str:
        return (
            f"<Order(id={self.id}, code={self.order_code!r}, "
            f"status={self.status!r})>"
        )
