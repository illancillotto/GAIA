from __future__ import annotations

import asyncio
import inspect
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from sqlalchemy import and_, case, exists, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catasto_phase1 import CatUtenzaIrrigua
from app.modules.utenze.anpr.client import AnprClient
from app.modules.utenze.anpr.models import AnprCheckLog, AnprSyncConfig
from app.modules.utenze.anpr.schemas import AnprSyncConfigUpdate, AnprSyncResult
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


async def build_check_queue(db: AsyncSession, config: AnprSyncConfig) -> list[str]:
    now = datetime.now(UTC)
    current_year = now.year
    retry_threshold = now - timedelta(days=config.retry_not_found_days)

    prev_year_exists = exists(
        select(1).where(
            and_(
                CatUtenzaIrrigua.codice_fiscale == AnagraficaPerson.codice_fiscale,
                CatUtenzaIrrigua.anno_campagna == current_year - 1,
            )
        )
    )
    current_year_exists = exists(
        select(1).where(
            and_(
                CatUtenzaIrrigua.codice_fiscale == AnagraficaPerson.codice_fiscale,
                CatUtenzaIrrigua.anno_campagna == current_year,
            )
        )
    )
    priority_flag = case(
        (and_(prev_year_exists, not_(current_year_exists)), 1),
        else_=0,
    )

    stmt = (
        select(AnagraficaSubject.id)
        .join(AnagraficaPerson, AnagraficaPerson.subject_id == AnagraficaSubject.id)
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
        .order_by(priority_flag.desc(), AnagraficaPerson.data_nascita.asc().nulls_last())
        .limit(config.max_calls_per_day)
    )

    result = await _maybe_await(db.execute(stmt))
    return [str(subject_id) for subject_id in result.scalars().all()]


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

        queue = await build_check_queue(db, config)
        calls_budget = config.max_calls_per_day
        processed = 0
        deceased_found = 0
        errors = 0
        calls_used = 0

        from app.modules.utenze.anpr.auth import PdndAuthManager

        auth = PdndAuthManager()
        client = AnprClient(auth)

        for queued_subject_id in queue:
            if calls_budget <= 0:
                break

            result = await sync_single_subject(queued_subject_id, db, "job", auth, client)
            calls_budget -= result.calls_made
            calls_used += result.calls_made
            processed += 1
            if result.esito == "deceased":
                deceased_found += 1
            if not result.success:
                errors += 1
            await asyncio.sleep(0.5)

        logger.info(
            "ANPR daily job completed processed=%s deceased=%s errors=%s calls_used=%s",
            processed,
            deceased_found,
            errors,
            calls_used,
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
