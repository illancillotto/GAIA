from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatImportBatch
from app.modules.catasto.services.import_shapefile import _apply_best_effort_local_settings, drop_staging_table


def finalize_distretti_shapefile_import(
    db: Session,
    *,
    created_by: int,
    source_srid: int | None = 7791,
    staging_table: str = "cat_distretti_staging",
    batch_id: UUID | None = None,
    filename: str | None = None,
    log_callback: Callable[[str], None] | None = None,
    cleanup_staging: bool = True,
) -> dict[str, Any]:
    """
    Finalizza un import shapefile autonomo dei distretti.

    Operazioni:
    - normalizza attributi e geometrie del layer distretti
    - aggrega eventuali feature multiple per `num_distretto`
    - aggiorna `cat_distretti` mantenendo l'identità stabile del distretto
    - storicizza le geometrie correnti in `cat_distretti_geometry_versions`
    - crea/aggiorna `cat_import_batches` con tipo='shapefile_distretti'
    """
    if batch_id is None:
        batch_id = uuid4()
    now = datetime.now(timezone.utc)

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

    righe_staging = int(
        db.execute(text(f'SELECT COUNT(*) FROM "{staging_table}"')).scalar_one()  # nosec - controlled internal table name
    )

    def _log(msg: str) -> None:
        if log_callback:
            log_callback(msg)

    _log(f"Staging distretti: {righe_staging:,} righe trovate — avvio finalizzazione…")

    existing_batch = db.get(CatImportBatch, batch_id)
    if existing_batch is None:
        existing_batch = CatImportBatch(
            id=batch_id,
            filename=filename or staging_table,
            tipo="shapefile_distretti",
            anno_campagna=None,
            hash_file=None,
            righe_totali=righe_staging,
            righe_importate=0,
            righe_anomalie=0,
            status="processing",
            created_by=created_by,
            created_at=now,
        )
        db.add(existing_batch)
        db.flush()

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
        _log(f"Trasformazione geometrie distretti da SRID {source_srid} → 4326…")
        db.execute(
            text(
                f"""
                UPDATE "{staging_table}"
                SET "{geom_col}" = ST_Transform(ST_SetSRID("{geom_col}", :src_srid), 4326)
                WHERE "{geom_col}" IS NOT NULL
                """
            ),
            {"src_srid": int(source_srid)},
        )

    _apply_best_effort_local_settings(
        db,
        [
            "SET LOCAL work_mem = '512MB'",
            "SET LOCAL maintenance_work_mem = '1GB'",
            "SET LOCAL temp_buffers = '256MB'",
            "SET LOCAL max_parallel_workers_per_gather = 4",
            "SET LOCAL jit = off",
        ],
    )

    raw_stage_table = f"cat_distretti_raw_stage_{batch_id.hex[:8]}"
    agg_stage_table = f"cat_distretti_agg_stage_{batch_id.hex[:8]}"
    delta_stage_table = f"cat_distretti_delta_stage_{batch_id.hex[:8]}"

    _log("Distretti [1/4]: normalizzazione staging…")
    db.execute(
        text(
            f"""
            CREATE TEMP TABLE "{raw_stage_table}" ON COMMIT DROP AS
            SELECT
              NULLIF(TRIM(COALESCE(
                to_jsonb(t)->>'num_dist',
                to_jsonb(t)->>'NUM_DIST',
                to_jsonb(t)->>'num_distretto',
                to_jsonb(t)->>'distretto',
                to_jsonb(t)->>'DISTRETTO'
              )), '') AS num_distretto,
              NULLIF(TRIM(COALESCE(
                to_jsonb(t)->>'nome_dist',
                to_jsonb(t)->>'Nome_Dist',
                to_jsonb(t)->>'nome_distretto',
                to_jsonb(t)->>'NOME_DIST',
                to_jsonb(t)->>'nome'
              )), '') AS nome_distretto,
              CASE
                WHEN t."{geom_col}" IS NULL THEN NULL
                ELSE ST_Multi(ST_CollectionExtract(ST_MakeValid(t."{geom_col}"), 3))
              END AS geometry
            FROM "{staging_table}" t
            """
        )
    )
    skipped_missing_num = int(
        db.execute(text(f'SELECT COUNT(*) FROM "{raw_stage_table}" WHERE num_distretto IS NULL')).scalar_one()
    )
    skipped_missing_geom = int(
        db.execute(
            text(
                f'''
                SELECT COUNT(*)
                FROM "{raw_stage_table}"
                WHERE geometry IS NULL OR ST_IsEmpty(geometry)
                '''
            )
        ).scalar_one()
    )

    _log("Distretti [2/4]: aggregazione per distretto…")
    db.execute(
        text(
            f"""
            CREATE TEMP TABLE "{agg_stage_table}" ON COMMIT DROP AS
            SELECT
              num_distretto,
              MAX(nome_distretto) AS nome_distretto,
              ST_Multi(ST_CollectionExtract(ST_UnaryUnion(ST_Collect(geometry)), 3)) AS geometry
            FROM "{raw_stage_table}"
            WHERE num_distretto IS NOT NULL
              AND geometry IS NOT NULL
              AND NOT ST_IsEmpty(geometry)
            GROUP BY num_distretto
            """
        )
    )
    valid_distretti = int(db.execute(text(f'SELECT COUNT(*) FROM "{agg_stage_table}"')).scalar_one())
    if valid_distretti == 0:
        raise ValueError("Nessun distretto valido trovato nello shapefile caricato.")

    _log("Distretti [3/4]: calcolo delta rispetto ai confini correnti…")
    db.execute(
        text(
            f"""
            CREATE TEMP TABLE "{delta_stage_table}" ON COMMIT DROP AS
            SELECT
              COALESCE(d.id, gen_random_uuid()) AS distretto_id,
              d.id AS existing_id,
              s.num_distretto,
              s.nome_distretto,
              s.geometry,
              CASE
                WHEN d.id IS NULL THEN 'insert'
                WHEN d.nome_distretto IS DISTINCT FROM s.nome_distretto
                  OR ((d.geometry IS NULL) <> (s.geometry IS NULL))
                  OR (d.geometry IS NOT NULL AND s.geometry IS NOT NULL AND NOT ST_Equals(d.geometry, s.geometry))
                THEN 'update'
                ELSE 'noop'
              END AS action
            FROM "{agg_stage_table}" s
            LEFT JOIN cat_distretti d
              ON d.num_distretto = s.num_distretto
            """
        )
    )
    inserted_distretti = int(
        db.execute(text(f"""SELECT COUNT(*) FROM "{delta_stage_table}" WHERE action = 'insert'""")).scalar_one()
    )
    updated_distretti = int(
        db.execute(text(f"""SELECT COUNT(*) FROM "{delta_stage_table}" WHERE action = 'update'""")).scalar_one()
    )
    unchanged_distretti = int(
        db.execute(text(f"""SELECT COUNT(*) FROM "{delta_stage_table}" WHERE action = 'noop'""")).scalar_one()
    )
    missing_from_snapshot = int(
        db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM cat_distretti d
                WHERE NOT EXISTS (
                  SELECT 1
                  FROM "{agg_stage_table}" s
                  WHERE s.num_distretto = d.num_distretto
                )
                """
            )
        ).scalar_one()
    )

    _log("Distretti [4/4]: upsert distretti e scrittura storico geometrie…")
    db.execute(
        text(
            f"""
            UPDATE cat_distretti d
            SET
              nome_distretto = src.nome_distretto,
              geometry = src.geometry,
              attivo = true,
              updated_at = now()
            FROM "{delta_stage_table}" src
            WHERE src.action = 'update'
              AND d.id = src.distretto_id
            """
        )
    )
    db.execute(
        text(
            f"""
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
              src.distretto_id,
              src.num_distretto,
              src.nome_distretto,
              src.geometry,
              true,
              now(),
              now()
            FROM "{delta_stage_table}" src
            WHERE src.action = 'insert'
            """
        )
    )
    db.execute(
        text(
            f"""
            UPDATE cat_distretti_geometry_versions v
            SET valid_to = CURRENT_DATE,
                is_current = false
            WHERE v.is_current = true
              AND EXISTS (
                SELECT 1
                FROM "{delta_stage_table}" src
                WHERE src.distretto_id = v.distretto_id
                  AND src.action IN ('insert', 'update')
              )
            """
        )
    )
    versioned_distretti = db.execute(
        text(
            f"""
            INSERT INTO cat_distretti_geometry_versions (
              id,
              distretto_id,
              source_batch_id,
              source_filename,
              num_distretto,
              nome_distretto,
              geometry,
              valid_from,
              valid_to,
              is_current,
              created_at
            )
            SELECT
              gen_random_uuid(),
              src.distretto_id,
              :batch_id,
              :source_filename,
              src.num_distretto,
              src.nome_distretto,
              src.geometry,
              CURRENT_DATE,
              NULL,
              true,
              now()
            FROM "{delta_stage_table}" src
            WHERE src.action IN ('insert', 'update')
            RETURNING id
            """
        ),
        {"batch_id": str(batch_id), "source_filename": filename or staging_table},
    ).rowcount or 0

    def _store_completed_batch(*, report_payload: dict[str, Any]) -> CatImportBatch:
        batch = existing_batch or db.get(CatImportBatch, batch_id)
        if batch is None:
            raise ValueError("Batch distretti non disponibile durante la finalizzazione.")
        db.refresh(batch, attribute_names=["report_json"])

        if filename:
            batch.filename = filename
        batch.righe_totali = righe_staging
        batch.righe_importate = valid_distretti
        batch.righe_anomalie = skipped_missing_num + skipped_missing_geom
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

    batch = _store_completed_batch(
        report_payload={
            "staging_table": staging_table,
            "righe_staging": righe_staging,
            "distretti_validi": valid_distretti,
            "distretti_inseriti": inserted_distretti,
            "distretti_aggiornati": updated_distretti,
            "distretti_invariati": unchanged_distretti,
            "distretti_versionati": int(versioned_distretti),
            "distretti_assenti_nello_snapshot": missing_from_snapshot,
            "righe_scartate_senza_numero": skipped_missing_num,
            "righe_scartate_senza_geometria": skipped_missing_geom,
            "completed_at": now.isoformat(),
            "valid_from": date.today().isoformat(),
        }
    )

    return {
        "batch_id": str(batch_id),
        "status": batch.status,
        "report": batch.report_json,
    }
