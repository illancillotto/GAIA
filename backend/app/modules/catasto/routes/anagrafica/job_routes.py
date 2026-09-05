from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto import (
    CatastoDistrettoExportJob,
    CatastoElaborazioniMassiveJob,
    CatastoElaborazioniMassiveJobStatus,
)
from app.modules.catasto.routes.anagrafica.distretto_routes import (
    _build_distretto_export_results,
    _write_distretto_export_file,
)
from app.modules.catasto.routes.anagrafica.execution import execute_bulk_search_payload
from app.modules.catasto.routes.anagrafica.exports import (
    _build_bulk_export_rows,
    _bulk_job_row_label,
    _export_basename,
    _stream_bulk_export_csv,
    _stream_bulk_export_xlsx,
)
from app.modules.catasto.routes.anagrafica.matching import _results_need_live_refresh
from app.modules.catasto.routes.anagrafica.normalization import (
    _build_summary,
    _empty_bulk_summary,
    _infer_bulk_kind,
    _norm_str,
    _normalize_bulk_payload,
)
from app.modules.catasto.routes.anagrafica.uploads import (
    _bulk_job_detail_from_model,
    _parse_bulk_upload_file,
    _update_bulk_job_progress,
)
from app.schemas.catasto_phase1 import (
    CatAnagraficaBulkJobCreateRequest,
    CatAnagraficaBulkJobDetail,
    CatAnagraficaBulkJobItem,
    CatAnagraficaBulkJobListResponse,
    CatAnagraficaBulkJobSaveRequest,
    CatAnagraficaBulkJobSummary,
    CatAnagraficaBulkSearchRequest,
    CatAnagraficaBulkSearchResponse,
    CatAnagraficaBulkSearchRow,
    CatAnagraficaBulkSearchRowResult,
)

router = APIRouter(
    prefix="/catasto/elaborazioni-massive/particelle", tags=["catasto-elaborazioni-massive"]
)
logger = logging.getLogger(__name__)
CATASTO_DISTRETTO_EXPORT_STORAGE_PATH = Path(
    os.getenv("CATASTO_DISTRETTO_EXPORT_STORAGE_PATH", "/data/catasto/exports/distretti")
)


# fmt: off

