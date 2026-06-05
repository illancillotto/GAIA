"""wiki conversation backfill jobs

Revision ID: 20260529_0103
Revises: 20260529_0102
Create Date: 2026-05-29 12:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260529_0103"
down_revision: str | Sequence[str] | None = "20260529_0102"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True) if op.get_bind().dialect.name == "postgresql" else sa.String(length=36)

    op.create_table(
        "wiki_conversation_metrics_backfill_jobs",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requested_by", sa.String(length=256), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("data_complete_from", sa.Date(), nullable=True),
        sa.Column("progress_total_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_completed_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_message", sa.String(length=300), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wiki_conversation_metrics_backfill_jobs_status",
        "wiki_conversation_metrics_backfill_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_wiki_conversation_metrics_backfill_jobs_requested_by",
        "wiki_conversation_metrics_backfill_jobs",
        ["requested_by"],
        unique=False,
    )
    op.create_index(
        "ix_wiki_conversation_metrics_backfill_jobs_start_date",
        "wiki_conversation_metrics_backfill_jobs",
        ["start_date"],
        unique=False,
    )
    op.create_index(
        "ix_wiki_conversation_metrics_backfill_jobs_end_date",
        "wiki_conversation_metrics_backfill_jobs",
        ["end_date"],
        unique=False,
    )
    op.create_index(
        "ix_wiki_conversation_metrics_backfill_jobs_created_at",
        "wiki_conversation_metrics_backfill_jobs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_wiki_conversation_metrics_backfill_jobs_created_at", table_name="wiki_conversation_metrics_backfill_jobs")
    op.drop_index("ix_wiki_conversation_metrics_backfill_jobs_end_date", table_name="wiki_conversation_metrics_backfill_jobs")
    op.drop_index("ix_wiki_conversation_metrics_backfill_jobs_start_date", table_name="wiki_conversation_metrics_backfill_jobs")
    op.drop_index("ix_wiki_conversation_metrics_backfill_jobs_requested_by", table_name="wiki_conversation_metrics_backfill_jobs")
    op.drop_index("ix_wiki_conversation_metrics_backfill_jobs_status", table_name="wiki_conversation_metrics_backfill_jobs")
    op.drop_table("wiki_conversation_metrics_backfill_jobs")
