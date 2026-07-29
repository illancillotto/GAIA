"""ruolo tributi interest start mode

Revision ID: 20260728_1120
Revises: 20260728_1110
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260728_1120"
down_revision = "20260728_1110"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ruolo_tributi_calculation_policies",
        sa.Column("interest_start_mode", sa.String(length=32), nullable=False, server_default="fixed_date"),
    )
    op.create_index(
        "ix_ruolo_tributi_calculation_policies_interest_start_mode",
        "ruolo_tributi_calculation_policies",
        ["interest_start_mode"],
    )
    op.alter_column("ruolo_tributi_calculation_policies", "interest_start_mode", server_default=None)


def downgrade() -> None:
    op.drop_index(
        "ix_ruolo_tributi_calculation_policies_interest_start_mode",
        table_name="ruolo_tributi_calculation_policies",
    )
    op.drop_column("ruolo_tributi_calculation_policies", "interest_start_mode")
