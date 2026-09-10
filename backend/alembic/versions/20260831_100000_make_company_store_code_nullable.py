"""make company store code nullable

Revision ID: 20260831_100000
Revises: 709c0f3c3aa4
Create Date: 2026-08-31 10:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260831_100000"
down_revision: Union[str, Sequence[str], None] = "709c0f3c3aa4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "company_stores",
        "store_code",
        existing_type=sa.String(length=128),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "company_stores",
        "store_code",
        existing_type=sa.String(length=128),
        nullable=False,
    )