"""drop legacy anagrafica module flag from application users

Revision ID: 20260401_0026
Revises: 20260401_0025
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260401_0026"
down_revision = "20260401_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure module_utenze stays enabled where legacy flag was set.
    op.execute("UPDATE application_users SET module_utenze = TRUE WHERE module_anagrafica = TRUE")
    op.drop_column("application_users", "module_anagrafica")


def downgrade() -> None:
    op.add_column(
        "application_users",
        sa.Column("module_anagrafica", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE application_users SET module_anagrafica = module_utenze")
    op.alter_column("application_users", "module_anagrafica", server_default=None)

