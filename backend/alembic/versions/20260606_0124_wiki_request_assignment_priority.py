"""add wiki request assignment and priority

Revision ID: 20260606_0124
Revises: 20260606_0122
Create Date: 2026-06-06 18:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260606_0124"
down_revision = "20260606_0122"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("wiki_requests")}
    indexes = {index["name"] for index in inspector.get_indexes("wiki_requests")}

    if "priority" not in columns:
        op.add_column("wiki_requests", sa.Column("priority", sa.String(length=16), nullable=False, server_default="medium"))
    if "assigned_to" not in columns:
        op.add_column("wiki_requests", sa.Column("assigned_to", sa.String(length=256), nullable=True))
    if "ix_wiki_requests_priority" not in indexes:
        op.create_index("ix_wiki_requests_priority", "wiki_requests", ["priority"], unique=False)
    if "ix_wiki_requests_assigned_to" not in indexes:
        op.create_index("ix_wiki_requests_assigned_to", "wiki_requests", ["assigned_to"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_wiki_requests_assigned_to", table_name="wiki_requests")
    op.drop_index("ix_wiki_requests_priority", table_name="wiki_requests")
    op.drop_column("wiki_requests", "assigned_to")
    op.drop_column("wiki_requests", "priority")
