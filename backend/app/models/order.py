"""
Order Model — Enterprise Data Model v4.1

Represents an order imported from an Excel/CSV file
within a specific ImportBatch and Project.

Architecture
------------

Company
    |
    +---- Project (مالک واقعی)
            |
            +---- Order

ImportBatch (Audit Record)
    |
    +---- Order (مرجع ضعیف)

Deleting Project deletes its Orders (ON DELETE CASCADE).

Deleting ImportBatch keeps Orders alive
(ON DELETE SET NULL on import_batch_id).
"""

from __future__ import annotations

import enum
from datetime import datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.models.base import BaseModel


if TYPE_CHECKING:
    from app.models.import_batch import ImportBatch
    from app.models.project import Project


# ==========================================================
# Order Status
# ==========================================================

class OrderStatus(str, enum.Enum):
    """
    Lifecycle status of an Order.

    This enum is intentionally local to the Order model because
    OrderStatus is not currently defined in app.core.enums.
    """

    NEW = "new"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


# ==========================================================
# Order Model
# ==========================================================

class Order(BaseModel):
    """
    Order imported from Excel/CSV.

    Each source row becomes one Order record.

    Ownership:

        Project
            |
            +---- Order

        ImportBatch
            |
            +---- Order

    Project is the real owner of the Order.

    ImportBatch is an audit/source reference only.
    """

    __tablename__ = "orders"

    # ==========================================================
    # Identity
    # ==========================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    # ==========================================================
    # Project Ownership
    # ==========================================================

    project_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
        comment="Project مالک واقعی این Order",
    )

    # ==========================================================
    # Import Batch Ownership / Audit Reference
    # ==========================================================

    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "import_batches.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
        comment="مرجع ضعیف به ImportBatch (Audit)",
    )

    # ==========================================================
    # Business Order Identity
    # ==========================================================

    order_code: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # Store Information
    #
    # Temporary source information from Excel.
    #
    # Future:
    # Order -> Store matching
    # ==========================================================

    store_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    store_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    # ==========================================================
    # Destination Address
    # ==========================================================

    address: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    # ==========================================================
    # Geographic Coordinates
    # ==========================================================

    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
    )

    # ==========================================================
    # Weight and Volume
    # ==========================================================

    weight_kg: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    volume_m3: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ==========================================================
    # Delivery Date and Time
    # ==========================================================

    delivery_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivery_time_from: Mapped[time | None] = mapped_column(
        Time(timezone=True),
        nullable=True,
    )

    delivery_time_to: Mapped[time | None] = mapped_column(
        Time(timezone=True),
        nullable=True,
    )

    # ==========================================================
    # Processing Status
    # ==========================================================

    status: Mapped[OrderStatus] = mapped_column(
        SQLAlchemyEnum(
            OrderStatus,
            native_enum=False,
            length=30,
        ),
        nullable=False,
        default=OrderStatus.NEW,
        index=True,
    )

    # ==========================================================
    # Raw Excel / Source Data
    # ==========================================================

    raw_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # ==========================================================
    # Error Information
    # ==========================================================

    error_note: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    # ==========================================================
    # Constraints
    # ==========================================================

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "order_code",
            name="uq_orders_project_order",
        ),
    )

    # ==========================================================
    # Relationships
    # ==========================================================

    project: Mapped["Project | None"] = relationship(
        "Project",
        back_populates="orders",
        lazy="selectin",
    )

    import_batch: Mapped["ImportBatch | None"] = relationship(
        "ImportBatch",
        back_populates="orders",
        lazy="selectin",
    )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def has_coordinates(self) -> bool:
        """
        Return True when latitude and longitude are present.
        """
        return (
            self.latitude is not None
            and self.longitude is not None
        )

    @property
    def is_geocoded(self) -> bool:
        """
        Return True when valid non-zero coordinates exist.
        """
        return (
            self.latitude is not None
            and self.longitude is not None
            and not (
                self.latitude == 0
                and self.longitude == 0
            )
        )

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<Order("
            f"id={self.id}, "
            f"project_id={self.project_id}, "
            f"import_batch_id={self.import_batch_id}, "
            f"order_code={self.order_code!r}, "
            f"status={self.status!r}"
            f")>"
        )