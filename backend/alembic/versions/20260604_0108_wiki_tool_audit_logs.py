"""add wiki tool audit logs table

Revision ID: 20260604_0108
Revises: 20260604_0107
Create Date: 2026-06-04 08:45:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260604_0108"
down_revision: str | Sequence[str] | None = "20260604_0107"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True) if op.get_bind().dialect.name == "postgresql" else sa.String(length=36)

    op.create_table(
        "wiki_tool_audit_logs",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("username", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("intent", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("module_key", sa.String(length=64), nullable=True),
        sa.Column("conversation_id", uuid_type, nullable=True),
        sa.Column("question_hash", sa.String(length=64), nullable=False),
        sa.Column("question_preview", sa.String(length=200), nullable=False),
        sa.Column("context_article", sa.String(length=512), nullable=True),
        sa.Column("entity_key", sa.String(length=512), nullable=True),
        sa.Column("entity_label", sa.String(length=256), nullable=True),
        sa.Column("response_excerpt", sa.String(length=300), nullable=True),
        sa.Column("fallback_reason", sa.String(length=64), nullable=True),
        sa.Column("success", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("found", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("docs_source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wiki_tool_audit_logs_conversation_id", "wiki_tool_audit_logs", ["conversation_id"], unique=False)
    op.create_index("ix_wiki_tool_audit_logs_created_at", "wiki_tool_audit_logs", ["created_at"], unique=False)
    op.create_index("ix_wiki_tool_audit_logs_entity_key", "wiki_tool_audit_logs", ["entity_key"], unique=False)
    op.create_index("ix_wiki_tool_audit_logs_fallback_reason", "wiki_tool_audit_logs", ["fallback_reason"], unique=False)
    op.create_index("ix_wiki_tool_audit_logs_id", "wiki_tool_audit_logs", ["id"], unique=False)
    op.create_index("ix_wiki_tool_audit_logs_intent", "wiki_tool_audit_logs", ["intent"], unique=False)
    op.create_index("ix_wiki_tool_audit_logs_mode", "wiki_tool_audit_logs", ["mode"], unique=False)
    op.create_index("ix_wiki_tool_audit_logs_module_key", "wiki_tool_audit_logs", ["module_key"], unique=False)
    op.create_index("ix_wiki_tool_audit_logs_question_hash", "wiki_tool_audit_logs", ["question_hash"], unique=False)
    op.create_index("ix_wiki_tool_audit_logs_tool_name", "wiki_tool_audit_logs", ["tool_name"], unique=False)
    op.create_index("ix_wiki_tool_audit_logs_username", "wiki_tool_audit_logs", ["username"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_wiki_tool_audit_logs_username", table_name="wiki_tool_audit_logs")
    op.drop_index("ix_wiki_tool_audit_logs_tool_name", table_name="wiki_tool_audit_logs")
    op.drop_index("ix_wiki_tool_audit_logs_question_hash", table_name="wiki_tool_audit_logs")
    op.drop_index("ix_wiki_tool_audit_logs_module_key", table_name="wiki_tool_audit_logs")
    op.drop_index("ix_wiki_tool_audit_logs_mode", table_name="wiki_tool_audit_logs")
    op.drop_index("ix_wiki_tool_audit_logs_intent", table_name="wiki_tool_audit_logs")
    op.drop_index("ix_wiki_tool_audit_logs_id", table_name="wiki_tool_audit_logs")
    op.drop_index("ix_wiki_tool_audit_logs_fallback_reason", table_name="wiki_tool_audit_logs")
    op.drop_index("ix_wiki_tool_audit_logs_entity_key", table_name="wiki_tool_audit_logs")
    op.drop_index("ix_wiki_tool_audit_logs_created_at", table_name="wiki_tool_audit_logs")
    op.drop_index("ix_wiki_tool_audit_logs_conversation_id", table_name="wiki_tool_audit_logs")
    op.drop_table("wiki_tool_audit_logs")
