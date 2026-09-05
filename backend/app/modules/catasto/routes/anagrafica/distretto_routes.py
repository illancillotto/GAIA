from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto import (
    CatastoDistrettoExportJob,
    CatastoElaborazioniMassiveJobStatus,
)
from app.models.catasto_phase1 import (
    CatDistretto,
    CatParticella,
)
from app.modules.catasto.routes.anagrafica.exports import (
    _build_bulk_export_rows,
    _render_bulk_export_csv_bytes,
    _render_bulk_export_xlsx_bytes,
    _stream_bulk_export_csv,
    _stream_bulk_export_xlsx,
)
from app.modules.catasto.routes.anagrafica.matching import (
    _build_consorzio_sub_matches,
    _build_match,
    _load_consorzio_presence_by_particella_ids,
)
from app.modules.catasto.routes.anagrafica.normalization import _norm_str
from app.schemas.catasto_phase1 import (
    CatAnagraficaBulkSearchRowResult,
    CatDistrettoExportJobListResponse,
    CatDistrettoExportJobResponse,
)

router = APIRouter(
    prefix="/catasto/elaborazioni-massive/particelle", tags=["catasto-elaborazioni-massive"]
)
logger = logging.getLogger(__name__)
CATASTO_DISTRETTO_EXPORT_STORAGE_PATH = Path(
    os.getenv("CATASTO_DISTRETTO_EXPORT_STORAGE_PATH", "/data/catasto/exports/distretti")
)


# fmt: off

def _build_distretto_export_results(
    db: Session,
    num_distretto: str,
) -> tuple[list[CatAnagraficaBulkSearchRowResult], str | None]:
    distretto = (
        db.execute(
            select(CatDistretto)
            .where(func.lower(CatDistretto.num_distretto) == num_distretto.strip().lower())
            .limit(1)
        )
        .scalars()
        .first()
    )
    distretto_label = distretto.nome_distretto if distretto is not None else None
    particelle = (
        db.execute(
            select(CatParticella)
            .where(
                CatParticella.is_current.is_(True),
                CatParticella.suppressed.is_(False),
                func.lower(func.coalesce(CatParticella.num_distretto, "")) == num_distretto.strip().lower(),
            )
            .order_by(
                CatParticella.nome_comune.asc().nulls_last(),
                CatParticella.foglio.asc(),
                CatParticella.particella.asc(),
                CatParticella.subalterno.asc().nullsfirst(),
            )
        )
        .scalars()
        .all()
    )
    consorzio_present_ids = _load_consorzio_presence_by_particella_ids(db, {p.id for p in particelle if p.id is not None})
    results: list[CatAnagraficaBulkSearchRowResult] = []
    for index, particella in enumerate(particelle, start=1):
        match = _build_match(
            db,
            particella,
            presente_in_catasto_consorzio=(particella.id in consorzio_present_ids),
        )
        sub_matches = None
        if not _norm_str(particella.subalterno):
            sub_matches = _build_consorzio_sub_matches(db, particella) or None
        results.append(
            CatAnagraficaBulkSearchRowResult(
                row_index=index,
                comune_input=particella.nome_comune,
                sezione_input=particella.sezione_catastale,
                foglio_input=particella.foglio,
                particella_input=particella.particella,
                sub_input=particella.subalterno,
                esito="FOUND",
                message="OK",
                particella_id=match.particella_id,
                match=match,
                matches=sub_matches,
                matches_count=(len(sub_matches) if sub_matches else 1),
            )
        )
    return results, distretto_label


def _safe_distretto_export_label(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-").lower() or "nd"


def _distretto_export_job_response(job: CatastoDistrettoExportJob) -> CatDistrettoExportJobResponse:
    download_url = (
        f"/catasto/elaborazioni-massive/particelle/distretti/exports/{job.id}/download"
        if job.status == CatastoElaborazioniMassiveJobStatus.COMPLETED.value and job.output_path
        else None
    )
    return CatDistrettoExportJobResponse(
        id=job.id,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        num_distretto=job.num_distretto,
        nome_distretto=job.nome_distretto,
        format=job.format,  # type: ignore[arg-type]
        status=job.status,  # type: ignore[arg-type]
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        current_label=job.current_label,
        error_message=job.error_message,
        output_filename=job.output_filename,
        download_url=download_url,
    )


def _build_distretto_export_basename(num_distretto: str, distretto_label: str | None) -> str:
    basename = f"catasto-intestatari-distretto-{_safe_distretto_export_label(num_distretto)}"
    if distretto_label:
        basename = f"{basename}-{_safe_distretto_export_label(distretto_label)[:40]}"
    return basename


def _write_distretto_export_file(job: CatastoDistrettoExportJob, rows: list[dict[str, object]]) -> tuple[str, str, str]:
    filename = f"{_build_distretto_export_basename(job.num_distretto, job.nome_distretto)}.{job.format}"
    content_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if job.format == "xlsx"
        else "text/csv; charset=utf-8"
    )
    content = _render_bulk_export_xlsx_bytes(rows) if job.format == "xlsx" else _render_bulk_export_csv_bytes(rows)
    CATASTO_DISTRETTO_EXPORT_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    output_path = CATASTO_DISTRETTO_EXPORT_STORAGE_PATH / f"{job.id}.{job.format}"
    output_path.write_bytes(content)
    return filename, str(output_path), content_type


