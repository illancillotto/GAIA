"""org structure assignments

Revision ID: 20260608_0132
Revises: 20260608_0131
Create Date: 2026-06-08 23:55:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260608_0132"
down_revision = "20260608_0131"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "org_structure_assignment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_user_id", sa.Integer(), nullable=False),
        sa.Column("manager_user_id", sa.Integer(), nullable=True),
        sa.Column("source_mode", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column("area_label", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source_wc_operator_id", sa.Uuid(), nullable=True),
        sa.Column("source_wc_role", sa.String(length=120), nullable=True),
        sa.Column("source_chart_summary", sa.Text(), nullable=True),
        sa.Column("last_synced_from_source_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["application_user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_wc_operator_id"], ["wc_operator.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_user_id", name="uq_org_structure_assignment_application_user"),
    )
    op.create_index(op.f("ix_org_structure_assignment_application_user_id"), "org_structure_assignment", ["application_user_id"], unique=False)
    op.create_index(op.f("ix_org_structure_assignment_manager_user_id"), "org_structure_assignment", ["manager_user_id"], unique=False)
    op.create_index(op.f("ix_org_structure_assignment_source_wc_operator_id"), "org_structure_assignment", ["source_wc_operator_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_org_structure_assignment_source_wc_operator_id"), table_name="org_structure_assignment")
    op.drop_index(op.f("ix_org_structure_assignment_manager_user_id"), table_name="org_structure_assignment")
    op.drop_index(op.f("ix_org_structure_assignment_application_user_id"), table_name="org_structure_assignment")
    op.drop_table("org_structure_assignment")
