"""utenze: add anpr role batch runs and hourly defaults

Revision ID: 20260515_0082
Revises: 20260514_0081
Create Date: 2026-05-15 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260515_0082"
down_revision = "20260514_0081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anpr_job_runs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("ruolo_year", sa.Integer(), nullable=False),
        sa.Column("triggered_by", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("batch_size", sa.Integer(), nullable=False),
        sa.Column("hard_daily_limit", sa.Integer(), nullable=False),
        sa.Column("configured_daily_limit", sa.Integer(), nullable=False),
        sa.Column("daily_calls_before", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("daily_calls_after", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("subjects_selected", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("subjects_processed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("deceased_found", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("errors", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("calls_used", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        CREATE INDEX ix_anpr_job_runs_run_date_started_at_desc
        ON anpr_job_runs (run_date, started_at DESC)
        """
    )
    op.create_index("ix_anpr_job_runs_run_date", "anpr_job_runs", ["run_date"], unique=False)
    op.execute(
        """
        ALTER TABLE anpr_sync_config
        ALTER COLUMN max_calls_per_day SET DEFAULT 90
        """
    )
    op.execute(
        """
        ALTER TABLE anpr_sync_config
        ALTER COLUMN job_cron SET DEFAULT '0 8-17 * * *'
        """
    )
    op.execute(
        """
        UPDATE anpr_sync_config
        SET job_cron = '0 8-17 * * *'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE anpr_sync_config
        ALTER COLUMN job_cron SET DEFAULT '0 2 * * *'
        """
    )
    op.execute(
        """
        ALTER TABLE anpr_sync_config
        ALTER COLUMN max_calls_per_day SET DEFAULT 100
        """
    )
    op.drop_index("ix_anpr_job_runs_run_date", table_name="anpr_job_runs")
    op.execute("DROP INDEX IF EXISTS ix_anpr_job_runs_run_date_started_at_desc")
    op.drop_table("anpr_job_runs")
