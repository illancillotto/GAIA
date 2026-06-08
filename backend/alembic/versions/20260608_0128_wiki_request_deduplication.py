"""wiki request deduplication fields

Revision ID: 20260608_0128
Revises: 20260608_0126
Create Date: 2026-06-08 19:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260608_0128"
down_revision = "20260608_0126"
branch_labels = None
depends_on = None


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _fk_exists(inspector: sa.Inspector, table_name: str, fk_name: str) -> bool:
    return any(fk.get("name") == fk_name for fk in inspector.get_foreign_keys(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _column_exists(inspector, "wiki_requests", "dedupe_key"):
        op.add_column("wiki_requests", sa.Column("dedupe_key", sa.String(length=128), nullable=True))
    if not _column_exists(inspector, "wiki_requests", "canonical_request_id"):
        op.add_column("wiki_requests", sa.Column("canonical_request_id", sa.UUID(), nullable=True))
        inspector = sa.inspect(bind)

    if not _fk_exists(inspector, "wiki_requests", "fk_wiki_requests_canonical_request_id"):
        op.create_foreign_key(
            "fk_wiki_requests_canonical_request_id",
            "wiki_requests",
            "wiki_requests",
            ["canonical_request_id"],
            ["id"],
            ondelete="SET NULL",
        )

    for index_name, columns in (
        ("ix_wiki_requests_dedupe_key", ["dedupe_key"]),
        ("ix_wiki_requests_canonical_request_id", ["canonical_request_id"]),
    ):
        if not _index_exists(inspector, "wiki_requests", index_name):
            op.create_index(index_name, "wiki_requests", columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _index_exists(inspector, "wiki_requests", "ix_wiki_requests_canonical_request_id"):
        op.drop_index("ix_wiki_requests_canonical_request_id", table_name="wiki_requests")
    if _index_exists(inspector, "wiki_requests", "ix_wiki_requests_dedupe_key"):
        op.drop_index("ix_wiki_requests_dedupe_key", table_name="wiki_requests")
    if _fk_exists(inspector, "wiki_requests", "fk_wiki_requests_canonical_request_id"):
        op.drop_constraint("fk_wiki_requests_canonical_request_id", "wiki_requests", type_="foreignkey")
    if _column_exists(inspector, "wiki_requests", "canonical_request_id"):
        op.drop_column("wiki_requests", "canonical_request_id")
    if _column_exists(inspector, "wiki_requests", "dedupe_key"):
        op.drop_column("wiki_requests", "dedupe_key")
