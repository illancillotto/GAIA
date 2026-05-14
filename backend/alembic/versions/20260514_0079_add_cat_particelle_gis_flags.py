"""catasto: add cached GIS flags for particelle

Revision ID: 20260514_0079
Revises: 20260514_0078
Create Date: 2026-05-14 11:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260514_0079"
down_revision = "20260514_0078"
branch_labels = None
depends_on = None


def _create_cached_view() -> None:
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
            COALESCE(gf.ha_anomalie, FALSE) AS ha_anomalie,
            COALESCE(gf.ha_ruolo, FALSE) AS ha_ruolo
        FROM cat_particelle p
        LEFT JOIN cat_particelle_gis_flags gf ON gf.particella_id = p.id
        WHERE p.is_current = TRUE;
        """
    )


def _create_dynamic_view() -> None:
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


def upgrade() -> None:
    op.create_table(
        "cat_particelle_gis_flags",
        sa.Column(
            "particella_id",
            sa.Uuid(),
            sa.ForeignKey("cat_particelle.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("ha_ruolo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ha_anomalie", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ruolo_anno_latest", sa.Integer(), nullable=True),
        sa.Column("anomalie_aperte_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_cat_particelle_gis_flags_ha_ruolo",
        "cat_particelle_gis_flags",
        ["ha_ruolo"],
        postgresql_where=sa.text("ha_ruolo IS TRUE"),
    )
    op.create_index(
        "ix_cat_particelle_gis_flags_ha_anomalie",
        "cat_particelle_gis_flags",
        ["ha_anomalie"],
        postgresql_where=sa.text("ha_anomalie IS TRUE"),
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ruolo_particelle_cat_particella_anno
        ON ruolo_particelle (cat_particella_id, anno_tributario)
        WHERE cat_particella_id IS NOT NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cat_anomalie_particella_status
        ON cat_anomalie (particella_id, status)
        WHERE particella_id IS NOT NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cat_anomalie_utenza_status
        ON cat_anomalie (utenza_id, status)
        WHERE utenza_id IS NOT NULL;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION refresh_cat_particella_gis_flag(_particella_id uuid)
        RETURNS void
        LANGUAGE plpgsql
        AS $$
        DECLARE
            _ruolo_anno_latest integer;
            _anomalie_aperte_count integer;
        BEGIN
            IF _particella_id IS NULL THEN
                RETURN;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM cat_particelle p
                WHERE p.id = _particella_id AND p.is_current IS TRUE
            ) THEN
                DELETE FROM cat_particelle_gis_flags WHERE particella_id = _particella_id;
                RETURN;
            END IF;

            SELECT MAX(rp.anno_tributario)
            INTO _ruolo_anno_latest
            FROM ruolo_particelle rp
            WHERE rp.cat_particella_id = _particella_id
              AND rp.anno_tributario <= EXTRACT(YEAR FROM CURRENT_DATE)::integer;

            SELECT COUNT(DISTINCT a.id)
            INTO _anomalie_aperte_count
            FROM cat_anomalie a
            LEFT JOIN cat_utenze_irrigue u ON u.id = a.utenza_id
            WHERE a.status = 'aperta'
              AND (
                a.particella_id = _particella_id
                OR u.particella_id = _particella_id
              );

            INSERT INTO cat_particelle_gis_flags (
                particella_id,
                ha_ruolo,
                ha_anomalie,
                ruolo_anno_latest,
                anomalie_aperte_count,
                updated_at
            )
            VALUES (
                _particella_id,
                _ruolo_anno_latest IS NOT NULL,
                _anomalie_aperte_count > 0,
                _ruolo_anno_latest,
                _anomalie_aperte_count,
                now()
            )
            ON CONFLICT (particella_id) DO UPDATE SET
                ha_ruolo = EXCLUDED.ha_ruolo,
                ha_anomalie = EXCLUDED.ha_anomalie,
                ruolo_anno_latest = EXCLUDED.ruolo_anno_latest,
                anomalie_aperte_count = EXCLUDED.anomalie_aperte_count,
                updated_at = EXCLUDED.updated_at;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION refresh_cat_particelle_gis_flags_all()
        RETURNS integer
        LANGUAGE plpgsql
        AS $$
        DECLARE
            _affected integer;
        BEGIN
            WITH ruolo_flags AS (
                SELECT
                    rp.cat_particella_id AS particella_id,
                    MAX(rp.anno_tributario) AS ruolo_anno_latest
                FROM ruolo_particelle rp
                WHERE rp.cat_particella_id IS NOT NULL
                  AND rp.anno_tributario <= EXTRACT(YEAR FROM CURRENT_DATE)::integer
                GROUP BY rp.cat_particella_id
            ),
            anomalia_source AS (
                SELECT a.id AS anomalia_id, a.particella_id
                FROM cat_anomalie a
                WHERE a.status = 'aperta'
                  AND a.particella_id IS NOT NULL
                UNION ALL
                SELECT a.id AS anomalia_id, u.particella_id
                FROM cat_anomalie a
                JOIN cat_utenze_irrigue u ON u.id = a.utenza_id
                WHERE a.status = 'aperta'
                  AND u.particella_id IS NOT NULL
            ),
            anomalia_flags AS (
                SELECT
                    particella_id,
                    COUNT(DISTINCT anomalia_id)::integer AS anomalie_aperte_count
                FROM anomalia_source
                GROUP BY particella_id
            ),
            upserted AS (
                INSERT INTO cat_particelle_gis_flags (
                    particella_id,
                    ha_ruolo,
                    ha_anomalie,
                    ruolo_anno_latest,
                    anomalie_aperte_count,
                    updated_at
                )
                SELECT
                    p.id,
                    COALESCE(r.ruolo_anno_latest IS NOT NULL, FALSE),
                    COALESCE(a.anomalie_aperte_count > 0, FALSE),
                    r.ruolo_anno_latest,
                    COALESCE(a.anomalie_aperte_count, 0),
                    now()
                FROM cat_particelle p
                LEFT JOIN ruolo_flags r ON r.particella_id = p.id
                LEFT JOIN anomalia_flags a ON a.particella_id = p.id
                WHERE p.is_current IS TRUE
                ON CONFLICT (particella_id) DO UPDATE SET
                    ha_ruolo = EXCLUDED.ha_ruolo,
                    ha_anomalie = EXCLUDED.ha_anomalie,
                    ruolo_anno_latest = EXCLUDED.ruolo_anno_latest,
                    anomalie_aperte_count = EXCLUDED.anomalie_aperte_count,
                    updated_at = EXCLUDED.updated_at
                RETURNING 1
            ),
            deleted AS (
                DELETE FROM cat_particelle_gis_flags gf
                WHERE NOT EXISTS (
                    SELECT 1 FROM cat_particelle p
                    WHERE p.id = gf.particella_id AND p.is_current IS TRUE
                )
                RETURNING 1
            )
            SELECT COUNT(*) INTO _affected FROM upserted;

            RETURN _affected;
        END;
        $$;
        """
    )
    op.execute("SELECT refresh_cat_particelle_gis_flags_all();")
    _create_cached_view()

    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_refresh_gis_flags_from_ruolo()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                PERFORM refresh_cat_particella_gis_flag(OLD.cat_particella_id);
            END IF;
            IF TG_OP IN ('INSERT', 'UPDATE') THEN
                PERFORM refresh_cat_particella_gis_flag(NEW.cat_particella_id);
            END IF;

            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_refresh_gis_flags_from_anomalia()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            _old_utenza_particella_id uuid;
            _new_utenza_particella_id uuid;
        BEGIN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                PERFORM refresh_cat_particella_gis_flag(OLD.particella_id);
                IF OLD.utenza_id IS NOT NULL THEN
                    SELECT u.particella_id INTO _old_utenza_particella_id
                    FROM cat_utenze_irrigue u
                    WHERE u.id = OLD.utenza_id;
                    PERFORM refresh_cat_particella_gis_flag(_old_utenza_particella_id);
                END IF;
            END IF;

            IF TG_OP IN ('INSERT', 'UPDATE') THEN
                PERFORM refresh_cat_particella_gis_flag(NEW.particella_id);
                IF NEW.utenza_id IS NOT NULL THEN
                    SELECT u.particella_id INTO _new_utenza_particella_id
                    FROM cat_utenze_irrigue u
                    WHERE u.id = NEW.utenza_id;
                    PERFORM refresh_cat_particella_gis_flag(_new_utenza_particella_id);
                END IF;
            END IF;

            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_refresh_gis_flags_from_utenza()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'UPDATE' AND OLD.particella_id IS DISTINCT FROM NEW.particella_id THEN
                PERFORM refresh_cat_particella_gis_flag(OLD.particella_id);
                PERFORM refresh_cat_particella_gis_flag(NEW.particella_id);
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_refresh_gis_flags_from_particella()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                DELETE FROM cat_particelle_gis_flags WHERE particella_id = OLD.id;
                RETURN OLD;
            END IF;

            IF NEW.is_current IS TRUE THEN
                PERFORM refresh_cat_particella_gis_flag(NEW.id);
            ELSE
                DELETE FROM cat_particelle_gis_flags WHERE particella_id = NEW.id;
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER cat_particelle_gis_flags_ruolo_refresh_trg
        AFTER INSERT OR UPDATE OF cat_particella_id, anno_tributario OR DELETE
        ON ruolo_particelle
        FOR EACH ROW
        EXECUTE FUNCTION trg_refresh_gis_flags_from_ruolo();
        """
    )
    op.execute(
        """
        CREATE TRIGGER cat_particelle_gis_flags_anomalia_refresh_trg
        AFTER INSERT OR UPDATE OF status, particella_id, utenza_id OR DELETE
        ON cat_anomalie
        FOR EACH ROW
        EXECUTE FUNCTION trg_refresh_gis_flags_from_anomalia();
        """
    )
    op.execute(
        """
        CREATE TRIGGER cat_particelle_gis_flags_utenza_refresh_trg
        AFTER UPDATE OF particella_id
        ON cat_utenze_irrigue
        FOR EACH ROW
        EXECUTE FUNCTION trg_refresh_gis_flags_from_utenza();
        """
    )
    op.execute(
        """
        CREATE TRIGGER cat_particelle_gis_flags_particella_refresh_trg
        AFTER INSERT OR UPDATE OF is_current OR DELETE
        ON cat_particelle
        FOR EACH ROW
        EXECUTE FUNCTION trg_refresh_gis_flags_from_particella();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS cat_particelle_gis_flags_particella_refresh_trg ON cat_particelle")
    op.execute("DROP TRIGGER IF EXISTS cat_particelle_gis_flags_utenza_refresh_trg ON cat_utenze_irrigue")
    op.execute("DROP TRIGGER IF EXISTS cat_particelle_gis_flags_anomalia_refresh_trg ON cat_anomalie")
    op.execute("DROP TRIGGER IF EXISTS cat_particelle_gis_flags_ruolo_refresh_trg ON ruolo_particelle")
    op.execute("DROP FUNCTION IF EXISTS trg_refresh_gis_flags_from_particella()")
    op.execute("DROP FUNCTION IF EXISTS trg_refresh_gis_flags_from_utenza()")
    op.execute("DROP FUNCTION IF EXISTS trg_refresh_gis_flags_from_anomalia()")
    op.execute("DROP FUNCTION IF EXISTS trg_refresh_gis_flags_from_ruolo()")
    _create_dynamic_view()
    op.execute("DROP FUNCTION IF EXISTS refresh_cat_particelle_gis_flags_all()")
    op.execute("DROP FUNCTION IF EXISTS refresh_cat_particella_gis_flag(uuid)")
    op.execute("DROP INDEX IF EXISTS ix_cat_anomalie_utenza_status")
    op.execute("DROP INDEX IF EXISTS ix_cat_anomalie_particella_status")
    op.execute("DROP INDEX IF EXISTS ix_ruolo_particelle_cat_particella_anno")
    op.drop_index("ix_cat_particelle_gis_flags_ha_anomalie", table_name="cat_particelle_gis_flags")
    op.drop_index("ix_cat_particelle_gis_flags_ha_ruolo", table_name="cat_particelle_gis_flags")
    op.drop_table("cat_particelle_gis_flags")
