"""catasto: add distretti boundaries view for GIS tiles

Revision ID: 20260511_0073
Revises: 20260504_0072
Create Date: 2026-05-11 12:00:00.000000
"""

from __future__ import annotations

from alembic import op


revision = "20260511_0073"
down_revision = "20260504_0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE VIEW cat_distretti_boundaries AS
        SELECT
            d.id,
            d.num_distretto,
            d.nome_distretto,
            d.attivo,
            ST_Multi(
                ST_CollectionExtract(
                    ST_Boundary(
                        ST_UnaryUnion(ST_CollectionExtract(ST_MakeValid(d.geometry), 3))
                    ),
                    2
                )
            )::geometry(MULTILINESTRING, 4326) AS geometry
        FROM cat_distretti d
        WHERE d.geometry IS NOT NULL
          AND NOT ST_IsEmpty(d.geometry);
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS cat_distretti_boundaries;")
