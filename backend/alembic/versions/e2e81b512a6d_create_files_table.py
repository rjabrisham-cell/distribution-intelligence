"""create files table

Revision ID: e2e81b512a6d
Revises: a5f2bbe42d1a
Create Date: 2026-07-14

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision = "e2e81b512a6d"
down_revision = "a5f2bbe42d1a"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "files",

        sa.Column(
            "entity_type",
            sa.String(50),
            nullable=False,
        ),

        sa.Column(
            "entity_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "category",
            sa.String(50),
            nullable=False,
        ),

        sa.Column(
            "original_name",
            sa.String(255),
            nullable=False,
        ),

        sa.Column(
            "stored_name",
            sa.String(255),
            nullable=False,
            unique=True,
        ),

        sa.Column(
            "file_path",
            sa.String(500),
            nullable=False,
        ),

        sa.Column(
            "content_type",
            sa.String(100),
            nullable=True,
        ),

        sa.Column(
            "file_size",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_files_entity_type",
        "files",
        ["entity_type"],
    )

    op.create_index(
        "ix_files_entity_id",
        "files",
        ["entity_id"],
    )

    op.create_index(
        "ix_files_category",
        "files",
        ["category"],
    )

    op.create_index(
        "ix_files_id",
        "files",
        ["id"],
    )

    # ----------------------------------------------------
    # Migrate old request_files
    # ----------------------------------------------------

    op.execute(
        """
        INSERT INTO files
        (
            entity_type,
            entity_id,
            category,
            original_name,
            stored_name,
            file_path,
            content_type,
            file_size,
            created_at,
            updated_at
        )

        SELECT
            'REQUEST',
            request_id,
            file_type,
            original_name,
            stored_name,
            file_path,
            content_type,
            file_size,
            created_at,
            updated_at

        FROM request_files
        """
    )


def downgrade():

    op.execute(
        """
        DELETE FROM files
        WHERE entity_type='REQUEST'
        """
    )

    op.drop_index("ix_files_id", table_name="files")
    op.drop_index("ix_files_category", table_name="files")
    op.drop_index("ix_files_entity_id", table_name="files")
    op.drop_index("ix_files_entity_type", table_name="files")

    op.drop_table("files")