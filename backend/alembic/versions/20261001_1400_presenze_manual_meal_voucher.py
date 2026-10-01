"""Audited manual meal voucher per collaborator/day, preserving automatic grants.

Revision ID: 20261001_1400
Revises: 20260923_1300
"""

import sqlalchemy as sa

from alembic import op

revision = "20261001_1400"
down_revision = "20260923_1300"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "presenze_daily_records",
        sa.Column("meal_voucher_manual", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "presenze_daily_records", sa.Column("meal_voucher_audit", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("presenze_daily_records", "meal_voucher_audit")
    op.drop_column("presenze_daily_records", "meal_voucher_manual")
