"""add riordino module flag to application users

Revision ID: 20260409_0034
Revises: 20260407_0033
Create Date: 2026-04-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260409_0034"
down_revision: Union[str, None] = "20260407_0033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "application_users",
        sa.Column("module_riordino", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("application_users", "module_riordino", server_default=None)


def downgrade() -> None:
    op.drop_column("application_users", "module_riordino")
