from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import logging
import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.application_user import ApplicationUser
from app.models.wc_sync_job import WCSyncJob
from app.modules.elaborazioni.bonifica_oristanese.apps.areas.client import BonificaAreasClient
from app.modules.elaborazioni.bonifica_oristanese.apps.org_charts.client import BonificaOrgChartsClient
from app.modules.elaborazioni.bonifica_oristanese.apps.report_types.client import BonificaReportTypesClient
from app.modules.elaborazioni.bonifica_oristanese.apps.refuels.client import BonificaRefuelsClient
from app.modules.elaborazioni.bonifica_oristanese.apps.reports.client import BonificaReportsClient
from app.modules.elaborazioni.bonifica_oristanese.apps.taken_charge.client import BonificaTakenChargeClient
from app.modules.elaborazioni.bonifica_oristanese.apps.users.client import BonificaUsersClient
from app.modules.elaborazioni.bonifica_oristanese.apps.vehicles.client import BonificaVehiclesClient
from app.modules.elaborazioni.bonifica_oristanese.apps.warehouse_requests.client import (
    BonificaWarehouseRequestsClient,
)
from app.modules.inventory.services import sync_white_warehouse_requests
from app.modules.accessi.sync_org_charts import sync_white_org_charts
from app.modules.utenze.services.sync_consorziati import sync_white_consorziati
from app.modules.elaborazioni.bonifica_oristanese.models import (
    BonificaSyncEntityStatus,
    BonificaSyncJobStart,
    BonificaSyncRunRequest,
    BonificaSyncRunResponse,
    BonificaSyncStatusResponse,
)
from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSessionManager
from app.modules.operazioni.services.sync_report_types import sync_white_report_types
from app.modules.operazioni.services.sync_areas import sync_white_areas
from app.modules.operazioni.services.sync_operators import sync_white_operators
from app.modules.operazioni.services.sync_vehicles import (
    sync_white_refuels,
    sync_white_taken_charge,
    sync_white_vehicles,
)
from app.modules.operazioni.services.sync_white import sync_white_reports
from app.modules.operazioni.models.vehicles import Vehicle
from app.services.elaborazioni_bonifica_oristanese import (
    mark_credential_error,
    mark_credential_used,
    pick_credential,
)

SUPPORTED_SYNC_ENTITIES = (
    "report_types",
    "reports",
    "vehicles",
    "refuels",
    "taken_charge",
    "users",
    "areas",
    "warehouse_requests",
    "org_charts",
    "consorziati",
)
DATE_AWARE_SYNC_ENTITIES = {"reports", "refuels", "taken_charge", "warehouse_requests"}
VEHICLE_DEPENDENT_SYNC_ENTITIES = {"refuels", "taken_charge"}
logger = logging.getLogger(__name__)
_background_tasks: set[asyncio.Task] = set()
_BACKEND_PROCESS_STARTED_AT = datetime.now(timezone.utc)


@dataclass(frozen=True)
class _SyncExecutionResult:
    synced: int
    skipped: int
    errors: int
    error_detail: str | None = None


def _persist_job_runtime_snapshot(
    db: Session,
    job: WCSyncJob,
    *,
    source_total: int | None = None,
) -> None:
    """
    Persist minimal runtime information while the entity is still running.
    This keeps the UI status endpoint from showing only '—' until completion.
    """
    updates: dict[str, object] = {}
    if source_total is not None:
        updates["source_total"] = int(source_total)
    if updates:
        job.params_json = {**(job.params_json or {}), **updates}

    # Ensure counters are visible even before finalize.
    if job.records_synced is None:
        job.records_synced = 0
    if job.records_skipped is None:
        job.records_skipped = 0
    if job.records_errors is None:
        job.records_errors = 0

    db.flush()
    db.commit()


def _resolve_entities(request: BonificaSyncRunRequest) -> list[str]:
    requested = request.entities
    if requested == "all":
        return list(SUPPORTED_SYNC_ENTITIES)
    if isinstance(requested, str):
        requested_entities = [requested]
    else:
        requested_entities = requested

    unknown = sorted(set(requested_entities) - set(SUPPORTED_SYNC_ENTITIES))
    if unknown:
        raise RuntimeError(
            "Entity Bonifica non ancora supportate in questa fase: " + ", ".join(unknown)
        )

    return [entity for entity in SUPPORTED_SYNC_ENTITIES if entity in requested_entities]


