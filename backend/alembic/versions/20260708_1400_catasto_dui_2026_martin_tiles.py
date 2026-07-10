"""catasto DUI 2026 Martin tile layer

Revision ID: 20260708_1400
Revises: 20260708_1030
Create Date: 2026-07-08 14:00:00
"""

from __future__ import annotations

from alembic import op


revision = "20260708_1400"
down_revision = "20260708_1030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cat_dui_2026_current (
          id uuid PRIMARY KEY,
          source_path text NOT NULL,
          source_filename varchar(255) NOT NULL,
          source_date date NULL,
          source_updated_at timestamptz NULL,
          domanda_irrigua varchar(64) NULL,
          codice_fiscale varchar(32) NULL,
          intestatario text NULL,
          telefono varchar(64) NULL,
          sup_grafica_mq numeric(14, 2) NULL,
          coltura varchar(255) NULL,
          tipo_domanda varchar(255) NULL,
          data_domanda varchar(64) NULL,
          contatore varchar(16) NULL,
          telerilev varchar(16) NULL,
          operatore varchar(255) NULL,
          point_x numeric(14, 3) NULL,
          point_y numeric(14, 3) NULL,
          in_ruolo_2025 boolean NOT NULL DEFAULT false,
          ruolo_2025_match_count integer NOT NULL DEFAULT 0,
          source_payload_json jsonb NULL,
          geometry geometry(MULTIPOLYGON, 4326) NOT NULL,
          synced_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_cat_dui_2026_current_domanda ON cat_dui_2026_current (domanda_irrigua);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cat_dui_2026_current_source_filename ON cat_dui_2026_current (source_filename);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cat_dui_2026_current_in_ruolo ON cat_dui_2026_current (in_ruolo_2025);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cat_dui_2026_current_geom ON cat_dui_2026_current USING gist (geometry);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cat_dui_2026_current;")
