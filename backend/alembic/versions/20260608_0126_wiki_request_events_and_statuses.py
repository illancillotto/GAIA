"""wiki request events and richer workflow statuses

Revision ID: 20260608_0126
Revises: 20260608_0125
Create Date: 2026-06-08 08:55:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260608_0126"
down_revision = "20260608_0125"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "wiki_request_events"):
        op.create_table(
            "wiki_request_events",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("request_id", sa.UUID(), nullable=False),
            sa.Column("event_type", sa.String(length=32), nullable=False),
            sa.Column("actor_username", sa.String(length=256), nullable=True),
            sa.Column("from_status", sa.String(length=32), nullable=True),
            sa.Column("to_status", sa.String(length=32), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["request_id"], ["wiki_requests.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    for index_name, columns in (
        ("ix_wiki_request_events_request_id", ["request_id"]),
        ("ix_wiki_request_events_event_type", ["event_type"]),
        ("ix_wiki_request_events_actor_username", ["actor_username"]),
        ("ix_wiki_request_events_created_at", ["created_at"]),
    ):
        if not _index_exists(inspector, "wiki_request_events", index_name):
            op.create_index(index_name, "wiki_request_events", columns, unique=False)

    op.execute("UPDATE wiki_requests SET status = 'new' WHERE status = 'pending'")
    op.execute("UPDATE wiki_requests SET status = 'triaged' WHERE status = 'reviewed'")
    op.execute("UPDATE wiki_requests SET status = 'resolved' WHERE status = 'done'")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    op.execute("UPDATE wiki_requests SET status = 'pending' WHERE status = 'new'")
    op.execute("UPDATE wiki_requests SET status = 'reviewed' WHERE status = 'triaged'")
    op.execute("UPDATE wiki_requests SET status = 'done' WHERE status = 'resolved'")

    if _table_exists(inspector, "wiki_request_events"):
        op.drop_table("wiki_request_events")
