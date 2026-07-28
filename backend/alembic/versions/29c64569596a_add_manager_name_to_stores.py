"""add manager_name to stores

Revision ID: 29c64569596a
Revises: 600b325a6b39
Create Date: 2026-07-25 14:32:16.830057

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29c64569596a'
down_revision: Union[str, Sequence[str], None] = '600b325a6b39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('stores', sa.Column('manager_name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('stores', 'manager_name')
