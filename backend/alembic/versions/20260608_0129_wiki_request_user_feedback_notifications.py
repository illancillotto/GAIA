"""wiki request user feedback and notification fields

Revision ID: 20260608_0129
Revises: 20260608_0128
Create Date: 2026-06-08 19:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260608_0129"
down_revision = "20260608_0128"
branch_labels = None
depends_on = None


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = (
        ("resolution_message", sa.Text(), None),
        ("last_admin_update_at", sa.DateTime(), None),
        ("user_last_viewed_at", sa.DateTime(), None),
        ("user_feedback_rating", sa.String(length=16), None),
        ("user_feedback_notes", sa.Text(), None),
        ("user_feedback_submitted_at", sa.DateTime(), None),
    )

    for column_name, column_type, server_default in columns:
        if not _column_exists(inspector, "wiki_requests", column_name):
            op.add_column("wiki_requests", sa.Column(column_name, column_type, nullable=True, server_default=server_default))

    inspector = sa.inspect(bind)
    for index_name, columns in (
        ("ix_wiki_requests_last_admin_update_at", ["last_admin_update_at"]),
        ("ix_wiki_requests_user_last_viewed_at", ["user_last_viewed_at"]),
        ("ix_wiki_requests_user_feedback_rating", ["user_feedback_rating"]),
        ("ix_wiki_requests_user_feedback_submitted_at", ["user_feedback_submitted_at"]),
    ):
        if not _index_exists(inspector, "wiki_requests", index_name):
            op.create_index(index_name, "wiki_requests", columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for index_name in (
        "ix_wiki_requests_user_feedback_submitted_at",
        "ix_wiki_requests_user_feedback_rating",
        "ix_wiki_requests_user_last_viewed_at",
        "ix_wiki_requests_last_admin_update_at",
    ):
        if _index_exists(inspector, "wiki_requests", index_name):
            op.drop_index(index_name, table_name="wiki_requests")

    for column_name in (
        "user_feedback_submitted_at",
        "user_feedback_notes",
        "user_feedback_rating",
        "user_last_viewed_at",
        "last_admin_update_at",
        "resolution_message",
    ):
        if _column_exists(inspector, "wiki_requests", column_name):
            op.drop_column("wiki_requests", column_name)
