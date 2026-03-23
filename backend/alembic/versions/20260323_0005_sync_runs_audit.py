"""sync runs audit

Revision ID: 20260323_0005
Revises: 20260320_0004
Create Date: 2026-03-23 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260323_0005"
down_revision = "20260320_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("snapshots.id"), nullable=True),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts_used", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sync_runs_id", "sync_runs", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sync_runs_id", table_name="sync_runs")
    op.drop_table("sync_runs")
