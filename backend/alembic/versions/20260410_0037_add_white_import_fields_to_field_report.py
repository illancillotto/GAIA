"""add white import fields to field_report

Revision ID: 20260410_0037
Revises: 20260410_0036
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260410_0037"
down_revision = "20260410_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("field_report", sa.Column("external_code", sa.String(length=50), nullable=True))
    op.add_column("field_report", sa.Column("reporter_name", sa.String(length=200), nullable=True))
    op.add_column("field_report", sa.Column("area_code", sa.String(length=200), nullable=True))
    op.add_column("field_report", sa.Column("assigned_responsibles", sa.Text(), nullable=True))
    op.add_column("field_report", sa.Column("completion_time_text", sa.String(length=200), nullable=True))
    op.add_column("field_report", sa.Column("completion_time_minutes", sa.Integer(), nullable=True))
    op.add_column(
        "field_report",
        sa.Column("source_system", sa.String(length=50), nullable=True, server_default="gaia"),
    )

    op.create_index(op.f("ix_field_report_external_code"), "field_report", ["external_code"], unique=True)
    op.create_index(op.f("ix_field_report_area_code"), "field_report", ["area_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_field_report_area_code"), table_name="field_report")
    op.drop_index(op.f("ix_field_report_external_code"), table_name="field_report")
    op.drop_column("field_report", "source_system")
    op.drop_column("field_report", "completion_time_minutes")
    op.drop_column("field_report", "completion_time_text")
    op.drop_column("field_report", "assigned_responsibles")
    op.drop_column("field_report", "area_code")
    op.drop_column("field_report", "reporter_name")
    op.drop_column("field_report", "external_code")
