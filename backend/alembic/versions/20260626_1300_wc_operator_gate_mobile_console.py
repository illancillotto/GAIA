"""add gate mobile console flags to wc_operator

Revision ID: 20260626_1300
Revises: 20260626_1000
Create Date: 2026-06-26 13:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260626_1300"
down_revision = "20260626_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wc_operator",
        sa.Column("gate_mobile_console_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "wc_operator",
        sa.Column("gate_mobile_console_role", sa.String(length=50), nullable=True),
    )
    op.execute("UPDATE wc_operator SET gate_mobile_console_role = NULL WHERE gate_mobile_console_enabled = false")
    op.alter_column("wc_operator", "gate_mobile_console_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("wc_operator", "gate_mobile_console_role")
    op.drop_column("wc_operator", "gate_mobile_console_enabled")
