"""merge outstanding alembic heads

Revision ID: 20260608_0131
Revises: 20260606_0123, 20260608_0127, 20260608_0130
Create Date: 2026-06-08 23:15:00
"""

from __future__ import annotations


revision = "20260608_0131"
down_revision = ("20260606_0123", "20260608_0127", "20260608_0130")
branch_labels = None
depends_on = None


def upgrade() -> None:
    return None


def downgrade() -> None:
    return None
