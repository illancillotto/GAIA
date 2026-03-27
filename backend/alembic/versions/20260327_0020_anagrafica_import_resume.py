"""anagrafica import resume tracking

Revision ID: 20260327_0020
Revises: 20260327_0019
Create Date: 2026-03-27 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_0020"
down_revision = "20260327_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ana_import_job_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("letter", sa.String(length=32), nullable=True),
        sa.Column("folder_name", sa.String(length=512), nullable=False),
        sa.Column("nas_folder_path", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("documents_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("documents_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["ana_import_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "nas_folder_path", name="uq_ana_import_job_items_job_path"),
    )
    op.create_index(op.f("ix_ana_import_job_items_job_id"), "ana_import_job_items", ["job_id"], unique=False)
    op.create_index(op.f("ix_ana_import_job_items_subject_id"), "ana_import_job_items", ["subject_id"], unique=False)
    op.create_index(op.f("ix_ana_import_job_items_letter"), "ana_import_job_items", ["letter"], unique=False)
    op.create_index(op.f("ix_ana_import_job_items_status"), "ana_import_job_items", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ana_import_job_items_status"), table_name="ana_import_job_items")
    op.drop_index(op.f("ix_ana_import_job_items_letter"), table_name="ana_import_job_items")
    op.drop_index(op.f("ix_ana_import_job_items_subject_id"), table_name="ana_import_job_items")
    op.drop_index(op.f("ix_ana_import_job_items_job_id"), table_name="ana_import_job_items")
    op.drop_table("ana_import_job_items")
