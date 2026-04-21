"""add fleet_unresolved_transaction table for persistent review queue

Revision ID: 20260421_0055
Revises: 20260421_0054
Create Date: 2026-04-21

"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision = "20260421_0055"
down_revision: Union[str, None] = "20260421_0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fleet_unresolved_transaction",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("import_ref", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("reason_type", sa.String(50), nullable=False),
        sa.Column("reason_detail", sa.Text(), nullable=False),
        sa.Column("targa", sa.String(20), nullable=True),
        sa.Column("identificativo", sa.String(100), nullable=True),
        sa.Column("fueled_at_iso", sa.String(30), nullable=True),
        sa.Column("liters", sa.String(20), nullable=True),
        sa.Column("total_cost", sa.String(20), nullable=True),
        sa.Column("odometer_km", sa.String(20), nullable=True),
        sa.Column("operator_name", sa.String(200), nullable=True),
        sa.Column("wc_operator_id", sa.String(36), nullable=True),
        sa.Column("card_code", sa.String(50), nullable=True),
        sa.Column("station_name", sa.String(200), nullable=True),
        sa.Column("notes_extra", sa.Text(), nullable=True),
        sa.Column(
            "resolved_vehicle_id",
            sa.Uuid(),
            sa.ForeignKey("vehicle.id"),
            nullable=True,
        ),
        sa.Column(
            "resolved_by_user_id",
            sa.Integer(),
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_fleet_unresolved_import_ref", "fleet_unresolved_transaction", ["import_ref"])
    op.create_index("ix_fleet_unresolved_status", "fleet_unresolved_transaction", ["status"])


def downgrade() -> None:
    op.drop_index("ix_fleet_unresolved_status", "fleet_unresolved_transaction")
    op.drop_index("ix_fleet_unresolved_import_ref", "fleet_unresolved_transaction")
    op.drop_table("fleet_unresolved_transaction")
