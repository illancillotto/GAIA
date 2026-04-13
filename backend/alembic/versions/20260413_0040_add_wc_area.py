"""add wc area

Revision ID: 20260413_0040
Revises: 20260413_0039
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_0040"
down_revision = "20260413_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wc_area",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("wc_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("is_district", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("polygon", sa.Text(), nullable=True),
        sa.Column("wc_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_wc_area_wc_id"), "wc_area", ["wc_id"], unique=True)
    op.create_index(op.f("ix_wc_area_name"), "wc_area", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_wc_area_name"), table_name="wc_area")
    op.drop_index(op.f("ix_wc_area_wc_id"), table_name="wc_area")
    op.drop_table("wc_area")
