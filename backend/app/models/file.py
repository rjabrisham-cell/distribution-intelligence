from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.models.base import BaseModel


if TYPE_CHECKING:
    from app.models.import_batch import ImportBatch


class File(BaseModel):
    __tablename__ = "files"

    # ==========================================================
    # Entity Reference
    # ==========================================================

    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    entity_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    # ==========================================================
    # File Classification
    # ==========================================================

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # ==========================================================
    # File Identity
    # ==========================================================

    original_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    stored_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    # ==========================================================
    # File Metadata
    # ==========================================================

    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # ==========================================================
    # Uploaded By
    # ==========================================================

    uploaded_by: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="Account ID of the user who uploaded this file.",
    )

    # ==========================================================
    # Relationships
    # ==========================================================

    # ----------------------------------------------------------
    # Import Batches
    # ----------------------------------------------------------

    import_batches: Mapped[list["ImportBatch"]] = relationship(
        "ImportBatch",
        back_populates="file",
        cascade="all, delete-orphan",
    )

    # ==========================================================
    # Helpers
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<File("
            f"id={self.id}, "
            f"name='{self.original_name}', "
            f"entity={self.entity_type}:{self.entity_id}"
            f")>"
        )

    @property
    def file_size_human(self) -> str:
        if self.file_size is None:
            return "0 B"

        size = float(self.file_size)

        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                if unit == "B":
                    return f"{int(size)} {unit}"

                return f"{size:.1f} {unit}"

            size /= 1024

        return f"{size:.1f} PB"