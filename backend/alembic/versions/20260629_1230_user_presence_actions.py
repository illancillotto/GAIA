"""add action tracking to user presence

Revision ID: 20260629_1230
Revises: 20260629_1130
Create Date: 2026-06-29 12:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260629_1230"
down_revision = "20260629_1130"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_presence",
        sa.Column("last_action_label", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "user_presence",
        sa.Column("recent_actions_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.alter_column("user_presence", "recent_actions_json", server_default=None)


def downgrade() -> None:
    op.drop_column("user_presence", "recent_actions_json")
    op.drop_column("user_presence", "last_action_label")