def _resolve_date_window(request: BonificaSyncRunRequest, entity: str) -> tuple[date | None, date | None]:
    if entity not in DATE_AWARE_SYNC_ENTITIES:
        return None, None

    if request.date_from and request.date_to and request.date_from > request.date_to:
        raise RuntimeError("`date_from` non può essere successiva a `date_to`")

    end_date = request.date_to or date.today()
    start_date = request.date_from or (end_date - timedelta(days=settings.wc_sync_default_days))
    return start_date, end_date


def _parse_optional_iso_date(raw_value: object) -> date | None:
    if isinstance(raw_value, datetime):
        return raw_value.date()
    if isinstance(raw_value, date):
        return raw_value
    if not isinstance(raw_value, str) or not raw_value:
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return None


def _is_single_entity_request(request: BonificaSyncRunRequest, entity: str) -> bool:
    requested = request.entities
    if isinstance(requested, str):
        return requested == entity
    return len(requested) == 1 and requested[0] == entity


def _resolve_date_window_from_job(job: WCSyncJob, entity: str) -> tuple[date | None, date | None]:
    if entity not in DATE_AWARE_SYNC_ENTITIES:
        return None, None

    params = job.params_json or {}
    inherited_request = BonificaSyncRunRequest(
        entities=[entity],
        date_from=_parse_optional_iso_date(params.get("date_from")),
        date_to=_parse_optional_iso_date(params.get("date_to")),
    )
    return _resolve_date_window(inherited_request, entity)


def _resolve_job_params(
    db: Session,
    request: BonificaSyncRunRequest,
    entity: str,
) -> dict[str, object]:
    date_from, date_to = _resolve_date_window(request, entity)
    if (
        entity in DATE_AWARE_SYNC_ENTITIES
        and request.date_from is None
        and request.date_to is None
        and _is_single_entity_request(request, entity)
    ):
        latest_job = db.scalar(
            select(WCSyncJob)
            .where(WCSyncJob.entity == entity)
            .order_by(WCSyncJob.started_at.desc())
            .limit(1)
        )
        if latest_job is not None:
            inherited_date_from, inherited_date_to = _resolve_date_window_from_job(latest_job, entity)
            if inherited_date_from is not None or inherited_date_to is not None:
                date_from, date_to = inherited_date_from, inherited_date_to

    return {
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
    }


def _has_vehicle_sync_base(db: Session) -> bool:
    return (
        db.scalar(
            select(Vehicle.id)
            .where(
                or_(
                    Vehicle.wc_id.is_not(None),
                    Vehicle.wc_vehicle_id.is_not(None),
                    Vehicle.plate_number.is_not(None),
                )
            )
            .limit(1)
        )
        is not None
    )


def _list_vehicle_refuel_search_codes(db: Session) -> list[str]:
    vehicles = db.scalars(
        select(Vehicle).where(
            or_(
                Vehicle.wc_id.is_not(None),
                Vehicle.wc_vehicle_id.is_not(None),
                Vehicle.plate_number.is_not(None),
            )
        )
    ).all()

    search_codes: list[str] = []
    seen: set[str] = set()
    for vehicle in vehicles:
        for candidate in (vehicle.wc_vehicle_id, vehicle.plate_number, vehicle.code):
            if not candidate:
                continue
            normalized = candidate.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            search_codes.append(normalized)
            break
    return search_codes


def _validate_entity_dependencies(db: Session, entities: list[str]) -> None:
    requested_vehicle_dependents = [
        entity for entity in entities if entity in VEHICLE_DEPENDENT_SYNC_ENTITIES
    ]
    if not requested_vehicle_dependents:
        return
    if "vehicles" in entities:
        return
    if _has_vehicle_sync_base(db):
        return

    raise RuntimeError(
        "Impossibile avviare "
        + ", ".join(requested_vehicle_dependents)
        + " senza una base mezzi locale. "
        "Esegui prima `vehicles` (Automezzi e attrezzature) oppure includilo nello stesso run."
    )


