"""add network scan snapshot table

Revision ID: 20260330_0022
Revises: 20260327_0021
Create Date: 2026-03-30 10:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260330_0022"
down_revision = "20260327_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "network_scan_devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scan_id", sa.Integer(), sa.ForeignKey("network_scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("network_devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("mac_address", sa.String(length=64), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("hostname_source", sa.String(length=64), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("asset_label", sa.String(length=255), nullable=True),
        sa.Column("vendor", sa.String(length=255), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("device_type", sa.String(length=64), nullable=True),
        sa.Column("operating_system", sa.String(length=255), nullable=True),
        sa.Column("dns_name", sa.String(length=255), nullable=True),
        sa.Column("location_hint", sa.String(length=255), nullable=True),
        sa.Column("metadata_sources", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("open_ports", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("scan_id", "ip_address", name="uq_network_scan_devices_scan_ip"),
    )
    op.create_index("ix_network_scan_devices_id", "network_scan_devices", ["id"])
    op.create_index("ix_network_scan_devices_scan_id", "network_scan_devices", ["scan_id"])
    op.create_index("ix_network_scan_devices_device_id", "network_scan_devices", ["device_id"])
    op.create_index("ix_network_scan_devices_ip_address", "network_scan_devices", ["ip_address"])
    op.create_index("ix_network_scan_devices_mac_address", "network_scan_devices", ["mac_address"])
    op.create_index("ix_network_scan_devices_status", "network_scan_devices", ["status"])


def downgrade() -> None:
    op.drop_index("ix_network_scan_devices_status", table_name="network_scan_devices")
    op.drop_index("ix_network_scan_devices_mac_address", table_name="network_scan_devices")
    op.drop_index("ix_network_scan_devices_ip_address", table_name="network_scan_devices")
    op.drop_index("ix_network_scan_devices_device_id", table_name="network_scan_devices")
    op.drop_index("ix_network_scan_devices_scan_id", table_name="network_scan_devices")
    op.drop_index("ix_network_scan_devices_id", table_name="network_scan_devices")
    op.drop_table("network_scan_devices")
