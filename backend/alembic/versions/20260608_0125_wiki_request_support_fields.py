"""Extend wiki requests with support workflow fields.

Revision ID: 20260608_0125
Revises: 20260606_0124
Create Date: 2026-06-08 10:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260608_0125"
down_revision = "20260606_0124"
branch_labels = None
depends_on = None


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(bind, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()

    columns = [
        ("request_type", sa.String(length=32), False, "feature_request"),
        ("severity", sa.String(length=16), False, "medium"),
        ("module_key", sa.String(length=64), True, None),
        ("page_path", sa.String(length=512), True, None),
        ("source_channel", sa.String(length=32), False, "widget"),
        ("impact_scope", sa.String(length=32), True, None),
        ("conversation_id", sa.UUID(), True, None),
        ("context_article", sa.String(length=512), True, None),
        ("context_entity_key", sa.String(length=512), True, None),
        ("desired_outcome", sa.Text(), True, None),
        ("observed_behavior", sa.Text(), True, None),
        ("expected_behavior", sa.Text(), True, None),
    ]

    for column_name, column_type, nullable, server_default in columns:
        if not _column_exists(bind, "wiki_requests", column_name):
            op.add_column(
                "wiki_requests",
                sa.Column(
                    column_name,
                    column_type,
                    nullable=nullable,
                    server_default=sa.text(f"'{server_default}'") if server_default is not None else None,
                ),
            )

    if not _index_exists(bind, "wiki_requests", "ix_wiki_requests_request_type"):
        op.create_index("ix_wiki_requests_request_type", "wiki_requests", ["request_type"])
    if not _index_exists(bind, "wiki_requests", "ix_wiki_requests_severity"):
        op.create_index("ix_wiki_requests_severity", "wiki_requests", ["severity"])
    if not _index_exists(bind, "wiki_requests", "ix_wiki_requests_module_key"):
        op.create_index("ix_wiki_requests_module_key", "wiki_requests", ["module_key"])
    if not _index_exists(bind, "wiki_requests", "ix_wiki_requests_source_channel"):
        op.create_index("ix_wiki_requests_source_channel", "wiki_requests", ["source_channel"])
    if not _index_exists(bind, "wiki_requests", "ix_wiki_requests_conversation_id"):
        op.create_index("ix_wiki_requests_conversation_id", "wiki_requests", ["conversation_id"])
    if not _index_exists(bind, "wiki_requests", "ix_wiki_requests_context_entity_key"):
        op.create_index("ix_wiki_requests_context_entity_key", "wiki_requests", ["context_entity_key"])

    op.execute("UPDATE wiki_requests SET request_type = 'bug_report' WHERE request_type IS NULL AND category = 'bug_report'")
    op.execute("UPDATE wiki_requests SET request_type = 'help_request' WHERE request_type IS NULL AND category IN ('question', 'support_request')")
    op.execute("UPDATE wiki_requests SET request_type = 'feature_request' WHERE request_type IS NULL")
    op.execute("UPDATE wiki_requests SET severity = 'medium' WHERE severity IS NULL")
    op.execute("UPDATE wiki_requests SET source_channel = 'widget' WHERE source_channel IS NULL")

    for column_name in ("request_type", "severity", "source_channel"):
        op.alter_column("wiki_requests", column_name, server_default=None)


def downgrade() -> None:
    bind = op.get_bind()

    for index_name in (
        "ix_wiki_requests_context_entity_key",
        "ix_wiki_requests_conversation_id",
        "ix_wiki_requests_source_channel",
        "ix_wiki_requests_module_key",
        "ix_wiki_requests_severity",
        "ix_wiki_requests_request_type",
    ):
        if _index_exists(bind, "wiki_requests", index_name):
            op.drop_index(index_name, table_name="wiki_requests")

    for column_name in (
        "expected_behavior",
        "observed_behavior",
        "desired_outcome",
        "context_entity_key",
        "context_article",
        "conversation_id",
        "impact_scope",
        "source_channel",
        "page_path",
        "module_key",
        "severity",
        "request_type",
    ):
        if _column_exists(bind, "wiki_requests", column_name):
            op.drop_column("wiki_requests", column_name)
