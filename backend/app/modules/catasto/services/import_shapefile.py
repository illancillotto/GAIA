from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timezone
import io
import os
import re
import subprocess
import tempfile
from typing import Any
from uuid import UUID, uuid4
import zipfile

from sqlalchemy.engine import make_url
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatImportBatch
from app.core.config import settings
from app.modules.catasto.services.comuni_reference import (
    get_capacitas_code_by_catastale,
    get_official_name_by_catastale,
)


def _build_ogr_pg_connection_string() -> str:
    url = make_url(settings.database_url)
    if not url.drivername.startswith("postgresql"):
        raise ValueError("DATABASE_URL deve puntare a PostgreSQL per importare shapefile via ogr2ogr.")

    if not url.host or not url.database or not url.username:
        raise ValueError("DATABASE_URL incompleta: host, database e username sono obbligatori per ogr2ogr.")

    parts = [
        f"host={url.host}",
        f"port={url.port or 5432}",
        f"dbname={url.database}",
        f"user={url.username}",
    ]
    if url.password:
        parts.append(f"password={url.password}")
    return "PG:" + " ".join(parts)


def drop_staging_table(db: Session, staging_table: str = "cat_particelle_staging") -> None:
    try:
        db.rollback()
    except Exception:
        pass
    db.execute(text(f'DROP TABLE IF EXISTS "{staging_table}"'))  # nosec - internal table name
    db.commit()


def load_zip_to_staging(
    db: Session,
    *,
    zip_bytes: bytes,
    source_srid: int = 7791,
    staging_table: str = "cat_particelle_staging",
    progress_callback: Callable[[int, int], None] | None = None,
) -> str:
    """
    Estrae uno ZIP contenente .shp/.dbf/.shx e carica i dati in cat_particelle_staging.
    Restituisce il nome del file .shp trovato nell'archivio.
    """
    import shapefile as pyshp

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(tmpdir)

        shp_path: str | None = None
        for root, _, files in os.walk(tmpdir):
            for fname in files:
                if fname.lower().endswith(".shp"):
                    shp_path = os.path.join(root, fname)
                    break
            if shp_path:
                break

        if not shp_path:
            raise ValueError(
                "Nessun file .shp trovato nel ZIP. "
                "L'archivio deve contenere i file .shp, .dbf e .shx."
            )

        shp_filename = os.path.basename(shp_path)

        total = 0
        for enc in ("utf-8", "latin-1"):
            try:
                with pyshp.Reader(shp_path, encoding=enc) as sf:
                    total = len(sf)
                break
            except Exception:
                if enc == "latin-1":
                    raise
        if progress_callback:
            progress_callback(0, total)

        ogr_conn = _build_ogr_pg_connection_string()
        command = [
            "ogr2ogr",
            "--config",
            "PG_USE_COPY",
            "YES",
            "-f",
            "PostgreSQL",
            ogr_conn,
            shp_path,
            "-nln",
            staging_table,
            "-nlt",
            "PROMOTE_TO_MULTI",
            "-lco",
            "GEOMETRY_NAME=wkb_geometry",
            "-lco",
            "UNLOGGED=ON",
            "-overwrite",
            "-progress",
            "-t_srs",
            "EPSG:4326",
        ]
        if source_srid:
            command.extend(["-s_srs", f"EPSG:{int(source_srid)}"])

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        try:
            last_done = 0
            if process.stdout is not None:
                for line in process.stdout:
                    if not progress_callback or total <= 0:
                        continue
                    for pct_str in re.findall(r"(\d{1,3})", line):
                        pct = max(0, min(100, int(pct_str)))
                        done = min(total, int(total * pct / 100))
                        if done > last_done:
                            last_done = done
                            progress_callback(done, total)
            returncode = process.wait()
        finally:
            if process.stdout is not None:
                process.stdout.close()

        if returncode != 0:
            raise ValueError(f"ogr2ogr ha restituito exit code {returncode} durante il caricamento staging.")

        if progress_callback and total > 0:
            progress_callback(total, total)
        return shp_filename


def _escape_sql_string(value: str) -> str:
    return value.replace("'", "''")


def _apply_best_effort_local_settings(db: Session, statements: list[str]) -> None:
    for statement in statements:
        try:
            db.execute(text(statement))
        except Exception:
            db.rollback()


