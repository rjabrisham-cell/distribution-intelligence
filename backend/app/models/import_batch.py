from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ImportStatus(str, Enum):
    """وضعیت‌های چرخهٔ عمر یک Import Batch."""

    PENDING = "pending"
    VALIDATING = "validating"
    VALIDATED = "validated"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"


class EntityType(str, Enum):
    """انواع موجودیت‌هایی که می‌توان از فایل import کرد."""

    ORDER = "order"
    FLEET = "fleet"
    DRIVER = "driver"
    STORE = "store"
    GPS = "gps"


class ImportBatch(BaseModel):
    """
    یک Batch ورود داده از یک فایل (Excel/CSV).

    هر ImportBatch وضعیت خود را از PENDING → VALIDATING → … → COMPLETED طی می‌کند
    و آمار rows را در خود نگه می‌دارد.

    ستون‌های id, created_at, updated_at از BaseModel به ارث می‌رسند.
    """

    __tablename__ = "import_batches"

    # ── Foreign Key ──────────────────────────────────────────
    file_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Entity ───────────────────────────────────────────────
    entity_type: Mapped[EntityType] = mapped_column(
        SQLAlchemyEnum(EntityType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )

    # ── Status ───────────────────────────────────────────────
    status: Mapped[ImportStatus] = mapped_column(
        SQLAlchemyEnum(ImportStatus, native_enum=False, length=50),
        nullable=False,
        default=ImportStatus.PENDING,
        index=True,
    )

    # ── Counts ───────────────────────────────────────────────
    total_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    valid_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    error_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    imported_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # ── JSON Payloads ────────────────────────────────────────
    error_log: Mapped[Optional[list[dict]]] = mapped_column(
        JSON,
        nullable=True,
    )

    column_mapping: Mapped[Optional[dict[str, str]]] = mapped_column(
        JSON,
        nullable=True,
    )

    # ── Timestamps (اختصاصی ImportBatch) ────────────────────
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ────────────────────────────────────────
    file: Mapped["File"] = relationship(
        "File",
        back_populates="import_batches",
    )

    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="import_batch",
        lazy="dynamic",
    )

    vehicles: Mapped[list["Vehicle"]] = relationship(
        "Vehicle",
        back_populates="import_batch",
        lazy="dynamic",
    )

    drivers: Mapped[list["Driver"]] = relationship(
        "Driver",
        back_populates="import_batch",
        lazy="dynamic",
    )

    stores: Mapped[list["Store"]] = relationship(
        "Store",
        back_populates="import_batch",
        lazy="dynamic",
    )

    gps_records: Mapped[list["GPSRecord"]] = relationship(
        "GPSRecord",
        back_populates="import_batch",
        lazy="dynamic",
    )

    # ── Computed Properties (Dashboard) ──────────────────────

    @property
    def progress_percent(self) -> float:
        """درصد پیشرفت import (بر اساس imported_rows)."""
        if self.total_rows == 0:
            return 0.0
        return round((self.imported_rows / self.total_rows) * 100, 1)

    @property
    def has_errors(self) -> bool:
        """آیا این batch خطا دارد."""
        return self.error_rows > 0

    @property
    def success_rate(self) -> float:
        """نرخ موفقیت (valid_rows / total_rows)."""
        if self.total_rows == 0:
            return 0.0
        return round((self.valid_rows / self.total_rows) * 100, 1)

    @property
    def is_finished(self) -> bool:
        """آیا کار batch تمام شده (چه با موفقیت چه با شکست)."""
        return self.status in (ImportStatus.COMPLETED, ImportStatus.FAILED)

    # ── Representation ───────────────────────────────────────
    def __repr__(self) -> str:
        return (
            f"<ImportBatch(id={self.id}, entity={self.entity_type.value!r}, "
            f"status={self.status.value!r}, "
            f"rows={self.imported_rows}/{self.total_rows})>"
        )
