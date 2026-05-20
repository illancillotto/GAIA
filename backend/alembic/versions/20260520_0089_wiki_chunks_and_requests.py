"""add wiki_chunks and wiki_requests tables for wiki agent module

Revision ID: 20260520_0089
Revises: 20260519_0088
Create Date: 2026-05-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260520_0089"
down_revision: Union[str, None] = "20260519_0088"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wiki_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_file", sa.String(length=512), nullable=False),
        sa.Column("section_title", sa.String(length=512), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wiki_chunks_source_file", "wiki_chunks", ["source_file"])
    # GIN index per full-text search — necessario per prestazioni su plainto_tsquery
    op.create_index(
        "ix_wiki_chunks_search_vector",
        "wiki_chunks",
        ["search_vector"],
        postgresql_using="gin",
    )

    op.create_table(
        "wiki_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_question", sa.Text(), nullable=False),
        sa.Column("agent_response", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="feature_request"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_by", sa.String(length=256), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wiki_requests_status", "wiki_requests", ["status"])
    op.create_index("ix_wiki_requests_created_by", "wiki_requests", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_wiki_requests_created_by", table_name="wiki_requests")
    op.drop_index("ix_wiki_requests_status", table_name="wiki_requests")
    op.drop_table("wiki_requests")
    op.drop_index("ix_wiki_chunks_search_vector", table_name="wiki_chunks")
    op.drop_index("ix_wiki_chunks_source_file", table_name="wiki_chunks")
    op.drop_table("wiki_chunks")
