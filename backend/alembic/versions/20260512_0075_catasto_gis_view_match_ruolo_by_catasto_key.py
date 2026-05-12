"""catasto: match GIS ruolo by cadastral key

Revision ID: 20260512_0075
Revises: 20260511_0074
Create Date: 2026-05-12 09:20:00.000000
"""

from __future__ import annotations

from alembic import op


revision = "20260512_0075"
down_revision = "20260511_0074"
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
            ) AS ha_anomalie,
            EXISTS(
                SELECT 1
                FROM catasto_parcels cp
                JOIN ruolo_particelle rp ON rp.catasto_parcel_id = cp.id
                WHERE cp.comune_codice = p.codice_catastale
                  AND cp.foglio = p.foglio
                  AND cp.particella = p.particella
                  AND (
                    COALESCE(p.subalterno, '') = ''
                    OR COALESCE(cp.subalterno, '') = p.subalterno
                  )
                  AND rp.anno_tributario <= EXTRACT(YEAR FROM CURRENT_DATE)::integer
            ) AS ha_ruolo
        FROM cat_particelle p
        WHERE p.is_current = TRUE;
        """
    )


def downgrade() -> None:
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
            ) AS ha_anomalie,
            EXISTS(
                SELECT 1
                FROM ruolo_particelle rp
                WHERE rp.catasto_parcel_id = p.id
            ) AS ha_ruolo
        FROM cat_particelle p
        WHERE p.is_current = TRUE;
        """
    )
