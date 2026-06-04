"""add sync job queue

Revision ID: 20260604_0115
Revises: 20260604_0114
Create Date: 2026-06-04 16:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0115"
down_revision = "20260604_0114"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
        sa.Column("profile", sa.String(length=20), nullable=False),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=True),
        sa.Column("persisted_users", sa.Integer(), nullable=False),
        sa.Column("persisted_groups", sa.Integer(), nullable=False),
        sa.Column("persisted_shares", sa.Integer(), nullable=False),
        sa.Column("persisted_permission_entries", sa.Integer(), nullable=False),
        sa.Column("persisted_effective_permissions", sa.Integer(), nullable=False),
        sa.Column("share_acl_pairs_used", sa.Integer(), nullable=False),
        sa.Column("worker_log_path", sa.String(length=500), nullable=True),
        sa.Column("worker_pid", sa.Integer(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("source_label", sa.String(length=120), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["snapshots.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sync_jobs_id"), "sync_jobs", ["id"], unique=False)
    op.create_index(op.f("ix_sync_jobs_profile"), "sync_jobs", ["profile"], unique=False)
    op.create_index(op.f("ix_sync_jobs_requested_by_user_id"), "sync_jobs", ["requested_by_user_id"], unique=False)
    op.create_index(op.f("ix_sync_jobs_snapshot_id"), "sync_jobs", ["snapshot_id"], unique=False)
    op.create_index(op.f("ix_sync_jobs_status"), "sync_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sync_jobs_status"), table_name="sync_jobs")
    op.drop_index(op.f("ix_sync_jobs_snapshot_id"), table_name="sync_jobs")
    op.drop_index(op.f("ix_sync_jobs_requested_by_user_id"), table_name="sync_jobs")
    op.drop_index(op.f("ix_sync_jobs_profile"), table_name="sync_jobs")
    op.drop_index(op.f("ix_sync_jobs_id"), table_name="sync_jobs")
    op.drop_table("sync_jobs")
