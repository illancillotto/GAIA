"""add catasto module flag to application users

Revision ID: 20260326_0013
Revises: 20260324_0012
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260326_0013"
down_revision = "20260324_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application_users",
        sa.Column("module_catasto", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("application_users", "module_catasto")
