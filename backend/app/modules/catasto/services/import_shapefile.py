from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatImportBatch
from app.modules.catasto.services.comuni_reference import (
    get_capacitas_code_by_catastale,
    get_official_name_by_catastale,
)


def _escape_sql_string(value: str) -> str:
    return value.replace("'", "''")


def finalize_shapefile_import(
    db: Session,
    *,
    created_by: int,
    source_srid: int | None = 4326,
    staging_table: str = "cat_particelle_staging",
) -> dict[str, Any]:
    """
    Finalizza l'import shapefile caricato via ogr2ogr in `cat_particelle_staging`.

    Operazioni:
    - SCD Type 2 verso `cat_particelle` (chiave operativa: cod_comune_capacitas,foglio,particella,subalterno)
    - Inserisce storico in `cat_particelle_history` per record cambiati
    - Deriva e upserta `cat_distretti` via ST_Union sulle particelle correnti
    - Crea `cat_import_batches` con tipo='shapefile' e report_json con conteggi

    Nota importante:
    - `cod_comune_capacitas` nel modello Catasto e il codice sorgente Capacitas,
      non il codice comune numerico ufficiale ISTAT moderno
    - il mapping da `codice catastale` a questo codice deve sempre passare dal
      dataset di riferimento `comuni_istat.csv`, mai da CASE hardcoded nel SQL
    """
    batch_id = uuid4()
    now = datetime.now(timezone.utc)
    codice_by_catastale = get_capacitas_code_by_catastale()
    nome_by_catastale = get_official_name_by_catastale()
    mapping_rows_sql = ",\n        ".join(
        f"('{codice_catastale}', {codice}, '{_escape_sql_string(nome_by_catastale[codice_catastale])}')"
        for codice_catastale, codice in sorted(codice_by_catastale.items())
    )

    # Pre-check: staging deve esistere
    exists = db.execute(
        text(
            """
            SELECT to_regclass(:table_name) IS NOT NULL
            """
        ),
        {"table_name": staging_table},
    ).scalar_one()
    if not exists:
        raise ValueError(f"Tabella staging non trovata: {staging_table}. Esegui ogr2ogr prima di finalize.")

    # Conta righe staging
    righe_staging = int(
        db.execute(text(f"SELECT COUNT(*) FROM {staging_table}")).scalar_one()  # nosec - controlled internal table name
    )

    batch = CatImportBatch(
        id=batch_id,
        filename=f"{staging_table}",
        tipo="shapefile",
        anno_campagna=None,
        hash_file=None,
        righe_totali=righe_staging,
        righe_importate=0,
        righe_anomalie=0,
        status="processing",
        created_by=created_by,
        created_at=now,
    )
    db.add(batch)
    db.flush()

    # Detect geometry column name in staging (usually wkb_geometry from ogr2ogr)
    geom_col = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND udt_name = 'geometry'
            ORDER BY ordinal_position
            LIMIT 1
            """
        ),
        {"table_name": staging_table},
    ).scalar_one_or_none()
    if not geom_col:
        raise ValueError(f"Nessuna colonna geometry trovata nella staging: {staging_table}")

    # Normalizza geometria se necessario (assumiamo che ogr2ogr abbia già trasformato in 4326,
    # ma manteniamo una guardia per import "grezzo")
    if source_srid and int(source_srid) != 4326:
        db.execute(
            text(
                f"""
                UPDATE {staging_table}
                SET "{geom_col}" = ST_Transform(ST_SetSRID("{geom_col}", :src_srid), 4326)
                WHERE "{geom_col}" IS NOT NULL
                """
            ),
            {"src_srid": int(source_srid)},
        )

    # Mapping colonne staging -> canonical (tollerante a naming diversi).
    # Importante: riferirsi a colonne non esistenti in SQL causa errore anche dentro COALESCE.
    # Per questo usiamo to_jsonb(t)->>'COL' (NULL se la chiave/colonna non esiste).
    # Il mapping comuni viene materializzato dal dataset di riferimento del dominio
    # per evitare divergenze tra shapefile, Capacitas e anagrafica ufficiale.
    staged_rows_cte = f"""
    WITH mapping AS (
      SELECT *
      FROM (VALUES
        {mapping_rows_sql}
      ) AS m(codice_catastale, cod_comune_capacitas, nome_comune)
    ),
    staged AS (
      SELECT
        c.cod_catastale AS codice_catastale,
        cc.id AS comune_id,
        COALESCE(m.cod_comune_capacitas, 0) AS cod_comune_capacitas,
        regexp_replace(
          COALESCE(NULLIF(TRIM(COALESCE(to_jsonb(t)->>'nume_fogl', to_jsonb(t)->>'FOGLIO', to_jsonb(t)->>'foglio')), ''), ''),
          '\\.0$',
          ''
        ) AS foglio,
        regexp_replace(
          COALESCE(NULLIF(TRIM(COALESCE(to_jsonb(t)->>'nume_part', to_jsonb(t)->>'PARTIC', to_jsonb(t)->>'particella')), ''), ''),
          '^\\.',
          ''
        ) AS particella,
        NULLIF(TRIM(COALESCE(to_jsonb(t)->>'suba_part', to_jsonb(t)->>'SUBA_PART', to_jsonb(t)->>'subalterno')), '') AS subalterno,

        -- attributi
        NULLIF(TRIM(COALESCE(to_jsonb(t)->>'nationalca', to_jsonb(t)->>'national_code', to_jsonb(t)->>'NATIONALCA')), '') AS national_code,
        m.nome_comune AS nome_comune,
        NULLIF(TRIM(COALESCE(to_jsonb(t)->>'sezi_cens', to_jsonb(t)->>'sezione_catastale', to_jsonb(t)->>'SEZI_CENS')), '') AS sezione_catastale,
        NULLIF(TRIM(COALESCE(to_jsonb(t)->>'cfm', to_jsonb(t)->>'CFM')), '') AS cfm,
        COALESCE(
          NULLIF(NULLIF(UPPER(TRIM(to_jsonb(t)->>'supe_part')), 'NULL'), '')::numeric,
          NULLIF(NULLIF(UPPER(TRIM(to_jsonb(t)->>'SUPE_PART')), 'NULL'), '')::numeric,
          NULLIF(NULLIF(UPPER(TRIM(to_jsonb(t)->>'superficie_mq')), 'NULL'), '')::numeric
        ) AS superficie_mq,
        NULLIF(TRIM(COALESCE(to_jsonb(t)->>'num_dist', to_jsonb(t)->>'NUM_DIST', to_jsonb(t)->>'num_distretto')), '') AS num_distretto,
        NULLIF(TRIM(COALESCE(to_jsonb(t)->>'nome_dist', to_jsonb(t)->>'Nome_Dist', to_jsonb(t)->>'nome_distretto')), '') AS nome_distretto,
        COALESCE(NULLIF(TRIM(to_jsonb(t)->>'suppressed'), '')::boolean, false) AS suppressed,
        t."{geom_col}" AS geometry
      FROM {staging_table} t
      CROSS JOIN LATERAL (
        SELECT NULLIF(TRIM(COALESCE(
          NULLIF(TRIM(left(split_part(COALESCE(to_jsonb(t)->>'cfm',''), '-', 1), 4)), ''),
          NULLIF(TRIM(left(COALESCE(to_jsonb(t)->>'nationalca',''), 4)), '')
        )), '') AS cod_catastale
      ) c
      LEFT JOIN mapping m
        ON m.codice_catastale = c.cod_catastale
      LEFT JOIN cat_comuni cc
        ON cc.codice_catastale = c.cod_catastale
    )
    """

    # 1) Inserisci nello storico tutte le particelle correnti che cambiano (SCD2)
    # Consideriamo "cambiamento" quando uno dei campi canonici o geometria differiscono.
    moved_to_history = db.execute(
        text(
            staged_rows_cte
            + """
            , changed AS (
              SELECT p.*
              FROM cat_particelle p
              JOIN staged s
                ON p.is_current = true
               AND p.cod_comune_capacitas = s.cod_comune_capacitas
               AND p.foglio = s.foglio
               AND p.particella = s.particella
               AND (p.subalterno IS NOT DISTINCT FROM s.subalterno)
              WHERE
                (p.national_code IS DISTINCT FROM s.national_code)
                OR (p.nome_comune IS DISTINCT FROM s.nome_comune)
                OR (p.sezione_catastale IS DISTINCT FROM s.sezione_catastale)
                OR (p.cfm IS DISTINCT FROM s.cfm)
                OR (p.superficie_mq IS DISTINCT FROM s.superficie_mq)
                OR (p.num_distretto IS DISTINCT FROM s.num_distretto)
                OR (p.nome_distretto IS DISTINCT FROM s.nome_distretto)
                OR (p.suppressed IS DISTINCT FROM s.suppressed)
                OR (
                  (p.geometry IS NULL) <> (s.geometry IS NULL)
                  OR (p.geometry IS NOT NULL AND s.geometry IS NOT NULL AND NOT ST_Equals(p.geometry, s.geometry))
                )
            )
            INSERT INTO cat_particelle_history (
              history_id,
              particella_id,
              comune_id,
              national_code,
              cod_comune_capacitas,
              codice_catastale,
              foglio,
              particella,
              subalterno,
              superficie_mq,
              num_distretto,
              geometry,
              valid_from,
              valid_to,
              changed_at,
              change_reason
            )
            SELECT
              gen_random_uuid(),
              c.id,
              c.comune_id,
              c.national_code,
              c.cod_comune_capacitas,
              c.codice_catastale,
              c.foglio,
              c.particella,
              c.subalterno,
              c.superficie_mq,
              c.num_distretto,
              c.geometry,
              c.valid_from,
              CURRENT_DATE,
              now(),
              'import_shapefile'
            FROM changed c
            RETURNING particella_id
            """
        )
    ).rowcount or 0

    # 2) Chiudi i record correnti che cambiano (valid_to + is_current=false)
    db.execute(
        text(
            staged_rows_cte
            + """
            UPDATE cat_particelle p
            SET valid_to = CURRENT_DATE,
                is_current = false,
                updated_at = now()
            FROM staged s
            WHERE
              p.is_current = true
              AND p.cod_comune_capacitas = s.cod_comune_capacitas
              AND p.foglio = s.foglio
              AND p.particella = s.particella
              AND (p.subalterno IS NOT DISTINCT FROM s.subalterno)
              AND (
                (p.national_code IS DISTINCT FROM s.national_code)
                OR (p.nome_comune IS DISTINCT FROM s.nome_comune)
                OR (p.sezione_catastale IS DISTINCT FROM s.sezione_catastale)
                OR (p.cfm IS DISTINCT FROM s.cfm)
                OR (p.superficie_mq IS DISTINCT FROM s.superficie_mq)
                OR (p.num_distretto IS DISTINCT FROM s.num_distretto)
                OR (p.nome_distretto IS DISTINCT FROM s.nome_distretto)
                OR (p.suppressed IS DISTINCT FROM s.suppressed)
                OR (
                  (p.geometry IS NULL) <> (s.geometry IS NULL)
                  OR (p.geometry IS NOT NULL AND s.geometry IS NOT NULL AND NOT ST_Equals(p.geometry, s.geometry))
                )
              )
            """
        )
    )

    # 3) Inserisci nuovi record correnti per righe staging che non hanno un current corrispondente
    inserted_current = db.execute(
        text(
            staged_rows_cte
            + """
            INSERT INTO cat_particelle (
              id,
              comune_id,
              national_code,
              cod_comune_capacitas,
              codice_catastale,
              nome_comune,
              sezione_catastale,
              foglio,
              particella,
              subalterno,
              cfm,
              superficie_mq,
              num_distretto,
              nome_distretto,
              geometry,
              source_type,
              import_batch_id,
              valid_from,
              valid_to,
              is_current,
              suppressed,
              created_at,
              updated_at
            )
            SELECT
              gen_random_uuid(),
              s.comune_id,
              s.national_code,
              s.cod_comune_capacitas,
              s.codice_catastale,
              s.nome_comune,
              s.sezione_catastale,
              s.foglio,
              s.particella,
              s.subalterno,
              s.cfm,
              s.superficie_mq,
              s.num_distretto,
              s.nome_distretto,
              s.geometry,
              'shapefile',
              :batch_id,
              CURRENT_DATE,
              NULL,
              true,
              s.suppressed,
              now(),
              now()
            FROM staged s
            LEFT JOIN cat_particelle p
              ON p.is_current = true
             AND p.cod_comune_capacitas = s.cod_comune_capacitas
             AND p.foglio = s.foglio
             AND p.particella = s.particella
             AND (p.subalterno IS NOT DISTINCT FROM s.subalterno)
            WHERE p.id IS NULL
            RETURNING id
            """
        ),
        {"batch_id": str(batch_id)},
    ).rowcount or 0

    # 4) Deriva distretti via ST_Union e upsert
    # Usiamo num_distretto + nome_distretto della particella corrente come fonte.
    upserted_distretti = db.execute(
        text(
            """
            WITH src AS (
              SELECT
                num_distretto,
                MAX(nome_distretto) AS nome_distretto,
                ST_Multi(ST_Union(geometry)) AS geom
              FROM cat_particelle
              WHERE is_current = true
                AND geometry IS NOT NULL
                AND num_distretto IS NOT NULL
                AND num_distretto <> 'FD'
              GROUP BY num_distretto
            )
            INSERT INTO cat_distretti (
              id,
              num_distretto,
              nome_distretto,
              geometry,
              attivo,
              created_at,
              updated_at
            )
            SELECT
              gen_random_uuid(),
              src.num_distretto,
              src.nome_distretto,
              src.geom,
              true,
              now(),
              now()
            FROM src
            ON CONFLICT (num_distretto) DO UPDATE
            SET
              nome_distretto = EXCLUDED.nome_distretto,
              geometry = EXCLUDED.geometry,
              updated_at = now()
            RETURNING id
            """
        )
    ).rowcount or 0

    # 5) Report e chiusura batch
    batch.righe_importate = int(inserted_current)
    batch.righe_anomalie = 0
    batch.status = "completed"
    batch.completed_at = now
    batch.report_json = {
        "staging_table": staging_table,
        "righe_staging": righe_staging,
        "records_history_written": int(moved_to_history),
        "records_inserted_current": int(inserted_current),
        "distretti_upserted": int(upserted_distretti),
        "completed_at": now.isoformat(),
        "valid_from": date.today().isoformat(),
    }
    db.add(batch)
    db.commit()

    return {
        "batch_id": str(batch_id),
        "status": batch.status,
        "report": batch.report_json,
    }
