"""ruolo tributi bonario due date

Revision ID: 20260729_0900
Revises: 20260728_1120
Create Date: 2026-07-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260729_0900"
down_revision = "20260728_1120"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ruolo_tributi_calculation_policies", sa.Column("bonario_due_date", sa.Date(), nullable=True))
    op.create_index(
        "ix_ruolo_tributi_calculation_policies_bonario_due_date",
        "ruolo_tributi_calculation_policies",
        ["bonario_due_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_ruolo_tributi_calculation_policies_bonario_due_date", table_name="ruolo_tributi_calculation_policies")
    op.drop_column("ruolo_tributi_calculation_policies", "bonario_due_date")
