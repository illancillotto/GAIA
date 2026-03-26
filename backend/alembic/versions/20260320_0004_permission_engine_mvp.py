"""permission engine mvp

Revision ID: 20260320_0004
Revises: 20260320_0003
Create Date: 2026-03-20 01:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260320_0004"
down_revision = "20260320_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "permission_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("snapshots.id"), nullable=True),
        sa.Column("share_id", sa.Integer(), sa.ForeignKey("shares.id"), nullable=False),
        sa.Column("subject_type", sa.String(length=20), nullable=False),
        sa.Column("subject_name", sa.String(length=120), nullable=False),
        sa.Column("permission_level", sa.String(length=20), nullable=False),
        sa.Column("is_deny", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_system", sa.String(length=50), nullable=False, server_default="nas"),
        sa.Column("raw_reference", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_permission_entries_id", "permission_entries", ["id"], unique=False)

    op.create_table(
        "effective_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("snapshots.id"), nullable=True),
        sa.Column("nas_user_id", sa.Integer(), sa.ForeignKey("nas_users.id"), nullable=False),
        sa.Column("share_id", sa.Integer(), sa.ForeignKey("shares.id"), nullable=False),
        sa.Column("can_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_write", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_denied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_summary", sa.String(length=255), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_effective_permissions_id", "effective_permissions", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_effective_permissions_id", table_name="effective_permissions")
    op.drop_table("effective_permissions")
    op.drop_index("ix_permission_entries_id", table_name="permission_entries")
    op.drop_table("permission_entries")
