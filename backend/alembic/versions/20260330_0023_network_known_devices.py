"""add known device flag to network devices

Revision ID: 20260330_0023
Revises: 20260330_0022
Create Date: 2026-03-30 16:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260330_0023"
down_revision = "20260330_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "network_devices",
        sa.Column("is_known_device", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_network_devices_is_known_device", "network_devices", ["is_known_device"])
    op.alter_column("network_devices", "is_known_device", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_network_devices_is_known_device", table_name="network_devices")
    op.drop_column("network_devices", "is_known_device")
