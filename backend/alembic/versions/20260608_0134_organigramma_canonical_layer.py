"""organigramma canonical layer

Revision ID: 20260608_0134
Revises: 20260608_0133
Create Date: 2026-06-08 23:59:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260608_0134"
down_revision = "20260608_0133"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application_users",
        sa.Column("module_organigramma", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "org_unit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manuale"),
        sa.Column("wc_area_id", sa.Uuid(), nullable=True),
        sa.Column("legacy_team_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["org_unit.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["wc_area_id"], ["wc_area.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["legacy_team_id"], ["team.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_org_unit_nome"), "org_unit", ["nome"], unique=False)
    op.create_index(op.f("ix_org_unit_tipo"), "org_unit", ["tipo"], unique=False)
    op.create_index(op.f("ix_org_unit_parent_id"), "org_unit", ["parent_id"], unique=False)

    op.create_table(
        "org_assignment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("org_unit_id", sa.Uuid(), nullable=False),
        sa.Column("manager_user_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=150), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manuale"),
        sa.Column("wc_operator_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_unit_id"], ["org_unit.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["wc_operator_id"], ["wc_operator.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_org_assignment_user_id"), "org_assignment", ["user_id"], unique=False)
    op.create_index(op.f("ix_org_assignment_org_unit_id"), "org_assignment", ["org_unit_id"], unique=False)
    op.create_index(op.f("ix_org_assignment_manager_user_id"), "org_assignment", ["manager_user_id"], unique=False)

    op.create_table(
        "org_visibility_override",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("viewer_user_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("target_org_unit_id", sa.Uuid(), nullable=True),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["viewer_user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_org_unit_id"], ["org_unit.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_org_visibility_override_viewer_user_id"), "org_visibility_override", ["viewer_user_id"], unique=False)

    op.create_table(
        "org_source_link",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("org_unit_id", sa.Uuid(), nullable=True),
        sa.Column("org_assignment_id", sa.Uuid(), nullable=True),
        sa.Column("source_system", sa.String(length=30), nullable=False, server_default="whitecompany"),
        sa.Column("wc_area_id", sa.Uuid(), nullable=True),
        sa.Column("wc_operator_id", sa.Uuid(), nullable=True),
        sa.Column("wc_org_chart_entry_id", sa.Uuid(), nullable=True),
        sa.Column("external_wc_id", sa.Integer(), nullable=True),
        sa.Column("is_manual_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["org_unit_id"], ["org_unit.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_assignment_id"], ["org_assignment.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wc_area_id"], ["wc_area.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["wc_operator_id"], ["wc_operator.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["wc_org_chart_entry_id"], ["wc_org_chart_entry.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entity_type",
            "source_system",
            "external_wc_id",
            name="uq_org_source_link_entity_source_external",
        ),
    )
    op.create_index(op.f("ix_org_source_link_external_wc_id"), "org_source_link", ["external_wc_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_org_source_link_external_wc_id"), table_name="org_source_link")
    op.drop_table("org_source_link")

    op.drop_index(op.f("ix_org_visibility_override_viewer_user_id"), table_name="org_visibility_override")
    op.drop_table("org_visibility_override")

    op.drop_index(op.f("ix_org_assignment_manager_user_id"), table_name="org_assignment")
    op.drop_index(op.f("ix_org_assignment_org_unit_id"), table_name="org_assignment")
    op.drop_index(op.f("ix_org_assignment_user_id"), table_name="org_assignment")
    op.drop_table("org_assignment")

    op.drop_index(op.f("ix_org_unit_parent_id"), table_name="org_unit")
    op.drop_index(op.f("ix_org_unit_tipo"), table_name="org_unit")
    op.drop_index(op.f("ix_org_unit_nome"), table_name="org_unit")
    op.drop_table("org_unit")

    op.drop_column("application_users", "module_organigramma")
