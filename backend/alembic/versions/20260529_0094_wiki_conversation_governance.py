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
    op.add_column("wiki_conversations", sa.Column("priority", sa.String(length=16), nullable=False, server_default="medium"))
    op.add_column("wiki_conversations", sa.Column("assigned_to", sa.String(length=256), nullable=True))
    op.add_column("wiki_conversations", sa.Column("review_reason", sa.String(length=64), nullable=True))
    op.add_column("wiki_conversations", sa.Column("last_reviewed_at", sa.DateTime(), nullable=True))
    op.create_index("ix_wiki_conversations_priority", "wiki_conversations", ["priority"])
    op.create_index("ix_wiki_conversations_assigned_to", "wiki_conversations", ["assigned_to"])
    op.create_index("ix_wiki_conversations_review_reason", "wiki_conversations", ["review_reason"])
    op.create_index("ix_wiki_conversations_last_reviewed_at", "wiki_conversations", ["last_reviewed_at"])


def downgrade() -> None:
    op.drop_index("ix_wiki_conversations_last_reviewed_at", table_name="wiki_conversations")
    op.drop_index("ix_wiki_conversations_review_reason", table_name="wiki_conversations")
    op.drop_index("ix_wiki_conversations_assigned_to", table_name="wiki_conversations")
    op.drop_index("ix_wiki_conversations_priority", table_name="wiki_conversations")
    op.drop_column("wiki_conversations", "last_reviewed_at")
    op.drop_column("wiki_conversations", "review_reason")
    op.drop_column("wiki_conversations", "assigned_to")
    op.drop_column("wiki_conversations", "priority")