@router.get("/distretti/{num_distretto}/export")
async def download_distretto_bulk_export(
    num_distretto: str,
    format: Literal["csv", "xlsx"] = Query(...),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> StreamingResponse:
    normalized_num = _norm_str(num_distretto)
    if normalized_num is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Distretto non valido")

    results, distretto_label = _build_distretto_export_results(db, normalized_num)
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nessuna particella corrente per il distretto")

    rows = _build_bulk_export_rows("COMUNE_FOGLIO_PARTICELLA_INTESTATARI", results)
    safe_label = re.sub(r"[^A-Za-z0-9_-]+", "-", normalized_num).strip("-").lower() or "nd"
    basename = f"catasto-intestatari-distretto-{safe_label}"
    if distretto_label:
        basename = f"{basename}-{re.sub(r'[^A-Za-z0-9_-]+', '-', distretto_label).strip('-').lower()[:40]}"
    if format == "xlsx":
        return _stream_bulk_export_xlsx(f"{basename}.xlsx", rows)
    return _stream_bulk_export_csv(f"{basename}.csv", rows)


@router.post("/distretti/{num_distretto}/exports", response_model=CatDistrettoExportJobResponse)
async def create_distretto_export_job(
    num_distretto: str,
    format: Literal["csv", "xlsx"] = Query(...),
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> CatDistrettoExportJobResponse:
    normalized_num = _norm_str(num_distretto)
    if normalized_num is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Distretto non valido")
    distretto = (
        db.execute(
            select(CatDistretto)
            .where(func.lower(CatDistretto.num_distretto) == normalized_num.lower())
            .limit(1)
        )
        .scalars()
        .first()
    )
    job = CatastoDistrettoExportJob(
        user_id=user.id,
        num_distretto=normalized_num,
        nome_distretto=distretto.nome_distretto if distretto is not None else None,
        format=format,
        status=CatastoElaborazioniMassiveJobStatus.PENDING.value,
        current_label="Export distretto in coda.",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _distretto_export_job_response(job)


@router.get("/distretti/exports", response_model=CatDistrettoExportJobListResponse)
async def list_distretto_export_jobs(
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
    limit: int = Query(5, ge=1, le=20),
) -> CatDistrettoExportJobListResponse:
    rows = (
        db.execute(
            select(CatastoDistrettoExportJob)
            .where(CatastoDistrettoExportJob.user_id == user.id)
            .order_by(desc(CatastoDistrettoExportJob.created_at))
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return CatDistrettoExportJobListResponse(items=[_distretto_export_job_response(job) for job in rows])


@router.get("/distretti/exports/{job_id}", response_model=CatDistrettoExportJobResponse)
async def get_distretto_export_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> CatDistrettoExportJobResponse:
    job = (
        db.execute(
            select(CatastoDistrettoExportJob)
            .where(CatastoDistrettoExportJob.id == job_id)
            .where(CatastoDistrettoExportJob.user_id == user.id)
            .limit(1)
        )
        .scalars()
        .one_or_none()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export non trovato")
    return _distretto_export_job_response(job)


@router.get("/distretti/exports/{job_id}/download")
async def download_distretto_export_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> FileResponse:
    job = (
        db.execute(
            select(CatastoDistrettoExportJob)
            .where(CatastoDistrettoExportJob.id == job_id)
            .where(CatastoDistrettoExportJob.user_id == user.id)
            .limit(1)
        )
        .scalars()
        .one_or_none()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export non trovato")
    if job.status != CatastoElaborazioniMassiveJobStatus.COMPLETED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Export non ancora completato")
    if not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File export non disponibile")
    return FileResponse(
        job.output_path,
        media_type=job.content_type or "application/octet-stream",
        filename=job.output_filename or f"catasto-export-distretto-{job.num_distretto}.{job.format}",
    )
