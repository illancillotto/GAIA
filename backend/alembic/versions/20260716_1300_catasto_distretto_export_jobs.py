"""catasto distretto export jobs

Revision ID: 20260716_1300
Revises: 20260715_0900
Create Date: 2026-07-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260716_1300"
down_revision = "20260715_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catasto_distretto_export_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("application_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("num_distretto", sa.String(length=32), nullable=False),
        sa.Column("nome_distretto", sa.String(length=200), nullable=True),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_label", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("output_filename", sa.String(length=255), nullable=True),
        sa.Column("output_path", sa.String(length=1024), nullable=True),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_catasto_distretto_export_jobs_user_id", "catasto_distretto_export_jobs", ["user_id"])
    op.create_index("ix_catasto_distretto_export_jobs_num_distretto", "catasto_distretto_export_jobs", ["num_distretto"])
    op.create_index("ix_catasto_distretto_export_jobs_status", "catasto_distretto_export_jobs", ["status"])
    op.create_index("ix_catasto_distretto_export_jobs_created_at", "catasto_distretto_export_jobs", ["created_at"])
    op.alter_column("catasto_distretto_export_jobs", "status", server_default=None)
    op.alter_column("catasto_distretto_export_jobs", "total_rows", server_default=None)
    op.alter_column("catasto_distretto_export_jobs", "processed_rows", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_catasto_distretto_export_jobs_created_at", table_name="catasto_distretto_export_jobs")
    op.drop_index("ix_catasto_distretto_export_jobs_status", table_name="catasto_distretto_export_jobs")
    op.drop_index("ix_catasto_distretto_export_jobs_num_distretto", table_name="catasto_distretto_export_jobs")
    op.drop_index("ix_catasto_distretto_export_jobs_user_id", table_name="catasto_distretto_export_jobs")
    op.drop_table("catasto_distretto_export_jobs")
