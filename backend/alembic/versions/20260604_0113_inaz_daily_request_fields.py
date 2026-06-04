"""add inaz daily request normalization fields

Revision ID: 20260604_0113
Revises: 20260604_0112
Create Date: 2026-06-04 15:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0113"
down_revision = "20260604_0112"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inaz_daily_records", sa.Column("request_type", sa.String(length=120), nullable=True))
    op.add_column("inaz_daily_records", sa.Column("request_description", sa.Text(), nullable=True))
    op.add_column("inaz_daily_records", sa.Column("request_status", sa.String(length=64), nullable=True))
    op.add_column("inaz_daily_records", sa.Column("request_authorized_by", sa.String(length=255), nullable=True))
    op.add_column("inaz_daily_records", sa.Column("resolved_absence_cause", sa.String(length=64), nullable=True))
    op.create_index(
        op.f("ix_inaz_daily_records_resolved_absence_cause"),
        "inaz_daily_records",
        ["resolved_absence_cause"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_inaz_daily_records_resolved_absence_cause"), table_name="inaz_daily_records")
    op.drop_column("inaz_daily_records", "resolved_absence_cause")
    op.drop_column("inaz_daily_records", "request_authorized_by")
    op.drop_column("inaz_daily_records", "request_status")
    op.drop_column("inaz_daily_records", "request_description")
    op.drop_column("inaz_daily_records", "request_type")
