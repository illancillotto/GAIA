from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_admin_user
from app.core.database import SessionLocal, get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatAnomalia, CatImportBatch, CatUtenzaIrrigua
from app.modules.catasto.services.import_distretti import finalize_distretti_shapefile_import
from app.modules.catasto.services.import_capacitas import CapacitasImportDuplicateError, import_capacitas_excel
from app.modules.catasto.services.import_shapefile import drop_staging_table, finalize_shapefile_import, load_zip_to_staging
from app.schemas.catasto_phase1 import (
    CatAnomaliaListResponse,
    CatAnomaliaResponse,
    CatImportBatchResponse,
    CatImportStartResponse,
    CatImportSummaryResponse,
)

router = APIRouter(prefix="/catasto/import", tags=["catasto-import"])


def _run_import(batch_id: uuid.UUID, file_bytes: bytes, filename: str, created_by: int, force: bool) -> None:
    db = SessionLocal()
    try:
        import_capacitas_excel(
            db=db,
            file_bytes=file_bytes,
            filename=filename,
            created_by=created_by,
            force=force,
            batch_id=batch_id,
        )
    except Exception as exc:
        batch = db.get(CatImportBatch, batch_id)
        if batch is not None:
            batch.status = "failed"
            batch.errore = str(exc)
            db.commit()
        else:
            db.rollback()
    finally:
        db.close()


@router.post("/capacitas", response_model=CatImportStartResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_capacitas(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    force: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_admin_user),
) -> CatImportStartResponse:
    file_bytes = file.file.read()
    batch_id = uuid.uuid4()
    placeholder = CatImportBatch(
        id=batch_id,
        filename=file.filename or "capacitas.xlsx",
        tipo="capacitas_ruolo",
        status="processing",
        righe_totali=0,
        righe_importate=0,
        righe_anomalie=0,
        created_by=current_user.id,
    )
    db.add(placeholder)
    db.commit()
    background_tasks.add_task(_run_import, batch_id, file_bytes, file.filename or "capacitas.xlsx", current_user.id, force)
    return CatImportStartResponse(batch_id=batch_id, status="processing")