def _build_job_report_summary(
    job: WCSyncJob,
    *,
    source_total: int | None = None,
    error_detail: str | None = None,
) -> dict[str, object]:
    started_at = job.started_at
    finished_at = job.finished_at or datetime.now(timezone.utc)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    if finished_at.tzinfo is None:
        finished_at = finished_at.replace(tzinfo=timezone.utc)
    duration_seconds = max(0.0, round((finished_at - started_at).total_seconds(), 3))
    params = job.params_json or {}
    effective_source_total = source_total
    if effective_source_total is None:
        raw_total = params.get("source_total")
        if isinstance(raw_total, (int, float)):
            effective_source_total = int(raw_total)
        elif isinstance(raw_total, str) and raw_total.isdigit():
            effective_source_total = int(raw_total)

    summary: dict[str, object] = {
        "entity": job.entity,
        "outcome": job.status,
        "generated_at": finished_at.isoformat(),
        "duration_seconds": duration_seconds,
        "records_synced": job.records_synced or 0,
        "records_skipped": job.records_skipped or 0,
        "records_errors": job.records_errors or 0,
        "range_used": {
            "date_from": params.get("date_from"),
            "date_to": params.get("date_to"),
        },
        "source_total": effective_source_total,
        "error_preview": None,
    }
    preview_source = error_detail or job.error_detail
    if preview_source:
        summary["error_preview"] = preview_source.split("\n")[:5]
    return summary


def _stale_job_minutes_for_entity(entity: str) -> int:
    if entity in {"users", "consorziati"}:
        return max(settings.wc_sync_user_stale_job_minutes, settings.wc_sync_stale_job_minutes)
    return settings.wc_sync_stale_job_minutes


def _create_job(
    db: Session,
    *,
    entity: str,
    current_user: ApplicationUser,
    params_json: dict,
    status: str = "running",
) -> WCSyncJob:
    job = WCSyncJob(
        id=uuid.uuid4(),
        entity=entity,
        status=status,
        triggered_by=current_user.id,
        params_json=params_json,
    )
    db.add(job)
    db.flush()
    return job


