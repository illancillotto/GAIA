"""catasto delivery points import jobs

Revision ID: 20260707_0800
Revises: 20260706_1200
Create Date: 2026-07-07 08:00:00
"""

from __future__ import annotations

from alembic import op


revision = "20260707_0800"
down_revision = "20260706_1200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE catasto_delivery_points_import_jobs (
          id uuid PRIMARY KEY,
          status varchar(32) NOT NULL DEFAULT 'pending',
          root_path text NOT NULL,
          requested_by varchar(256) NULL,
          error_message text NULL,
          points_processed integer NULL,
          canals_processed integer NULL,
          meter_readings_linked integer NULL,
          meter_readings_unlinked integer NULL,
          started_at timestamptz NULL,
          completed_at timestamptz NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_catasto_delivery_points_import_jobs_status "
        "ON catasto_delivery_points_import_jobs (status);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS catasto_delivery_points_import_jobs;")
