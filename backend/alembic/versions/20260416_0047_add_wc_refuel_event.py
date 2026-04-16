"""add wc refuel event

Revision ID: 20260416_0047
Revises: 20260416_0046
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260416_0047"
down_revision = "20260416_0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wc_refuel_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("wc_id", sa.Integer(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=True),
        sa.Column("wc_operator_id", sa.Uuid(), nullable=True),
        sa.Column("matched_fuel_log_id", sa.Uuid(), nullable=True),
        sa.Column("matched_fuel_card_id", sa.Uuid(), nullable=True),
        sa.Column("vehicle_code", sa.String(length=100), nullable=True),
        sa.Column("operator_name", sa.String(length=200), nullable=True),
        sa.Column("fueled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("odometer_km", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("source_issue", sa.Text(), nullable=True),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wc_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["matched_fuel_card_id"], ["fuel_card.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["matched_fuel_log_id"], ["vehicle_fuel_log.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicle.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["wc_operator_id"], ["wc_operator.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wc_refuel_event_wc_id", "wc_refuel_event", ["wc_id"], unique=True)
    op.create_index("ix_wc_refuel_event_vehicle_id", "wc_refuel_event", ["vehicle_id"], unique=False)
    op.create_index("ix_wc_refuel_event_wc_operator_id", "wc_refuel_event", ["wc_operator_id"], unique=False)
    op.create_index("ix_wc_refuel_event_matched_fuel_log_id", "wc_refuel_event", ["matched_fuel_log_id"], unique=False)
    op.create_index("ix_wc_refuel_event_matched_fuel_card_id", "wc_refuel_event", ["matched_fuel_card_id"], unique=False)
    op.create_index("ix_wc_refuel_event_vehicle_code", "wc_refuel_event", ["vehicle_code"], unique=False)
    op.create_index("ix_wc_refuel_event_fueled_at", "wc_refuel_event", ["fueled_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_wc_refuel_event_fueled_at", table_name="wc_refuel_event")
    op.drop_index("ix_wc_refuel_event_vehicle_code", table_name="wc_refuel_event")
    op.drop_index("ix_wc_refuel_event_matched_fuel_card_id", table_name="wc_refuel_event")
    op.drop_index("ix_wc_refuel_event_matched_fuel_log_id", table_name="wc_refuel_event")
    op.drop_index("ix_wc_refuel_event_wc_operator_id", table_name="wc_refuel_event")
    op.drop_index("ix_wc_refuel_event_vehicle_id", table_name="wc_refuel_event")
    op.drop_index("ix_wc_refuel_event_wc_id", table_name="wc_refuel_event")
    op.drop_table("wc_refuel_event")