def finalize_shapefile_import(
    db: Session,
    *,
    created_by: int,
    source_srid: int | None = 7791,
    staging_table: str = "cat_particelle_staging",
    batch_id: UUID | None = None,
    filename: str | None = None,
    log_callback: Callable[[str], None] | None = None,
    cleanup_staging: bool = True,
) -> dict[str, Any]:
    """
    Finalizza l'import shapefile caricato via ogr2ogr in `cat_particelle_staging`.

    Operazioni:
    - SCD Type 2 verso `cat_particelle` (chiave operativa: cod_comune_capacitas,foglio,particella,subalterno)
    - Inserisce storico in `cat_particelle_history` per record cambiati
    - Crea `cat_import_batches` con tipo='shapefile' e report_json con conteggi

    Nota importante:
    - `cod_comune_capacitas` nel modello Catasto e il codice sorgente Capacitas,
      non il codice comune numerico ufficiale ISTAT moderno
    - il mapping da `codice catastale` a questo codice deve sempre passare dal
      dataset di riferimento `comuni_istat.csv`, mai da CASE hardcoded nel SQL
    """
    if batch_id is None:
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

    def _log(msg: str) -> None:
        if log_callback:
            log_callback(msg)

    _log(f"Staging: {righe_staging:,} righe trovate — avvio SCD2…")

    existing_batch = db.get(CatImportBatch, batch_id)

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

    if source_srid and int(source_srid) != 4326:
        _log(f"Trasformazione geometrie da SRID {source_srid} → 4326…")
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
    raw_staged AS (
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
        CASE
          WHEN t."{geom_col}" IS NOT NULL THEN ROUND(ST_Area(ST_Transform(t."{geom_col}", 3003))::numeric, 2)
          ELSE NULL
        END AS superficie_grafica_mq,
        NULLIF(TRIM(COALESCE(to_jsonb(t)->>'num_dist', to_jsonb(t)->>'NUM_DIST', to_jsonb(t)->>'num_distretto')), '') AS num_distretto,
        NULLIF(TRIM(COALESCE(to_jsonb(t)->>'nome_dist', to_jsonb(t)->>'Nome_Dist', to_jsonb(t)->>'nome_distretto')), '') AS nome_distretto,
        COALESCE(NULLIF(TRIM(to_jsonb(t)->>'suppressed'), '')::boolean, false) AS suppressed,
        t."{geom_col}" AS geometry
      FROM {staging_table} t
      CROSS JOIN LATERAL (
        SELECT NULLIF(TRIM(COALESCE(
          NULLIF(TRIM(COALESCE(to_jsonb(t)->>'codi_fisc', to_jsonb(t)->>'CODI_FISC', to_jsonb(t)->>'cod_fisc', to_jsonb(t)->>'COD_FISC')), ''),
          NULLIF(TRIM(left(split_part(COALESCE(to_jsonb(t)->>'cfm',''), '-', 1), 4)), ''),
          NULLIF(TRIM(left(COALESCE(to_jsonb(t)->>'nationalca',''), 4)), '')
        )), '') AS cod_catastale
      ) c
      LEFT JOIN mapping m
        ON m.codice_catastale = c.cod_catastale
      LEFT JOIN cat_comuni cc
        ON cc.codice_catastale = c.cod_catastale
    ),
    staged AS (
      -- Deduplica frammenti con stessa chiave operativa (es. particelle spezzate da overlay con distretti).
      -- Geometria: ST_Union di tutti i frammenti. Distretto: quello del frammento con area maggiore.
      SELECT
        MAX(codice_catastale)                                                          AS codice_catastale,
        (array_agg(comune_id ORDER BY comune_id NULLS LAST))[1]                       AS comune_id,
        cod_comune_capacitas,
        foglio,
        particella,
        subalterno,
        MAX(national_code)                                                             AS national_code,
        MAX(nome_comune)                                                               AS nome_comune,
        MAX(sezione_catastale)                                                         AS sezione_catastale,
        MAX(cfm)                                                                       AS cfm,
        SUM(superficie_mq)                                                             AS superficie_mq,
        SUM(superficie_grafica_mq)                                                     AS superficie_grafica_mq,
        (array_agg(num_distretto  ORDER BY superficie_grafica_mq DESC NULLS LAST))[1] AS num_distretto,
        (array_agg(nome_distretto ORDER BY superficie_grafica_mq DESC NULLS LAST))[1] AS nome_distretto,
        BOOL_OR(suppressed)                                                            AS suppressed,
        ST_Multi(ST_Union(geometry))                                                   AS geometry
      FROM raw_staged
      GROUP BY cod_comune_capacitas, foglio, particella, subalterno
    )
    """

    _apply_best_effort_local_settings(
        db,
        [
            "SET LOCAL work_mem = '1GB'",
            "SET LOCAL maintenance_work_mem = '4GB'",
            "SET LOCAL temp_buffers = '512MB'",
            "SET LOCAL max_parallel_workers_per_gather = 8",
            "SET LOCAL parallel_setup_cost = 100",
            "SET LOCAL parallel_tuple_cost = 0.01",
            "SET LOCAL effective_io_concurrency = 200",
            "SET LOCAL random_page_cost = 1.1",
            "SET LOCAL jit = off",
        ],
    )
    current_particelle_count = int(
        db.execute(text("SELECT COUNT(*) FROM cat_particelle WHERE is_current = true")).scalar_one()
    )

    def _store_completed_batch(
        *,
        righe_importate: int,
        report_payload: dict[str, Any],
    ) -> CatImportBatch:
        batch = existing_batch or db.get(CatImportBatch, batch_id)
        if batch is None:
            batch = CatImportBatch(
                id=batch_id,
                filename=filename or staging_table,
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
        else:
            # Reload report_json written by progress callbacks in separate sessions.
            db.refresh(batch, attribute_names=["report_json"])

        if filename:
            batch.filename = filename
        batch.righe_totali = righe_staging
        batch.righe_importate = int(righe_importate)
        batch.righe_anomalie = 0
        batch.status = "completed"
        batch.completed_at = now
        report_json = dict(batch.report_json or {})
        report_json.update(report_payload)
        batch.report_json = report_json
        db.add(batch)
        db.commit()
        if cleanup_staging:
            drop_staging_table(db, staging_table)
        return batch

    if current_particelle_count == 0:
        fast_stage_table = f"cat_particelle_fast_stage_{batch_id.hex[:8]}"
        chunk_size = 50_000

        _log("Fast path DB vuoto [1/4]: materializzazione particelle deduplicate…")
        db.execute(
            text(
                f"""
                CREATE TEMP TABLE "{fast_stage_table}" ON COMMIT DROP AS
                {staged_rows_cte}
                SELECT
                  row_number() OVER (ORDER BY cod_comune_capacitas, foglio, particella, subalterno NULLS FIRST) AS seq,
                  s.*
                FROM staged s
                """
            )
        )
        db.execute(text(f'CREATE INDEX "{fast_stage_table}_seq_idx" ON "{fast_stage_table}" (seq)'))
        deduped_count = int(db.execute(text(f'SELECT COUNT(*) FROM "{fast_stage_table}"')).scalar_one())
        _log(f"Fast path DB vuoto [1/4]: {deduped_count:,} particelle uniche materializzate")

        _log("Fast path DB vuoto [2/4]: inserimento particelle correnti a chunk…")
        inserted_current = 0
        for chunk_start in range(1, deduped_count + 1, chunk_size):
            chunk_end = min(chunk_start + chunk_size - 1, deduped_count)
            db.execute(
                text(
                    f"""
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
                      superficie_grafica_mq,
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
                      s.superficie_grafica_mq,
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
                    FROM "{fast_stage_table}" s
                    WHERE s.seq BETWEEN :chunk_start AND :chunk_end
                    """
                ),
                {
                    "batch_id": str(batch_id),
                    "chunk_start": chunk_start,
                    "chunk_end": chunk_end,
                },
            )
            inserted_current = chunk_end
            _log(
                f"Fast path DB vuoto [2/4]: {inserted_current:,} / {deduped_count:,} particelle inserite"
            )

        _log("Fast path DB vuoto [3/3]: commit import particelle in corso…")

        batch = _store_completed_batch(
            righe_importate=int(inserted_current),
            report_payload={
                "staging_table": staging_table,
                "righe_staging": righe_staging,
                "records_deduped_unique": int(deduped_count),
                "records_history_written": 0,
                "records_inserted_current": int(inserted_current),
                "fast_path_empty_db": True,
                "completed_at": now.isoformat(),
                "valid_from": date.today().isoformat(),
            },
        )

        return {
            "batch_id": str(batch_id),
            "status": batch.status,
            "report": batch.report_json,
        }

    # 1) Inserisci nello storico tutte le particelle correnti che cambiano (SCD2)
    _log("SCD2 [1/4]: scrittura record modificati in storico…")
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
                OR (p.superficie_grafica_mq IS DISTINCT FROM s.superficie_grafica_mq)
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
              superficie_grafica_mq,
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
              c.superficie_grafica_mq,
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

    _log(f"SCD2 [1/4]: {moved_to_history:,} record spostati in storico")

    # 2) Chiudi i record correnti che cambiano (valid_to + is_current=false)
    _log("SCD2 [2/4]: chiusura record correnti modificati…")
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
                OR (p.superficie_grafica_mq IS DISTINCT FROM s.superficie_grafica_mq)
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
    _log("SCD2 [3/4]: inserimento nuove particelle correnti…")
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
              superficie_grafica_mq,
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
              s.superficie_grafica_mq,
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

    _log(f"SCD2 [3/4]: {inserted_current:,} particelle inserite")

    _log("SCD2 [4/4]: commit import particelle in corso…")

    batch = _store_completed_batch(
        righe_importate=int(inserted_current),
        report_payload={
            "staging_table": staging_table,
            "righe_staging": righe_staging,
            "records_history_written": int(moved_to_history),
            "records_inserted_current": int(inserted_current),
            "fast_path_empty_db": False,
            "completed_at": now.isoformat(),
            "valid_from": date.today().isoformat(),
        },
    )

    return {
        "batch_id": str(batch_id),
        "status": batch.status,
        "report": batch.report_json,
    }
