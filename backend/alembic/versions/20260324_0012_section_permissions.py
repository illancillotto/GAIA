"""create section permission tables

Revision ID: 20260324_0012
Revises: 20260324_0011
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260324_0012"
down_revision = "20260324_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("module", sa.String(length=50), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False, unique=True),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("min_role", sa.String(length=32), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "role_section_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_granted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_by_id", sa.Integer(), sa.ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("section_id", "role", name="uq_role_section_permissions_section_role"),
    )

    op.create_table(
        "user_section_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("application_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_granted", sa.Boolean(), nullable=False),
        sa.Column("granted_by_id", sa.Integer(), sa.ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "section_id", name="uq_user_section_permissions_user_section"),
    )


def downgrade() -> None:
    op.drop_table("user_section_permissions")
    op.drop_table("role_section_permissions")
    op.drop_table("sections")
