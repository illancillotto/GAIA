"""add network sophos runtime config

Revision ID: 20260617_0900
Revises: 20260616_1800
Create Date: 2026-06-17 09:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260617_0900"
down_revision = "20260616_1800"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "network_sophos_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("syslog_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("snmp_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("operation_window_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("operation_start_hour", sa.Integer(), nullable=False, server_default="19"),
        sa.Column("operation_end_hour", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("operation_timezone", sa.String(length=64), nullable=False, server_default="Europe/Rome"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["application_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.alter_column("network_sophos_config", "syslog_enabled", server_default=None)
    op.alter_column("network_sophos_config", "snmp_enabled", server_default=None)
    op.alter_column("network_sophos_config", "operation_window_enabled", server_default=None)
    op.alter_column("network_sophos_config", "operation_start_hour", server_default=None)
    op.alter_column("network_sophos_config", "operation_end_hour", server_default=None)
    op.alter_column("network_sophos_config", "operation_timezone", server_default=None)


def downgrade() -> None:
    op.drop_table("network_sophos_config")
