"""add geographic master data

Revision ID: 1a2f5543b37b
Revises: 29c64569596a
Create Date: 2026-08-08 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a2f5543b37b'
down_revision: Union[str, Sequence[str], None] = '29c64569596a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # provinces table
    op.create_table('provinces',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('file_id', sa.String(length=250), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('name_en', sa.String(length=80), nullable=False),
        sa.Column('status', sa.String(length=50), server_default=sa.text("'enable'"), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_provinces_status', 'provinces', ['status'])
    op.create_index('ix_provinces_file_id', 'provinces', ['file_id'])

    # cities table
    op.create_table('cities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('name_en', sa.String(length=255), nullable=True),
        sa.Column('province_id', sa.Integer(), nullable=False),
        sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column('status', sa.String(length=50), server_default=sa.text("'enable'"), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['province_id'], ['provinces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cities_status', 'cities', ['status'])
    op.create_index('ix_cities_province_id', 'cities', ['province_id'])

    # regions table
    op.create_table('regions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('city_id', sa.Integer(), nullable=False),
        sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column('status', sa.String(length=50), server_default=sa.text("'enable'"), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_regions_status', 'regions', ['status'])
    op.create_index('ix_regions_city_id', 'regions', ['city_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop in reverse order of dependencies
    op.drop_index('ix_regions_city_id', table_name='regions')
    op.drop_index('ix_regions_status', table_name='regions')
    op.drop_table('regions')

    op.drop_index('ix_cities_province_id', table_name='cities')
    op.drop_index('ix_cities_status', table_name='cities')
    op.drop_table('cities')

    op.drop_index('ix_provinces_file_id', table_name='provinces')
    op.drop_index('ix_provinces_status', table_name='provinces')
    op.drop_table('provinces')
