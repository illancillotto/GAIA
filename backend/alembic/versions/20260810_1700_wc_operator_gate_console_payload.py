"""persist gate mobile console pages and domains on wc_operator

Revision ID: 20260810_1700
Revises: 20260810_1030, 20260810_1400
Create Date: 2026-08-10 17:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260810_1700"
down_revision = ("20260810_1030", "20260810_1400")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("wc_operator", sa.Column("gate_mobile_console_pages", sa.JSON(), nullable=True))
    op.add_column("wc_operator", sa.Column("domains", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("wc_operator", "domains")
    op.drop_column("wc_operator", "gate_mobile_console_pages")
