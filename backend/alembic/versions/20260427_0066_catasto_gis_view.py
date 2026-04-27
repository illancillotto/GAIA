"""catasto: add cat_particelle_current view for Martin tile server

Revision ID: 20260427_0066
Revises: 20260427_0065
Create Date: 2026-04-27 11:05:00.000000
"""

from __future__ import annotations

from alembic import op


revision = "20260427_0066"
down_revision = "20260427_0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
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
            EXISTS(
                SELECT 1
                FROM cat_anomalie a
                WHERE a.particella_id = p.id
                  AND a.status = 'aperta'
            ) AS ha_anomalie
        FROM cat_particelle p
        WHERE p.is_current = TRUE;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS cat_particelle_current;")
