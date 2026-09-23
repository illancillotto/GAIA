from __future__ import annotations

import logging
import os
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import desc, func, or_, select
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
    _attach_sister_data,
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
    CatScopeExportJobCreateRequest,
)

router = APIRouter(
    prefix="/catasto/elaborazioni-massive/particelle", tags=["catasto-elaborazioni-massive"]
)
logger = logging.getLogger(__name__)
CATASTO_DISTRETTO_EXPORT_STORAGE_PATH = Path(
    os.getenv("CATASTO_DISTRETTO_EXPORT_STORAGE_PATH", "/data/catasto/exports/distretti")
)


# fmt: off

def _normalize_scope_values(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        cleaned = _norm_str(value)
        if cleaned is None or cleaned.casefold() in seen:
            continue
        seen.add(cleaned.casefold())
        normalized.append(cleaned)
    return normalized


def _build_export_results_from_particelle(
    db: Session,
    particelle: Sequence[CatParticella],
) -> list[CatAnagraficaBulkSearchRowResult]:
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
    return results


def _build_distretto_export_results(
    db: Session,
    num_distretto: str | Sequence[str],
) -> tuple[list[CatAnagraficaBulkSearchRowResult], str | None]:
    nums = _normalize_scope_values([num_distretto] if isinstance(num_distretto, str) else num_distretto)
    lowered = [value.lower() for value in nums]
    distretto_label = None
    if len(lowered) == 1:
        distretto = (
            db.execute(
                select(CatDistretto)
                .where(func.lower(CatDistretto.num_distretto) == lowered[0])
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
                func.lower(func.coalesce(CatParticella.num_distretto, "")).in_(lowered),
            )
            .order_by(
                CatParticella.num_distretto.asc().nulls_last(),
                CatParticella.nome_comune.asc().nulls_last(),
                CatParticella.foglio.asc(),
                CatParticella.particella.asc(),
                CatParticella.subalterno.asc().nullsfirst(),
            )
        )
        .scalars()
        .all()
    )
    return _build_export_results_from_particelle(db, particelle), distretto_label


def _build_comuni_export_results(
    db: Session,
    comuni: Sequence[str],
) -> list[CatAnagraficaBulkSearchRowResult]:
    values = _normalize_scope_values(comuni)
    codes = [int(value) for value in values if value.isdigit()]
    names = [value.casefold() for value in values if not value.isdigit()]
    conditions = []
    if codes:
        conditions.append(CatParticella.cod_comune_capacitas.in_(codes))
    if names:
        conditions.append(func.lower(CatParticella.nome_comune).in_(names))
    if not conditions:
        return []
    particelle = (
        db.execute(
            select(CatParticella)
            .where(
                CatParticella.is_current.is_(True),
                CatParticella.suppressed.is_(False),
                or_(*conditions),
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
    return _build_export_results_from_particelle(db, particelle)


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
        scope_kind=job.scope_kind or "distretti",  # type: ignore[arg-type]
        scope_values=job.scope_values,
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


def _build_scope_export_basename(job: CatastoDistrettoExportJob) -> str:
    values = job.scope_values or [job.num_distretto]
    if len(values) == 1 and job.scope_kind != "comuni":
        return _build_distretto_export_basename(values[0], job.nome_distretto)
    kind = "comuni" if job.scope_kind == "comuni" else "distretti"
    if len(values) == 1:
        return f"catasto-intestatari-comune-{_safe_distretto_export_label(job.nome_distretto or values[0])[:60]}"
    if len(values) <= 4:
        joined = "-".join(_safe_distretto_export_label(value)[:20] for value in values)
        return f"catasto-intestatari-{kind}-{joined}"
    return f"catasto-intestatari-{len(values)}-{kind}"


def _write_distretto_export_file(job: CatastoDistrettoExportJob, rows: list[dict[str, object]]) -> tuple[str, str, str]:
    filename = f"{_build_scope_export_basename(job)}.{job.format}"
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
    _attach_sister_data(db, rows)
    safe_label = re.sub(r"[^A-Za-z0-9_-]+", "-", normalized_num).strip("-").lower() or "nd"
    basename = f"catasto-intestatari-distretto-{safe_label}"
    if distretto_label:
        basename = f"{basename}-{re.sub(r'[^A-Za-z0-9_-]+', '-', distretto_label).strip('-').lower()[:40]}"
    if format == "xlsx":
        return _stream_bulk_export_xlsx(f"{basename}.xlsx", rows)
    return _stream_bulk_export_csv(f"{basename}.csv", rows)


def _scope_export_labels(db: Session, kind: str, values: list[str]) -> tuple[str, str | None]:
    if kind == "comuni":
        names: list[str] = []
        for value in values:
            query = select(func.max(CatParticella.nome_comune)).where(CatParticella.is_current.is_(True))
            if value.isdigit():
                query = query.where(CatParticella.cod_comune_capacitas == int(value))
            else:
                query = query.where(func.lower(CatParticella.nome_comune) == value.casefold())
            names.append(db.execute(query).scalar() or value)
        return ", ".join(values)[:255], ", ".join(names)[:200]
    distretti = (
        db.execute(select(CatDistretto).where(func.lower(CatDistretto.num_distretto).in_([v.lower() for v in values])))
        .scalars()
        .all()
    )
    label = ", ".join(values)[:255]
    if len(values) == 1:
        return label, distretti[0].nome_distretto if distretti else None
    return label, None


def _create_scope_export_job(
    db: Session,
    user: ApplicationUser,
    kind: Literal["distretti", "comuni"],
    values: Sequence[str],
    format: Literal["csv", "xlsx"],
) -> CatDistrettoExportJobResponse:
    normalized = _normalize_scope_values(values)
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Distretto non valido" if kind == "distretti" else "Comune non valido",
        )
    label, nome = _scope_export_labels(db, kind, normalized)
    job = CatastoDistrettoExportJob(
        user_id=user.id,
        num_distretto=label,
        nome_distretto=nome,
        scope_kind=kind,
        scope_values=normalized,
        format=format,
        status=CatastoElaborazioniMassiveJobStatus.PENDING.value,
        current_label="Export in coda.",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _distretto_export_job_response(job)


@router.post("/distretti/{num_distretto}/exports", response_model=CatDistrettoExportJobResponse)
async def create_distretto_export_job(
    num_distretto: str,
    format: Literal["csv", "xlsx"] = Query(...),
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> CatDistrettoExportJobResponse:
    return _create_scope_export_job(db, user, "distretti", [num_distretto], format)


@router.post("/exports", response_model=CatDistrettoExportJobResponse)
async def create_scope_export_job(
    payload: CatScopeExportJobCreateRequest,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> CatDistrettoExportJobResponse:
    return _create_scope_export_job(db, user, payload.kind, payload.values, payload.format)


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
