"""ruolo: add resolved cat_particelle FK

Revision ID: 20260513_0077
Revises: 20260513_0076
Create Date: 2026-05-13 11:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260513_0077"
down_revision = "20260513_0076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cat_particelle_ruolo_match_current
        ON cat_particelle (
            codice_catastale,
            foglio,
            particella,
            (COALESCE(subalterno, ''))
        )
        WHERE is_current IS TRUE AND suppressed IS FALSE;
        """
    )
    op.add_column("ruolo_particelle", sa.Column("cat_particella_id", sa.Uuid(), nullable=True))
    op.add_column("ruolo_particelle", sa.Column("cat_particella_match_status", sa.String(length=20), nullable=True))
    op.add_column(
        "ruolo_particelle", sa.Column("cat_particella_match_confidence", sa.String(length=40), nullable=True)
    )
    op.add_column("ruolo_particelle", sa.Column("cat_particella_match_reason", sa.Text(), nullable=True))
    op.create_index(
        op.f("ix_ruolo_particelle_cat_particella_id"),
        "ruolo_particelle",
        ["cat_particella_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ruolo_particelle_cat_particella_match_status"),
        "ruolo_particelle",
        ["cat_particella_match_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ruolo_particelle_cat_particella_match_confidence"),
        "ruolo_particelle",
        ["cat_particella_match_confidence"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_ruolo_particelle_cat_particella_id",
        "ruolo_particelle",
        "cat_particelle",
        ["cat_particella_id"],
        ["id"],
        ondelete="SET NULL",
    )
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
                LEFT JOIN catasto_parcels cp ON cp.id = rp.catasto_parcel_id
                WHERE rp.anno_tributario <= EXTRACT(YEAR FROM CURRENT_DATE)::integer
                  AND (
                    rp.cat_particella_id = p.id
                    OR (
                      cp.comune_codice = p.codice_catastale
                      AND cp.foglio = p.foglio
                      AND cp.particella = p.particella
                      AND (
                        COALESCE(p.subalterno, '') = ''
                        OR COALESCE(cp.subalterno, '') = p.subalterno
                      )
                    )
                  )
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
    op.drop_constraint("fk_ruolo_particelle_cat_particella_id", "ruolo_particelle", type_="foreignkey")
    op.drop_index(op.f("ix_ruolo_particelle_cat_particella_match_confidence"), table_name="ruolo_particelle")
    op.drop_index(op.f("ix_ruolo_particelle_cat_particella_match_status"), table_name="ruolo_particelle")
    op.drop_index(op.f("ix_ruolo_particelle_cat_particella_id"), table_name="ruolo_particelle")
    op.drop_column("ruolo_particelle", "cat_particella_match_reason")
    op.drop_column("ruolo_particelle", "cat_particella_match_confidence")
    op.drop_column("ruolo_particelle", "cat_particella_match_status")
    op.drop_column("ruolo_particelle", "cat_particella_id")
    op.execute("DROP INDEX IF EXISTS ix_cat_particelle_ruolo_match_current")
