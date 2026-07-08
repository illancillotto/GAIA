"""add organization teams for gate presenze

Revision ID: 20260708_1700
Revises: 20260708_1030
Create Date: 2026-07-08 17:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260708_1700"
down_revision = "20260708_1030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_teams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_from_channel", sa.String(length=32), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "scope", name="uq_organization_teams_code_scope"),
    )
    op.create_index(op.f("ix_organization_teams_active"), "organization_teams", ["active"], unique=False)
    op.create_index(op.f("ix_organization_teams_code"), "organization_teams", ["code"], unique=False)
    op.create_index(op.f("ix_organization_teams_created_by_user_id"), "organization_teams", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_organization_teams_created_from_channel"), "organization_teams", ["created_from_channel"], unique=False)
    op.create_index(op.f("ix_organization_teams_name"), "organization_teams", ["name"], unique=False)
    op.create_index(op.f("ix_organization_teams_scope"), "organization_teams", ["scope"], unique=False)

    op.create_table(
        "organization_team_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("collaborator_id", sa.Uuid(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("source_channel", sa.String(length=32), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["collaborator_id"], ["presenze_collaborators.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["organization_teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "team_id",
            "collaborator_id",
            "valid_from",
            "valid_to",
            name="uq_organization_team_memberships_exact_period",
        ),
    )
    op.create_index(op.f("ix_organization_team_memberships_collaborator_id"), "organization_team_memberships", ["collaborator_id"], unique=False)
    op.create_index(op.f("ix_organization_team_memberships_created_by_user_id"), "organization_team_memberships", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_organization_team_memberships_role"), "organization_team_memberships", ["role"], unique=False)
    op.create_index(op.f("ix_organization_team_memberships_source_channel"), "organization_team_memberships", ["source_channel"], unique=False)
    op.create_index(op.f("ix_organization_team_memberships_team_id"), "organization_team_memberships", ["team_id"], unique=False)
    op.create_index(op.f("ix_organization_team_memberships_valid_from"), "organization_team_memberships", ["valid_from"], unique=False)
    op.create_index(op.f("ix_organization_team_memberships_valid_to"), "organization_team_memberships", ["valid_to"], unique=False)

    op.create_table(
        "organization_team_supervisor_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("application_user_id", sa.Integer(), nullable=False),
        sa.Column("permission_scope", sa.String(length=32), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("source_channel", sa.String(length=32), nullable=False),
        sa.Column("assigned_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["application_user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["organization_teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "team_id",
            "application_user_id",
            "permission_scope",
            "valid_from",
            "valid_to",
            name="uq_organization_team_supervisors_exact_period",
        ),
    )
    op.create_index(op.f("ix_organization_team_supervisor_assignments_application_user_id"), "organization_team_supervisor_assignments", ["application_user_id"], unique=False)
    op.create_index(op.f("ix_organization_team_supervisor_assignments_assigned_by_user_id"), "organization_team_supervisor_assignments", ["assigned_by_user_id"], unique=False)
    op.create_index(op.f("ix_organization_team_supervisor_assignments_permission_scope"), "organization_team_supervisor_assignments", ["permission_scope"], unique=False)
    op.create_index(op.f("ix_organization_team_supervisor_assignments_source_channel"), "organization_team_supervisor_assignments", ["source_channel"], unique=False)
    op.create_index(op.f("ix_organization_team_supervisor_assignments_team_id"), "organization_team_supervisor_assignments", ["team_id"], unique=False)
    op.create_index(op.f("ix_organization_team_supervisor_assignments_valid_from"), "organization_team_supervisor_assignments", ["valid_from"], unique=False)
    op.create_index(op.f("ix_organization_team_supervisor_assignments_valid_to"), "organization_team_supervisor_assignments", ["valid_to"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_organization_team_supervisor_assignments_valid_to"), table_name="organization_team_supervisor_assignments")
    op.drop_index(op.f("ix_organization_team_supervisor_assignments_valid_from"), table_name="organization_team_supervisor_assignments")
    op.drop_index(op.f("ix_organization_team_supervisor_assignments_team_id"), table_name="organization_team_supervisor_assignments")
    op.drop_index(op.f("ix_organization_team_supervisor_assignments_source_channel"), table_name="organization_team_supervisor_assignments")
    op.drop_index(op.f("ix_organization_team_supervisor_assignments_permission_scope"), table_name="organization_team_supervisor_assignments")
    op.drop_index(op.f("ix_organization_team_supervisor_assignments_assigned_by_user_id"), table_name="organization_team_supervisor_assignments")
    op.drop_index(op.f("ix_organization_team_supervisor_assignments_application_user_id"), table_name="organization_team_supervisor_assignments")
    op.drop_table("organization_team_supervisor_assignments")

    op.drop_index(op.f("ix_organization_team_memberships_valid_to"), table_name="organization_team_memberships")
    op.drop_index(op.f("ix_organization_team_memberships_valid_from"), table_name="organization_team_memberships")
    op.drop_index(op.f("ix_organization_team_memberships_team_id"), table_name="organization_team_memberships")
    op.drop_index(op.f("ix_organization_team_memberships_source_channel"), table_name="organization_team_memberships")
    op.drop_index(op.f("ix_organization_team_memberships_role"), table_name="organization_team_memberships")
    op.drop_index(op.f("ix_organization_team_memberships_created_by_user_id"), table_name="organization_team_memberships")
    op.drop_index(op.f("ix_organization_team_memberships_collaborator_id"), table_name="organization_team_memberships")
    op.drop_table("organization_team_memberships")

    op.drop_index(op.f("ix_organization_teams_scope"), table_name="organization_teams")
    op.drop_index(op.f("ix_organization_teams_name"), table_name="organization_teams")
    op.drop_index(op.f("ix_organization_teams_created_from_channel"), table_name="organization_teams")
    op.drop_index(op.f("ix_organization_teams_created_by_user_id"), table_name="organization_teams")
    op.drop_index(op.f("ix_organization_teams_code"), table_name="organization_teams")
    op.drop_index(op.f("ix_organization_teams_active"), table_name="organization_teams")
    op.drop_table("organization_teams")
