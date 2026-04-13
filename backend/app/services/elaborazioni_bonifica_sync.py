from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
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
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _SyncExecutionResult:
    synced: int
    skipped: int
    errors: int
    error_detail: str | None = None


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


def _create_job(
    db: Session,
    *,
    entity: str,
    current_user: ApplicationUser,
    params_json: dict,
) -> WCSyncJob:
    job = WCSyncJob(
        id=uuid.uuid4(),
        entity=entity,
        status="running",
        triggered_by=current_user.id,
        params_json=params_json,
    )
    db.add(job)
    db.flush()
    return job


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
    if params_updates:
        job.params_json = {**(job.params_json or {}), **params_updates}
    db.flush()


def _expire_stale_running_jobs(db: Session) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.wc_sync_stale_job_minutes)
    stale_jobs = db.scalars(
        select(WCSyncJob).where(
            WCSyncJob.status == "running",
            WCSyncJob.finished_at.is_(None),
            WCSyncJob.started_at < cutoff,
        )
    ).all()
    if not stale_jobs:
        return

    expired_at = datetime.now(timezone.utc)
    for job in stale_jobs:
        stale_detail = (
            "Job marcato come failed: rimasto in stato running oltre la soglia "
            f"di {settings.wc_sync_stale_job_minutes} minuti."
        )
        job.status = "failed"
        job.finished_at = expired_at
        job.records_synced = job.records_synced or 0
        job.records_skipped = job.records_skipped or 0
        job.records_errors = max(job.records_errors or 0, 1)
        job.error_detail = f"{job.error_detail}\n{stale_detail}".strip() if job.error_detail else stale_detail
    db.commit()


async def run_bonifica_sync(
    db: Session,
    current_user: ApplicationUser,
    request: BonificaSyncRunRequest,
) -> BonificaSyncRunResponse:
    _expire_stale_running_jobs(db)
    entities = _resolve_entities(request)
    jobs: dict[str, WCSyncJob] = {}

    for entity in entities:
        date_from, date_to = _resolve_date_window(request, entity)
        jobs[entity] = _create_job(
            db,
            entity=entity,
            current_user=current_user,
            params_json={
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
            },
        )
    db.commit()

    credential, password = pick_credential(db)
    manager = BonificaOristaneseSessionManager(
        login_identifier=credential.login_identifier,
        password=password,
        remember_me=credential.remember_me,
    )

    try:
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
            job = db.get(WCSyncJob, jobs[entity].id)
            assert job is not None
            try:
                if entity == "report_types":
                    rows, total = await report_types_client.fetch_report_types()
                    sync_result = sync_white_report_types(db=db, rows=rows)
                    result = _SyncExecutionResult(
                        synced=sync_result.synced,
                        skipped=sync_result.skipped,
                        errors=len(sync_result.errors),
                        error_detail="\n".join(sync_result.errors[:20]) if sync_result.errors else None,
                    )
                    params_updates = {"source_total": total}
                elif entity == "reports":
                    date_from, date_to = _resolve_date_window(request, entity)
                    assert date_from is not None and date_to is not None
                    rows, total = await reports_client.fetch_reports(date_from=date_from, date_to=date_to)
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
                    date_from, date_to = _resolve_date_window(request, entity)
                    assert date_from is not None and date_to is not None
                    rows, total = await refuels_client.fetch_refuels(
                        date_from=date_from,
                        date_to=date_to,
                    )
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
                    date_from, date_to = _resolve_date_window(request, entity)
                    assert date_from is not None and date_to is not None
                    rows, total = await taken_charge_client.fetch_taken_charge(
                        date_from=date_from,
                        date_to=date_to,
                    )
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
                    sync_result = sync_white_areas(db=db, rows=rows)
                    result = _SyncExecutionResult(
                        synced=sync_result.synced,
                        skipped=sync_result.skipped,
                        errors=len(sync_result.errors),
                        error_detail="\n".join(sync_result.errors[:20]) if sync_result.errors else None,
                    )
                    params_updates = {"source_total": total}
                elif entity == "warehouse_requests":
                    date_from, date_to = _resolve_date_window(request, entity)
                    assert date_from is not None and date_to is not None
                    rows, total = await warehouse_requests_client.fetch_warehouse_requests(
                        date_from=date_from,
                        date_to=date_to,
                    )
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
                db.commit()
    except Exception as exc:
        logger.exception("Bonifica sync bootstrap failed before entity execution")
        mark_credential_error(db, credential.id, str(exc))
        for entity in entities:
            job = db.get(WCSyncJob, jobs[entity].id)
            if job is None:
                continue
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc)
            job.records_synced = 0
            job.records_skipped = 0
            job.records_errors = 1
            job.error_detail = str(exc)
        db.commit()
    finally:
        await manager.close()

    return BonificaSyncRunResponse(
        jobs={
            entity: BonificaSyncJobStart(
                job_id=str(db.get(WCSyncJob, job.id).id),
                status=db.get(WCSyncJob, job.id).status,
                started_at=db.get(WCSyncJob, job.id).started_at,
            )
            for entity, job in jobs.items()
            if db.get(WCSyncJob, job.id) is not None
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
