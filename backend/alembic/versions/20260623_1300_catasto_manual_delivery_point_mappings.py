"""catasto manual meter reading delivery point mappings

Revision ID: 20260623_1300
Revises: 20260623_1200, 20260623_1210
Create Date: 2026-06-23 13:00:00
"""

from __future__ import annotations

from alembic import op


revision = "20260623_1300"
down_revision = ("20260623_1200", "20260623_1210")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE catasto_meter_reading_delivery_point_mappings (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          distretto_code varchar(32) NOT NULL,
          source_point_code varchar(128) NOT NULL,
          delivery_point_id uuid NOT NULL REFERENCES cat_delivery_points(id) ON DELETE CASCADE,
          change_note text NULL,
          created_by integer NULL REFERENCES application_users(id),
          updated_by integer NULL REFERENCES application_users(id),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT uq_catasto_meter_reading_delivery_point_mappings_distretto_point
            UNIQUE (distretto_code, source_point_code)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_catasto_meter_reading_delivery_point_mappings_distretto_code "
        "ON catasto_meter_reading_delivery_point_mappings (distretto_code);"
    )
    op.execute(
        "CREATE INDEX ix_catasto_meter_reading_delivery_point_mappings_delivery_point_id "
        "ON catasto_meter_reading_delivery_point_mappings (delivery_point_id);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS catasto_meter_reading_delivery_point_mappings;")
