"""Add event-derived conversation metrics columns.

Revision ID: 20260529_0097
Revises: 20260529_0096
Create Date: 2026-05-29 09:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260529_0097"
down_revision = "20260529_0096"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("wiki_conversation_daily_metrics", sa.Column("review_entered_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("wiki_conversation_daily_metrics", sa.Column("reassigned_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("wiki_conversation_daily_metrics", sa.Column("reopened_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("wiki_conversation_daily_metrics", sa.Column("avg_open_to_review_hours", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("wiki_conversation_daily_metrics", sa.Column("avg_review_to_resolve_hours", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("wiki_conversation_daily_metrics", sa.Column("avg_waiting_user_hours", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("wiki_conversation_daily_metrics", "review_entered_count", server_default=None)
    op.alter_column("wiki_conversation_daily_metrics", "reassigned_count", server_default=None)
    op.alter_column("wiki_conversation_daily_metrics", "reopened_count", server_default=None)
    op.alter_column("wiki_conversation_daily_metrics", "avg_open_to_review_hours", server_default=None)
    op.alter_column("wiki_conversation_daily_metrics", "avg_review_to_resolve_hours", server_default=None)
    op.alter_column("wiki_conversation_daily_metrics", "avg_waiting_user_hours", server_default=None)


def downgrade() -> None:
    op.drop_column("wiki_conversation_daily_metrics", "avg_waiting_user_hours")
    op.drop_column("wiki_conversation_daily_metrics", "avg_review_to_resolve_hours")
    op.drop_column("wiki_conversation_daily_metrics", "avg_open_to_review_hours")
    op.drop_column("wiki_conversation_daily_metrics", "reopened_count")
    op.drop_column("wiki_conversation_daily_metrics", "reassigned_count")
    op.drop_column("wiki_conversation_daily_metrics", "review_entered_count")
