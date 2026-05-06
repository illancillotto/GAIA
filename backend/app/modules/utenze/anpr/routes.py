from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Annotated, Any
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_role
from app.core.database import SessionLocal, get_db
from app.models.application_user import ApplicationUser
from app.modules.utenze.anpr.auth import PdndConfigurationError
from app.modules.utenze.anpr.client import AnprClient
from app.modules.utenze.anpr.models import AnprCheckLog
from app.modules.utenze.anpr.schemas import (
    AnprCheckLogItem,
    AnprJobTriggerResult,
    AnprPreviewLookupRequest,
    AnprPreviewLookupResponse,
    AnprSubjectStatus,
    AnprSyncConfigRead,
    AnprSyncConfigUpdate,
    AnprSyncResult,
)
from app.modules.utenze.anpr.service import (
    AnprJobSummary,
    get_config,
    lookup_anpr_by_codice_fiscale,
    run_daily_job,
    sync_single_subject,
    update_config,
)
from app.modules.utenze.models import AnagraficaPerson, AnagraficaSubject

router = APIRouter(prefix="/utenze/anpr", tags=["anpr"])

UTC = timezone.utc
RequireUtenzeModule = Depends(require_module("utenze"))
RequireAnprSyncRole = Depends(require_role("super_admin", "admin", "reviewer"))

_job_runtime_state: dict[str, Any] = {
    "running": False,
    "last_summary": None,
    "last_error": None,
}


def _get_runtime_loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


async def _run_daily_job_with_sync_session() -> AnprJobSummary:
    async def db_factory():
        return SessionLocal()

    return await run_daily_job(db_factory)


def _run_daily_job_task() -> None:
    _job_runtime_state["running"] = True
    _job_runtime_state["last_error"] = None
    try:
        summary = asyncio.run(_run_daily_job_with_sync_session())
        _job_runtime_state["last_summary"] = summary
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        _job_runtime_state["last_error"] = str(exc)
        raise
    finally:
        _job_runtime_state["running"] = False


def _serialize_job_summary(summary: AnprJobSummary | None, *, message: str) -> AnprJobTriggerResult:
    now = datetime.now(UTC)
    if summary is None:
        return AnprJobTriggerResult(
            started_at=now,
            subjects_processed=0,
            deceased_found=0,
            errors=0,
            calls_used=0,
            message=message,
        )
    return AnprJobTriggerResult(
        started_at=summary.started_at,
        subjects_processed=summary.subjects_processed,
        deceased_found=summary.deceased_found,
        errors=summary.errors,
        calls_used=summary.calls_used,
        message=message,
    )


@router.post("/preview-lookup", response_model=AnprPreviewLookupResponse)
async def post_preview_lookup_anpr(
    payload: AnprPreviewLookupRequest,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    ___: Annotated[ApplicationUser, RequireAnprSyncRole],
) -> AnprPreviewLookupResponse:
    try:
        result = await lookup_anpr_by_codice_fiscale(payload.codice_fiscale, client=AnprClient())
    except PdndConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return result


@router.post("/sync/{subject_id}", response_model=AnprSyncResult)
async def post_sync_subject(
    subject_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    __: Annotated[ApplicationUser, RequireAnprSyncRole],
    db: Annotated[Session, Depends(get_db)],
) -> AnprSyncResult:
    try:
        result = await sync_single_subject(
            str(subject_id),
            db,
            triggered_by=f"user:{current_user.id}",
            auth=None,
            client=AnprClient(),
        )
    except PdndConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    result = AnprSyncResult.model_validate(result)
    if result.esito == "error" and result.calls_made == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message)
    return result


