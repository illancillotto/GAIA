"""add wc_operator_id to vehicle_fuel_log and backfill from wc_refuel_event

Revision ID: 20260422_0056
Revises: 20260421_0055
Create Date: 2026-04-22

"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision = "20260422_0056"
down_revision: Union[str, None] = "20260421_0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vehicle_fuel_log",
        sa.Column(
            "wc_operator_id",
            sa.Uuid(),
            sa.ForeignKey("wc_operator.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_vehicle_fuel_log_wc_operator_id",
        "vehicle_fuel_log",
        ["wc_operator_id"],
    )

    # Backfill: propagate wc_operator_id from already-matched wc_refuel_event rows.
    op.execute(
        """
        UPDATE vehicle_fuel_log fl
        SET wc_operator_id = wce.wc_operator_id
        FROM wc_refuel_event wce
        WHERE wce.matched_fuel_log_id = fl.id
          AND wce.wc_operator_id IS NOT NULL
          AND fl.wc_operator_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_vehicle_fuel_log_wc_operator_id", "vehicle_fuel_log")
    op.drop_column("vehicle_fuel_log", "wc_operator_id")
