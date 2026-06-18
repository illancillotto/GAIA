"""add elaborazione auto job config table

Revision ID: 20260618_1100
Revises: 20260617_1000
Create Date: 2026-06-18 11:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260618_1100"
down_revision = "20260617_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "elaborazione_auto_job_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_key", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_elaborazione_auto_job_configs_job_key",
        "elaborazione_auto_job_configs",
        ["job_key"],
        unique=True,
    )
    op.alter_column("elaborazione_auto_job_configs", "enabled", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_elaborazione_auto_job_configs_job_key", table_name="elaborazione_auto_job_configs")
    op.drop_table("elaborazione_auto_job_configs")
