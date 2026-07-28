"""
Order Model — Enterprise Data Model v4.0

Represents an order imported from an Excel file
within a specific ImportBatch and Project.

Architecture
------------

Company
    |
    +---- Project
            |
            +---- Order
                    |
                    +---- ImportBatch

An Order belongs to exactly one Project.

An Order also belongs to exactly one ImportBatch.

Project owns the operational boundary of Orders.

ImportBatch represents the source/import operation.

Deleting a Project may delete its Orders depending on
the configured database relationship policy.

Deleting an ImportBatch deletes its imported Orders
because Order.import_batch_id uses ON DELETE CASCADE.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

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
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.models.base import BaseModel


if TYPE_CHECKING:
    from app.models.import_batch import ImportBatch
    from app.models.project import Project


class Order(BaseModel):
    """
    Order imported from an Excel file.

    Each Excel row becomes one Order record.

    An Order belongs to:

        - exactly one Project
        - exactly one ImportBatch

    The Project defines the business/operational workspace.

    The ImportBatch defines the source import operation.
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

    project_id: Mapped[int] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
        comment="Project مالک این Order",
    )

    # ==========================================================
    # Import Batch
    # ==========================================================

    import_batch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "import_batches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
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
    # ==========================================================

    store_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    store_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
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

    delivery_time_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivery_time_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ==========================================================
    # Processing Status
    # ==========================================================

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="NEW",
        index=True,
    )

    # ==========================================================
    # Raw Excel Row Data
    # ==========================================================

    raw_data: Mapped[dict | None] = mapped_column(
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
            "import_batch_id",
            "order_code",
            name="uq_orders_batch_order",
        ),
    )

    # ==========================================================
    # Relationships
    # ==========================================================

    # ----------------------------------------------------------
    # Project
    # ----------------------------------------------------------

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="orders",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Import Batch
    # ----------------------------------------------------------

    import_batch: Mapped["ImportBatch"] = relationship(
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
        Returns True when latitude and longitude exist.

        Coordinates may technically be zero.
        """

        return (
            self.latitude is not None
            and self.longitude is not None
        )

    @property
    def is_geocoded(self) -> bool:
        """
        Returns True when valid non-zero coordinates exist.
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