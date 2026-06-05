"""meter readings unique key by point and serial

Revision ID: 20260605_0116
Revises: 20260604_0115
Create Date: 2026-06-05 11:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260605_0116"
down_revision: str | None = "20260604_0115"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_catasto_meter_readings_ref", "catasto_meter_readings", type_="unique")
    op.create_index(
        "ux_catasto_meter_readings_ref_meter",
        "catasto_meter_readings",
        ["anno", "distretto_id", "punto_consegna", sa.text("coalesce(matricola, '')")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_catasto_meter_readings_ref_meter", table_name="catasto_meter_readings")
    op.create_unique_constraint(
        "uq_catasto_meter_readings_ref",
        "catasto_meter_readings",
        ["anno", "distretto_id", "punto_consegna"],
    )