@router.get("/sync/{subject_id}/status", response_model=AnprSubjectStatus)
async def get_subject_status(
    subject_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnprSubjectStatus:
    row = (
        db.execute(
            select(AnagraficaSubject, AnagraficaPerson)
            .join(AnagraficaPerson, AnagraficaPerson.subject_id == AnagraficaSubject.id)
            .where(AnagraficaSubject.id == subject_id)
        )
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    subject, person = row
    return AnprSubjectStatus(
        subject_id=str(subject.id),
        anpr_id=person.anpr_id,
        stato_anpr=person.stato_anpr,
        data_decesso=person.data_decesso,
        luogo_decesso_comune=person.luogo_decesso_comune,
        last_anpr_check_at=person.last_anpr_check_at,
        last_c030_check_at=person.last_c030_check_at,
    )


@router.get("/log")
async def get_logs(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    __: Annotated[ApplicationUser, Depends(require_role("super_admin", "admin"))],
    db: Annotated[Session, Depends(get_db)],
    subject_id: uuid.UUID | None = Query(default=None),
    esito: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
) -> dict[str, Any]:
    del current_user
    query = select(AnprCheckLog)
    count_query = select(func.count()).select_from(AnprCheckLog)
    if subject_id is not None:
        query = query.where(AnprCheckLog.subject_id == subject_id)
        count_query = count_query.where(AnprCheckLog.subject_id == subject_id)
    if esito:
        query = query.where(AnprCheckLog.esito == esito)
        count_query = count_query.where(AnprCheckLog.esito == esito)

    total = db.execute(count_query).scalar_one()
    items = db.execute(
        query.order_by(AnprCheckLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()

    return {
        "items": [AnprCheckLogItem.model_validate(item).model_dump() for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/log/{subject_id}", response_model=list[AnprCheckLogItem])
async def get_subject_logs(
    subject_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    ___: Annotated[ApplicationUser, RequireAnprSyncRole],
    db: Annotated[Session, Depends(get_db)],
) -> list[AnprCheckLogItem]:
    items = db.execute(
        select(AnprCheckLog)
        .where(AnprCheckLog.subject_id == subject_id)
        .order_by(AnprCheckLog.created_at.desc())
    ).scalars().all()
    return [AnprCheckLogItem.model_validate(item) for item in items]


@router.get("/config", response_model=AnprSyncConfigRead)
async def get_job_config(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    ___: Annotated[ApplicationUser, Depends(require_role("super_admin", "admin"))],
    db: Annotated[Session, Depends(get_db)],
) -> AnprSyncConfigRead:
    config = await get_config(db)
    return AnprSyncConfigRead.model_validate(config)


@router.put("/config", response_model=AnprSyncConfigRead)
async def put_job_config(
    payload: AnprSyncConfigUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    __: Annotated[ApplicationUser, Depends(require_role("super_admin", "admin"))],
    db: Annotated[Session, Depends(get_db)],
) -> AnprSyncConfigRead:
    try:
        config = await update_config(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return AnprSyncConfigRead.model_validate(config)


@router.post("/job/trigger", response_model=AnprJobTriggerResult, status_code=status.HTTP_202_ACCEPTED)
async def post_job_trigger(
    background_tasks: BackgroundTasks,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    ___: Annotated[ApplicationUser, Depends(require_role("super_admin", "admin"))],
) -> AnprJobTriggerResult:
    if _job_runtime_state["running"]:
        return _serialize_job_summary(None, message="job already running")

    background_tasks.add_task(_run_daily_job_task)
    return AnprJobTriggerResult(
        started_at=datetime.now(UTC),
        subjects_processed=0,
        deceased_found=0,
        errors=0,
        calls_used=0,
        message="job scheduled",
    )


@router.get("/job/status", response_model=AnprJobTriggerResult)
async def get_job_status(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    ___: Annotated[ApplicationUser, Depends(require_role("super_admin", "admin"))],
) -> AnprJobTriggerResult:
    if _job_runtime_state["running"]:
        return _serialize_job_summary(_job_runtime_state["last_summary"], message="job running")
    if _job_runtime_state["last_error"]:
        return _serialize_job_summary(_job_runtime_state["last_summary"], message=_job_runtime_state["last_error"])
    return _serialize_job_summary(_job_runtime_state["last_summary"], message="job idle")
