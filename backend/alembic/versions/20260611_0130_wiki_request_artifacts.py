"""wiki request artifacts

Revision ID: 20260611_0130
Revises: 20260608_0129
Create Date: 2026-06-11 10:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260611_0130"
down_revision = "20260608_0129"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "wiki_request_artifacts"):
        op.create_table(
            "wiki_request_artifacts",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("artifact_type", sa.String(length=32), nullable=False),
            sa.Column("filename", sa.String(length=255), nullable=True),
            sa.Column("mime_type", sa.String(length=128), nullable=True),
            sa.Column("storage_path", sa.String(length=1024), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(length=256), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["request_id"], ["wiki_requests.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    for index_name, columns in (
        ("ix_wiki_request_artifacts_request_id", ["request_id"]),
        ("ix_wiki_request_artifacts_artifact_type", ["artifact_type"]),
        ("ix_wiki_request_artifacts_created_at", ["created_at"]),
    ):
        if not _index_exists(inspector, "wiki_request_artifacts", index_name):
            op.create_index(index_name, "wiki_request_artifacts", columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "wiki_request_artifacts"):
        for index_name in (
            "ix_wiki_request_artifacts_created_at",
            "ix_wiki_request_artifacts_artifact_type",
            "ix_wiki_request_artifacts_request_id",
        ):
            if _index_exists(inspector, "wiki_request_artifacts", index_name):
                op.drop_index(index_name, table_name="wiki_request_artifacts")
        op.drop_table("wiki_request_artifacts")
