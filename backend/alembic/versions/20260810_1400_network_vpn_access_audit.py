"""network vpn access audit

Revision ID: 20260810_1400
Revises: 20260807_1200
Create Date: 2026-08-10
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260810_1400"
down_revision: str | None = "20260807_1200"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "network_vpn_devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("client_device_id", sa.String(length=128), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
        sa.Column("user_agent_sample", sa.String(length=512), nullable=True),
        sa.Column("first_client_ip", sa.String(length=64), nullable=True),
        sa.Column("last_client_ip", sa.String(length=64), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "device_fingerprint", name="uq_network_vpn_devices_user_fingerprint"),
    )
    op.create_index(op.f("ix_network_vpn_devices_id"), "network_vpn_devices", ["id"], unique=False)
    op.create_index(op.f("ix_network_vpn_devices_user_id"), "network_vpn_devices", ["user_id"], unique=False)
    op.create_index(op.f("ix_network_vpn_devices_device_fingerprint"), "network_vpn_devices", ["device_fingerprint"], unique=False)
    op.create_index(op.f("ix_network_vpn_devices_client_device_id"), "network_vpn_devices", ["client_device_id"], unique=False)
    op.create_index(op.f("ix_network_vpn_devices_status"), "network_vpn_devices", ["status"], unique=False)
    op.create_index(op.f("ix_network_vpn_devices_user_agent_hash"), "network_vpn_devices", ["user_agent_hash"], unique=False)
    op.create_index(op.f("ix_network_vpn_devices_last_client_ip"), "network_vpn_devices", ["last_client_ip"], unique=False)
    op.create_index(op.f("ix_network_vpn_devices_last_seen_at"), "network_vpn_devices", ["last_seen_at"], unique=False)

    op.create_table(
        "network_vpn_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="gaia_login"),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("client_ip", sa.String(length=64), nullable=True),
        sa.Column("vpn_ip", sa.String(length=64), nullable=True),
        sa.Column("public_ip", sa.String(length=64), nullable=True),
        sa.Column("device_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
        sa.Column("user_agent_sample", sa.String(length=512), nullable=True),
        sa.Column("blocked_reason", sa.String(length=255), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["network_vpn_devices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_network_vpn_sessions_id"), "network_vpn_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_network_vpn_sessions_user_id"), "network_vpn_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_network_vpn_sessions_device_id"), "network_vpn_sessions", ["device_id"], unique=False)
    op.create_index(op.f("ix_network_vpn_sessions_source"), "network_vpn_sessions", ["source"], unique=False)
    op.create_index(op.f("ix_network_vpn_sessions_event_type"), "network_vpn_sessions", ["event_type"], unique=False)
    op.create_index(op.f("ix_network_vpn_sessions_username"), "network_vpn_sessions", ["username"], unique=False)
    op.create_index(op.f("ix_network_vpn_sessions_client_ip"), "network_vpn_sessions", ["client_ip"], unique=False)
    op.create_index(op.f("ix_network_vpn_sessions_vpn_ip"), "network_vpn_sessions", ["vpn_ip"], unique=False)
    op.create_index(op.f("ix_network_vpn_sessions_public_ip"), "network_vpn_sessions", ["public_ip"], unique=False)
    op.create_index(op.f("ix_network_vpn_sessions_device_fingerprint"), "network_vpn_sessions", ["device_fingerprint"], unique=False)
    op.create_index(op.f("ix_network_vpn_sessions_observed_at"), "network_vpn_sessions", ["observed_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_network_vpn_sessions_observed_at"), table_name="network_vpn_sessions")
    op.drop_index(op.f("ix_network_vpn_sessions_device_fingerprint"), table_name="network_vpn_sessions")
    op.drop_index(op.f("ix_network_vpn_sessions_public_ip"), table_name="network_vpn_sessions")
    op.drop_index(op.f("ix_network_vpn_sessions_vpn_ip"), table_name="network_vpn_sessions")
    op.drop_index(op.f("ix_network_vpn_sessions_client_ip"), table_name="network_vpn_sessions")
    op.drop_index(op.f("ix_network_vpn_sessions_username"), table_name="network_vpn_sessions")
    op.drop_index(op.f("ix_network_vpn_sessions_event_type"), table_name="network_vpn_sessions")
    op.drop_index(op.f("ix_network_vpn_sessions_source"), table_name="network_vpn_sessions")
    op.drop_index(op.f("ix_network_vpn_sessions_device_id"), table_name="network_vpn_sessions")
    op.drop_index(op.f("ix_network_vpn_sessions_user_id"), table_name="network_vpn_sessions")
    op.drop_index(op.f("ix_network_vpn_sessions_id"), table_name="network_vpn_sessions")
    op.drop_table("network_vpn_sessions")
    op.drop_index(op.f("ix_network_vpn_devices_last_seen_at"), table_name="network_vpn_devices")
    op.drop_index(op.f("ix_network_vpn_devices_last_client_ip"), table_name="network_vpn_devices")
    op.drop_index(op.f("ix_network_vpn_devices_user_agent_hash"), table_name="network_vpn_devices")
    op.drop_index(op.f("ix_network_vpn_devices_status"), table_name="network_vpn_devices")
    op.drop_index(op.f("ix_network_vpn_devices_client_device_id"), table_name="network_vpn_devices")
    op.drop_index(op.f("ix_network_vpn_devices_device_fingerprint"), table_name="network_vpn_devices")
    op.drop_index(op.f("ix_network_vpn_devices_user_id"), table_name="network_vpn_devices")
    op.drop_index(op.f("ix_network_vpn_devices_id"), table_name="network_vpn_devices")
    op.drop_table("network_vpn_devices")
