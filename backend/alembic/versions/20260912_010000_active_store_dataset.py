"""Explicit active store dataset and retained import membership; no backfill."""

from alembic import op
import sqlalchemy as sa

revision = "20260912_010000"
down_revision = "20260831_100000"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("files", sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("active_store_batch_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_projects_active_store_batch", "projects", "import_batches",
                          ["active_store_batch_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_projects_active_store_batch_id", "projects", ["active_store_batch_id"])
    op.create_table(
        "import_store_rows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("import_batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("company_store_id", sa.Integer(), sa.ForeignKey("company_stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("batch_id", "row_number", name="uq_import_store_row"),
    )
    op.create_index("ix_import_store_rows_batch_id", "import_store_rows", ["batch_id"])
    op.create_index("ix_import_store_rows_company_store_id", "import_store_rows", ["company_store_id"])


def downgrade():
    # Refuse destructive rollback after the new workflow has recorded history.
    connection = op.get_bind()
    used = connection.execute(sa.text(
        "SELECT EXISTS(SELECT 1 FROM import_store_rows) "
        "OR EXISTS(SELECT 1 FROM files WHERE removed_at IS NOT NULL) "
        "OR EXISTS(SELECT 1 FROM projects WHERE active_store_batch_id IS NOT NULL)"
    )).scalar()
    if used:
        raise RuntimeError("Cannot downgrade: active dataset/history must be retained.")
    op.drop_table("import_store_rows")
    op.drop_index("ix_projects_active_store_batch_id", table_name="projects")
    op.drop_constraint("fk_projects_active_store_batch", "projects", type_="foreignkey")
    op.drop_column("projects", "active_store_batch_id")
    op.drop_column("files", "removed_at")
