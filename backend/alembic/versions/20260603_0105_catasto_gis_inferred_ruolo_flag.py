"""catasto: add inferred ruolo GIS flag

Revision ID: 20260603_0105
Revises: 20260603_0104
Create Date: 2026-06-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260603_0105"
down_revision = "20260603_0104"
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
            COALESCE(gf.ha_ruolo, FALSE) AS ha_ruolo,
            COALESCE(gf.ha_ruolo_inferito, FALSE) AS ha_ruolo_inferito
        FROM cat_particelle p
        LEFT JOIN cat_particelle_gis_flags gf ON gf.particella_id = p.id
        WHERE p.is_current = TRUE;
        """
    )


def _create_refresh_functions() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION refresh_cat_particella_gis_flag(_particella_id uuid)
        RETURNS void
        LANGUAGE plpgsql
        AS $$
        DECLARE
            _ruolo_anno_latest integer;
            _anomalie_aperte_count integer;
            _ha_ruolo_inferito boolean;
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

            IF _ruolo_anno_latest IS NULL THEN
                SELECT EXISTS (
                    WITH target AS (
                        SELECT UPPER(nome_comune) AS comune_nome
                        FROM cat_particelle
                        WHERE id = _particella_id
                    ),
                    identifiers AS (
                        SELECT DISTINCT UPPER(regexp_replace(value, '\\s+', '', 'g')) AS token
                        FROM (
                            SELECT ui.codice_fiscale AS value
                            FROM cat_utenze_irrigue ui
                            WHERE ui.particella_id = _particella_id
                              AND ui.codice_fiscale IS NOT NULL
                              AND BTRIM(ui.codice_fiscale) <> ''
                            UNION ALL
                            SELECT ci.codice_fiscale AS value
                            FROM cat_utenza_intestatari ci
                            JOIN cat_utenze_irrigue ui ON ui.id = ci.utenza_id
                            WHERE ui.particella_id = _particella_id
                              AND ci.codice_fiscale IS NOT NULL
                              AND BTRIM(ci.codice_fiscale) <> ''
                            UNION ALL
                            SELECT ci.partita_iva AS value
                            FROM cat_utenza_intestatari ci
                            JOIN cat_utenze_irrigue ui ON ui.id = ci.utenza_id
                            WHERE ui.particella_id = _particella_id
                              AND ci.partita_iva IS NOT NULL
                              AND BTRIM(ci.partita_iva) <> ''
                        ) raw
                    )
                    SELECT 1
                    FROM identifiers i
                    JOIN ruolo_avvisi ra
                      ON UPPER(regexp_replace(COALESCE(ra.codice_fiscale_raw, ''), '\\s+', '', 'g')) = i.token
                    JOIN ruolo_partite rpt ON rpt.avviso_id = ra.id
                    JOIN target t ON UPPER(rpt.comune_nome) = t.comune_nome
                    WHERE ra.anno_tributario <= EXTRACT(YEAR FROM CURRENT_DATE)::integer
                      AND NOT EXISTS (
                        SELECT 1
                        FROM ruolo_particelle rpp
                        WHERE rpp.partita_id = rpt.id
                      )
                    LIMIT 1
                )
                INTO _ha_ruolo_inferito;
            ELSE
                _ha_ruolo_inferito := FALSE;
            END IF;

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
                ha_ruolo_inferito,
                ha_anomalie,
                ruolo_anno_latest,
                anomalie_aperte_count,
                updated_at
            )
            VALUES (
                _particella_id,
                _ruolo_anno_latest IS NOT NULL,
                COALESCE(_ha_ruolo_inferito, FALSE),
                _anomalie_aperte_count > 0,
                _ruolo_anno_latest,
                _anomalie_aperte_count,
                now()
            )
            ON CONFLICT (particella_id) DO UPDATE SET
                ha_ruolo = EXCLUDED.ha_ruolo,
                ha_ruolo_inferito = EXCLUDED.ha_ruolo_inferito,
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
            WITH current_particelle AS (
                SELECT
                    p.id,
                    UPPER(p.nome_comune) AS comune_nome
                FROM cat_particelle p
                WHERE p.is_current IS TRUE
            ),
            ruolo_flags AS (
                SELECT
                    rp.cat_particella_id AS particella_id,
                    MAX(rp.anno_tributario) AS ruolo_anno_latest
                FROM ruolo_particelle rp
                WHERE rp.cat_particella_id IS NOT NULL
                  AND rp.anno_tributario <= EXTRACT(YEAR FROM CURRENT_DATE)::integer
                GROUP BY rp.cat_particella_id
            ),
            identifier_source AS (
                SELECT
                    ui.particella_id,
                    UPPER(regexp_replace(ui.codice_fiscale, '\\s+', '', 'g')) AS token
                FROM cat_utenze_irrigue ui
                WHERE ui.particella_id IS NOT NULL
                  AND ui.codice_fiscale IS NOT NULL
                  AND BTRIM(ui.codice_fiscale) <> ''
                UNION ALL
                SELECT
                    ui.particella_id,
                    UPPER(regexp_replace(ci.codice_fiscale, '\\s+', '', 'g')) AS token
                FROM cat_utenza_intestatari ci
                JOIN cat_utenze_irrigue ui ON ui.id = ci.utenza_id
                WHERE ui.particella_id IS NOT NULL
                  AND ci.codice_fiscale IS NOT NULL
                  AND BTRIM(ci.codice_fiscale) <> ''
                UNION ALL
                SELECT
                    ui.particella_id,
                    UPPER(regexp_replace(ci.partita_iva, '\\s+', '', 'g')) AS token
                FROM cat_utenza_intestatari ci
                JOIN cat_utenze_irrigue ui ON ui.id = ci.utenza_id
                WHERE ui.particella_id IS NOT NULL
                  AND ci.partita_iva IS NOT NULL
                  AND BTRIM(ci.partita_iva) <> ''
            ),
            identifiers AS (
                SELECT DISTINCT particella_id, token
                FROM identifier_source
            ),
            ruolo_inferito_flags AS (
                SELECT
                    cp.id AS particella_id
                FROM current_particelle cp
                JOIN identifiers i ON i.particella_id = cp.id
                JOIN ruolo_avvisi ra
                  ON UPPER(regexp_replace(COALESCE(ra.codice_fiscale_raw, ''), '\\s+', '', 'g')) = i.token
                JOIN ruolo_partite rpt
                  ON rpt.avviso_id = ra.id
                 AND UPPER(rpt.comune_nome) = cp.comune_nome
                LEFT JOIN ruolo_flags rf ON rf.particella_id = cp.id
                WHERE ra.anno_tributario <= EXTRACT(YEAR FROM CURRENT_DATE)::integer
                  AND rf.particella_id IS NULL
                  AND NOT EXISTS (
                    SELECT 1
                    FROM ruolo_particelle rpp
                    WHERE rpp.partita_id = rpt.id
                  )
                GROUP BY cp.id
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
                    ha_ruolo_inferito,
                    ha_anomalie,
                    ruolo_anno_latest,
                    anomalie_aperte_count,
                    updated_at
                )
                SELECT
                    p.id,
                    COALESCE(r.ruolo_anno_latest IS NOT NULL, FALSE),
                    COALESCE(ri.particella_id IS NOT NULL, FALSE),
                    COALESCE(a.anomalie_aperte_count > 0, FALSE),
                    r.ruolo_anno_latest,
                    COALESCE(a.anomalie_aperte_count, 0),
                    now()
                FROM cat_particelle p
                LEFT JOIN ruolo_flags r ON r.particella_id = p.id
                LEFT JOIN ruolo_inferito_flags ri ON ri.particella_id = p.id
                LEFT JOIN anomalia_flags a ON a.particella_id = p.id
                WHERE p.is_current IS TRUE
                ON CONFLICT (particella_id) DO UPDATE SET
                    ha_ruolo = EXCLUDED.ha_ruolo,
                    ha_ruolo_inferito = EXCLUDED.ha_ruolo_inferito,
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


def upgrade() -> None:
    op.add_column(
        "cat_particelle_gis_flags",
        sa.Column("ha_ruolo_inferito", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "ix_cat_particelle_gis_flags_ha_ruolo_inferito",
        "cat_particelle_gis_flags",
        ["ha_ruolo_inferito"],
        postgresql_where=sa.text("ha_ruolo_inferito IS TRUE"),
    )
    _create_refresh_functions()
    op.execute("SELECT refresh_cat_particelle_gis_flags_all();")
    _create_cached_view()


def downgrade() -> None:
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
    op.execute("DROP INDEX IF EXISTS ix_cat_particelle_gis_flags_ha_ruolo_inferito")
    op.drop_column("cat_particelle_gis_flags", "ha_ruolo_inferito")
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
