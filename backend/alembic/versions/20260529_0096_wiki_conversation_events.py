"""add wiki conversation events

Revision ID: 20260529_0096
Revises: 20260529_0095
Create Date: 2026-05-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0096"
down_revision: Union[str, None] = "20260529_0095"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wiki_conversation_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("actor_username", sa.String(length=256), nullable=True),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["conversation_id"], ["wiki_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wiki_conversation_events_conversation_id", "wiki_conversation_events", ["conversation_id"])
    op.create_index("ix_wiki_conversation_events_event_type", "wiki_conversation_events", ["event_type"])
    op.create_index("ix_wiki_conversation_events_actor_username", "wiki_conversation_events", ["actor_username"])
    op.create_index("ix_wiki_conversation_events_created_at", "wiki_conversation_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_wiki_conversation_events_created_at", table_name="wiki_conversation_events")
    op.drop_index("ix_wiki_conversation_events_actor_username", table_name="wiki_conversation_events")
    op.drop_index("ix_wiki_conversation_events_event_type", table_name="wiki_conversation_events")
    op.drop_index("ix_wiki_conversation_events_conversation_id", table_name="wiki_conversation_events")
    op.drop_table("wiki_conversation_events")
