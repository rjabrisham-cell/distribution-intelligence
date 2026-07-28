"""
ImportBatch Model — Enterprise Data Model v4.1

ImportBatch = Data Import Event

An ImportBatch represents one data ingestion session.

It is a source/audit record.

It does NOT own the business entities imported from the file.

Business entities such as:

    Vehicle
    Driver
    Store
    Order
    GPSRecord

have their own lifecycle and ownership.

For Vehicles and Drivers:

    Vehicle.company_id -> Company
    Vehicle.import_batch_id -> ImportBatch

    Driver.company_id -> Company
    Driver.import_batch_id -> ImportBatch

For Orders:

    Order.project_id -> Project
    Order.import_batch_id -> ImportBatch

For Store:

    Store is the canonical physical location.

    Store does NOT currently contain:
        import_batch_id

    Therefore ImportBatch does NOT maintain a direct
    Store relationship.

Address ingestion and Store matching are handled through:

    AddressCandidate -> Store
    AddressCandidate -> CompanyStore

The ImportBatch relationship is therefore an
audit/source relationship for entities that explicitly
reference the ImportBatch through a ForeignKey.
"""


from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    JSON,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.core.enums import ImportStatus
from app.models.base import BaseModel


if TYPE_CHECKING:
    from app.models.driver import Driver
    from app.models.file import File
    from app.models.gps_record import GPSRecord
    from app.models.order import Order
    from app.models.row_error import RowError


class EntityType(str, Enum):
    """
    انواع موجودیت‌هایی که می‌توان از فایل import کرد.
    """

    ORDER = "order"
    FLEET = "fleet"
    DRIVER = "driver"
    STORE = "store"
    GPS = "gps"


class ImportBatch(BaseModel):
    """
    یک رویداد ورود داده از یک فایل Excel/CSV.

    ImportBatch مالک Business Entityها نیست.

    این مدل صرفاً برای ثبت:

        - منبع داده
        - نوع موجودیت واردشده
        - وضعیت پردازش
        - تعداد رکوردها
        - خطاها
        - زمان پردازش
        - ارتباط با فایل ورودی

    استفاده می‌شود.

    نکته معماری:

    ImportBatch فقط با مدل‌هایی رابطه مستقیم دارد که
    ForeignKey مربوط به import_batches.id را در جدول خود دارند.

    در معماری فعلی:

        Vehicle.import_batch_id -> ImportBatch.id
        Driver.import_batch_id -> ImportBatch.id
        Order.import_batch_id -> ImportBatch.id
        GPSRecord.import_batch_id -> ImportBatch.id

    اما:

        Store.import_batch_id

    در مدل Store وجود ندارد.

    بنابراین رابطه مستقیم:

        ImportBatch -> Store

    تعریف نشده است.

    برای داده‌های آدرس و مکان، مسیر فعلی معماری:

        ImportBatch
            |
            | source/audit context
            v
        AddressCandidate
            |
            +------> Store
            |
            +------> CompanyStore

    است.
    """

    __tablename__ = "import_batches"

    # ==========================================================
    # Source File
    # ==========================================================

    file_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "files.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # Entity Type
    # ==========================================================

    entity_type: Mapped[EntityType] = mapped_column(
        SQLAlchemyEnum(
            EntityType,
            native_enum=False,
            length=50,
        ),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # Processing Status
    # ==========================================================

    status: Mapped[ImportStatus] = mapped_column(
        SQLAlchemyEnum(
            ImportStatus,
            native_enum=False,
            length=50,
        ),
        nullable=False,
        default=ImportStatus.PROCESSING,
        index=True,
    )

    # ==========================================================
    # Row Counters
    # ==========================================================

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

    # ==========================================================
    # JSON Payloads
    # ==========================================================

    error_log: Mapped[Optional[list[dict]]] = mapped_column(
        JSON,
        nullable=True,
        comment=(
            "DEPRECATED — use row_errors relationship instead"
        ),
    )

    column_mapping: Mapped[
        Optional[dict[str, str]]
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    # ==========================================================
    # Processing Timestamps
    # ==========================================================

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ==========================================================
    # Relationships
    # ==========================================================

    # ----------------------------------------------------------
    # Source File
    # ----------------------------------------------------------

    file: Mapped["File"] = relationship(
        "File",
        back_populates="import_batches",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Imported Orders
    #
    # Requires:
    #
    # Order.import_batch_id
    #
    # and:
    #
    # Order.import_batch
    # ----------------------------------------------------------

    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="import_batch",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Imported Vehicles
    #
    # Requires:
    #
    # Vehicle.import_batch_id
    #
    # and:
    #
    # Vehicle.import_batch
    # ----------------------------------------------------------

    vehicles: Mapped[list["Vehicle"]] = relationship(
        "Vehicle",
        back_populates="import_batch",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Imported Drivers
    #
    # Requires:
    #
    # Driver.import_batch_id
    #
    # and:
    #
    # Driver.import_batch
    # ----------------------------------------------------------

    drivers: Mapped[list["Driver"]] = relationship(
        "Driver",
        back_populates="import_batch",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Imported GPS Records
    #
    # Requires:
    #
    # GPSRecord.import_batch_id
    #
    # and:
    #
    # GPSRecord.import_batch
    # ----------------------------------------------------------

    gps_records: Mapped[list["GPSRecord"]] = relationship(
        "GPSRecord",
        back_populates="import_batch",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Row-Level Errors
    # ----------------------------------------------------------

    row_errors: Mapped[list["RowError"]] = relationship(
        "RowError",
        back_populates="import_batch",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ==========================================================
    # Computed Properties
    # ==========================================================

    @property
    def progress_percent(self) -> float:
        """
        درصد پیشرفت import.
        """

        if self.total_rows == 0:
            return 0.0

        return round(
            (self.imported_rows / self.total_rows) * 100,
            1,
        )

    @property
    def has_errors(self) -> bool:
        """
        آیا این batch خطا دارد؟
        """

        return self.error_rows > 0

    @property
    def success_rate(self) -> float:
        """
        نرخ موفقیت import.
        """

        if self.total_rows == 0:
            return 0.0

        return round(
            (self.valid_rows / self.total_rows) * 100,
            1,
        )

    @property
    def is_finished(self) -> bool:
        """
        آیا پردازش batch تمام شده است؟
        """

        return self.status in (
            ImportStatus.COMPLETED,
            ImportStatus.COMPLETED_WITH_ERRORS,
            ImportStatus.FAILED,
        )

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<ImportBatch("
            f"id={self.id}, "
            f"entity={self.entity_type.value!r}, "
            f"status={self.status.value!r}, "
            f"rows={self.imported_rows}/{self.total_rows}"
            f")>"
        )