"""add recent routes json to user presence

Revision ID: 20260629_1130
Revises: 20260629_1000
Create Date: 2026-06-29 11:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260629_1130"
down_revision = "20260629_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_presence",
        sa.Column("recent_routes_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.alter_column("user_presence", "recent_routes_json", server_default=None)


def downgrade() -> None:
    op.drop_column("user_presence", "recent_routes_json")