@router.get("/{batch_id}/status", response_model=CatImportBatchResponse)
def get_import_status(batch_id: uuid.UUID, db: Session = Depends(get_db), _: ApplicationUser = Depends(require_active_user)) -> CatImportBatch:
    batch = db.get(CatImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import batch not found")
    return batch


@router.get("/{batch_id}/report", response_model=CatAnomaliaListResponse)
def get_import_report(
    batch_id: uuid.UUID,
    tipo: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAnomaliaListResponse:
    batch = db.get(CatImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import batch not found")

    query = (
        select(CatAnomalia)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
        .where(CatUtenzaIrrigua.import_batch_id == batch_id)
        .order_by(desc(CatAnomalia.created_at))
    )
    count_query = (
        select(func.count())
        .select_from(CatAnomalia)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
        .where(CatUtenzaIrrigua.import_batch_id == batch_id)
    )
    if tipo:
        query = query.where(CatAnomalia.tipo == tipo)
        count_query = count_query.where(CatAnomalia.tipo == tipo)

    total = db.execute(count_query).scalar_one()
    items = db.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return CatAnomaliaListResponse(
        items=[CatAnomaliaResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/history", response_model=list[CatImportBatchResponse])
def get_import_history(
    status_filter: str | None = Query(None, alias="status"),
    tipo: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> list[CatImportBatch]:
    query = select(CatImportBatch).order_by(desc(CatImportBatch.created_at))
    if status_filter:
        query = query.where(CatImportBatch.status == status_filter)
    if tipo:
        query = query.where(CatImportBatch.tipo == tipo)
    return list(db.execute(query.limit(limit)).scalars().all())


@router.get("/summary", response_model=CatImportSummaryResponse)
def get_import_summary(
    tipo: str | None = Query(None),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatImportSummaryResponse:
    filters = [CatImportBatch.tipo == tipo] if tipo else []

    counts = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(case((CatImportBatch.status == "processing", 1), else_=0)), 0),
            func.coalesce(func.sum(case((CatImportBatch.status == "completed", 1), else_=0)), 0),
            func.coalesce(func.sum(case((CatImportBatch.status == "failed", 1), else_=0)), 0),
            func.coalesce(func.sum(case((CatImportBatch.status == "replaced", 1), else_=0)), 0),
            func.max(CatImportBatch.completed_at),
        ).where(*filters)
    ).one()

    return CatImportSummaryResponse(
        tipo=tipo,
        totale_batch=int(counts[0] or 0),
        processing_batch=int(counts[1] or 0),
        completed_batch=int(counts[2] or 0),
        failed_batch=int(counts[3] or 0),
        replaced_batch=int(counts[4] or 0),
        ultimo_completed_at=counts[5],
    )


def _append_step(
    batch_id: uuid.UUID,
    msg: str,
    righe_elaborate: int | None = None,
    righe_totali: int | None = None,
) -> None:
    """Aggiunge un log step a report_json usando una sessione separata (non-transazionale)."""
    from datetime import datetime, timezone as _tz

    db2 = SessionLocal()
    try:
        batch = db2.get(CatImportBatch, batch_id)
        if batch is None:
            return
        rj: dict = dict(batch.report_json or {})
        steps: list = list(rj.get("steps", []))
        steps.append({"ts": datetime.now(_tz.utc).strftime("%H:%M:%S"), "msg": msg})
        rj["steps"] = steps
        if righe_elaborate is not None:
            batch.righe_importate = righe_elaborate
        if righe_totali is not None:
            batch.righe_totali = righe_totali
        batch.report_json = rj
        db2.commit()
    except Exception:
        db2.rollback()
    finally:
        db2.close()


def _run_shapefile_import(
    batch_id: uuid.UUID,
    zip_bytes: bytes,
    shp_filename: str,
    created_by: int,
    source_srid: int,
) -> None:
    db = SessionLocal()
    staging_table = "cat_particelle_staging"
    try:
        _append_step(batch_id, "Estrazione archivio ZIP in corso…")

        last_pct: list[float] = [0.0]

        def staging_progress(done: int, total: int) -> None:
            if done == 0:
                _append_step(batch_id, f"Avvio caricamento: {total:,} righe nel file", righe_totali=total)
                return
            pct = done / total if total else 0
            if pct >= last_pct[0] + 0.10 or done == total:
                last_pct[0] = pct
                _append_step(
                    batch_id,
                    f"Staging: {done:,} / {total:,} righe ({int(pct * 100)}%)",
                    righe_elaborate=done,
                    righe_totali=total,
                )

        actual_filename = load_zip_to_staging(
            db,
            zip_bytes=zip_bytes,
            source_srid=source_srid,
            staging_table=staging_table,
            progress_callback=staging_progress,
        )
        _append_step(batch_id, f"Staging completato — {actual_filename}")

        finalize_shapefile_import(
            db,
            created_by=created_by,
            source_srid=source_srid,
            batch_id=batch_id,
            filename=actual_filename,
            log_callback=lambda msg: _append_step(batch_id, msg),
            cleanup_staging=False,
        )
    except Exception as exc:
        _append_step(batch_id, f"Errore: {exc}")
        db2 = SessionLocal()
        try:
            batch = db2.get(CatImportBatch, batch_id)
            if batch is not None:
                batch.status = "failed"
                batch.errore = str(exc)
                db2.commit()
        except Exception:
            db2.rollback()
        finally:
            db2.close()
    finally:
        try:
            drop_staging_table(db, staging_table)
        except Exception:
            db.rollback()
        db.close()


def _run_distretti_shapefile_import(
    batch_id: uuid.UUID,
    zip_bytes: bytes,
    shp_filename: str,
    created_by: int,
    source_srid: int,
) -> None:
    db = SessionLocal()
    staging_table = "cat_distretti_staging"
    try:
        _append_step(batch_id, "Estrazione archivio ZIP distretti in corso…")

        last_pct: list[float] = [0.0]

        def staging_progress(done: int, total: int) -> None:
            if done == 0:
                _append_step(batch_id, f"Avvio caricamento distretti: {total:,} righe nel file", righe_totali=total)
                return
            pct = done / total if total else 0
            if pct >= last_pct[0] + 0.10 or done == total:
                last_pct[0] = pct
                _append_step(
                    batch_id,
                    f"Staging distretti: {done:,} / {total:,} righe ({int(pct * 100)}%)",
                    righe_elaborate=done,
                    righe_totali=total,
                )

        actual_filename = load_zip_to_staging(
            db,
            zip_bytes=zip_bytes,
            source_srid=source_srid,
            staging_table=staging_table,
            progress_callback=staging_progress,
        )
        _append_step(batch_id, f"Staging distretti completato — {actual_filename}")

        finalize_distretti_shapefile_import(
            db,
            created_by=created_by,
            source_srid=source_srid,
            batch_id=batch_id,
            filename=actual_filename,
            log_callback=lambda msg: _append_step(batch_id, msg),
            cleanup_staging=False,
        )
    except Exception as exc:
        _append_step(batch_id, f"Errore: {exc}")
        db2 = SessionLocal()
        try:
            batch = db2.get(CatImportBatch, batch_id)
            if batch is not None:
                batch.status = "failed"
                batch.errore = str(exc)
                db2.commit()
        except Exception:
            db2.rollback()
        finally:
            db2.close()
    finally:
        try:
            drop_staging_table(db, staging_table)
        except Exception:
            db.rollback()
        db.close()


@router.post("/shapefile/upload", response_model=CatImportStartResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_shapefile(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_srid: int = Query(4326),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_admin_user),
) -> CatImportStartResponse:
    """
    Upload di un archivio ZIP contenente i file shapefile (.shp, .dbf, .shx).
    Carica le particelle in staging e avvia la finalizzazione SCD2 in background.
    """
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Il file deve essere un archivio ZIP (.zip) contenente .shp, .dbf e .shx.",
        )
    zip_bytes = file.file.read()
    batch_id = uuid.uuid4()
    placeholder = CatImportBatch(
        id=batch_id,
        filename=file.filename or "shapefile.zip",
        tipo="shapefile",
        status="processing",
        righe_totali=0,
        righe_importate=0,
        righe_anomalie=0,
        created_by=current_user.id,
    )
    db.add(placeholder)
    db.commit()
    background_tasks.add_task(
        _run_shapefile_import,
        batch_id,
        zip_bytes,
        file.filename or "shapefile.zip",
        current_user.id,
        source_srid,
    )
    return CatImportStartResponse(batch_id=batch_id, status="processing")


@router.post("/shapefile/finalize")
def finalize_shapefile(
    cleanup_staging: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_admin_user),
):
    """
    Finalizza import shapefile caricato in `cat_particelle_staging` via ogr2ogr.
    Crea un batch di tipo 'shapefile' e aggiorna solo cat_particelle.
    """
    try:
        return finalize_shapefile_import(db, created_by=current_user.id, cleanup_staging=cleanup_staging)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/distretti/upload", response_model=CatImportStartResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_distretti_shapefile(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_srid: int = Query(4326),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_admin_user),
) -> CatImportStartResponse:
    """
    Upload di un archivio ZIP contenente il layer shapefile dei distretti.
    Carica i dati in staging e avvia la finalizzazione autonoma dei confini in background.
    """
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Il file deve essere un archivio ZIP (.zip) contenente .shp, .dbf e .shx.",
        )
    zip_bytes = file.file.read()
    batch_id = uuid.uuid4()
    placeholder = CatImportBatch(
        id=batch_id,
        filename=file.filename or "distretti.zip",
        tipo="shapefile_distretti",
        status="processing",
        righe_totali=0,
        righe_importate=0,
        righe_anomalie=0,
        created_by=current_user.id,
    )
    db.add(placeholder)
    db.commit()
    background_tasks.add_task(
        _run_distretti_shapefile_import,
        batch_id,
        zip_bytes,
        file.filename or "distretti.zip",
        current_user.id,
        source_srid,
    )
    return CatImportStartResponse(batch_id=batch_id, status="processing")


@router.post("/distretti/finalize")
def finalize_distretti_shapefile(
    cleanup_staging: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_admin_user),
):
    """
    Finalizza import shapefile distretti caricato in `cat_distretti_staging` via ogr2ogr.
    Crea un batch di tipo 'shapefile_distretti' e aggiorna i confini correnti con storico geometrico.
    """
    try:
        return finalize_distretti_shapefile_import(db, created_by=current_user.id, cleanup_staging=cleanup_staging)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
