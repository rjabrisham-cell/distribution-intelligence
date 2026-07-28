"""
RowError model — Sprint 2 (Contract v1.2).

Tracks per-row errors during data import.
Replaces inline error_log JSON for structured error reporting.

Relationship:
    ImportBatch (1:M) ──< RowError
"""

from __future__ import annotations

from sqlalchemy import (
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class RowError(BaseModel):
    """
    خطای یک ردیف مشخص در Import Batch.

    جایگزین error_log JSON با یک جدول رابطه‌ای برای
    قابلیت جستجو، فیلتر و گزارش‌گیری دقیق.
    """

    __tablename__ = "row_errors"

    # ── Foreign Key ──────────────────────────────────────────
    import_batch_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Row Identification ──────────────────────────────────
    row_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="شماره ردیف در فایل Excel/CSV (از ۱)",
    )

    # ── Error Details ───────────────────────────────────────
    error_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="نوع خطا: VALIDATION, DUPLICATE, FORMAT, MISSING_FIELD, etc.",
    )

    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="پیام خطای قابل نمایش به کاربر",
    )

    field_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="نام فیلد مشکل‌دار (در صورت مرتبط بودن با یک ستون)",
    )

    # ── Raw Data ────────────────────────────────────────────
    raw_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="داده خام ردیف برای اشکال‌زدایی",
    )

    # ── Relationships ────────────────────────────────────────
    import_batch: Mapped["ImportBatch"] = relationship(
        "ImportBatch",
        back_populates="row_errors",
    )

    # ── Representation ───────────────────────────────────────
    def __repr__(self) -> str:
        return (
            f"<RowError(id={self.id}, batch={self.import_batch_id}, "
            f"row={self.row_number}, type={self.error_type!r})>"
        )
