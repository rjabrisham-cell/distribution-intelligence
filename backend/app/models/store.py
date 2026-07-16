"""
Store model for Data Import Engine.

Represents a store (customer/shop) imported from external sources.
In the future B2B2C architecture, this entity represents the "Store" layer
between Company and Consumer.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Store(BaseModel):
    """
    فروشگاه (Store) واردشده از فایل Excel در هر Import Batch.

    در معماری B2B2C آینده، این موجودیت لایهٔ «فروشگاه» بین
    «شرکت» و «مصرف‌کنندهٔ نهایی» را تشکیل می‌دهد.
    """

    __tablename__ = "stores"

    # ── ارتباط با Import Batch ──────────────────────────────
    import_batch_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── شناسه فروشگاه ───────────────────────────────────────
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # ── اطلاعات هویتی ───────────────────────────────────────
    name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    # ── اطلاعات تماس ────────────────────────────────────────
    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

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

    # ── دسته‌بندی ───────────────────────────────────────────
    category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # ── اولویت ──────────────────────────────────────────────
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # ── وضعیت ───────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="active",
        index=True,
    )

    # ── زمان تخمینی سرویس (دقیقه) ──────────────────────────
    service_time_min: Mapped[int | None] = mapped_column(
        Integer,
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

    # ── محدودیت یکتایی ──────────────────────────────────────
    __table_args__ = (
        UniqueConstraint(
            "import_batch_id",
            "code",
            name="uq_stores_batch_code",
        ),
    )

    # ── Relationships ────────────────────────────────────────
    import_batch: Mapped["ImportBatch"] = relationship(
        "ImportBatch",
        back_populates="stores",
    )

    # ── Properties ──────────────────────────────────────────

    @property
    def has_coordinates(self) -> bool:
        """آیا مختصات ثبت شده (حتی اگر صفر باشد)."""
        return self.latitude is not None and self.longitude is not None

    @property
    def is_geocoded(self) -> bool:
        """آیا مختصات معتبر دارد (نه صفر مطلق)."""
        return (
            self.latitude is not None
            and self.longitude is not None
            and not (self.latitude == 0 and self.longitude == 0)
        )

    @property
    def is_vip(self) -> bool:
        """آیا فروشگاه VIP است."""
        return self.category is not None and self.category.upper() == "VIP"

    @property
    def is_active(self) -> bool:
        """آیا فروشگاه فعال است."""
        return self.status == "active"

    def __repr__(self) -> str:
        return (
            f"<Store(id={self.id}, code={self.code!r}, "
            f"name={self.name!r})>"
        )
