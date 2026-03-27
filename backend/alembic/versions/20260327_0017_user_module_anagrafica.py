"""add anagrafica module flag to application users

Revision ID: 20260327_0017
Revises: 20260327_0016
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_0017"
down_revision = "20260327_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application_users",
        sa.Column("module_anagrafica", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("application_users", "module_anagrafica")
