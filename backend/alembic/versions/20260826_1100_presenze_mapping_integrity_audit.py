"""Make Presenze identity mappings unique and auditable.

Revision ID: 20260826_1100
Revises: 20260826_1000
"""

import sqlalchemy as sa

from alembic import op

revision = "20260826_1100"
down_revision = "20260826_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_presenze_collaborators_application_user_id",
        "presenze_collaborators",
        ["application_user_id"],
        unique=True,
        postgresql_where=sa.text("application_user_id IS NOT NULL"),
    )
    op.create_table(
        "presenze_collaborator_mapping_audit",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("collaborator_id", sa.Uuid(), nullable=False),
        sa.Column("previous_application_user_id", sa.Integer(), nullable=True),
        sa.Column("new_application_user_id", sa.Integer(), nullable=True),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("changed_by_username", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"], ["application_users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["collaborator_id"], ["presenze_collaborators.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_presenze_collaborator_mapping_audit_changed_by_user_id",
        "presenze_collaborator_mapping_audit",
        ["changed_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_presenze_collaborator_mapping_audit_collaborator_id",
        "presenze_collaborator_mapping_audit",
        ["collaborator_id"],
        unique=False,
    )
    op.create_index(
        "ix_presenze_collaborator_mapping_audit_created_at",
        "presenze_collaborator_mapping_audit",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_presenze_collaborator_mapping_audit_created_at",
        table_name="presenze_collaborator_mapping_audit",
    )
    op.drop_index(
        "ix_presenze_collaborator_mapping_audit_collaborator_id",
        table_name="presenze_collaborator_mapping_audit",
    )
    op.drop_index(
        "ix_presenze_collaborator_mapping_audit_changed_by_user_id",
        table_name="presenze_collaborator_mapping_audit",
    )
    op.drop_table("presenze_collaborator_mapping_audit")
    op.drop_index(
        "uq_presenze_collaborators_application_user_id",
        table_name="presenze_collaborators",
    )