async def _run_bonifica_sync_background(
    *,
    triggered_by_user_id: int,
    request: BonificaSyncRunRequest,
    job_ids_by_entity: dict[str, str],
) -> None:
    db = SessionLocal()
    manager: BonificaOristaneseSessionManager | None = None
    credential_id: int | None = None
    entities = _resolve_entities(request)

    try:
        current_user = db.get(ApplicationUser, triggered_by_user_id)
        if current_user is None:
            raise RuntimeError("Utente non trovato per esecuzione sync Bonifica")

        credential, password = pick_credential(db)
        credential_id = credential.id

        manager = BonificaOristaneseSessionManager(
            login_identifier=credential.login_identifier,
            password=password,
            remember_me=credential.remember_me,
        )

        session = await manager.login()
        mark_credential_used(db, credential.id, authenticated_url=session.authenticated_url)
        areas_client = BonificaAreasClient(manager)
        report_types_client = BonificaReportTypesClient(manager)
        reports_client = BonificaReportsClient(manager)
        vehicles_client = BonificaVehiclesClient(manager)
        refuels_client = BonificaRefuelsClient(manager)
        taken_charge_client = BonificaTakenChargeClient(manager)
        users_client = BonificaUsersClient(manager)
        warehouse_requests_client = BonificaWarehouseRequestsClient(manager)
        org_charts_client = BonificaOrgChartsClient(manager)

        for entity in entities:
            job_id = job_ids_by_entity.get(entity)
            if not job_id:
                continue
            job = db.get(WCSyncJob, uuid.UUID(job_id))
            if job is None:
                continue

            job.status = "running"
            db.commit()

            try:
                if entity == "report_types":
                    rows, total = await report_types_client.fetch_report_types()
                    _persist_job_runtime_snapshot(db, job, source_total=total)
                    sync_result = sync_white_report_types(db=db, rows=rows)
                    result = _SyncExecutionResult(
                        synced=sync_result.synced,
                        skipped=sync_result.skipped,
                        errors=len(sync_result.errors),
                        error_detail="\n".join(sync_result.errors[:20]) if sync_result.errors else None,
                    )
                    params_updates = {"source_total": total}
                elif entity == "reports":
                    date_from, date_to = _resolve_date_window_from_job(job, entity)
                    assert date_from is not None and date_to is not None
                    rows, total = await reports_client.fetch_reports(date_from=date_from, date_to=date_to)
                    _persist_job_runtime_snapshot(db, job, source_total=total)
                    sync_result = sync_white_reports(
                        db=db,
                        current_user=current_user,
                        rows=rows,
                    )
                    result = _SyncExecutionResult(
                        synced=sync_result.synced,
                        skipped=sync_result.skipped,
                        errors=len(sync_result.errors),
                        error_detail="\n".join(sync_result.errors[:20]) if sync_result.errors else None,
                    )
                    params_updates = {"source_total": total}
                elif entity == "vehicles":
                    rows, total = await vehicles_client.fetch_vehicles()
                    _persist_job_runtime_snapshot(db, job, source_total=total)
                    sync_result = sync_white_vehicles(
                        db=db,
                        current_user=current_user,
                        rows=rows,
                    )
                    result = _SyncExecutionResult(
                        synced=sync_result.vehicles_synced,
                        skipped=sync_result.vehicles_skipped,
                        errors=len(sync_result.errors),
                        error_detail="\n".join(sync_result.errors[:20]) if sync_result.errors else None,
                    )
                    params_updates = {"source_total": total}
                elif entity == "refuels":
                    date_from, date_to = _resolve_date_window_from_job(job, entity)
                    assert date_from is not None and date_to is not None
                    vehicle_codes = _list_vehicle_refuel_search_codes(db)
                    rows, total = await refuels_client.fetch_refuels_for_vehicle_codes(
                        vehicle_codes=vehicle_codes,
                        date_from=date_from,
                        date_to=date_to,
                    )
                    _persist_job_runtime_snapshot(db, job, source_total=total)
                    sync_result = sync_white_refuels(
                        db=db,
                        current_user=current_user,
                        rows=rows,
                    )
                    result = _SyncExecutionResult(
                        synced=sync_result.fuel_logs_synced,
                        skipped=sync_result.fuel_logs_skipped,
                        errors=len(sync_result.errors),
                        error_detail="\n".join(sync_result.errors[:20]) if sync_result.errors else None,
                    )
                    params_updates = {"source_total": total}
                elif entity == "taken_charge":
                    date_from, date_to = _resolve_date_window_from_job(job, entity)
                    assert date_from is not None and date_to is not None
                    rows, total = await taken_charge_client.fetch_taken_charge(
                        date_from=date_from,
                        date_to=date_to,
                    )
                    _persist_job_runtime_snapshot(db, job, source_total=total)
                    sync_result = sync_white_taken_charge(
                        db=db,
                        current_user=current_user,
                        rows=rows,
                    )
                    result = _SyncExecutionResult(
                        synced=sync_result.usage_sessions_synced,
                        skipped=sync_result.usage_sessions_skipped,
                        errors=len(sync_result.errors),
                        error_detail="\n".join(sync_result.errors[:20]) if sync_result.errors else None,
                    )
                    params_updates = {"source_total": total}
                elif entity == "users":
                    rows, total = await users_client.fetch_users()
                    _persist_job_runtime_snapshot(db, job, source_total=total)
                    sync_result = sync_white_operators(db=db, rows=rows)
                    result = _SyncExecutionResult(
                        synced=sync_result.synced,
                        skipped=sync_result.skipped,
                        errors=len(sync_result.errors),
                        error_detail="\n".join(sync_result.errors[:20]) if sync_result.errors else None,
                    )
                    params_updates = {"source_total": total}
                elif entity == "areas":
                    rows, total = await areas_client.fetch_areas()
                    _persist_job_runtime_snapshot(db, job, source_total=total)
                    sync_result = sync_white_areas(db=db, rows=rows)
                    result = _SyncExecutionResult(
                        synced=sync_result.synced,
                        skipped=sync_result.skipped,
                        errors=len(sync_result.errors),
                        error_detail="\n".join(sync_result.errors[:20]) if sync_result.errors else None,
                    )
                    params_updates = {"source_total": total}
                elif entity == "warehouse_requests":
                    date_from, date_to = _resolve_date_window_from_job(job, entity)
                    assert date_from is not None and date_to is not None
                    rows, total = await warehouse_requests_client.fetch_warehouse_requests(
                        date_from=date_from,
                        date_to=date_to,
                    )
                    _persist_job_runtime_snapshot(db, job, source_total=total)
                    sync_result = sync_white_warehouse_requests(db=db, rows=rows)
                    result = _SyncExecutionResult(
                        synced=sync_result.synced,
                        skipped=sync_result.skipped,
                        errors=len(sync_result.errors),
                        error_detail="\n".join(sync_result.errors[:20]) if sync_result.errors else None,
                    )
                    params_updates = {"source_total": total}
                elif entity == "org_charts":
                    rows, total = await org_charts_client.fetch_org_charts()
                    _persist_job_runtime_snapshot(db, job, source_total=total)
                    sync_result = sync_white_org_charts(db=db, rows=rows)
                    result = _SyncExecutionResult(
                        synced=sync_result.synced,
                        skipped=sync_result.skipped,
                        errors=len(sync_result.errors),
                        error_detail="\n".join(sync_result.errors[:20]) if sync_result.errors else None,
                    )
                    params_updates = {"source_total": total}
                elif entity == "consorziati":
                    rows, total = await users_client.fetch_consorziati()
                    _persist_job_runtime_snapshot(db, job, source_total=total)
                    sync_result = sync_white_consorziati(db=db, rows=rows)
                    result = _SyncExecutionResult(
                        synced=sync_result.synced,
                        skipped=sync_result.skipped,
                        errors=len(sync_result.errors),
                        error_detail="\n".join(sync_result.errors[:20]) if sync_result.errors else None,
                    )
                    params_updates = {"source_total": total}
                else:  # pragma: no cover
                    raise RuntimeError(f"Entity `{entity}` non supportata")

                _finalize_job(db, job, result, params_updates=params_updates)
                db.commit()
            except Exception as exc:
                logger.exception("Bonifica sync failed for entity `%s`", entity)
                job.status = "failed"
                job.finished_at = datetime.now(timezone.utc)
                job.records_synced = 0
                job.records_skipped = 0
                job.records_errors = 1
                job.error_detail = str(exc)
                job.params_json = {
                    **(job.params_json or {}),
                    "report_summary": _build_job_report_summary(job, error_detail=str(exc)),
                }
                db.commit()
    except Exception as exc:
        logger.exception("Bonifica sync bootstrap failed before entity execution")
        if credential_id is not None:
            mark_credential_error(db, credential_id, str(exc))
        for entity in entities:
            job_id = job_ids_by_entity.get(entity)
            if not job_id:
                continue
            job = db.get(WCSyncJob, uuid.UUID(job_id))
            if job is None:
                continue
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc)
            job.records_synced = 0
            job.records_skipped = 0
            job.records_errors = 1
            job.error_detail = str(exc)
            job.params_json = {
                **(job.params_json or {}),
                "report_summary": _build_job_report_summary(job, error_detail=str(exc)),
            }
        db.commit()
    finally:
        try:
            if manager is not None:
                await manager.close()
        finally:
            db.close()


