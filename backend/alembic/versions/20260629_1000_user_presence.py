"""add user presence table

Revision ID: 20260629_1000
Revises: 20260626_1300
Create Date: 2026-06-29 10:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260629_1000"
down_revision = "20260626_1300"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_presence",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_path", sa.String(length=512), nullable=False),
        sa.Column("last_route_label", sa.String(length=255), nullable=True),
        sa.Column("last_module_key", sa.String(length=64), nullable=True),
        sa.Column("last_visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_ip", sa.String(length=64), nullable=True),
        sa.Column("last_user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(op.f("ix_user_presence_last_module_key"), "user_presence", ["last_module_key"], unique=False)
    op.create_index(op.f("ix_user_presence_last_seen_at"), "user_presence", ["last_seen_at"], unique=False)
    op.alter_column("user_presence", "last_visible", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_presence_last_seen_at"), table_name="user_presence")
    op.drop_index(op.f("ix_user_presence_last_module_key"), table_name="user_presence")
    op.drop_table("user_presence")
