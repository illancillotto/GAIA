"""add trasferta minutes to inaz daily records

Revision ID: 20260615_1300
Revises: 20260615_1230
Create Date: 2026-06-15 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260615_1300"
down_revision = "20260615_1230"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inaz_daily_records", sa.Column("trasferta_minutes", sa.Integer(), nullable=True))
    op.add_column("inaz_daily_records", sa.Column("trasferta_montano", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("inaz_daily_records", "trasferta_montano", server_default=None)


def downgrade() -> None:
    op.drop_column("inaz_daily_records", "trasferta_montano")
    op.drop_column("inaz_daily_records", "trasferta_minutes")
