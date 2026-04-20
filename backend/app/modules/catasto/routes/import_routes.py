from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_admin_user
from app.core.database import SessionLocal, get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatAnomalia, CatImportBatch, CatUtenzaIrrigua
from app.modules.catasto.services.import_capacitas import CapacitasImportDuplicateError, import_capacitas_excel
from app.modules.catasto.services.import_shapefile import finalize_shapefile_import
from app.schemas.catasto_phase1 import (
    CatAnomaliaListResponse,
    CatAnomaliaResponse,
    CatImportBatchResponse,
    CatImportStartResponse,
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
def get_import_history(db: Session = Depends(get_db), _: ApplicationUser = Depends(require_active_user)) -> list[CatImportBatch]:
    return list(db.execute(select(CatImportBatch).order_by(desc(CatImportBatch.created_at)).limit(50)).scalars().all())


@router.post("/shapefile/finalize")
def finalize_shapefile(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_admin_user),
):
    """
    Finalizza import shapefile caricato in `cat_particelle_staging` via ogr2ogr.
    Crea un batch di tipo 'shapefile' e aggiorna cat_particelle + cat_distretti.
    """
    try:
        return finalize_shapefile_import(db, created_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
