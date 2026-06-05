"""add wiki conversation governance fields

Revision ID: 20260529_0094
Revises: 20260529_0093
Create Date: 2026-05-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0094"
down_revision: Union[str, None] = "20260529_0093"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("wiki_conversations"):
        op.create_table(
            "wiki_conversations",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("created_by", sa.String(length=256), nullable=False),
            sa.Column("context_article", sa.String(length=512), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
            sa.Column("priority", sa.String(length=16), nullable=False, server_default="medium"),
            sa.Column("assigned_to", sa.String(length=256), nullable=True),
            sa.Column("review_reason", sa.String(length=64), nullable=True),
            sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_by", sa.String(length=256), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_wiki_conversations_created_by", "wiki_conversations", ["created_by"])
        op.create_index("ix_wiki_conversations_status", "wiki_conversations", ["status"])
        op.create_index("ix_wiki_conversations_priority", "wiki_conversations", ["priority"])
        op.create_index("ix_wiki_conversations_assigned_to", "wiki_conversations", ["assigned_to"])
        op.create_index("ix_wiki_conversations_review_reason", "wiki_conversations", ["review_reason"])
        op.create_index("ix_wiki_conversations_last_reviewed_at", "wiki_conversations", ["last_reviewed_at"])
        op.create_index("ix_wiki_conversations_created_at", "wiki_conversations", ["created_at"])
        op.create_index("ix_wiki_conversations_updated_at", "wiki_conversations", ["updated_at"])
    else:
        column_names = {column["name"] for column in inspector.get_columns("wiki_conversations")}
        if "priority" not in column_names:
            op.add_column("wiki_conversations", sa.Column("priority", sa.String(length=16), nullable=False, server_default="medium"))
        if "assigned_to" not in column_names:
            op.add_column("wiki_conversations", sa.Column("assigned_to", sa.String(length=256), nullable=True))
        if "review_reason" not in column_names:
            op.add_column("wiki_conversations", sa.Column("review_reason", sa.String(length=64), nullable=True))
        if "last_reviewed_at" not in column_names:
            op.add_column("wiki_conversations", sa.Column("last_reviewed_at", sa.DateTime(), nullable=True))

        index_names = {index["name"] for index in inspector.get_indexes("wiki_conversations")}
        if "ix_wiki_conversations_priority" not in index_names:
            op.create_index("ix_wiki_conversations_priority", "wiki_conversations", ["priority"])
        if "ix_wiki_conversations_assigned_to" not in index_names:
            op.create_index("ix_wiki_conversations_assigned_to", "wiki_conversations", ["assigned_to"])
        if "ix_wiki_conversations_review_reason" not in index_names:
            op.create_index("ix_wiki_conversations_review_reason", "wiki_conversations", ["review_reason"])
        if "ix_wiki_conversations_last_reviewed_at" not in index_names:
            op.create_index("ix_wiki_conversations_last_reviewed_at", "wiki_conversations", ["last_reviewed_at"])

    if not inspector.has_table("wiki_conversation_messages"):
        op.create_table(
            "wiki_conversation_messages",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("conversation_id", sa.Uuid(), nullable=False),
            sa.Column("role", sa.String(length=16), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("found", sa.Integer(), nullable=True),
            sa.Column("mode", sa.String(length=32), nullable=True),
            sa.Column("sources_json", sa.Text(), nullable=True),
            sa.Column("evidences_json", sa.Text(), nullable=True),
            sa.Column("tool_calls_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["conversation_id"], ["wiki_conversations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_wiki_conversation_messages_conversation_id", "wiki_conversation_messages", ["conversation_id"])
        op.create_index("ix_wiki_conversation_messages_created_at", "wiki_conversation_messages", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("wiki_conversation_messages"):
        index_names = {index["name"] for index in inspector.get_indexes("wiki_conversation_messages")}
        if "ix_wiki_conversation_messages_created_at" in index_names:
            op.drop_index("ix_wiki_conversation_messages_created_at", table_name="wiki_conversation_messages")
        if "ix_wiki_conversation_messages_conversation_id" in index_names:
            op.drop_index("ix_wiki_conversation_messages_conversation_id", table_name="wiki_conversation_messages")
        op.drop_table("wiki_conversation_messages")

    if inspector.has_table("wiki_conversations"):
        index_names = {index["name"] for index in inspector.get_indexes("wiki_conversations")}
        if "ix_wiki_conversations_last_reviewed_at" in index_names:
            op.drop_index("ix_wiki_conversations_last_reviewed_at", table_name="wiki_conversations")
        if "ix_wiki_conversations_review_reason" in index_names:
            op.drop_index("ix_wiki_conversations_review_reason", table_name="wiki_conversations")
        if "ix_wiki_conversations_assigned_to" in index_names:
            op.drop_index("ix_wiki_conversations_assigned_to", table_name="wiki_conversations")
        if "ix_wiki_conversations_priority" in index_names:
            op.drop_index("ix_wiki_conversations_priority", table_name="wiki_conversations")

        column_names = {column["name"] for column in inspector.get_columns("wiki_conversations")}
        if "last_reviewed_at" in column_names:
            op.drop_column("wiki_conversations", "last_reviewed_at")
        if "review_reason" in column_names:
            op.drop_column("wiki_conversations", "review_reason")
        if "assigned_to" in column_names:
            op.drop_column("wiki_conversations", "assigned_to")
        if "priority" in column_names:
            op.drop_column("wiki_conversations", "priority")
