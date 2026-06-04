"""add inaz owner user scope

Revision ID: 20260604_0110
Revises: 20260604_0109
Create Date: 2026-06-04 10:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0110"
down_revision = "20260604_0109"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inaz_collaborators", sa.Column("owner_user_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_inaz_collaborators_owner_user_id"), "inaz_collaborators", ["owner_user_id"], unique=False)
    op.create_foreign_key(
        "fk_inaz_collaborators_owner_user_id_application_users",
        "inaz_collaborators",
        "application_users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("inaz_daily_records", sa.Column("owner_user_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_inaz_daily_records_owner_user_id"), "inaz_daily_records", ["owner_user_id"], unique=False)
    op.create_foreign_key(
        "fk_inaz_daily_records_owner_user_id_application_users",
        "inaz_daily_records",
        "application_users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("inaz_event_summaries", sa.Column("owner_user_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_inaz_event_summaries_owner_user_id"), "inaz_event_summaries", ["owner_user_id"], unique=False)
    op.create_foreign_key(
        "fk_inaz_event_summaries_owner_user_id_application_users",
        "inaz_event_summaries",
        "application_users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        UPDATE inaz_daily_records AS record
        SET owner_user_id = job.requested_by_user_id
        FROM inaz_import_jobs AS job
        WHERE record.source_job_id = job.id
          AND record.owner_user_id IS NULL
        """
    )

    op.execute(
        """
        UPDATE inaz_event_summaries AS summary
        SET owner_user_id = job.requested_by_user_id
        FROM inaz_import_jobs AS job
        WHERE summary.source_job_id = job.id
          AND summary.owner_user_id IS NULL
        """
    )

    op.execute(
        """
        UPDATE inaz_collaborators AS collaborator
        SET owner_user_id = scoped.owner_user_id
        FROM (
            SELECT collaborator_id, max(owner_user_id) AS owner_user_id
            FROM inaz_daily_records
            WHERE owner_user_id IS NOT NULL
            GROUP BY collaborator_id
        ) AS scoped
        WHERE collaborator.id = scoped.collaborator_id
          AND collaborator.owner_user_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_inaz_event_summaries_owner_user_id_application_users", "inaz_event_summaries", type_="foreignkey")
    op.drop_index(op.f("ix_inaz_event_summaries_owner_user_id"), table_name="inaz_event_summaries")
    op.drop_column("inaz_event_summaries", "owner_user_id")

    op.drop_constraint("fk_inaz_daily_records_owner_user_id_application_users", "inaz_daily_records", type_="foreignkey")
    op.drop_index(op.f("ix_inaz_daily_records_owner_user_id"), table_name="inaz_daily_records")
    op.drop_column("inaz_daily_records", "owner_user_id")

    op.drop_constraint("fk_inaz_collaborators_owner_user_id_application_users", "inaz_collaborators", type_="foreignkey")
    op.drop_index(op.f("ix_inaz_collaborators_owner_user_id"), table_name="inaz_collaborators")
    op.drop_column("inaz_collaborators", "owner_user_id")
