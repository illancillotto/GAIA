from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatImportBatch


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
    - SCD Type 2 verso `cat_particelle` (chiave: cod_comune_istat,foglio,particella,subalterno)
    - Inserisce storico in `cat_particelle_history` per record cambiati
    - Deriva e upserta `cat_distretti` via ST_Union sulle particelle correnti
    - Crea `cat_import_batches` con tipo='shapefile' e report_json con conteggi
    """
    batch_id = uuid4()
    now = datetime.now(timezone.utc)

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

    # Normalizza geometria se necessario (assumiamo che ogr2ogr abbia già trasformato in 4326,
    # ma manteniamo una guardia per import "grezzo")
    if source_srid and int(source_srid) != 4326:
        db.execute(
            text(
                f"""
                UPDATE {staging_table}
                SET geometry = ST_Transform(ST_SetSRID(geometry, :src_srid), 4326)
                WHERE geometry IS NOT NULL
                """
            ),
            {"src_srid": int(source_srid)},
        )

    # Mapping colonne staging -> canonical (tollerante a naming diversi)
    # Nota: si appoggia a COALESCE e cast per gestire shapefile con colonne diverse.
    staged_rows_cte = f"""
    WITH staged AS (
      SELECT
        -- chiave catastale
        COALESCE("cod_comune_istat"::int, "COM"::int, "COD_COM"::int, "COD_ISTAT"::int) AS cod_comune_istat,
        COALESCE(NULLIF(TRIM(COALESCE("foglio"::text, "FOGLIO"::text, "FOGL"::text)), ''), '') AS foglio,
        COALESCE(NULLIF(TRIM(COALESCE("particella"::text, "PARTIC"::text, "PART"::text)), ''), '') AS particella,
        NULLIF(TRIM(COALESCE("subalterno"::text, "SUB"::text, "SUBA_PART"::text)), '') AS subalterno,

        -- attributi
        NULLIF(TRIM(COALESCE("national_code"::text, "NATIONALCA"::text, "NATIONAL_CODE"::text)), '') AS national_code,
        NULLIF(TRIM(COALESCE("nome_comune"::text, "COMUNE"::text, "NOME_COM"::text)), '') AS nome_comune,
        NULLIF(TRIM(COALESCE("sezione_catastale"::text, "SEZIONE"::text, "SEZI_CENS"::text)), '') AS sezione_catastale,
        NULLIF(TRIM(COALESCE("cfm"::text, "CFM"::text)), '') AS cfm,
        COALESCE("superficie_mq"::numeric, "SUPE_PART"::numeric, "SUP_MQ"::numeric) AS superficie_mq,
        NULLIF(TRIM(COALESCE("num_distretto"::text, "NUM_DIST"::text)), '') AS num_distretto,
        NULLIF(TRIM(COALESCE("nome_distretto"::text, "Nome_Dist"::text, "NOME_DIST"::text)), '') AS nome_distretto,
        COALESCE("suppressed"::boolean, false) AS suppressed,
        geometry
      FROM {staging_table}
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
               AND p.cod_comune_istat = s.cod_comune_istat
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
              national_code,
              cod_comune_istat,
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
              c.national_code,
              c.cod_comune_istat,
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
              AND p.cod_comune_istat = s.cod_comune_istat
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
              national_code,
              cod_comune_istat,
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
              s.national_code,
              s.cod_comune_istat,
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
             AND p.cod_comune_istat = s.cod_comune_istat
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

