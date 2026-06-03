"""inaz daily record manual fields

Revision ID: 20260603_0103
Revises: 20260529_0102
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260603_0103"
down_revision = "20260529_0102"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inaz_daily_records", sa.Column("km_value", sa.Integer(), nullable=True))
    op.add_column("inaz_daily_records", sa.Column("override_straordinario_minutes", sa.Integer(), nullable=True))
    op.add_column("inaz_daily_records", sa.Column("override_mpe_minutes", sa.Integer(), nullable=True))
    op.add_column("inaz_daily_records", sa.Column("manual_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("inaz_daily_records", "manual_note")
    op.drop_column("inaz_daily_records", "override_mpe_minutes")
    op.drop_column("inaz_daily_records", "override_straordinario_minutes")
    op.drop_column("inaz_daily_records", "km_value")
