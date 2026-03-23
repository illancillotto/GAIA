"""sync runs metadata

Revision ID: 20260323_0006
Revises: 20260323_0005
Create Date: 2026-03-23 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260323_0006"
down_revision = "20260323_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sync_runs", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column("sync_runs", sa.Column("initiated_by", sa.String(length=120), nullable=True))
    op.add_column("sync_runs", sa.Column("source_label", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("sync_runs", "source_label")
    op.drop_column("sync_runs", "initiated_by")
    op.drop_column("sync_runs", "duration_ms")
