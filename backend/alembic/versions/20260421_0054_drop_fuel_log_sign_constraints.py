"""drop fuel_log non-negative / positive constraints to allow storno entries

Revision ID: 20260421_0054
Revises: 20260421_0052, 20260421_0053
Create Date: 2026-04-21

"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision = "20260421_0054"
down_revision: Union[str, tuple[str, ...]] = ("20260421_0052", "20260421_0053")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_fuel_liters_positive", "vehicle_fuel_log", type_="check")
    op.drop_constraint("ck_fuel_cost_non_negative", "vehicle_fuel_log", type_="check")


def downgrade() -> None:
    op.create_check_constraint("ck_fuel_liters_positive", "vehicle_fuel_log", "liters > 0")
    op.create_check_constraint(
        "ck_fuel_cost_non_negative",
        "vehicle_fuel_log",
        "total_cost IS NULL OR total_cost >= 0",
    )
