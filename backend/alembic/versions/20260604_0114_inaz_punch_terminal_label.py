"""add terminal label to inaz daily punches

Revision ID: 20260604_0114
Revises: 20260604_0113
Create Date: 2026-06-04 16:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0114"
down_revision = "20260604_0113"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inaz_daily_punches", sa.Column("terminal_label", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("inaz_daily_punches", "terminal_label")
