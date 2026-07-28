"""ruolo tributi calculation policies

Revision ID: 20260728_0900
Revises: 20260727_0900
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260728_0900"
down_revision = "20260727_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ruolo_tributi_reminder_batch_items", sa.Column("surcharge_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("ruolo_tributi_reminder_batch_items", sa.Column("interest_amount", sa.Numeric(12, 2), nullable=True))

    op.create_table(
        "ruolo_tributi_calculation_policies",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("year_from", sa.Integer(), nullable=True),
        sa.Column("year_to", sa.Integer(), nullable=True),
        sa.Column("surcharge_rate_percent", sa.Numeric(7, 4), nullable=False),
        sa.Column("surcharge_from", sa.Date(), nullable=True),
        sa.Column("interest_rate_percent", sa.Numeric(7, 4), nullable=False),
        sa.Column("interest_from", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["updated_by"], ["application_users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ruolo_tributi_calculation_policies_interest_from", "ruolo_tributi_calculation_policies", ["interest_from"])
    op.create_index("ix_ruolo_tributi_calculation_policies_is_active", "ruolo_tributi_calculation_policies", ["is_active"])
    op.create_index("ix_ruolo_tributi_calculation_policies_surcharge_from", "ruolo_tributi_calculation_policies", ["surcharge_from"])
    op.create_index("ix_ruolo_tributi_calculation_policies_updated_by", "ruolo_tributi_calculation_policies", ["updated_by"])
    op.create_index("ix_ruolo_tributi_calculation_policies_year_from", "ruolo_tributi_calculation_policies", ["year_from"])
    op.create_index("ix_ruolo_tributi_calculation_policies_year_to", "ruolo_tributi_calculation_policies", ["year_to"])


def downgrade() -> None:
    op.drop_index("ix_ruolo_tributi_calculation_policies_year_to", table_name="ruolo_tributi_calculation_policies")
    op.drop_index("ix_ruolo_tributi_calculation_policies_year_from", table_name="ruolo_tributi_calculation_policies")
    op.drop_index("ix_ruolo_tributi_calculation_policies_updated_by", table_name="ruolo_tributi_calculation_policies")
    op.drop_index("ix_ruolo_tributi_calculation_policies_surcharge_from", table_name="ruolo_tributi_calculation_policies")
    op.drop_index("ix_ruolo_tributi_calculation_policies_is_active", table_name="ruolo_tributi_calculation_policies")
    op.drop_index("ix_ruolo_tributi_calculation_policies_interest_from", table_name="ruolo_tributi_calculation_policies")
    op.drop_table("ruolo_tributi_calculation_policies")
    op.drop_column("ruolo_tributi_reminder_batch_items", "interest_amount")
    op.drop_column("ruolo_tributi_reminder_batch_items", "surcharge_amount")
