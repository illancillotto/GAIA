"""add network device to application user mapping

Revision ID: 20260604_0111
Revises: 20260604_0110
Create Date: 2026-06-04 12:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0111"
down_revision = "20260604_0110"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("application_users", sa.Column("full_name", sa.String(length=255), nullable=True))
    op.add_column("application_users", sa.Column("office_location", sa.String(length=255), nullable=True))
    op.add_column("application_users", sa.Column("phone_extension", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_application_users_full_name"), "application_users", ["full_name"], unique=False)

    op.add_column("network_devices", sa.Column("assigned_user_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_network_devices_assigned_user_id"), "network_devices", ["assigned_user_id"], unique=False)
    op.create_foreign_key(
        "fk_network_devices_assigned_user_id_application_users",
        "network_devices",
        "application_users",
        ["assigned_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_network_devices_assigned_user_id_application_users", "network_devices", type_="foreignkey")
    op.drop_index(op.f("ix_network_devices_assigned_user_id"), table_name="network_devices")
    op.drop_column("network_devices", "assigned_user_id")

    op.drop_index(op.f("ix_application_users_full_name"), table_name="application_users")
    op.drop_column("application_users", "phone_extension")
    op.drop_column("application_users", "office_location")
    op.drop_column("application_users", "full_name")
