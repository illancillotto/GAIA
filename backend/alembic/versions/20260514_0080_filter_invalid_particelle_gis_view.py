"""catasto: hide invalid particelle from GIS tiles

Revision ID: 20260514_0080
Revises: 20260514_0079
Create Date: 2026-05-14 15:10:00.000000
"""

from __future__ import annotations

from alembic import op


revision = "20260514_0080"
down_revision = "20260514_0079"
branch_labels = None
depends_on = None


def _create_view(*, require_valid_key: bool) -> None:
    valid_filter = """
          AND p.suppressed IS FALSE
          AND p.cod_comune_capacitas > 0
          AND NULLIF(BTRIM(p.codice_catastale), '') IS NOT NULL
          AND NULLIF(BTRIM(p.foglio), '') IS NOT NULL
          AND NULLIF(BTRIM(p.particella), '') IS NOT NULL
    """ if require_valid_key else ""
    op.execute(
        f"""
        CREATE OR REPLACE VIEW cat_particelle_current AS
        SELECT
            p.id,
            p.cfm,
            p.cod_comune_capacitas,
            p.cod_comune_capacitas AS cod_comune_istat,
            p.codice_catastale,
            p.comune_id,
            p.nome_comune,
            p.foglio,
            p.particella,
            p.subalterno,
            p.superficie_mq,
            p.superficie_grafica_mq,
            p.num_distretto,
            p.nome_distretto,
            (p.num_distretto = 'FD') AS fuori_distretto,
            p.geometry,
            COALESCE(gf.ha_anomalie, FALSE) AS ha_anomalie,
            COALESCE(gf.ha_ruolo, FALSE) AS ha_ruolo
        FROM cat_particelle p
        LEFT JOIN cat_particelle_gis_flags gf ON gf.particella_id = p.id
        WHERE p.is_current = TRUE
        {valid_filter};
        """
    )


def upgrade() -> None:
    _create_view(require_valid_key=True)


def downgrade() -> None:
    _create_view(require_valid_key=False)
