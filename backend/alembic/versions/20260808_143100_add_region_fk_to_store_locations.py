"""add region_id foreign key to store_locations

Revision ID: 5a6b3c8d9e0f
Revises: 1a2f5543b37b
Create Date: 2026-08-08 14:31:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a6b3c8d9e0f'
down_revision: Union[str, Sequence[str], None] = '1a2f5543b37b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add region_id column to store_locations (existing data → nullable)
    op.add_column('store_locations', sa.Column('region_id', sa.Integer(), nullable=True))
    
    # Create index for performance
    op.create_index('ix_store_locations_region_id', 'store_locations', ['region_id'])
    
    # Add foreign key constraint to regions table
    op.create_foreign_key(
        'fk_store_locations_region_id',
        'store_locations',
        'regions',
        ['region_id'],
        ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop foreign key constraint first
    op.drop_constraint('fk_store_locations_region_id', 'store_locations', type_='foreignkey')
    
    # Drop index
    op.drop_index('ix_store_locations_region_id', table_name='store_locations')
    
    # Drop column
    op.drop_column('store_locations', 'region_id')
