"""add warehouse request

Revision ID: 20260413_0041
Revises: 20260413_0040
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_0041"
down_revision = "20260413_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "warehouse_request",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("wc_id", sa.Integer(), nullable=False),
        sa.Column("wc_report_id", sa.Integer(), nullable=True),
        sa.Column("field_report_id", sa.Uuid(), nullable=True),
        sa.Column("report_type", sa.String(length=200), nullable=True),
        sa.Column("reported_by", sa.String(length=200), nullable=True),
        sa.Column("requested_by", sa.String(length=200), nullable=True),
        sa.Column("report_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("wc_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["field_report_id"], ["field_report.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_warehouse_request_wc_id"), "warehouse_request", ["wc_id"], unique=True)
    op.create_index(op.f("ix_warehouse_request_wc_report_id"), "warehouse_request", ["wc_report_id"], unique=False)
    op.create_index(op.f("ix_warehouse_request_field_report_id"), "warehouse_request", ["field_report_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_warehouse_request_field_report_id"), table_name="warehouse_request")
    op.drop_index(op.f("ix_warehouse_request_wc_report_id"), table_name="warehouse_request")
    op.drop_index(op.f("ix_warehouse_request_wc_id"), table_name="warehouse_request")
    op.drop_table("warehouse_request")
