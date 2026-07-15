"""add GIS module flag to application users

Revision ID: 20260714_1100
Revises: 20260713_0900
Create Date: 2026-07-14 11:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260714_1100"
down_revision: str | Sequence[str] | None = "20260713_0900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "application_users",
        sa.Column("module_gis", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE application_users SET module_gis = TRUE WHERE module_catasto = TRUE")
    op.alter_column("application_users", "module_gis", server_default=None)


def downgrade() -> None:
    op.drop_column("application_users", "module_gis")
