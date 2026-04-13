"""add wc org charts

Revision ID: 20260413_0042
Revises: 20260413_0041
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_0042"
down_revision = "20260413_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wc_org_chart",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("wc_id", sa.Integer(), nullable=False),
        sa.Column("chart_type", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("wc_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chart_type", "wc_id", name="uq_wc_org_chart_type_wc_id"),
    )
    op.create_index(op.f("ix_wc_org_chart_wc_id"), "wc_org_chart", ["wc_id"], unique=False)
    op.create_index(op.f("ix_wc_org_chart_chart_type"), "wc_org_chart", ["chart_type"], unique=False)
    op.create_index(op.f("ix_wc_org_chart_name"), "wc_org_chart", ["name"], unique=False)

    op.create_table(
        "wc_org_chart_entry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_chart_id", sa.Uuid(), nullable=False),
        sa.Column("wc_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("wc_operator_id", sa.Uuid(), nullable=True),
        sa.Column("wc_area_id", sa.Uuid(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("source_field", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_chart_id"], ["wc_org_chart.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wc_operator_id"], ["wc_operator.id"]),
        sa.ForeignKeyConstraint(["wc_area_id"], ["wc_area.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_wc_org_chart_entry_org_chart_id"), "wc_org_chart_entry", ["org_chart_id"], unique=False)
    op.create_index(op.f("ix_wc_org_chart_entry_wc_id"), "wc_org_chart_entry", ["wc_id"], unique=False)
    op.create_index(op.f("ix_wc_org_chart_entry_role"), "wc_org_chart_entry", ["role"], unique=False)
    op.create_index(op.f("ix_wc_org_chart_entry_wc_operator_id"), "wc_org_chart_entry", ["wc_operator_id"], unique=False)
    op.create_index(op.f("ix_wc_org_chart_entry_wc_area_id"), "wc_org_chart_entry", ["wc_area_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_wc_org_chart_entry_wc_area_id"), table_name="wc_org_chart_entry")
    op.drop_index(op.f("ix_wc_org_chart_entry_wc_operator_id"), table_name="wc_org_chart_entry")
    op.drop_index(op.f("ix_wc_org_chart_entry_role"), table_name="wc_org_chart_entry")
    op.drop_index(op.f("ix_wc_org_chart_entry_wc_id"), table_name="wc_org_chart_entry")
    op.drop_index(op.f("ix_wc_org_chart_entry_org_chart_id"), table_name="wc_org_chart_entry")
    op.drop_table("wc_org_chart_entry")
    op.drop_index(op.f("ix_wc_org_chart_name"), table_name="wc_org_chart")
    op.drop_index(op.f("ix_wc_org_chart_chart_type"), table_name="wc_org_chart")
    op.drop_index(op.f("ix_wc_org_chart_wc_id"), table_name="wc_org_chart")
    op.drop_table("wc_org_chart")
