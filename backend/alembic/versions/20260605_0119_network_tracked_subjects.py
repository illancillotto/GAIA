"""network tracked subjects

Revision ID: 20260605_0119
Revises: 20260605_0118
Create Date: 2026-06-05 18:05:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_0119"
down_revision: str | None = "20260605_0118"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "network_tracked_subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("normalized_value", sa.String(length=1024), nullable=False),
        sa.Column("value", sa.String(length=1024), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["device_id"], ["network_devices.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "normalized_value", name="uq_network_tracked_subjects_type_value"),
    )
    op.create_index(op.f("ix_network_tracked_subjects_id"), "network_tracked_subjects", ["id"], unique=False)
    op.create_index(op.f("ix_network_tracked_subjects_entity_type"), "network_tracked_subjects", ["entity_type"], unique=False)
    op.create_index(op.f("ix_network_tracked_subjects_normalized_value"), "network_tracked_subjects", ["normalized_value"], unique=False)
    op.create_index(op.f("ix_network_tracked_subjects_is_active"), "network_tracked_subjects", ["is_active"], unique=False)
    op.create_index(op.f("ix_network_tracked_subjects_device_id"), "network_tracked_subjects", ["device_id"], unique=False)
    op.create_index(op.f("ix_network_tracked_subjects_created_by_user_id"), "network_tracked_subjects", ["created_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_network_tracked_subjects_created_by_user_id"), table_name="network_tracked_subjects")
    op.drop_index(op.f("ix_network_tracked_subjects_device_id"), table_name="network_tracked_subjects")
    op.drop_index(op.f("ix_network_tracked_subjects_is_active"), table_name="network_tracked_subjects")
    op.drop_index(op.f("ix_network_tracked_subjects_normalized_value"), table_name="network_tracked_subjects")
    op.drop_index(op.f("ix_network_tracked_subjects_entity_type"), table_name="network_tracked_subjects")
    op.drop_index(op.f("ix_network_tracked_subjects_id"), table_name="network_tracked_subjects")
    op.drop_table("network_tracked_subjects")
