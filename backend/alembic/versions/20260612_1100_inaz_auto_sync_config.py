"""inaz auto sync config

Revision ID: 20260612_1100
Revises: 20260612_0900
Create Date: 2026-06-12 11:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260612_1100"
down_revision = "20260612_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inaz_auto_sync_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("credential_id", sa.Integer(), nullable=True),
        sa.Column("collaborator_limit", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["credential_id"], ["inaz_credentials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inaz_auto_sync_config_credential_id", "inaz_auto_sync_config", ["credential_id"], unique=False)
    op.create_index(
        "ix_inaz_auto_sync_config_updated_by_user_id",
        "inaz_auto_sync_config",
        ["updated_by_user_id"],
        unique=False,
    )
    op.execute(
        sa.text(
            """
            INSERT INTO inaz_auto_sync_config (id, job_enabled, credential_id, collaborator_limit, updated_at, updated_by_user_id)
            VALUES (1, FALSE, NULL, NULL, NULL, NULL)
            """
        )
    )
    op.alter_column("inaz_auto_sync_config", "job_enabled", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_inaz_auto_sync_config_updated_by_user_id", table_name="inaz_auto_sync_config")
    op.drop_index("ix_inaz_auto_sync_config_credential_id", table_name="inaz_auto_sync_config")
    op.drop_table("inaz_auto_sync_config")
