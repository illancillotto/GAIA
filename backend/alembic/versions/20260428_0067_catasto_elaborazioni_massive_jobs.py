"""catasto elaborazioni massive jobs

Revision ID: 20260428_0067
Revises: 20260427_0066
Create Date: 2026-04-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260428_0067"
down_revision = "20260427_0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catasto_elaborazioni_massive_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("application_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("skipped_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("results_json", sa.JSON(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_catasto_elaborazioni_massive_jobs_user_id", "catasto_elaborazioni_massive_jobs", ["user_id"])
    op.create_index("ix_catasto_elaborazioni_massive_jobs_kind", "catasto_elaborazioni_massive_jobs", ["kind"])
    op.create_index("ix_catasto_elaborazioni_massive_jobs_created_at", "catasto_elaborazioni_massive_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_catasto_elaborazioni_massive_jobs_created_at", table_name="catasto_elaborazioni_massive_jobs")
    op.drop_index("ix_catasto_elaborazioni_massive_jobs_kind", table_name="catasto_elaborazioni_massive_jobs")
    op.drop_index("ix_catasto_elaborazioni_massive_jobs_user_id", table_name="catasto_elaborazioni_massive_jobs")
    op.drop_table("catasto_elaborazioni_massive_jobs")

