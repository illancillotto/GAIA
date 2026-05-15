from __future__ import annotations

import asyncio
import inspect
import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo

import anyio
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.ruolo.models import RuoloAvviso
from app.modules.utenze.anpr.client import AnprClient
from app.modules.utenze.anpr.models import AnprCheckLog, AnprJobRun, AnprSyncConfig
from app.modules.utenze.anpr.schemas import (
    AnprPreviewLookupResponse,
    AnprSyncConfigUpdate,
    AnprSyncResult,
)
from app.modules.utenze.models import AnagraficaPerson, AnagraficaSubject, AnagraficaSubjectType

logger = logging.getLogger(__name__)

UTC = timezone.utc


@dataclass(slots=True)
class AnprJobSummary:
    started_at: datetime
    subjects_processed: int
    deceased_found: int
    errors: int
    calls_used: int
    message: str


@dataclass(slots=True)
class AnprQueueItem:
    subject_id: str
    estimated_calls: int


async def get_config(db: AsyncSession) -> AnprSyncConfig:
    return await AnprSyncConfig.get_or_create_default(db)


async def update_config(db: AsyncSession, update: AnprSyncConfigUpdate, user_id: int) -> AnprSyncConfig:
    config = await get_config(db)

    if update.job_cron is not None and len(update.job_cron.split()) != 5:
        raise ValueError("job_cron must contain exactly 5 cron fields")

    update_data = update.model_dump(exclude_none=True)
    for field_name, value in update_data.items():
        setattr(config, field_name, value)

    config.updated_at = datetime.now(UTC)
    config.updated_by_user_id = user_id
    await _maybe_await(db.commit())
    await _maybe_await(db.refresh(config))
    return config


async def build_check_queue(db: AsyncSession, config: AnprSyncConfig, *, limit: int | None = None) -> list[AnprQueueItem]:
    now = datetime.now(UTC)
    retry_threshold = now - timedelta(days=config.retry_not_found_days)
    day_start_utc, _ = _local_day_bounds_utc(now)
    queue_limit = limit or settings.anpr_job_batch_size
    ruolo_year = await _resolve_ruolo_year(db)

    ruolo_subjects = (
        select(RuoloAvviso.subject_id)
        .where(
            RuoloAvviso.anno_tributario == ruolo_year,
            RuoloAvviso.subject_id.is_not(None),
        )
        .distinct()
        .subquery()
    )

    stmt = (
        select(AnagraficaSubject.id, AnagraficaPerson.anpr_id)
        .join(AnagraficaPerson, AnagraficaPerson.subject_id == AnagraficaSubject.id)
        .join(ruolo_subjects, ruolo_subjects.c.subject_id == AnagraficaSubject.id)
        .where(AnagraficaSubject.subject_type == AnagraficaSubjectType.PERSON.value)
        .where(AnagraficaPerson.codice_fiscale.is_not(None))
        .where(or_(AnagraficaPerson.stato_anpr.is_(None), AnagraficaPerson.stato_anpr != "deceased"))
        .where(
            or_(
                AnagraficaPerson.stato_anpr != "not_found_anpr",
                AnagraficaPerson.stato_anpr.is_(None),
                AnagraficaPerson.last_anpr_check_at.is_(None),
                AnagraficaPerson.last_anpr_check_at < retry_threshold,
            )
        )
        .where(
            or_(
                AnagraficaPerson.last_anpr_check_at.is_(None),
                AnagraficaPerson.last_anpr_check_at < day_start_utc,
            )
        )
        .where(
            or_(
                AnagraficaPerson.last_c030_check_at.is_(None),
                AnagraficaPerson.last_c030_check_at < day_start_utc,
            )
        )
        .order_by(AnagraficaPerson.data_nascita.asc().nulls_last(), AnagraficaSubject.created_at.asc())
        .limit(queue_limit)
    )

    result = await _maybe_await(db.execute(stmt))
    return [
        AnprQueueItem(subject_id=str(subject_id), estimated_calls=1 if anpr_id else 2)
        for subject_id, anpr_id in result.all()
    ]


