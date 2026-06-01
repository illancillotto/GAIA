"""add wiki conversation daily metrics

Revision ID: 20260529_0095
Revises: 20260529_0094
Create Date: 2026-05-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0095"
down_revision: Union[str, None] = "20260529_0094"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wiki_conversation_daily_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("dimension_type", sa.String(length=32), nullable=False),
        sa.Column("dimension_key", sa.String(length=256), nullable=True),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("closed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("open_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("in_review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("waiting_user_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resolved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("high_priority_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("needs_review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("denied_threads_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fallback_threads_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("no_match_threads_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_time_to_review_hours", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_time_to_resolve_hours", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metric_date", "dimension_type", "dimension_key", name="uq_wiki_conversation_daily_dimension"),
    )
    op.create_index("ix_wiki_conversation_daily_metrics_metric_date", "wiki_conversation_daily_metrics", ["metric_date"])
    op.create_index("ix_wiki_conversation_daily_metrics_dimension_type", "wiki_conversation_daily_metrics", ["dimension_type"])
    op.create_index("ix_wiki_conversation_daily_metrics_dimension_key", "wiki_conversation_daily_metrics", ["dimension_key"])


def downgrade() -> None:
    op.drop_index("ix_wiki_conversation_daily_metrics_dimension_key", table_name="wiki_conversation_daily_metrics")
    op.drop_index("ix_wiki_conversation_daily_metrics_dimension_type", table_name="wiki_conversation_daily_metrics")
    op.drop_index("ix_wiki_conversation_daily_metrics_metric_date", table_name="wiki_conversation_daily_metrics")
    op.drop_table("wiki_conversation_daily_metrics")
