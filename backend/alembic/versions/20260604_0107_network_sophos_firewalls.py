"""add sophos firewall ingestion tables

Revision ID: 20260604_0107
Revises: 20260603_0106
Create Date: 2026-06-04 09:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0107"
down_revision = "20260603_0106"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "network_firewalls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("serial_number", sa.String(length=255), nullable=True),
        sa.Column("management_ip", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata_sources", sa.Text(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_network_firewalls_id"), "network_firewalls", ["id"], unique=False)
    op.create_index(op.f("ix_network_firewalls_management_ip"), "network_firewalls", ["management_ip"], unique=False)
    op.create_index(op.f("ix_network_firewalls_name"), "network_firewalls", ["name"], unique=False)
    op.create_index(op.f("ix_network_firewalls_serial_number"), "network_firewalls", ["serial_number"], unique=False)
    op.create_index(op.f("ix_network_firewalls_status"), "network_firewalls", ["status"], unique=False)
    op.create_index(op.f("ix_network_firewalls_vendor"), "network_firewalls", ["vendor"], unique=False)

    op.create_table(
        "network_firewall_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("firewall_id", sa.Integer(), nullable=False),
        sa.Column("metric_key", sa.String(length=128), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("metric_text", sa.String(length=255), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["firewall_id"], ["network_firewalls.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_network_firewall_metrics_firewall_id"), "network_firewall_metrics", ["firewall_id"], unique=False)
    op.create_index(op.f("ix_network_firewall_metrics_id"), "network_firewall_metrics", ["id"], unique=False)
    op.create_index(op.f("ix_network_firewall_metrics_metric_key"), "network_firewall_metrics", ["metric_key"], unique=False)
    op.create_index(op.f("ix_network_firewall_metrics_observed_at"), "network_firewall_metrics", ["observed_at"], unique=False)
    op.create_index(op.f("ix_network_firewall_metrics_severity"), "network_firewall_metrics", ["severity"], unique=False)

    op.create_table(
        "network_firewall_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("firewall_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("log_id", sa.String(length=64), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("src_ip", sa.String(length=64), nullable=True),
        sa.Column("dst_ip", sa.String(length=64), nullable=True),
        sa.Column("protocol", sa.String(length=32), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["network_devices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["firewall_id"], ["network_firewalls.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_network_firewall_events_device_id"), "network_firewall_events", ["device_id"], unique=False)
    op.create_index(op.f("ix_network_firewall_events_dst_ip"), "network_firewall_events", ["dst_ip"], unique=False)
    op.create_index(op.f("ix_network_firewall_events_event_type"), "network_firewall_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_network_firewall_events_firewall_id"), "network_firewall_events", ["firewall_id"], unique=False)
    op.create_index(op.f("ix_network_firewall_events_id"), "network_firewall_events", ["id"], unique=False)
    op.create_index(op.f("ix_network_firewall_events_log_id"), "network_firewall_events", ["log_id"], unique=False)
    op.create_index(op.f("ix_network_firewall_events_observed_at"), "network_firewall_events", ["observed_at"], unique=False)
    op.create_index(op.f("ix_network_firewall_events_severity"), "network_firewall_events", ["severity"], unique=False)
    op.create_index(op.f("ix_network_firewall_events_source"), "network_firewall_events", ["source"], unique=False)
    op.create_index(op.f("ix_network_firewall_events_src_ip"), "network_firewall_events", ["src_ip"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_network_firewall_events_src_ip"), table_name="network_firewall_events")
    op.drop_index(op.f("ix_network_firewall_events_source"), table_name="network_firewall_events")
    op.drop_index(op.f("ix_network_firewall_events_severity"), table_name="network_firewall_events")
    op.drop_index(op.f("ix_network_firewall_events_observed_at"), table_name="network_firewall_events")
    op.drop_index(op.f("ix_network_firewall_events_log_id"), table_name="network_firewall_events")
    op.drop_index(op.f("ix_network_firewall_events_id"), table_name="network_firewall_events")
    op.drop_index(op.f("ix_network_firewall_events_firewall_id"), table_name="network_firewall_events")
    op.drop_index(op.f("ix_network_firewall_events_event_type"), table_name="network_firewall_events")
    op.drop_index(op.f("ix_network_firewall_events_dst_ip"), table_name="network_firewall_events")
    op.drop_index(op.f("ix_network_firewall_events_device_id"), table_name="network_firewall_events")
    op.drop_table("network_firewall_events")

    op.drop_index(op.f("ix_network_firewall_metrics_severity"), table_name="network_firewall_metrics")
    op.drop_index(op.f("ix_network_firewall_metrics_observed_at"), table_name="network_firewall_metrics")
    op.drop_index(op.f("ix_network_firewall_metrics_metric_key"), table_name="network_firewall_metrics")
    op.drop_index(op.f("ix_network_firewall_metrics_id"), table_name="network_firewall_metrics")
    op.drop_index(op.f("ix_network_firewall_metrics_firewall_id"), table_name="network_firewall_metrics")
    op.drop_table("network_firewall_metrics")

    op.drop_index(op.f("ix_network_firewalls_vendor"), table_name="network_firewalls")
    op.drop_index(op.f("ix_network_firewalls_status"), table_name="network_firewalls")
    op.drop_index(op.f("ix_network_firewalls_serial_number"), table_name="network_firewalls")
    op.drop_index(op.f("ix_network_firewalls_name"), table_name="network_firewalls")
    op.drop_index(op.f("ix_network_firewalls_management_ip"), table_name="network_firewalls")
    op.drop_index(op.f("ix_network_firewalls_id"), table_name="network_firewalls")
    op.drop_table("network_firewalls")
