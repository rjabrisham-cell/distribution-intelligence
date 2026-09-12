"""Add public demo identity, session and trial ownership without backfill."""
from alembic import op
import sqlalchemy as sa

revision = "20260912_020000"
down_revision = "20260912_010000"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("accounts", sa.Column("mobile_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("trial_owner_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_projects_trial_owner", "projects", "accounts", ["trial_owner_id"], ["id"])
    op.create_index("ix_projects_trial_owner_id", "projects", ["trial_owner_id"])
    op.add_column("projects", sa.Column("trial_state", sa.String(20), nullable=True))
    op.add_column("projects", sa.Column("trial_result_batch_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_projects_trial_result", "projects", "import_batches", ["trial_result_batch_id"], ["id"])
    op.add_column("projects", sa.Column("trial_consumed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("trial_file_hash", sa.String(64), nullable=True))
    for name, columns in [
        ("demo_challenges", [sa.Column("reference", sa.String(64), nullable=False, unique=True), sa.Column("mobile", sa.String(20), nullable=False), sa.Column("ip_hash", sa.String(64), nullable=False), sa.Column("proof_hash", sa.String(256), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("attempts", sa.Integer(), nullable=False), sa.Column("used_at", sa.DateTime(timezone=True), nullable=True)]),
        ("demo_sessions", [sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False, unique=True), sa.Column("csrf_hash", sa.String(64), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True)]),
        ("demo_rate_events", [sa.Column("key_hash", sa.String(64), nullable=False)]),
    ]:
        op.create_table(name, sa.Column("id", sa.Integer(), primary_key=True),
                        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
                        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), *columns)
    for table, cols in [("demo_challenges", ["mobile", "ip_hash"]), ("demo_sessions", ["account_id"]), ("demo_rate_events", ["key_hash"])]:
        for col in cols:
            op.create_index(f"ix_{table}_{col}", table, [col])


def downgrade():
    # Destructive downgrade is for the disposable test schema only, never live DIP.
    for name in ["demo_rate_events", "demo_sessions", "demo_challenges"]:
        op.drop_table(name)
    op.drop_constraint("fk_projects_trial_result", "projects", type_="foreignkey")
    op.drop_constraint("fk_projects_trial_owner", "projects", type_="foreignkey")
    op.drop_index("ix_projects_trial_owner_id", table_name="projects")
    for col in ["trial_file_hash", "trial_consumed_at", "trial_result_batch_id", "trial_state", "trial_owner_id"]:
        op.drop_column("projects", col)
    op.drop_column("accounts", "mobile_verified_at")
