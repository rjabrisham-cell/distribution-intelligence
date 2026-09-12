"""Add invitation access without claiming SMS verification or backfilling history."""
from alembic import op
import sqlalchemy as sa

revision = "20260913_010000"
down_revision = "20260912_020000"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("accounts", sa.Column("demo_access_granted_at", sa.DateTime(timezone=True), nullable=True))
    for name, cols in [
        ("demo_access_codes", [sa.Column("code_hash", sa.String(128), nullable=False, unique=True), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("max_mobile_uses", sa.Integer(), nullable=False), sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True), sa.CheckConstraint("max_mobile_uses > 0")]),
        ("demo_access_code_usages", [sa.Column("access_code_id", sa.Integer(), sa.ForeignKey("demo_access_codes.id"), nullable=False), sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False), sa.Column("first_used_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("access_code_id", "account_id")]),
    ]:
        op.create_table(name, sa.Column("id", sa.Integer(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), *cols)
    for col in ["access_code_id", "account_id"]:
        op.create_index("ix_demo_access_code_usages_" + col, "demo_access_code_usages", [col])


def downgrade():
    # Only for isolated migration tests; never a live rollback procedure.
    op.drop_table("demo_access_code_usages")
    op.drop_table("demo_access_codes")
    op.drop_column("accounts", "demo_access_granted_at")
