"""organigramma drafts and versions foundation

Revision ID: 20260611_0905
Revises: 20260609_0136
Create Date: 2026-06-11 09:05:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260611_0905"
down_revision = "20260609_0136"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "org_revision",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_revision_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("published_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_revision_id"], ["org_revision.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["published_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_org_revision_status"), "org_revision", ["status"], unique=False)

    op.create_table(
        "org_revision_unit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("logical_org_unit_id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("canvas_x", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("canvas_y", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manuale"),
        sa.Column("wc_area_id", sa.Uuid(), nullable=True),
        sa.Column("legacy_team_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["revision_id"], ["org_revision.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revision_id", "logical_org_unit_id", name="uq_org_revision_unit_revision_logical"),
    )
    op.create_index(op.f("ix_org_revision_unit_revision_id"), "org_revision_unit", ["revision_id"], unique=False)
    op.create_index(op.f("ix_org_revision_unit_logical_org_unit_id"), "org_revision_unit", ["logical_org_unit_id"], unique=False)
    op.create_index(op.f("ix_org_revision_unit_tipo"), "org_revision_unit", ["tipo"], unique=False)
    op.create_index(op.f("ix_org_revision_unit_parent_id"), "org_revision_unit", ["parent_id"], unique=False)

    op.create_table(
        "org_revision_assignment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("logical_org_assignment_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["revision_id"], ["org_revision.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revision_id", "logical_org_assignment_id", name="uq_org_revision_assignment_revision_logical"),
    )
    op.create_index(op.f("ix_org_revision_assignment_revision_id"), "org_revision_assignment", ["revision_id"], unique=False)
    op.create_index(op.f("ix_org_revision_assignment_logical_org_assignment_id"), "org_revision_assignment", ["logical_org_assignment_id"], unique=False)
    op.create_index(op.f("ix_org_revision_assignment_user_id"), "org_revision_assignment", ["user_id"], unique=False)
    op.create_index(op.f("ix_org_revision_assignment_org_unit_id"), "org_revision_assignment", ["org_unit_id"], unique=False)
    op.create_index(op.f("ix_org_revision_assignment_manager_user_id"), "org_revision_assignment", ["manager_user_id"], unique=False)

    op.create_table(
        "org_draft",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("base_revision_id", sa.Uuid(), nullable=False),
        sa.Column("working_revision_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("published_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["base_revision_id"], ["org_revision.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["working_revision_id"], ["org_revision.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["published_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("working_revision_id"),
    )
    op.create_index(op.f("ix_org_draft_status"), "org_draft", ["status"], unique=False)

    op.create_table(
        "org_change_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["org_draft.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_org_change_event_draft_id"), "org_change_event", ["draft_id"], unique=False)
    op.create_index(op.f("ix_org_change_event_entity_type"), "org_change_event", ["entity_type"], unique=False)
    op.create_index(op.f("ix_org_change_event_entity_id"), "org_change_event", ["entity_id"], unique=False)
    op.create_index(op.f("ix_org_change_event_action"), "org_change_event", ["action"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_org_change_event_action"), table_name="org_change_event")
    op.drop_index(op.f("ix_org_change_event_entity_id"), table_name="org_change_event")
    op.drop_index(op.f("ix_org_change_event_entity_type"), table_name="org_change_event")
    op.drop_index(op.f("ix_org_change_event_draft_id"), table_name="org_change_event")
    op.drop_table("org_change_event")

    op.drop_index(op.f("ix_org_draft_status"), table_name="org_draft")
    op.drop_table("org_draft")

    op.drop_index(op.f("ix_org_revision_assignment_manager_user_id"), table_name="org_revision_assignment")
    op.drop_index(op.f("ix_org_revision_assignment_org_unit_id"), table_name="org_revision_assignment")
    op.drop_index(op.f("ix_org_revision_assignment_user_id"), table_name="org_revision_assignment")
    op.drop_index(op.f("ix_org_revision_assignment_logical_org_assignment_id"), table_name="org_revision_assignment")
    op.drop_index(op.f("ix_org_revision_assignment_revision_id"), table_name="org_revision_assignment")
    op.drop_table("org_revision_assignment")

    op.drop_index(op.f("ix_org_revision_unit_parent_id"), table_name="org_revision_unit")
    op.drop_index(op.f("ix_org_revision_unit_tipo"), table_name="org_revision_unit")
    op.drop_index(op.f("ix_org_revision_unit_logical_org_unit_id"), table_name="org_revision_unit")
    op.drop_index(op.f("ix_org_revision_unit_revision_id"), table_name="org_revision_unit")
    op.drop_table("org_revision_unit")

    op.drop_index(op.f("ix_org_revision_status"), table_name="org_revision")
    op.drop_table("org_revision")
