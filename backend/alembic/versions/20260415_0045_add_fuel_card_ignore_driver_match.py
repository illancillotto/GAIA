"""add fuel card ignore driver match

Revision ID: 20260415_0045
Revises: 20260415_0044
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa


revision = "20260415_0045"
down_revision = "20260415_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fuel_card",
        sa.Column(
            "ignore_driver_match", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column("fuel_card", sa.Column("ignored_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("fuel_card", sa.Column("ignored_by_user_id", sa.Integer(), nullable=True))
    op.add_column("fuel_card", sa.Column("ignored_note", sa.Text(), nullable=True))

    op.create_index(
        "ix_fuel_card_ignore_driver_match", "fuel_card", ["ignore_driver_match"], unique=False
    )
    op.create_index(
        "ix_fuel_card_ignored_by_user_id", "fuel_card", ["ignored_by_user_id"], unique=False
    )
    op.create_foreign_key(
        "fk_fuel_card_ignored_by_user",
        "fuel_card",
        "application_users",
        ["ignored_by_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_fuel_card_ignored_by_user", "fuel_card", type_="foreignkey")
    op.drop_index("ix_fuel_card_ignored_by_user_id", table_name="fuel_card")
    op.drop_index("ix_fuel_card_ignore_driver_match", table_name="fuel_card")

    op.drop_column("fuel_card", "ignored_note")
    op.drop_column("fuel_card", "ignored_by_user_id")
    op.drop_column("fuel_card", "ignored_at")
    op.drop_column("fuel_card", "ignore_driver_match")

