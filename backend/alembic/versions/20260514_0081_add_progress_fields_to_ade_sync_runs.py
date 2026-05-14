"""catasto: add progress fields to AdE sync runs

Revision ID: 20260514_0081
Revises: 20260514_0080
Create Date: 2026-05-14 16:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260514_0081"
down_revision = "20260514_0080"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cat_ade_sync_runs",
        sa.Column("progress_phase", sa.String(length=20), nullable=False, server_default="queued"),
    )
    op.add_column(
        "cat_ade_sync_runs",
        sa.Column("progress_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "cat_ade_sync_runs",
        sa.Column("tiles_completed", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("cat_ade_sync_runs", "tiles_completed")
    op.drop_column("cat_ade_sync_runs", "progress_message")
    op.drop_column("cat_ade_sync_runs", "progress_phase")
