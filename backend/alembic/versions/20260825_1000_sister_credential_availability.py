"""Add weekly availability to SISTER credentials.

Revision ID: 20260825_1000
Revises: 20260825_0900
"""

import sqlalchemy as sa

from alembic import op

revision = "20260825_1000"
down_revision = "20260825_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catasto_credentials",
        sa.Column("schedule_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("catasto_credentials", sa.Column("availability_schedule", sa.JSON(), nullable=True))
    op.alter_column("catasto_credentials", "schedule_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("catasto_credentials", "availability_schedule")
    op.drop_column("catasto_credentials", "schedule_enabled")
