"""add capacitas particelle sync jobs

Revision ID: 20260427_0065
Revises: 20260427_0064
Create Date: 2026-04-27 11:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260427_0065"
down_revision = "20260427_0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capacitas_particelle_sync_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=True),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["credential_id"], ["capacitas_credentials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_capacitas_particelle_sync_jobs_credential_id"),
        "capacitas_particelle_sync_jobs",
        ["credential_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_capacitas_particelle_sync_jobs_requested_by_user_id"),
        "capacitas_particelle_sync_jobs",
        ["requested_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_capacitas_particelle_sync_jobs_status"),
        "capacitas_particelle_sync_jobs",
        ["status"],
        unique=False,
    )

    op.add_column("cat_particelle", sa.Column("capacitas_last_sync_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cat_particelle", sa.Column("capacitas_last_sync_status", sa.String(length=32), nullable=True))
    op.add_column("cat_particelle", sa.Column("capacitas_last_sync_error", sa.Text(), nullable=True))
    op.add_column("cat_particelle", sa.Column("capacitas_last_sync_job_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_cat_particelle_capacitas_last_sync_at"), "cat_particelle", ["capacitas_last_sync_at"], unique=False)
    op.create_index(
        op.f("ix_cat_particelle_capacitas_last_sync_status"),
        "cat_particelle",
        ["capacitas_last_sync_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cat_particelle_capacitas_last_sync_job_id"),
        "cat_particelle",
        ["capacitas_last_sync_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_cat_particelle_capacitas_last_sync_job_id"), table_name="cat_particelle")
    op.drop_index(op.f("ix_cat_particelle_capacitas_last_sync_status"), table_name="cat_particelle")
    op.drop_index(op.f("ix_cat_particelle_capacitas_last_sync_at"), table_name="cat_particelle")
    op.drop_column("cat_particelle", "capacitas_last_sync_job_id")
    op.drop_column("cat_particelle", "capacitas_last_sync_error")
    op.drop_column("cat_particelle", "capacitas_last_sync_status")
    op.drop_column("cat_particelle", "capacitas_last_sync_at")

    op.drop_index(op.f("ix_capacitas_particelle_sync_jobs_status"), table_name="capacitas_particelle_sync_jobs")
    op.drop_index(
        op.f("ix_capacitas_particelle_sync_jobs_requested_by_user_id"),
        table_name="capacitas_particelle_sync_jobs",
    )
    op.drop_index(op.f("ix_capacitas_particelle_sync_jobs_credential_id"), table_name="capacitas_particelle_sync_jobs")
    op.drop_table("capacitas_particelle_sync_jobs")