async def sync_single_subject(
    subject_id: str,
    db: AsyncSession,
    triggered_by: str,
    auth: Any,
    client: AnprClient,
) -> AnprSyncResult:
    stmt = (
        select(AnagraficaSubject, AnagraficaPerson)
        .join(AnagraficaPerson, AnagraficaPerson.subject_id == AnagraficaSubject.id)
        .where(AnagraficaSubject.id == uuid.UUID(subject_id))
        .where(AnagraficaSubject.subject_type == AnagraficaSubjectType.PERSON.value)
    )
    row = (await _maybe_await(db.execute(stmt))).one_or_none()
    if row is None:
        return AnprSyncResult(
            subject_id=subject_id,
            success=False,
            esito="error",
            calls_made=0,
            message="Soggetto non trovato o non persona fisica",
        )

    subject, person = row
    if not person.codice_fiscale:
        return AnprSyncResult(
            subject_id=subject_id,
            success=False,
            esito="error",
            calls_made=0,
            message="Codice fiscale mancante",
        )

    now = datetime.now(UTC)
    subject_id_short = str(subject.id).split("-")[0]
    calls_made = 0

    if not person.anpr_id:
        c030_result = await client.c030_get_anpr_id(person.codice_fiscale, subject_id_short)
        calls_made += 1
        person.last_c030_check_at = now
        db.add(
            AnprCheckLog(
                subject_id=subject.id,
                call_type="C030",
                id_operazione_client=c030_result.id_operazione_client,
                id_operazione_anpr=c030_result.id_operazione_anpr,
                esito=c030_result.esito,
                error_detail=c030_result.error_detail,
                data_decesso_anpr=None,
                triggered_by=triggered_by,
            )
        )

        if c030_result.esito != "anpr_id_found":
            person.stato_anpr = _map_person_status(c030_result.esito)
            await _maybe_await(db.commit())
            return AnprSyncResult(
                subject_id=subject_id,
                success=False,
                esito=c030_result.esito,
                anpr_id=None,
                calls_made=calls_made,
                message=_build_result_message(c030_result.esito, c030_result.error_detail),
            )

        person.anpr_id = c030_result.anpr_id

    c004_result = await client.c004_check_death(person.anpr_id or "", subject_id_short)
    calls_made += 1
    db.add(
        AnprCheckLog(
            subject_id=subject.id,
            call_type="C004",
            id_operazione_client=c004_result.id_operazione_client,
            id_operazione_anpr=c004_result.id_operazione_anpr,
            esito=c004_result.esito,
            error_detail=c004_result.error_detail,
            data_decesso_anpr=c004_result.data_decesso,
            triggered_by=triggered_by,
        )
    )

    person.stato_anpr = _map_person_status(c004_result.esito)
    person.last_anpr_check_at = now
    if c004_result.esito == "deceased":
        person.data_decesso = c004_result.data_decesso

    await _maybe_await(db.commit())

    return AnprSyncResult(
        subject_id=subject_id,
        success=c004_result.success,
        esito=c004_result.esito,
        data_decesso=c004_result.data_decesso,
        anpr_id=person.anpr_id,
        calls_made=calls_made,
        message=_build_result_message(c004_result.esito, c004_result.error_detail),
    )


async def lookup_anpr_by_codice_fiscale(
    codice_fiscale: str,
    *,
    client: AnprClient | None = None,
    auth_manager: Any | None = None,
) -> AnprPreviewLookupResponse:
    """Interroga ANPR (C030 + eventuale C004) usando solo codice fiscale, senza soggetto in DB."""

    cf = codice_fiscale.replace(" ", "").upper().strip()
    if not cf:
        return AnprPreviewLookupResponse(success=False, calls_made=0, message="Codice fiscale mancante")

    anpr_client = client or AnprClient(auth_manager)
    preview_key = "preview"
    calls_made = 0

    c030 = await anpr_client.c030_get_anpr_id(cf, preview_key)
    calls_made += 1

    if c030.esito == "error":
        return AnprPreviewLookupResponse(
            success=False,
            calls_made=calls_made,
            message=_build_result_message(c030.esito, c030.error_detail),
        )

    if c030.esito != "anpr_id_found":
        stato = _map_person_status(c030.esito)
        return AnprPreviewLookupResponse(
            success=True,
            stato_anpr=stato,
            calls_made=calls_made,
            message=_build_result_message(c030.esito, c030.error_detail),
        )

    anpr_uid = (c030.anpr_id or "").strip() or None
    if not anpr_uid:
        return AnprPreviewLookupResponse(
            success=False,
            calls_made=calls_made,
            message=_build_result_message("error", "Identificativo ANPR vuoto dopo C030"),
        )

    c004 = await anpr_client.c004_check_death(anpr_uid, preview_key)
    calls_made += 1

    if c004.esito == "error":
        return AnprPreviewLookupResponse(
            success=False,
            anpr_id=anpr_uid,
            calls_made=calls_made,
            message=_build_result_message(c004.esito, c004.error_detail),
        )

    stato = _map_person_status(c004.esito)
    data_dec = c004.data_decesso if c004.esito == "deceased" else None
    return AnprPreviewLookupResponse(
        success=True,
        anpr_id=anpr_uid,
        stato_anpr=stato,
        data_decesso=data_dec,
        calls_made=calls_made,
        message=_build_result_message(c004.esito, c004.error_detail),
    )


