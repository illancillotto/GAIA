"""add meter reading record type fields

Revision ID: 20260518_0085
Revises: 20260518_0084
Create Date: 2026-05-18 13:15:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260518_0085"
down_revision: str | None = "20260518_0084"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("catasto_meter_readings", sa.Column("record_type", sa.String(length=64), nullable=True))
    op.add_column("catasto_meter_readings", sa.Column("record_kind", sa.String(length=32), nullable=True))
    op.add_column("catasto_meter_readings", sa.Column("operational_state", sa.String(length=32), nullable=True))
    op.create_index(op.f("ix_catasto_meter_readings_record_kind"), "catasto_meter_readings", ["record_kind"], unique=False)
    op.create_index(
        op.f("ix_catasto_meter_readings_operational_state"),
        "catasto_meter_readings",
        ["operational_state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_catasto_meter_readings_operational_state"), table_name="catasto_meter_readings")
    op.drop_index(op.f("ix_catasto_meter_readings_record_kind"), table_name="catasto_meter_readings")
    op.drop_column("catasto_meter_readings", "operational_state")
    op.drop_column("catasto_meter_readings", "record_kind")
    op.drop_column("catasto_meter_readings", "record_type")
