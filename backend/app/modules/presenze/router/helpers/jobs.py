from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeCredential,
    PresenzeSyncJob,
)
from app.modules.presenze.router.helpers.access import _can_access_collaborator
from app.modules.presenze.services.straordinari_export_job import (
    build_period_end as build_straordinari_period_end,
)
from app.modules.presenze.services.straordinari_export_job import (
    build_straordinari_filename,
)
from app.modules.presenze.services.sync_runtime import (
    apply_sync_job_retention,
    build_period,
    get_sync_artifact_dir,
    launch_straordinari_export_worker,
    launch_xlsm_export_worker,
    prepare_sync_job_artifacts,
    resolve_sync_artifact_path,
)
from app.modules.presenze.services.xlsm_export import DEFAULT_TEMPLATE_PATH
from app.modules.presenze.services.xlsm_export_job import (
    build_period_end,
)
from app.modules.presenze.services.xlsm_export_job import (
    resolve_export_template_path as _resolve_export_template_path,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

def _normalize_employee_codes(values: list[str] | None) -> list[str]:
    if not values:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        code = str(value or "").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        normalized.append(code)
    return normalized

def _load_sync_job_summary(job_id: str) -> dict[str, object]:
    summary_path = resolve_sync_artifact_path(job_id, "summary")
    if not summary_path.exists():
        raise HTTPException(status_code=409, detail="Summary artifact not available for this sync job")
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=409, detail="Summary artifact is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=409, detail="Summary artifact has an unexpected structure")
    return payload

def _create_sync_job_record(
    db: Session,
    *,
    requested_by_user_id: int,
    credential_id: int,
    year: int,
    month: int,
    collaborator_limit: int | None,
    employee_codes: list[str] | None = None,
    period_start_override: date | None = None,
    period_end_override: date | None = None,
    params_overrides: dict[str, object] | None = None,
    trigger: str = "manual",
) -> PresenzeSyncJob:
    credential = db.get(PresenzeCredential, credential_id)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credenziale Presenze non trovata")
    if not credential.active:
        raise HTTPException(status_code=409, detail="La credenziale Presenze selezionata non e attiva")

    period_start, period_end = build_period(year, month)
    if period_start_override is not None:
        period_start = period_start_override
    if period_end_override is not None:
        period_end = period_end_override
    normalized_employee_codes = _normalize_employee_codes(employee_codes)
    params_json: dict[str, object] = {
        "auth_mode": "credential",
        "year": year,
        "month": month,
        "trigger": trigger,
        "employee_codes": normalized_employee_codes,
    }
    if params_overrides:
        params_json.update(params_overrides)
    job = PresenzeSyncJob(
        status="pending",
        requested_by_user_id=requested_by_user_id,
        credential_id=credential_id,
        period_start=period_start,
        period_end=period_end,
        collaborator_limit=collaborator_limit,
        max_attempts=settings.presenze_sync_max_attempts,
        params_json=params_json,
    )
    db.add(job)
    db.flush()
    prepare_sync_job_artifacts(job)
    db.add(job)
    db.commit()
    db.refresh(job)
    apply_sync_job_retention(db)
    return job

def resolve_export_template_path(template_path: str | None) -> Path:
    if template_path is not None:
        try:
            return _resolve_export_template_path(template_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    if DEFAULT_TEMPLATE_PATH.exists():
        return DEFAULT_TEMPLATE_PATH
    raise HTTPException(status_code=404, detail=f"Template XLSM not found: {DEFAULT_TEMPLATE_PATH}")

def _is_xlsm_export_job(job: PresenzeSyncJob) -> bool:
    return (job.params_json or {}).get("mode") == "export_xlsm"

def _is_straordinari_export_job(job: PresenzeSyncJob) -> bool:
    return (job.params_json or {}).get("mode") == "export_straordinari_xlsx"

def _create_xlsm_export_job_record(
    db: Session,
    *,
    requested_by_user_id: int,
    period_start: date,
    collaborator_ids: list[uuid.UUID] | None,
    employee_kind: str | None,
    template_path: str | None,
) -> PresenzeSyncJob:
    period_end = build_period_end(period_start)
    job = PresenzeSyncJob(
        status="pending",
        requested_by_user_id=requested_by_user_id,
        credential_id=None,
        period_start=period_start,
        period_end=date.fromordinal(period_end.toordinal() - 1),
        collaborator_limit=len(collaborator_ids) if collaborator_ids else None,
        max_attempts=1,
        params_json={
            "mode": "export_xlsm",
            "period_start": period_start.isoformat(),
            "collaborator_ids": [str(item) for item in collaborator_ids] if collaborator_ids else [],
            "employee_kind": employee_kind,
            "template_path": template_path,
            "progress": {
                "state": "pending",
                "last_event": "queued",
                "last_event_at": datetime.now(UTC).isoformat(),
            },
        },
    )
    db.add(job)
    db.flush()

    artifact_dir = get_sync_artifact_dir(str(job.id))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    job.worker_log_path = str(artifact_dir / "worker.log")
    job.json_artifact_path = str(artifact_dir / "giornaliere_export.xlsm")

    try:
        job.worker_pid = launch_xlsm_export_worker(job)
    except Exception as exc:
        job.status = "failed"
        job.error_detail = str(exc)
        job.finished_at = datetime.now(UTC)
        db.add(job)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Unable to start Presenze XLSM export worker: {exc}") from exc

    db.add(job)
    db.commit()
    db.refresh(job)
    return job

def _resolve_straordinari_collaborator(
    db: Session,
    *,
    current_user: ApplicationUser,
    collaborator_id: uuid.UUID | None,
) -> PresenzeCollaborator:
    if collaborator_id is not None:
        collaborator = db.get(PresenzeCollaborator, collaborator_id)
        if collaborator is None or not _can_access_collaborator(db, current_user, collaborator):
            raise HTTPException(status_code=404, detail="Collaboratore non trovato")
        return collaborator

    candidates = db.execute(
        select(PresenzeCollaborator).where(PresenzeCollaborator.application_user_id == current_user.id).order_by(PresenzeCollaborator.name.asc())
    ).scalars().all()
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise HTTPException(status_code=409, detail="Nessun collaboratore GAIA associato all'utente corrente")
    raise HTTPException(status_code=409, detail="Seleziona il collaboratore per l'export straordinari")

def _create_straordinari_export_job_record(
    db: Session,
    *,
    requested_by_user_id: int,
    collaborator: PresenzeCollaborator,
    period_start: date,
    template_path: str | None,
    items: list[dict[str, object]],
) -> PresenzeSyncJob:
    period_end = build_straordinari_period_end(period_start)
    job = PresenzeSyncJob(
        status="pending",
        requested_by_user_id=requested_by_user_id,
        credential_id=None,
        period_start=period_start,
        period_end=date.fromordinal(period_end.toordinal() - 1),
        collaborator_limit=1,
        max_attempts=1,
        params_json={
            "mode": "export_straordinari_xlsx",
            "period_start": period_start.isoformat(),
            "collaborator_id": str(collaborator.id),
            "collaborator_name": collaborator.name,
            "template_path": template_path,
            "items": items,
            "output_filename": build_straordinari_filename(period_start),
            "progress": {
                "state": "pending",
                "last_event": "queued",
                "last_event_at": datetime.now(UTC).isoformat(),
            },
        },
    )
    db.add(job)
    db.flush()

    artifact_dir = get_sync_artifact_dir(str(job.id))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    job.worker_log_path = str(artifact_dir / "worker.log")
    job.json_artifact_path = str(artifact_dir / "straordinari.xlsx")

    try:
        job.worker_pid = launch_straordinari_export_worker(job)
    except Exception as exc:
        job.status = "failed"
        job.error_detail = str(exc)
        job.finished_at = datetime.now(UTC)
        db.add(job)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Unable to start Presenze straordinari export worker: {exc}") from exc

    db.add(job)
    db.commit()
    db.refresh(job)
    return job

# fmt: on

__all__ = [
    "_create_straordinari_export_job_record",
    "_create_sync_job_record",
    "_create_xlsm_export_job_record",
    "_is_straordinari_export_job",
    "_is_xlsm_export_job",
    "_load_sync_job_summary",
    "_normalize_employee_codes",
    "_resolve_straordinari_collaborator",
    "resolve_export_template_path",
]
