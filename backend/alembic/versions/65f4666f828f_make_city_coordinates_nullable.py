"""make city coordinates nullable

Revision ID: 65f4666f828f
Revises: 5a6b3c8d9e0f
Create Date: 2026-08-08 18:29:42.241698

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "65f4666f828f"
down_revision: Union[str, Sequence[str], None] = "5a6b3c8d9e0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make city coordinates nullable."""

    op.alter_column(
        "cities",
        "latitude",
        existing_type=sa.Numeric(precision=10, scale=7),
        nullable=True,
    )

    op.alter_column(
        "cities",
        "longitude",
        existing_type=sa.Numeric(precision=10, scale=7),
        nullable=True,
    )


def downgrade() -> None:
    """Restore city coordinates as NOT NULL."""

    op.alter_column(
        "cities",
        "latitude",
        existing_type=sa.Numeric(precision=10, scale=7),
        nullable=False,
    )

    op.alter_column(
        "cities",
        "longitude",
        existing_type=sa.Numeric(precision=10, scale=7),
        nullable=False,
    )