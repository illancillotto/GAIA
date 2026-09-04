"""Add the Capacitas irrigation applications autosync checkpoint.

Revision ID: 20260905_0900
Revises: 20260904_1000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260905_0900"
down_revision = "20260904_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capacitas_domande_irrigue_autosync_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cursor", sa.String(length=32), nullable=True),
        sa.Column("pending_cursor", sa.String(length=32), nullable=True),
        sa.Column("pending_job_id", sa.Integer(), nullable=True),
        sa.Column("cycle_key", sa.String(length=32), nullable=True),
        sa.Column("completed_cycle_key", sa.String(length=32), nullable=True),
        sa.Column("processed_identifiers", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cycle_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cycle_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["pending_job_id"],
            ["capacitas_domande_irrigue_sync_jobs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("DELETE FROM cat_domande_irrigue WHERE anno < 1900 OR anno > 2100")


def downgrade() -> None:
    op.drop_table("capacitas_domande_irrigue_autosync_state")
