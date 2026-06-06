"""network firewall hourly rollups

Revision ID: 20260605_0120
Revises: 20260605_0119
Create Date: 2026-06-05 19:05:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_0120"
down_revision: str | None = "20260605_0119"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "network_firewall_hourly_rollups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("dimension_key", sa.String(length=512), nullable=False),
        sa.Column("label", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("tracked_subject_id", sa.Integer(), nullable=True),
        sa.Column("events_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("allowed_events", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_events", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bytes_in", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("bytes_out", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["device_id"], ["network_devices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tracked_subject_id"], ["network_tracked_subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bucket_start", "category", "dimension_key", name="uq_network_firewall_hourly_rollups_bucket_category_key"),
    )
    op.create_index(op.f("ix_network_firewall_hourly_rollups_id"), "network_firewall_hourly_rollups", ["id"], unique=False)
    op.create_index(op.f("ix_network_firewall_hourly_rollups_bucket_start"), "network_firewall_hourly_rollups", ["bucket_start"], unique=False)
    op.create_index(op.f("ix_network_firewall_hourly_rollups_category"), "network_firewall_hourly_rollups", ["category"], unique=False)
    op.create_index(op.f("ix_network_firewall_hourly_rollups_dimension_key"), "network_firewall_hourly_rollups", ["dimension_key"], unique=False)
    op.create_index(op.f("ix_network_firewall_hourly_rollups_ip_address"), "network_firewall_hourly_rollups", ["ip_address"], unique=False)
    op.create_index(op.f("ix_network_firewall_hourly_rollups_device_id"), "network_firewall_hourly_rollups", ["device_id"], unique=False)
    op.create_index(op.f("ix_network_firewall_hourly_rollups_tracked_subject_id"), "network_firewall_hourly_rollups", ["tracked_subject_id"], unique=False)
    op.create_index(
        "ix_network_firewall_hourly_rollups_bucket_category",
        "network_firewall_hourly_rollups",
        ["bucket_start", "category"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_network_firewall_hourly_rollups_bucket_category", table_name="network_firewall_hourly_rollups")
    op.drop_index(op.f("ix_network_firewall_hourly_rollups_tracked_subject_id"), table_name="network_firewall_hourly_rollups")
    op.drop_index(op.f("ix_network_firewall_hourly_rollups_device_id"), table_name="network_firewall_hourly_rollups")
    op.drop_index(op.f("ix_network_firewall_hourly_rollups_ip_address"), table_name="network_firewall_hourly_rollups")
    op.drop_index(op.f("ix_network_firewall_hourly_rollups_dimension_key"), table_name="network_firewall_hourly_rollups")
    op.drop_index(op.f("ix_network_firewall_hourly_rollups_category"), table_name="network_firewall_hourly_rollups")
    op.drop_index(op.f("ix_network_firewall_hourly_rollups_bucket_start"), table_name="network_firewall_hourly_rollups")
    op.drop_index(op.f("ix_network_firewall_hourly_rollups_id"), table_name="network_firewall_hourly_rollups")
    op.drop_table("network_firewall_hourly_rollups")
