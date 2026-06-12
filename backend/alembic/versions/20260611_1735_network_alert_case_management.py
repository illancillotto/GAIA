"""network alert case management

Revision ID: 20260611_1735
Revises: 20260611_1715
Create Date: 2026-06-11 17:35:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260611_1735"
down_revision = "20260611_1715"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("network_alerts", sa.Column("assigned_to_user_id", sa.Integer(), nullable=True))
    op.add_column("network_alerts", sa.Column("verification_status", sa.String(length=32), nullable=False, server_default="pending"))
    op.add_column("network_alerts", sa.Column("verification_notes", sa.Text(), nullable=True))
    op.add_column("network_alerts", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_network_alerts_assigned_to_user_id"), "network_alerts", ["assigned_to_user_id"], unique=False)
    op.create_index(op.f("ix_network_alerts_verification_status"), "network_alerts", ["verification_status"], unique=False)
    op.create_foreign_key(
        "fk_network_alerts_assigned_to_user_id_application_users",
        "network_alerts",
        "application_users",
        ["assigned_to_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_network_alerts_assigned_to_user_id_application_users", "network_alerts", type_="foreignkey")
    op.drop_index(op.f("ix_network_alerts_verification_status"), table_name="network_alerts")
    op.drop_index(op.f("ix_network_alerts_assigned_to_user_id"), table_name="network_alerts")
    op.drop_column("network_alerts", "reviewed_at")
    op.drop_column("network_alerts", "verification_notes")
    op.drop_column("network_alerts", "verification_status")
    op.drop_column("network_alerts", "assigned_to_user_id")
