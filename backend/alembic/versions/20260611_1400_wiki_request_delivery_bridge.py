"""wiki request delivery bridge

Revision ID: 20260611_1400
Revises: 20260611_0130
Create Date: 2026-06-11 14:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260611_1400"
down_revision: str | Sequence[str] | None = "20260611_0130"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("wiki_requests", sa.Column("external_ticket_key", sa.String(length=128), nullable=True))
    op.add_column("wiki_requests", sa.Column("external_ticket_url", sa.String(length=1024), nullable=True))
    op.add_column("wiki_requests", sa.Column("delivery_status", sa.String(length=32), nullable=True))
    op.add_column("wiki_requests", sa.Column("delivery_notes", sa.Text(), nullable=True))
    op.create_index(op.f("ix_wiki_requests_external_ticket_key"), "wiki_requests", ["external_ticket_key"], unique=False)
    op.create_index(op.f("ix_wiki_requests_delivery_status"), "wiki_requests", ["delivery_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_wiki_requests_delivery_status"), table_name="wiki_requests")
    op.drop_index(op.f("ix_wiki_requests_external_ticket_key"), table_name="wiki_requests")
    op.drop_column("wiki_requests", "delivery_notes")
    op.drop_column("wiki_requests", "delivery_status")
    op.drop_column("wiki_requests", "external_ticket_url")
    op.drop_column("wiki_requests", "external_ticket_key")