def _finalize_job(
    db: Session,
    job: WCSyncJob,
    result: _SyncExecutionResult,
    *,
    params_updates: dict[str, object] | None = None,
) -> None:
    job.status = "failed" if result.errors > 0 and result.synced == 0 else "completed"
    job.finished_at = datetime.now(timezone.utc)
    job.records_synced = result.synced
    job.records_skipped = result.skipped
    job.records_errors = result.errors
    job.error_detail = result.error_detail
    merged_params = {**(job.params_json or {}), **(params_updates or {})}
    merged_params["report_summary"] = _build_job_report_summary(
        job,
        source_total=params_updates.get("source_total") if params_updates else None,
        error_detail=result.error_detail,
    )
    job.params_json = merged_params
    db.flush()


def _expire_stale_running_jobs(db: Session) -> None:
    now = datetime.now(timezone.utc)
    stale_jobs = db.scalars(
        select(WCSyncJob).where(
            WCSyncJob.status == "running",
            WCSyncJob.finished_at.is_(None),
        )
    ).all()
    if not stale_jobs:
        return

    expired_at = now
    for job in stale_jobs:
        started_at = job.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        if started_at < _BACKEND_PROCESS_STARTED_AT:
            orphaned_detail = (
                "Job marcato come failed: backend riavviato mentre il job era in stato running; "
                "il task runtime originale non e piu attivo. Rilanciare dal frontend."
            )
            job.status = "failed"
            job.finished_at = expired_at
            job.records_synced = job.records_synced or 0
            job.records_skipped = job.records_skipped or 0
            job.records_errors = max(job.records_errors or 0, 1)
            job.error_detail = f"{job.error_detail}\n{orphaned_detail}".strip() if job.error_detail else orphaned_detail
            job.params_json = {
                **(job.params_json or {}),
                "report_summary": _build_job_report_summary(job, error_detail=job.error_detail),
            }
            continue

        stale_job_minutes = _stale_job_minutes_for_entity(job.entity)
        cutoff = now - timedelta(minutes=stale_job_minutes)
        if started_at >= cutoff:
            continue
        stale_detail = (
            "Job marcato come failed: rimasto in stato running oltre la soglia "
            f"di {stale_job_minutes} minuti."
        )
        job.status = "failed"
        job.finished_at = expired_at
        job.records_synced = job.records_synced or 0
        job.records_skipped = job.records_skipped or 0
        job.records_errors = max(job.records_errors or 0, 1)
        job.error_detail = f"{job.error_detail}\n{stale_detail}".strip() if job.error_detail else stale_detail
        job.params_json = {
            **(job.params_json or {}),
            "report_summary": _build_job_report_summary(job, error_detail=job.error_detail),
        }
    db.commit()


