"""add reperibilita flag to inaz daily records

Revision ID: 20260608_0133
Revises: 20260608_0132
Create Date: 2026-06-08 12:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260608_0133"
down_revision = "20260608_0132"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inaz_daily_records",
        sa.Column("reperibilita_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("inaz_daily_records", "reperibilita_flag", server_default=None)


def downgrade() -> None:
    op.drop_column("inaz_daily_records", "reperibilita_flag")
