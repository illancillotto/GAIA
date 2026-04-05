"""add operazioni module flag to application users

Revision ID: 20260405_0030
Revises: 20260404_0029
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260405_0030"
down_revision = "20260404_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application_users",
        sa.Column(
            "module_operazioni", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    op.drop_column("application_users", "module_operazioni")
