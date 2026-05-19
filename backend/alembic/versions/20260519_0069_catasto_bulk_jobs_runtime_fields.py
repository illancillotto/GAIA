"""add runtime fields to catasto bulk jobs

Revision ID: 20260519_0069
Revises: 20260429_0068
Create Date: 2026-05-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260519_0069"
down_revision = "20260429_0068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catasto_elaborazioni_massive_jobs",
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
    )
    op.add_column(
        "catasto_elaborazioni_massive_jobs",
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "catasto_elaborazioni_massive_jobs",
        sa.Column("processed_rows", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "catasto_elaborazioni_massive_jobs",
        sa.Column("current_label", sa.Text(), nullable=True),
    )
    op.add_column(
        "catasto_elaborazioni_massive_jobs",
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "catasto_elaborazioni_massive_jobs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "catasto_elaborazioni_massive_jobs",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_catasto_elaborazioni_massive_jobs_status",
        "catasto_elaborazioni_massive_jobs",
        ["status"],
    )

    op.execute(
        sa.text(
            """
            UPDATE catasto_elaborazioni_massive_jobs
            SET
              status = 'completed',
              total_rows = COALESCE(jsonb_array_length(CAST(payload_json->'rows' AS jsonb)), 0),
              processed_rows = COALESCE(jsonb_array_length(CAST(results_json->'results' AS jsonb)), 0),
              completed_at = created_at
            """
        )
    )

    op.alter_column("catasto_elaborazioni_massive_jobs", "status", server_default=None)
    op.alter_column("catasto_elaborazioni_massive_jobs", "total_rows", server_default=None)
    op.alter_column("catasto_elaborazioni_massive_jobs", "processed_rows", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_catasto_elaborazioni_massive_jobs_status", table_name="catasto_elaborazioni_massive_jobs")
    op.drop_column("catasto_elaborazioni_massive_jobs", "completed_at")
    op.drop_column("catasto_elaborazioni_massive_jobs", "started_at")
    op.drop_column("catasto_elaborazioni_massive_jobs", "error_message")
    op.drop_column("catasto_elaborazioni_massive_jobs", "current_label")
    op.drop_column("catasto_elaborazioni_massive_jobs", "processed_rows")
    op.drop_column("catasto_elaborazioni_massive_jobs", "total_rows")
    op.drop_column("catasto_elaborazioni_massive_jobs", "status")
