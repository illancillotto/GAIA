"""add network monitor mvp schema

Revision ID: 20260326_0014
Revises: 20260326_0013
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260326_0014"
down_revision = "20260326_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "network_scans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("network_range", sa.String(length=64), nullable=False),
        sa.Column("scan_type", sa.String(length=32), nullable=False, server_default="incremental"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("hosts_scanned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_hosts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discovered_devices", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("initiated_by", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_network_scans_id", "network_scans", ["id"])
    op.create_index("ix_network_scans_network_range", "network_scans", ["network_range"])
    op.create_index("ix_network_scans_status", "network_scans", ["status"])

    op.create_table(
        "network_devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("last_scan_id", sa.Integer(), sa.ForeignKey("network_scans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("mac_address", sa.String(length=64), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("vendor", sa.String(length=255), nullable=True),
        sa.Column("device_type", sa.String(length=64), nullable=True),
        sa.Column("operating_system", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="online"),
        sa.Column("is_monitored", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("open_ports", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("ip_address", name="uq_network_devices_ip_address"),
    )
    op.create_index("ix_network_devices_id", "network_devices", ["id"])
    op.create_index("ix_network_devices_last_scan_id", "network_devices", ["last_scan_id"])
    op.create_index("ix_network_devices_ip_address", "network_devices", ["ip_address"])
    op.create_index("ix_network_devices_mac_address", "network_devices", ["mac_address"])
    op.create_index("ix_network_devices_hostname", "network_devices", ["hostname"])
    op.create_index("ix_network_devices_device_type", "network_devices", ["device_type"])
    op.create_index("ix_network_devices_status", "network_devices", ["status"])

    op.create_table(
        "network_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("network_devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scan_id", sa.Integer(), sa.ForeignKey("network_scans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="info"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_network_alerts_id", "network_alerts", ["id"])
    op.create_index("ix_network_alerts_device_id", "network_alerts", ["device_id"])
    op.create_index("ix_network_alerts_scan_id", "network_alerts", ["scan_id"])
    op.create_index("ix_network_alerts_alert_type", "network_alerts", ["alert_type"])
    op.create_index("ix_network_alerts_severity", "network_alerts", ["severity"])
    op.create_index("ix_network_alerts_status", "network_alerts", ["status"])

    op.create_table(
        "floor_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("building", sa.String(length=255), nullable=True),
        sa.Column("floor_label", sa.String(length=64), nullable=False),
        sa.Column("svg_content", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_floor_plans_id", "floor_plans", ["id"])
    op.create_index("ix_floor_plans_floor_label", "floor_plans", ["floor_label"])

    op.create_table(
        "device_positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("network_devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("floor_plan_id", sa.Integer(), sa.ForeignKey("floor_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("device_id", "floor_plan_id", name="uq_device_positions_device_floor"),
    )
    op.create_index("ix_device_positions_id", "device_positions", ["id"])
    op.create_index("ix_device_positions_device_id", "device_positions", ["device_id"])
    op.create_index("ix_device_positions_floor_plan_id", "device_positions", ["floor_plan_id"])

    op.create_table(
        "device_inventory_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("network_devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inventory_item_id", sa.Integer(), nullable=True),
        sa.Column("inventory_hostname", sa.String(length=255), nullable=True),
        sa.Column("inventory_mac_address", sa.String(length=64), nullable=True),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("device_id", name="uq_device_inventory_links_device_id"),
    )
    op.create_index("ix_device_inventory_links_id", "device_inventory_links", ["id"])
    op.create_index("ix_device_inventory_links_device_id", "device_inventory_links", ["device_id"])
    op.create_index("ix_device_inventory_links_inventory_item_id", "device_inventory_links", ["inventory_item_id"])
    op.create_index("ix_device_inventory_links_inventory_mac_address", "device_inventory_links", ["inventory_mac_address"])


def downgrade() -> None:
    op.drop_index("ix_device_inventory_links_inventory_mac_address", table_name="device_inventory_links")
    op.drop_index("ix_device_inventory_links_inventory_item_id", table_name="device_inventory_links")
    op.drop_index("ix_device_inventory_links_device_id", table_name="device_inventory_links")
    op.drop_index("ix_device_inventory_links_id", table_name="device_inventory_links")
    op.drop_table("device_inventory_links")

    op.drop_index("ix_device_positions_floor_plan_id", table_name="device_positions")
    op.drop_index("ix_device_positions_device_id", table_name="device_positions")
    op.drop_index("ix_device_positions_id", table_name="device_positions")
    op.drop_table("device_positions")

    op.drop_index("ix_floor_plans_floor_label", table_name="floor_plans")
    op.drop_index("ix_floor_plans_id", table_name="floor_plans")
    op.drop_table("floor_plans")

    op.drop_index("ix_network_alerts_status", table_name="network_alerts")
    op.drop_index("ix_network_alerts_severity", table_name="network_alerts")
    op.drop_index("ix_network_alerts_alert_type", table_name="network_alerts")
    op.drop_index("ix_network_alerts_scan_id", table_name="network_alerts")
    op.drop_index("ix_network_alerts_device_id", table_name="network_alerts")
    op.drop_index("ix_network_alerts_id", table_name="network_alerts")
    op.drop_table("network_alerts")

    op.drop_index("ix_network_devices_status", table_name="network_devices")
    op.drop_index("ix_network_devices_device_type", table_name="network_devices")
    op.drop_index("ix_network_devices_hostname", table_name="network_devices")
    op.drop_index("ix_network_devices_mac_address", table_name="network_devices")
    op.drop_index("ix_network_devices_ip_address", table_name="network_devices")
    op.drop_index("ix_network_devices_last_scan_id", table_name="network_devices")
    op.drop_index("ix_network_devices_id", table_name="network_devices")
    op.drop_table("network_devices")

    op.drop_index("ix_network_scans_status", table_name="network_scans")
    op.drop_index("ix_network_scans_network_range", table_name="network_scans")
    op.drop_index("ix_network_scans_id", table_name="network_scans")
    op.drop_table("network_scans")
