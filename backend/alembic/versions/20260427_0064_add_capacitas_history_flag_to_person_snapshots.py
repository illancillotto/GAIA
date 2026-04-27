"""add capacitas history flag to person snapshots

Revision ID: 20260427_0064
Revises: 20260424_0063
Create Date: 2026-04-27 08:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260427_0064"
down_revision = "20260424_0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ana_person_snapshots",
        sa.Column("is_capacitas_history", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_ana_person_snapshots_is_capacitas_history",
        "ana_person_snapshots",
        ["is_capacitas_history"],
        unique=False,
    )
    op.alter_column("ana_person_snapshots", "is_capacitas_history", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_ana_person_snapshots_is_capacitas_history", table_name="ana_person_snapshots")
    op.drop_column("ana_person_snapshots", "is_capacitas_history")
