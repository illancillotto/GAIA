"""Use canonical GAIA users for organization team memberships.

Revision ID: 20260902_1200
Revises: 20260902_1100
"""

import sqlalchemy as sa

from alembic import op

revision = "20260902_1200"
down_revision = "20260902_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organization_team_memberships",
        sa.Column("application_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_organization_team_memberships_application_user_id",
        "organization_team_memberships",
        "application_users",
        ["application_user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_organization_team_memberships_application_user_id",
        "organization_team_memberships",
        ["application_user_id"],
    )
    op.execute(
        """
        UPDATE organization_team_memberships AS membership
        SET application_user_id = collaborator.application_user_id
        FROM presenze_collaborators AS collaborator
        WHERE collaborator.id = membership.collaborator_id
          AND collaborator.application_user_id IS NOT NULL
        """
    )
    op.drop_constraint(
        "organization_team_memberships_collaborator_id_fkey",
        "organization_team_memberships",
        type_="foreignkey",
    )
    op.alter_column("organization_team_memberships", "collaborator_id", nullable=True)
    op.create_foreign_key(
        "fk_organization_team_memberships_collaborator_id",
        "organization_team_memberships",
        "presenze_collaborators",
        ["collaborator_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_organization_team_memberships_user_period",
        "organization_team_memberships",
        ["team_id", "application_user_id", "valid_from", "valid_to"],
    )
    op.create_check_constraint(
        "ck_organization_team_memberships_identity",
        "organization_team_memberships",
        "application_user_id IS NOT NULL OR collaborator_id IS NOT NULL",
    )


def downgrade() -> None:
    connection = op.get_bind()
    missing_collaborators = connection.scalar(
        sa.text("SELECT count(*) FROM organization_team_memberships WHERE collaborator_id IS NULL")
    )
    if missing_collaborators:
        raise RuntimeError(
            "organization_team_memberships contiene membri senza relazione Presenze; "
            "ripristinare collaborator_id prima del downgrade"
        )
    op.drop_constraint(
        "ck_organization_team_memberships_identity",
        "organization_team_memberships",
        type_="check",
    )
    op.drop_constraint(
        "uq_organization_team_memberships_user_period",
        "organization_team_memberships",
        type_="unique",
    )
    op.drop_constraint(
        "fk_organization_team_memberships_collaborator_id",
        "organization_team_memberships",
        type_="foreignkey",
    )
    op.alter_column("organization_team_memberships", "collaborator_id", nullable=False)
    op.create_foreign_key(
        "organization_team_memberships_collaborator_id_fkey",
        "organization_team_memberships",
        "presenze_collaborators",
        ["collaborator_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_index(
        "ix_organization_team_memberships_application_user_id",
        table_name="organization_team_memberships",
    )
    op.drop_constraint(
        "fk_organization_team_memberships_application_user_id",
        "organization_team_memberships",
        type_="foreignkey",
    )
    op.drop_column("organization_team_memberships", "application_user_id")