async def run_bonifica_sync(
    db: Session,
    current_user: ApplicationUser,
    request: BonificaSyncRunRequest,
) -> BonificaSyncRunResponse:
    _expire_stale_running_jobs(db)
    entities = _resolve_entities(request)
    _validate_entity_dependencies(db, entities)
    jobs: dict[str, WCSyncJob] = {}

    for entity in entities:
        params_json = _resolve_job_params(db, request, entity)
        jobs[entity] = _create_job(
            db,
            entity=entity,
            current_user=current_user,
            status="queued",
            params_json=params_json,
        )
    db.commit()

    task = asyncio.create_task(
        _run_bonifica_sync_background(
            triggered_by_user_id=current_user.id,
            request=request,
            job_ids_by_entity={entity: str(job.id) for entity, job in jobs.items()},
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return BonificaSyncRunResponse(
        jobs={
            entity: BonificaSyncJobStart(job_id=str(job.id), status=job.status, started_at=job.started_at)
            for entity, job in jobs.items()
        }
    )


def get_bonifica_sync_status(db: Session) -> BonificaSyncStatusResponse:
    _expire_stale_running_jobs(db)
    latest_by_entity: dict[str, BonificaSyncEntityStatus] = {}

    for entity in SUPPORTED_SYNC_ENTITIES:
        latest_job = db.scalar(
            select(WCSyncJob)
            .where(WCSyncJob.entity == entity)
            .order_by(WCSyncJob.started_at.desc())
            .limit(1)
        )
        if latest_job is None:
            latest_by_entity[entity] = BonificaSyncEntityStatus(
                entity=entity,
                status="never",
            )
            continue

        latest_by_entity[entity] = BonificaSyncEntityStatus(
            job_id=str(latest_job.id),
            entity=entity,
            status=latest_job.status,
            last_started_at=latest_job.started_at,
            last_finished_at=latest_job.finished_at,
            records_synced=latest_job.records_synced,
            records_skipped=latest_job.records_skipped,
            records_errors=latest_job.records_errors,
            error_detail=latest_job.error_detail,
            params_json=latest_job.params_json,
        )

    return BonificaSyncStatusResponse(entities=latest_by_entity)
