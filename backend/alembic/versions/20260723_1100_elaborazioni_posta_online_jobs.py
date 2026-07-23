"""elaborazioni posta online credentials and jobs

Revision ID: 20260723_1100
Revises: 20260723_0900
Create Date: 2026-07-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260723_1100"
down_revision = "20260723_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "posta_online_credentials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("allowed_hours_start", sa.Integer(), nullable=False),
        sa.Column("allowed_hours_end", sa.Integer(), nullable=False),
        sa.Column("min_delay_ms", sa.Integer(), nullable=False),
        sa.Column("max_delay_ms", sa.Integer(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_posta_online_credentials_active", "posta_online_credentials", ["active"])

    op.create_table(
        "posta_online_registered_mail_sync_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=True),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["credential_id"], ["posta_online_credentials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_posta_online_registered_mail_sync_jobs_credential_id", "posta_online_registered_mail_sync_jobs", ["credential_id"])
    op.create_index("ix_posta_online_registered_mail_sync_jobs_requested_by_user_id", "posta_online_registered_mail_sync_jobs", ["requested_by_user_id"])
    op.create_index("ix_posta_online_registered_mail_sync_jobs_status", "posta_online_registered_mail_sync_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_posta_online_registered_mail_sync_jobs_status", table_name="posta_online_registered_mail_sync_jobs")
    op.drop_index("ix_posta_online_registered_mail_sync_jobs_requested_by_user_id", table_name="posta_online_registered_mail_sync_jobs")
    op.drop_index("ix_posta_online_registered_mail_sync_jobs_credential_id", table_name="posta_online_registered_mail_sync_jobs")
    op.drop_table("posta_online_registered_mail_sync_jobs")
    op.drop_index("ix_posta_online_credentials_active", table_name="posta_online_credentials")
    op.drop_table("posta_online_credentials")
