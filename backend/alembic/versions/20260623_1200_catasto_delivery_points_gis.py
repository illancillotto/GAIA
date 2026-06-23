"""catasto delivery points and irrigation canals GIS layers

Revision ID: 20260623_1210
Revises: 20260618_1100
Create Date: 2026-06-23 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260623_1210"
down_revision = "20260618_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    op.execute(
        """
        CREATE TABLE cat_delivery_points (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          distretto_code varchar(32) NOT NULL,
          punto_consegna_code varchar(128) NOT NULL,
          tipologia varchar(255) NULL,
          tipo varchar(64) NULL,
          cod_cont varchar(128) NULL,
          photo_ref varchar(255) NULL,
          has_meter boolean NOT NULL DEFAULT true,
          source_dataset varchar(64) NOT NULL DEFAULT '2026_DEF',
          source_file varchar(255) NULL,
          source_updated_at timestamptz NULL,
          source_x numeric(14, 3) NULL,
          source_y numeric(14, 3) NULL,
          source_payload_json json NULL,
          geometry geometry(POINT, 4326) NULL,
          is_active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT uq_cat_delivery_points_distretto_point UNIQUE (distretto_code, punto_consegna_code)
        );
        """
    )
    op.execute("CREATE INDEX ix_cat_delivery_points_distretto_code ON cat_delivery_points (distretto_code);")
    op.execute("CREATE INDEX ix_cat_delivery_points_has_meter ON cat_delivery_points (has_meter);")
    op.execute("CREATE INDEX ix_cat_delivery_points_source_dataset ON cat_delivery_points (source_dataset);")
    op.execute("CREATE INDEX ix_cat_delivery_points_is_active ON cat_delivery_points (is_active);")
    op.execute("CREATE INDEX idx_cat_delivery_points_geom ON cat_delivery_points USING gist (geometry);")

    op.execute(
        """
        CREATE TABLE cat_irrigation_canals (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          source_key varchar(64) NOT NULL,
          distretto_code varchar(32) NOT NULL,
          label varchar(255) NULL,
          tipo_canale varchar(255) NULL,
          source_dataset varchar(64) NOT NULL DEFAULT '2026_DEF',
          source_file varchar(255) NULL,
          source_updated_at timestamptz NULL,
          source_payload_json json NULL,
          geometry geometry(LINESTRING, 4326) NULL,
          is_active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT uq_cat_irrigation_canals_source_key UNIQUE (source_key)
        );
        """
    )
    op.execute("CREATE INDEX ix_cat_irrigation_canals_distretto_code ON cat_irrigation_canals (distretto_code);")
    op.execute("CREATE INDEX ix_cat_irrigation_canals_source_dataset ON cat_irrigation_canals (source_dataset);")
    op.execute("CREATE INDEX ix_cat_irrigation_canals_is_active ON cat_irrigation_canals (is_active);")
    op.execute("CREATE INDEX idx_cat_irrigation_canals_geom ON cat_irrigation_canals USING gist (geometry);")

    op.add_column(
        "catasto_meter_readings",
        sa.Column("delivery_point_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_catasto_meter_readings_delivery_point_id"),
        "catasto_meter_readings",
        ["delivery_point_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_catasto_meter_readings_delivery_point_id",
        "catasto_meter_readings",
        "cat_delivery_points",
        ["delivery_point_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW cat_delivery_points_current AS
        SELECT
          id,
          distretto_code,
          punto_consegna_code,
          tipologia,
          tipo,
          cod_cont,
          photo_ref,
          has_meter,
          source_dataset,
          source_file,
          source_updated_at,
          source_x,
          source_y,
          source_payload_json,
          geometry
        FROM cat_delivery_points
        WHERE is_active = true;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW cat_irrigation_canals_current AS
        SELECT
          id,
          source_key,
          distretto_code,
          label,
          tipo_canale,
          source_dataset,
          source_file,
          source_updated_at,
          source_payload_json,
          geometry
        FROM cat_irrigation_canals
        WHERE is_active = true;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS cat_irrigation_canals_current;")
    op.execute("DROP VIEW IF EXISTS cat_delivery_points_current;")
    op.drop_constraint("fk_catasto_meter_readings_delivery_point_id", "catasto_meter_readings", type_="foreignkey")
    op.drop_index(op.f("ix_catasto_meter_readings_delivery_point_id"), table_name="catasto_meter_readings")
    op.drop_column("catasto_meter_readings", "delivery_point_id")
    op.execute("DROP TABLE IF EXISTS cat_irrigation_canals;")
    op.execute("DROP TABLE IF EXISTS cat_delivery_points;")