@router.post("", response_model=CatAnagraficaBulkSearchResponse)
async def bulk_search_anagrafica(
    payload: CatAnagraficaBulkSearchRequest = Body(...),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAnagraficaBulkSearchResponse:
    return await execute_bulk_search_payload(payload, db)


@router.post("/jobs/upload", response_model=CatAnagraficaBulkJobDetail)
async def upload_bulk_search_job(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> CatAnagraficaBulkJobDetail:
    filename = file.filename or "catasto-bulk-upload.xlsx"
    file_bytes = await file.read()
    kind, rows, skipped = _parse_bulk_upload_file(file_bytes, filename)
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File vuoto o senza righe valide.")
    payload = _normalize_bulk_payload(
        CatAnagraficaBulkSearchRequest(
            kind=kind,
            include_capacitas_live=True,
            rows=rows,
        )
    )
    request = CatAnagraficaBulkJobCreateRequest(
        source_filename=filename,
        skipped_rows=skipped,
        payload=payload,
    )
    return await create_bulk_search_job(request=request, db=db, user=user)


@router.post("/jobs", response_model=CatAnagraficaBulkJobDetail)
async def create_bulk_search_job(
    request: CatAnagraficaBulkJobCreateRequest = Body(...),
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> CatAnagraficaBulkJobDetail:
    payload = _normalize_bulk_payload(request.payload)
    kind: Literal["CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"] = _infer_bulk_kind(payload)
    job = CatastoElaborazioniMassiveJob(
        user_id=user.id,
        kind=str(kind),
        status=CatastoElaborazioniMassiveJobStatus.PENDING.value,
        source_filename=_norm_str(request.source_filename),
        skipped_rows=max(int(request.skipped_rows or 0), 0),
        total_rows=len(payload.rows),
        processed_rows=0,
        current_label="Queued for worker",
        payload_json=payload.model_dump(mode="json"),
        results_json={"results": []},
        summary_json=_empty_bulk_summary(len(payload.rows)),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _bulk_job_detail_from_model(job, results=[])


@router.post("/jobs/save", response_model=CatAnagraficaBulkJobDetail)
async def save_bulk_search_job(
    request: CatAnagraficaBulkJobSaveRequest = Body(...),
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> CatAnagraficaBulkJobDetail:
    payload = _normalize_bulk_payload(request.payload)
    kind = _infer_bulk_kind(payload)
    summary = _build_summary(request.results)
    job = CatastoElaborazioniMassiveJob(
        user_id=user.id,
        kind=str(kind),
        status=CatastoElaborazioniMassiveJobStatus.COMPLETED.value,
        source_filename=_norm_str(request.source_filename),
        skipped_rows=max(int(request.skipped_rows or 0), 0),
        total_rows=len(payload.rows),
        processed_rows=len(request.results),
        current_label="Elaborazione completata.",
        payload_json=payload.model_dump(mode="json"),
        results_json={"results": [r.model_dump(mode="json") for r in request.results]},
        summary_json=summary,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _bulk_job_detail_from_model(job, results=request.results)


@router.get("/jobs", response_model=CatAnagraficaBulkJobListResponse)
async def list_bulk_search_jobs(
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
    limit: int = Query(5, ge=1, le=20),
) -> CatAnagraficaBulkJobListResponse:
    rows = (
        db.execute(
            select(CatastoElaborazioniMassiveJob)
            .where(CatastoElaborazioniMassiveJob.user_id == user.id)
            .order_by(desc(CatastoElaborazioniMassiveJob.created_at))
            .limit(limit)
        )
        .scalars()
        .all()
    )

    items: list[CatAnagraficaBulkJobItem] = []
    for job in rows:
        items.append(
            CatAnagraficaBulkJobItem(
                id=job.id,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                source_filename=job.source_filename,
                kind=job.kind,  # type: ignore[arg-type]
                status=job.status,  # type: ignore[arg-type]
                skipped_rows=job.skipped_rows,
                total_rows=job.total_rows,
                processed_rows=job.processed_rows,
                current_label=job.current_label,
                error_message=job.error_message,
                summary=CatAnagraficaBulkJobSummary(**job.summary_json),
            )
        )

    return CatAnagraficaBulkJobListResponse(items=items)


@router.delete("/jobs", response_model=dict[str, int])
async def delete_bulk_search_jobs(
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> dict[str, int]:
    rows = (
        db.execute(
            select(CatastoElaborazioniMassiveJob).where(CatastoElaborazioniMassiveJob.user_id == user.id)
        )
        .scalars()
        .all()
    )
    deleted = len(rows)
    for job in rows:
        db.delete(job)
    db.commit()
    return {"deleted": deleted}


@router.get("/jobs/{job_id}", response_model=CatAnagraficaBulkJobDetail)
async def get_bulk_search_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> CatAnagraficaBulkJobDetail:
    job = (
        db.execute(
            select(CatastoElaborazioniMassiveJob)
            .where(CatastoElaborazioniMassiveJob.id == job_id)
            .where(CatastoElaborazioniMassiveJob.user_id == user.id)
            .limit(1)
        )
        .scalars()
        .one_or_none()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")

    raw_results = job.results_json.get("results") if isinstance(job.results_json, dict) else None
    results = [CatAnagraficaBulkSearchRowResult.model_validate(r) for r in (raw_results or [])]

    payload_has_live_results = (
        isinstance(job.payload_json, dict)
        and bool(job.payload_json.get("include_capacitas_live"))
    )
    should_refresh_live_results = (
        job.status == CatastoElaborazioniMassiveJobStatus.COMPLETED.value
        and job.processed_rows >= job.total_rows
        and job.kind == "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"
        and (not payload_has_live_results or _results_need_live_refresh(results))
    )
    if should_refresh_live_results:
        payload = _normalize_bulk_payload(CatAnagraficaBulkSearchRequest.model_validate(job.payload_json))
        results = (await execute_bulk_search_payload(payload, db)).results
        job.payload_json = payload.model_dump(mode="json")
        job.results_json = {"results": [r.model_dump(mode="json") for r in results]}
        job.summary_json = _build_summary(results)
        db.commit()
        db.refresh(job)
    return _bulk_job_detail_from_model(job, results=results)


def prepare_bulk_search_jobs_for_recovery(db: Session) -> int:
    rows = (
        db.execute(
            select(CatastoElaborazioniMassiveJob).where(
                CatastoElaborazioniMassiveJob.status == CatastoElaborazioniMassiveJobStatus.PROCESSING.value
            )
        )
        .scalars()
        .all()
    )
    for job in rows:
        job.status = CatastoElaborazioniMassiveJobStatus.PENDING.value
        job.processed_rows = 0
        job.current_label = "Recuperato dopo riavvio worker"
        job.error_message = None
        job.started_at = None
        job.completed_at = None
        job.results_json = {"results": []}
        job.summary_json = _empty_bulk_summary(job.total_rows)
    return len(rows)


def prepare_distretto_export_jobs_for_recovery(db: Session) -> int:
    rows = (
        db.execute(
            select(CatastoDistrettoExportJob).where(
                CatastoDistrettoExportJob.status == CatastoElaborazioniMassiveJobStatus.PROCESSING.value
            )
        )
        .scalars()
        .all()
    )
    for job in rows:
        job.status = CatastoElaborazioniMassiveJobStatus.PENDING.value
        job.processed_rows = 0
        job.current_label = "Recuperato dopo riavvio worker"
        job.error_message = None
        job.started_at = None
        job.completed_at = None
    return len(rows)


def run_distretto_export_job_by_id(job_id: UUID) -> None:
    from app.core.database import SessionLocal

    with SessionLocal() as db:
        job = db.get(CatastoDistrettoExportJob, job_id)
        if job is None:
            return
        job.status = CatastoElaborazioniMassiveJobStatus.PROCESSING.value
        job.started_at = datetime.now(UTC)
        job.completed_at = None
        job.error_message = None
        job.current_label = "Caricamento particelle del distretto..."
        job.processed_rows = 0
        job.total_rows = 0
        db.commit()

        try:
            results, distretto_label = _build_distretto_export_results(db, job.num_distretto)
            if not results:
                raise ValueError("Nessuna particella corrente per il distretto")
            job = db.get(CatastoDistrettoExportJob, job_id)
            if job is None:
                return
            if not job.nome_distretto and distretto_label:
                job.nome_distretto = distretto_label
            job.total_rows = len(results)
            job.processed_rows = len(results)
            job.current_label = "Generazione file export..."
            db.commit()

            rows = _build_bulk_export_rows("COMUNE_FOGLIO_PARTICELLA_INTESTATARI", results)
            filename, output_path, content_type = _write_distretto_export_file(job, rows)
            job = db.get(CatastoDistrettoExportJob, job_id)
            if job is None:
                return
            job.status = CatastoElaborazioniMassiveJobStatus.COMPLETED.value
            job.processed_rows = len(results)
            job.total_rows = len(results)
            job.current_label = "Export completato."
            job.output_filename = filename
            job.output_path = output_path
            job.content_type = content_type
            job.completed_at = datetime.now(UTC)
            db.commit()
        except Exception as exc:
            logger.exception("Export distretto %s fallito", job_id)
            job = db.get(CatastoDistrettoExportJob, job_id)
            if job is None:
                return
            job.status = CatastoElaborazioniMassiveJobStatus.FAILED.value
            job.error_message = str(exc)
            job.current_label = "Export fallito."
            job.completed_at = datetime.now(UTC)
            db.commit()


async def run_bulk_search_job_by_id(job_id: UUID) -> None:
    from app.core.database import SessionLocal

    with SessionLocal() as db:
        job = db.get(CatastoElaborazioniMassiveJob, job_id)
        if job is None:
            return
        payload = _normalize_bulk_payload(CatAnagraficaBulkSearchRequest.model_validate(job.payload_json))
        kind = _infer_bulk_kind(payload)
        job.status = CatastoElaborazioniMassiveJobStatus.PROCESSING.value
        job.started_at = datetime.now(UTC)
        job.completed_at = None
        job.error_message = None
        job.total_rows = len(payload.rows)
        job.processed_rows = 0
        job.current_label = "Avvio elaborazione..."
        job.results_json = {"results": []}
        job.summary_json = _empty_bulk_summary(len(payload.rows))
        db.commit()

        async def persist_progress(
            processed_rows: int,
            total_rows: int,
            row: CatAnagraficaBulkSearchRow,
            current_results: list[CatAnagraficaBulkSearchRowResult],
        ) -> None:
            await _update_bulk_job_progress(
                db,
                job_id,
                processed_rows=processed_rows,
                total_rows=total_rows,
                current_label=_bulk_job_row_label(kind, row),
                results=current_results,
            )

        try:
            response = await execute_bulk_search_payload(payload, db, on_row_processed=persist_progress)
            job = db.get(CatastoElaborazioniMassiveJob, job_id)
            if job is None:
                return
            job.status = CatastoElaborazioniMassiveJobStatus.COMPLETED.value
            job.processed_rows = len(response.results)
            job.current_label = "Elaborazione completata."
            job.results_json = {"results": [item.model_dump(mode="json") for item in response.results]}
            job.summary_json = _build_summary(response.results)
            job.completed_at = datetime.now(UTC)
            db.commit()
        except Exception as exc:
            logger.exception("Job catasto elaborazione massiva %s fallito", job_id)
            job = db.get(CatastoElaborazioniMassiveJob, job_id)
            if job is None:
                return
            job.status = CatastoElaborazioniMassiveJobStatus.FAILED.value
            job.error_message = str(exc)
            job.current_label = "Elaborazione fallita."
            job.completed_at = datetime.now(UTC)
            db.commit()


@router.get("/jobs/{job_id}/export")
async def download_bulk_search_job_export(
    job_id: UUID,
    format: Literal["csv", "xlsx"] = Query(...),
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> StreamingResponse:
    job = (
        db.execute(
            select(CatastoElaborazioniMassiveJob)
            .where(CatastoElaborazioniMassiveJob.id == job_id)
            .where(CatastoElaborazioniMassiveJob.user_id == user.id)
            .limit(1)
        )
        .scalars()
        .one_or_none()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")
    if job.status != CatastoElaborazioniMassiveJobStatus.COMPLETED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Il job non e ancora completato")
    raw_results = job.results_json.get("results") if isinstance(job.results_json, dict) else None
    results = [CatAnagraficaBulkSearchRowResult.model_validate(r) for r in (raw_results or [])]
    rows = _build_bulk_export_rows(job.kind, results)
    basename = _export_basename(job.kind)
    if format == "xlsx":
        return _stream_bulk_export_xlsx(f"{basename}.xlsx", rows)
    return _stream_bulk_export_csv(f"{basename}.csv", rows)
