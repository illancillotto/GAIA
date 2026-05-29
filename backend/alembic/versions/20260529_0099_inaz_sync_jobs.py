"""inaz sync jobs

Revision ID: 20260529_0099
Revises: 20260529_0098
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260529_0099"
down_revision = "20260529_0098"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inaz_sync_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
        sa.Column("import_job_id", sa.Uuid(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("collaborator_limit", sa.Integer(), nullable=True),
        sa.Column("records_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("json_artifact_path", sa.String(length=500), nullable=True),
        sa.Column("worker_log_path", sa.String(length=500), nullable=True),
        sa.Column("worker_pid", sa.Integer(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("params_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["import_job_id"], ["inaz_import_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inaz_sync_jobs_status"), "inaz_sync_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_inaz_sync_jobs_requested_by_user_id"), "inaz_sync_jobs", ["requested_by_user_id"], unique=False)
    op.create_index(op.f("ix_inaz_sync_jobs_import_job_id"), "inaz_sync_jobs", ["import_job_id"], unique=False)
    op.create_index(op.f("ix_inaz_sync_jobs_period_start"), "inaz_sync_jobs", ["period_start"], unique=False)
    op.create_index(op.f("ix_inaz_sync_jobs_period_end"), "inaz_sync_jobs", ["period_end"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_inaz_sync_jobs_period_end"), table_name="inaz_sync_jobs")
    op.drop_index(op.f("ix_inaz_sync_jobs_period_start"), table_name="inaz_sync_jobs")
    op.drop_index(op.f("ix_inaz_sync_jobs_import_job_id"), table_name="inaz_sync_jobs")
    op.drop_index(op.f("ix_inaz_sync_jobs_requested_by_user_id"), table_name="inaz_sync_jobs")
    op.drop_index(op.f("ix_inaz_sync_jobs_status"), table_name="inaz_sync_jobs")
    op.drop_table("inaz_sync_jobs")
