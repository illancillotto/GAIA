"""add operazioni fuel cards

Revision ID: 20260415_0044
Revises: 20260413_0043
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260415_0044"
down_revision = "20260413_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fuel_card",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("codice", sa.String(length=100), nullable=True),
        sa.Column("sigla", sa.String(length=50), nullable=True),
        sa.Column("cod", sa.String(length=100), nullable=True),
        sa.Column("pan", sa.String(length=80), nullable=False),
        sa.Column("card_number_emissione", sa.String(length=200), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("prodotti", sa.Text(), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("current_wc_operator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_driver_raw", sa.String(length=220), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["current_wc_operator_id"], ["wc_operator.id"]),
        sa.UniqueConstraint("pan"),
    )
    op.create_index("ix_fuel_card_pan", "fuel_card", ["pan"], unique=False)
    op.create_index("ix_fuel_card_codice", "fuel_card", ["codice"], unique=False)
    op.create_index("ix_fuel_card_sigla", "fuel_card", ["sigla"], unique=False)
    op.create_index("ix_fuel_card_cod", "fuel_card", ["cod"], unique=False)
    op.create_index("ix_fuel_card_is_blocked", "fuel_card", ["is_blocked"], unique=False)
    op.create_index("ix_fuel_card_expires_at", "fuel_card", ["expires_at"], unique=False)
    op.create_index("ix_fuel_card_current_wc_operator_id", "fuel_card", ["current_wc_operator_id"], unique=False)

    op.create_table(
        "fuel_card_assignment_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("fuel_card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wc_operator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("driver_raw", sa.String(length=220), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False, server_default="excel_import"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["application_users.id"]),
        sa.ForeignKeyConstraint(["fuel_card_id"], ["fuel_card.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wc_operator_id"], ["wc_operator.id"]),
    )
    op.create_index(
        "ix_fuel_card_assignment_history_fuel_card_id",
        "fuel_card_assignment_history",
        ["fuel_card_id"],
        unique=False,
    )
    op.create_index(
        "ix_fuel_card_assignment_history_wc_operator_id",
        "fuel_card_assignment_history",
        ["wc_operator_id"],
        unique=False,
    )
    op.create_index(
        "ix_fuel_card_assignment_history_start_at",
        "fuel_card_assignment_history",
        ["start_at"],
        unique=False,
    )
    op.create_index(
        "ix_fuel_card_assignment_history_end_at",
        "fuel_card_assignment_history",
        ["end_at"],
        unique=False,
    )
    op.create_index(
        "ix_fuel_card_assignment_history_changed_by_user_id",
        "fuel_card_assignment_history",
        ["changed_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_fuel_card_assignment_history_changed_by_user_id", table_name="fuel_card_assignment_history")
    op.drop_index("ix_fuel_card_assignment_history_end_at", table_name="fuel_card_assignment_history")
    op.drop_index("ix_fuel_card_assignment_history_start_at", table_name="fuel_card_assignment_history")
    op.drop_index("ix_fuel_card_assignment_history_wc_operator_id", table_name="fuel_card_assignment_history")
    op.drop_index("ix_fuel_card_assignment_history_fuel_card_id", table_name="fuel_card_assignment_history")
    op.drop_table("fuel_card_assignment_history")

    op.drop_index("ix_fuel_card_current_wc_operator_id", table_name="fuel_card")
    op.drop_index("ix_fuel_card_expires_at", table_name="fuel_card")
    op.drop_index("ix_fuel_card_is_blocked", table_name="fuel_card")
    op.drop_index("ix_fuel_card_cod", table_name="fuel_card")
    op.drop_index("ix_fuel_card_sigla", table_name="fuel_card")
    op.drop_index("ix_fuel_card_codice", table_name="fuel_card")
    op.drop_index("ix_fuel_card_pan", table_name="fuel_card")
    op.drop_table("fuel_card")