async def run_daily_job(db_factory: Callable[[], Any]) -> AnprJobSummary:
    started_at = datetime.now(UTC)
    db = await db_factory()
    try:
        config = await get_config(db)
        if not config.job_enabled:
            return AnprJobSummary(
                started_at=started_at,
                subjects_processed=0,
                deceased_found=0,
                errors=0,
                calls_used=0,
                message="job disabled",
            )

        if not _is_within_processing_window(started_at):
            await _record_job_run(
                db,
                started_at=started_at,
                status="outside_window",
                configured_daily_limit=config.max_calls_per_day,
                hard_daily_limit=settings.anpr_daily_call_hard_limit,
                daily_calls_before=await _count_calls_for_local_day(db, started_at),
                calls_used=0,
                subjects_selected=0,
                subjects_processed=0,
                deceased_found=0,
                errors=0,
                notes="outside processing window",
            )
            return AnprJobSummary(
                started_at=started_at,
                subjects_processed=0,
                deceased_found=0,
                errors=0,
                calls_used=0,
                message="outside processing window",
            )

        effective_daily_limit = min(config.max_calls_per_day, settings.anpr_daily_call_hard_limit)
        daily_calls_before = await _count_calls_for_local_day(db, started_at)
        if daily_calls_before >= effective_daily_limit:
            await _record_job_run(
                db,
                started_at=started_at,
                status="limit_reached",
                configured_daily_limit=config.max_calls_per_day,
                hard_daily_limit=settings.anpr_daily_call_hard_limit,
                daily_calls_before=daily_calls_before,
                calls_used=0,
                subjects_selected=0,
                subjects_processed=0,
                deceased_found=0,
                errors=0,
                notes="daily call limit reached",
            )
            return AnprJobSummary(
                started_at=started_at,
                subjects_processed=0,
                deceased_found=0,
                errors=0,
                calls_used=0,
                message="daily call limit reached",
            )

        queue = await build_check_queue(db, config, limit=settings.anpr_job_batch_size)
        calls_budget = effective_daily_limit - daily_calls_before
        processed = 0
        deceased_found = 0
        errors = 0
        calls_used = 0
        subjects_selected = 0

        from app.modules.utenze.anpr.auth import PdndAuthManager

        auth = PdndAuthManager()
        client = AnprClient(auth)

        for queue_item in queue:
            if calls_budget <= 0 or subjects_selected >= settings.anpr_job_batch_size:
                break
            if queue_item.estimated_calls > calls_budget:
                break

            subjects_selected += 1
            try:
                result = await sync_single_subject(queue_item.subject_id, db, "job", auth, client)
                calls_budget -= result.calls_made
                calls_used += result.calls_made
                processed += 1
                if result.esito == "deceased":
                    deceased_found += 1
                if not result.success:
                    errors += 1
            except Exception:
                logger.exception("ANPR batch job failed for subject_id=%s", queue_item.subject_id)
                rollback = getattr(db, "rollback", None)
                if rollback is not None:
                    await _maybe_await(rollback())
                calls_budget = max(calls_budget - queue_item.estimated_calls, 0)
                calls_used += queue_item.estimated_calls
                errors += 1
                break
            await anyio.sleep(0.5)

        completed_at = datetime.now(UTC)
        status = "completed" if errors == 0 else "completed_with_errors"
        await _record_job_run(
            db,
            started_at=started_at,
            completed_at=completed_at,
            status=status,
            configured_daily_limit=config.max_calls_per_day,
            hard_daily_limit=settings.anpr_daily_call_hard_limit,
            daily_calls_before=daily_calls_before,
            calls_used=calls_used,
            subjects_selected=subjects_selected,
            subjects_processed=processed,
            deceased_found=deceased_found,
            errors=errors,
            notes="job completed" if processed else "no eligible role subjects",
        )
        logger.info(
            "ANPR ruolo batch completed processed=%s deceased=%s errors=%s calls_used=%s daily_calls_before=%s daily_limit=%s",
            processed,
            deceased_found,
            errors,
            calls_used,
            daily_calls_before,
            effective_daily_limit,
        )
        return AnprJobSummary(
            started_at=started_at,
            subjects_processed=processed,
            deceased_found=deceased_found,
            errors=errors,
            calls_used=calls_used,
            message="job completed",
        )
    finally:
        generator = getattr(db, "_anpr_generator", None)
        close = getattr(db, "close", None)
        if close is not None:
            result = close()
            if asyncio.iscoroutine(result):
                await result
        if generator is not None:
            try:
                next(generator)
            except StopIteration:
                pass


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _processing_timezone() -> ZoneInfo:
    return ZoneInfo(settings.anpr_job_timezone)


