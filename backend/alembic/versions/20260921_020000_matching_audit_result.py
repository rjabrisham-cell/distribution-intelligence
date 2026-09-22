"""Persist the completed matching job's readiness snapshot.

Revision ID: 20260921_020000
Revises: 20260921_010000
"""
from alembic import op
import sqlalchemy as sa

revision = "20260921_020000"
down_revision = "20260921_010000"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("matching_jobs", sa.Column("audit_result", sa.JSON(), nullable=True))


def downgrade():
    # A downgrade must not silently destroy the only persisted readiness results.
    raise RuntimeError("Preserve matching_jobs.audit_result; use an application rollback instead")
