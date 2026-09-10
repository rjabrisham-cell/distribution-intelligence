"""
add store data readiness fields

Revision ID: 709c0f3c3aa4
Revises: 65f4666f828f
Create Date: 2026-08-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "709c0f3c3aa4"
down_revision: Union[str, Sequence[str], None] = "65f4666f828f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ==========================================================
    # Store Data Readiness
    # ==========================================================

    op.add_column(
        "stores",
        sa.Column(
            "data_quality_status",
            sa.Enum(
                "PENDING",
                "VALID",
                "INVALID",
                "WARNING",
                name="dataqualitystatus",
                native_enum=False,
                length=50,
            ),
            nullable=True,
            comment="وضعیت کیفیت داده‌های فروشگاه",
        ),
    )

    op.add_column(
        "stores",
        sa.Column(
            "geo_status",
            sa.Enum(
                "PENDING",
                "VALID",
                "INVALID",
                "MISSING",
                name="geostatus",
                native_enum=False,
                length=50,
            ),
            nullable=True,
            comment="وضعیت اعتبارسنجی جغرافیایی",
        ),
    )

    op.add_column(
        "stores",
        sa.Column(
            "duplicate_status",
            sa.Enum(
                "UNIQUE",
                "POSSIBLE_DUPLICATE",
                "DUPLICATE",
                "UNKNOWN",
                name="duplicatestatus",
                native_enum=False,
                length=50,
            ),
            nullable=True,
            comment="وضعیت شناسایی تکراری بودن",
        ),
    )

    op.add_column(
        "stores",
        sa.Column(
            "readiness_score",
            sa.Numeric(5, 2),
            nullable=True,
            comment="امتیاز آمادگی داده‌های فروشگاه (مثلاً 95.50)",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column("stores", "readiness_score")
    op.drop_column("stores", "duplicate_status")
    op.drop_column("stores", "geo_status")
    op.drop_column("stores", "data_quality_status")