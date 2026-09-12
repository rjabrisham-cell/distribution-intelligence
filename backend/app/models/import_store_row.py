"""Immutable input membership for every accepted store row, including no address."""

from sqlalchemy import ForeignKey, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ImportStoreRow(BaseModel):
    __tablename__ = "import_store_rows"
    __table_args__ = (UniqueConstraint("batch_id", "row_number", name="uq_import_store_row"),)

    batch_id: Mapped[int] = mapped_column(
        ForeignKey("import_batches.id", ondelete="RESTRICT"), nullable=False, index=True,
    )
    company_store_id: Mapped[int] = mapped_column(
        ForeignKey("company_stores.id", ondelete="RESTRICT"), nullable=False, index=True,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
