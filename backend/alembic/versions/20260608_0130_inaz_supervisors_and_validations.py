"""inaz supervisors and daily validations

Revision ID: 20260608_0130
Revises: 20260608_0129
Create Date: 2026-06-08 21:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260608_0130"
down_revision = "20260608_0129"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inaz_supervisor_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("supervisor_user_id", sa.Integer(), nullable=False),
        sa.Column("collaborator_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["collaborator_id"], ["inaz_collaborators.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supervisor_user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collaborator_id", name="uq_inaz_supervisor_assignments_collaborator"),
    )
    op.create_index(
        op.f("ix_inaz_supervisor_assignments_supervisor_user_id"),
        "inaz_supervisor_assignments",
        ["supervisor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inaz_supervisor_assignments_collaborator_id"),
        "inaz_supervisor_assignments",
        ["collaborator_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inaz_supervisor_assignments_assigned_by_user_id"),
        "inaz_supervisor_assignments",
        ["assigned_by_user_id"],
        unique=False,
    )

    op.add_column(
        "inaz_daily_records",
        sa.Column("validation_status", sa.String(length=32), nullable=False, server_default="pending"),
    )
    op.add_column("inaz_daily_records", sa.Column("validated_by_user_id", sa.Integer(), nullable=True))
    op.add_column("inaz_daily_records", sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("inaz_daily_records", sa.Column("validation_note", sa.Text(), nullable=True))
    op.create_index(
        op.f("ix_inaz_daily_records_validation_status"),
        "inaz_daily_records",
        ["validation_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inaz_daily_records_validated_by_user_id"),
        "inaz_daily_records",
        ["validated_by_user_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_inaz_daily_records_validated_by_user_id_application_users",
        "inaz_daily_records",
        "application_users",
        ["validated_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute("UPDATE inaz_daily_records SET validation_status = 'pending' WHERE validation_status IS NULL")
    op.alter_column("inaz_daily_records", "validation_status", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "fk_inaz_daily_records_validated_by_user_id_application_users",
        "inaz_daily_records",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_inaz_daily_records_validated_by_user_id"), table_name="inaz_daily_records")
    op.drop_index(op.f("ix_inaz_daily_records_validation_status"), table_name="inaz_daily_records")
    op.drop_column("inaz_daily_records", "validation_note")
    op.drop_column("inaz_daily_records", "validated_at")
    op.drop_column("inaz_daily_records", "validated_by_user_id")
    op.drop_column("inaz_daily_records", "validation_status")

    op.drop_index(
        op.f("ix_inaz_supervisor_assignments_assigned_by_user_id"),
        table_name="inaz_supervisor_assignments",
    )
    op.drop_index(
        op.f("ix_inaz_supervisor_assignments_collaborator_id"),
        table_name="inaz_supervisor_assignments",
    )
    op.drop_index(
        op.f("ix_inaz_supervisor_assignments_supervisor_user_id"),
        table_name="inaz_supervisor_assignments",
    )
    op.drop_table("inaz_supervisor_assignments")
