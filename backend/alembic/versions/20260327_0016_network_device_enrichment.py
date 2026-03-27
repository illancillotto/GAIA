"""add enrichment fields to network devices

Revision ID: 20260327_0016
Revises: 20260326_0015
Create Date: 2026-03-27 09:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_0016"
down_revision = "20260326_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("network_devices", sa.Column("model_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("network_devices", "model_name")
