"""ruolo tributi euribor interest rate

Revision ID: 20260730_1100
Revises: 20260730_0900
Create Date: 2026-07-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260730_1100"
down_revision = "20260730_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ruolo_tributi_calculation_policies",
        sa.Column("euribor_6m_rate_percent", sa.Numeric(7, 4), nullable=False, server_default="0"),
    )
    op.add_column("ruolo_tributi_calculation_policies", sa.Column("euribor_source_url", sa.Text(), nullable=True))
    op.add_column("ruolo_tributi_calculation_policies", sa.Column("euribor_reference_period", sa.String(length=32), nullable=True))
    op.add_column("ruolo_tributi_calculation_policies", sa.Column("euribor_fetched_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("ruolo_tributi_calculation_policies", "euribor_6m_rate_percent", server_default=None)


def downgrade() -> None:
    op.drop_column("ruolo_tributi_calculation_policies", "euribor_fetched_at")
    op.drop_column("ruolo_tributi_calculation_policies", "euribor_reference_period")
    op.drop_column("ruolo_tributi_calculation_policies", "euribor_source_url")
    op.drop_column("ruolo_tributi_calculation_policies", "euribor_6m_rate_percent")
