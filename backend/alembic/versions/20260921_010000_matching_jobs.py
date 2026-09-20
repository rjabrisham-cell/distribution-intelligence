"""create durable matching jobs queue

Revision ID: 20260921_010000
Revises: 20260913_010000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260921_010000"
down_revision = "20260913_010000"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "matching_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="QUEUED", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["batch_id"], ["import_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_matching_jobs_account_id", "matching_jobs", ["account_id"])
    op.create_index("ix_matching_jobs_project_id", "matching_jobs", ["project_id"])
    op.create_index("ix_matching_jobs_batch_id", "matching_jobs", ["batch_id"])
    op.create_index(
        "uq_matching_jobs_active_project_batch", "matching_jobs", ["project_id", "batch_id"],
        unique=True, postgresql_where=sa.text("status IN ('QUEUED', 'PROCESSING')")
    )
    op.create_index(
        "uq_matching_jobs_active_account", "matching_jobs", ["account_id"],
        unique=True, postgresql_where=sa.text("status IN ('QUEUED', 'PROCESSING')")
    )
    op.create_index(
        "ix_matching_jobs_queued_pickup", "matching_jobs", ["id"],
        postgresql_where=sa.text("status = 'QUEUED'")
    )
    op.create_index(
        "ix_matching_jobs_processing_heartbeat", "matching_jobs", ["heartbeat_at"],
        postgresql_where=sa.text("status = 'PROCESSING'")
    )


def downgrade():
    op.drop_table("matching_jobs")
