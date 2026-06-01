"""wiki backfill job retry lineage

Revision ID: 20260529_0101
Revises: 20260529_0100
Create Date: 2026-05-29 12:55:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260529_0101"
down_revision: str | Sequence[str] | None = "20260529_0100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True) if op.get_bind().dialect.name == "postgresql" else sa.String(length=36)
    op.add_column(
        "wiki_conversation_metrics_backfill_jobs",
        sa.Column("parent_job_id", uuid_type, nullable=True),
    )
    op.add_column(
        "wiki_conversation_metrics_backfill_jobs",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_wiki_conversation_metrics_backfill_jobs_parent_job_id",
        "wiki_conversation_metrics_backfill_jobs",
        ["parent_job_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_wiki_conversation_metrics_backfill_jobs_parent_job_id",
        "wiki_conversation_metrics_backfill_jobs",
        "wiki_conversation_metrics_backfill_jobs",
        ["parent_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("wiki_conversation_metrics_backfill_jobs", "retry_count", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "fk_wiki_conversation_metrics_backfill_jobs_parent_job_id",
        "wiki_conversation_metrics_backfill_jobs",
        type_="foreignkey",
    )
    op.drop_index("ix_wiki_conversation_metrics_backfill_jobs_parent_job_id", table_name="wiki_conversation_metrics_backfill_jobs")
    op.drop_column("wiki_conversation_metrics_backfill_jobs", "retry_count")
    op.drop_column("wiki_conversation_metrics_backfill_jobs", "parent_job_id")
