"""add utenze module flag to application users

Revision ID: 20260401_0025
Revises: 20260330_0024
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260401_0025"
down_revision = "20260330_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application_users",
        sa.Column("module_utenze", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE application_users SET module_utenze = module_anagrafica")
    op.alter_column("application_users", "module_utenze", server_default=None)


def downgrade() -> None:
    op.drop_column("application_users", "module_utenze")

