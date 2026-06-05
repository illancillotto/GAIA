"""meter reading manual corrections

Revision ID: 20260605_0118
Revises: 20260605_0117
Create Date: 2026-06-05 13:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260605_0118"
down_revision: str | None = "20260605_0117"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("catasto_meter_readings", sa.Column("import_payload_json", sa.JSON(), nullable=True))
    op.add_column("catasto_meter_readings", sa.Column("manual_corrections", sa.JSON(), nullable=True))
    op.add_column("catasto_meter_readings", sa.Column("manual_override_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("catasto_meter_readings", sa.Column("manual_override_updated_by", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_catasto_meter_readings_manual_override_updated_by",
        "catasto_meter_readings",
        "application_users",
        ["manual_override_updated_by"],
        ["id"],
    )
    op.create_table(
        "catasto_meter_reading_manual_audits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("meter_reading_id", sa.Uuid(), nullable=False),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("previous_values", sa.JSON(), nullable=True),
        sa.Column("new_values", sa.JSON(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["changed_by"], ["application_users.id"]),
        sa.ForeignKeyConstraint(["meter_reading_id"], ["catasto_meter_readings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_catasto_meter_reading_manual_audits_meter_reading_id"),
        "catasto_meter_reading_manual_audits",
        ["meter_reading_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_catasto_meter_reading_manual_audits_changed_at"),
        "catasto_meter_reading_manual_audits",
        ["changed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_catasto_meter_reading_manual_audits_changed_at"), table_name="catasto_meter_reading_manual_audits")
    op.drop_index(op.f("ix_catasto_meter_reading_manual_audits_meter_reading_id"), table_name="catasto_meter_reading_manual_audits")
    op.drop_table("catasto_meter_reading_manual_audits")
    op.drop_constraint("fk_catasto_meter_readings_manual_override_updated_by", "catasto_meter_readings", type_="foreignkey")
    op.drop_column("catasto_meter_readings", "manual_override_updated_by")
    op.drop_column("catasto_meter_readings", "manual_override_updated_at")
    op.drop_column("catasto_meter_readings", "manual_corrections")
    op.drop_column("catasto_meter_readings", "import_payload_json")
