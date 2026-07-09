from enum import Enum

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class FileType(str, Enum):
    ORDERS = "orders"
    FLEET = "fleet"
    DRIVERS = "drivers"
    GPS = "gps"
    OTHER = "other"


class RequestFile(BaseModel):
    __tablename__ = "request_files"

    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    file_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    original_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    stored_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    content_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    file_size: Mapped[int] = mapped_column(
        nullable=False,
    )

    request = relationship(
        "Request",
        back_populates="files",
    )