def _local_day_bounds_utc(reference: datetime) -> tuple[datetime, datetime]:
    local_tz = _processing_timezone()
    local_reference = reference.astimezone(local_tz)
    start_local = datetime.combine(local_reference.date(), time.min, tzinfo=local_tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def _is_within_processing_window(reference: datetime) -> bool:
    local_reference = reference.astimezone(_processing_timezone())
    return settings.anpr_job_start_hour <= local_reference.hour < settings.anpr_job_end_hour


async def _count_calls_for_local_day(db: AsyncSession, reference: datetime) -> int:
    day_start_utc, day_end_utc = _local_day_bounds_utc(reference)
    stmt = (
        select(func.count())
        .select_from(AnprCheckLog)
        .where(AnprCheckLog.created_at >= day_start_utc, AnprCheckLog.created_at < day_end_utc)
    )
    return int((await _maybe_await(db.execute(stmt))).scalar_one())


async def _resolve_ruolo_year(db: AsyncSession) -> int:
    if settings.anpr_job_ruolo_year is not None:
        return settings.anpr_job_ruolo_year

    stmt = select(func.max(RuoloAvviso.anno_tributario)).where(RuoloAvviso.subject_id.is_not(None))
    latest_year = (await _maybe_await(db.execute(stmt))).scalar_one_or_none()
    if latest_year is None:
        raise ValueError("Nessun ruolo disponibile per costruire la coda ANPR")
    return int(latest_year)


async def _record_job_run(
    db: AsyncSession,
    *,
    started_at: datetime,
    status: str,
    configured_daily_limit: int,
    hard_daily_limit: int,
    daily_calls_before: int,
    calls_used: int,
    subjects_selected: int,
    subjects_processed: int,
    deceased_found: int,
    errors: int,
    notes: str,
    completed_at: datetime | None = None,
) -> None:
    local_date = started_at.astimezone(_processing_timezone()).date()
    ruolo_year = await _resolve_ruolo_year(db)
    db.add(
        AnprJobRun(
            run_date=local_date,
            ruolo_year=ruolo_year,
            triggered_by="job",
            status=status,
            batch_size=settings.anpr_job_batch_size,
            hard_daily_limit=hard_daily_limit,
            configured_daily_limit=configured_daily_limit,
            daily_calls_before=daily_calls_before,
            daily_calls_after=daily_calls_before + calls_used,
            subjects_selected=subjects_selected,
            subjects_processed=subjects_processed,
            deceased_found=deceased_found,
            errors=errors,
            calls_used=calls_used,
            notes=notes,
            payload_json={
                "timezone": settings.anpr_job_timezone,
                "window_start_hour": settings.anpr_job_start_hour,
                "window_end_hour": settings.anpr_job_end_hour,
            },
            started_at=started_at,
            completed_at=completed_at or datetime.now(UTC),
        )
    )
    await _maybe_await(db.commit())


def _map_person_status(esito: str) -> str:
    mapping = {
        "alive": "alive",
        "deceased": "deceased",
        "not_found": "not_found_anpr",
        "cancelled": "cancelled_anpr",
        "error": "error",
        "anpr_id_found": "unknown",
    }
    return mapping.get(esito, "unknown")


def _build_result_message(esito: str, error_detail: str | None) -> str:
    messages = {
        "alive": "Soggetto presente in ANPR e non deceduto",
        "deceased": "Soggetto risultato deceduto in ANPR",
        "not_found": "Soggetto non trovato in ANPR",
        "cancelled": "Soggetto cancellato in ANPR",
        "error": "Errore durante la sincronizzazione ANPR",
        "anpr_id_found": "idANPR acquisito correttamente",
    }
    base_message = messages.get(esito, "Esito ANPR non riconosciuto")
    if error_detail:
        return f"{base_message}: {error_detail}"
    return base_message
