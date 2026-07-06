"""catasto delivery points import config

Revision ID: 20260706_1200
Revises: 20260704_0900
Create Date: 2026-07-06 12:00:00
"""

from __future__ import annotations

from alembic import op


revision = "20260706_1200"
down_revision = "20260704_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE catasto_delivery_points_import_config (
          id integer PRIMARY KEY,
          root_path text NULL,
          updated_by varchar(256) NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        INSERT INTO catasto_delivery_points_import_config (id)
        VALUES (1)
        ON CONFLICT (id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS catasto_delivery_points_import_config;")
