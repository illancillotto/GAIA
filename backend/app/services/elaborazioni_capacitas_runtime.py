from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagraficaHistoryImportJobCreateRequest,
    CapacitasParticelleSyncJobCreateRequest,
    CapacitasTerreniJobCreateRequest,
)
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
from app.services.elaborazioni_capacitas import mark_credential_error, mark_credential_used, pick_credential
from app.services.elaborazioni_capacitas_anagrafica_history import get_anagrafica_history_job, run_anagrafica_history_job
from app.services.elaborazioni_capacitas_particelle_sync import get_particelle_sync_job, run_particelle_sync_job
from app.services.elaborazioni_capacitas_terreni import get_terreni_sync_job, run_terreni_sync_job

logger = logging.getLogger(__name__)

TERMINAL_JOB_STATUSES = {"succeeded", "completed_with_errors", "failed"}


async def run_terreni_job_by_id(job_id: int) -> None:
    db = SessionLocal()
    managers: list[CapacitasSessionManager] = []
    credential_id: int | None = None
    try:
        job = get_terreni_sync_job(db, job_id)
        if job is None:
            return

        try:
            credential, password = pick_credential(db, job.credential_id)
        except RuntimeError as exc:
            job.status = "failed"
            job.error_detail = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        credential_id = credential.id
        payload = CapacitasTerreniJobCreateRequest.model_validate(job.payload_json or {})
        session_count = min(payload.parallel_workers, max(1, len(payload.items)))
        for _ in range(session_count):
            manager = CapacitasSessionManager(credential.username, password)
            await manager.login()
            await manager.activate_app("involture")
            await manager.start_keepalive("involture")
            managers.append(manager)
        client = InVoltureClient(managers[0])
        clients = [InVoltureClient(active_manager) for active_manager in managers]
        await run_terreni_sync_job(db, client, job, session_factory=SessionLocal, clients=clients)
        mark_credential_used(db, credential.id)
    except Exception as exc:
        logger.exception("Errore worker job terreni Capacitas: job_id=%d err=%s", job_id, exc)
        db.rollback()
        if credential_id is not None:
            mark_credential_error(db, credential_id, str(exc))
        job = get_terreni_sync_job(db, job_id)
        if job is not None and job.status not in TERMINAL_JOB_STATUSES:
            job.status = "failed"
            job.error_detail = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        for manager in managers:
            await manager.close()
        db.close()


async def run_particelle_job_by_id(job_id: int) -> None:
    db = SessionLocal()
    managers: list[CapacitasSessionManager] = []
    credential_id: int | None = None
    try:
        job = get_particelle_sync_job(db, job_id)
        if job is None:
            return

        try:
            credential, password = pick_credential(db, job.credential_id)
        except RuntimeError as exc:
            job.status = "failed"
            job.error_detail = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        credential_id = credential.id
        payload = CapacitasParticelleSyncJobCreateRequest.model_validate(job.payload_json or {})
        for _ in range(payload.parallel_workers):
            manager = CapacitasSessionManager(credential.username, password)
            await manager.login()
            await manager.activate_app("involture")
            await manager.start_keepalive("involture")
            managers.append(manager)
        clients = [InVoltureClient(manager) for manager in managers]
        await run_particelle_sync_job(db, clients[0], job, session_factory=SessionLocal, clients=clients)
        mark_credential_used(db, credential.id)
    except Exception as exc:
        logger.exception("Errore worker job particelle Capacitas: job_id=%d err=%s", job_id, exc)
        db.rollback()
        if credential_id is not None:
            mark_credential_error(db, credential_id, str(exc))
        job = get_particelle_sync_job(db, job_id)
        if job is not None and job.status not in TERMINAL_JOB_STATUSES:
            job.status = "failed"
            job.error_detail = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        for manager in managers:
            await manager.close()
        db.close()


async def run_anagrafica_history_job_by_id(job_id: int) -> None:
    db = SessionLocal()
    manager: CapacitasSessionManager | None = None
    credential_id: int | None = None
    try:
        job = get_anagrafica_history_job(db, job_id)
        if job is None:
            return

        payload = CapacitasAnagraficaHistoryImportJobCreateRequest.model_validate(job.payload_json or {})
        try:
            credential, password = pick_credential(db, payload.credential_id or job.credential_id)
        except RuntimeError as exc:
            job.status = "failed"
            job.error_detail = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        credential_id = credential.id
        manager = CapacitasSessionManager(credential.username, password)
        await manager.login()
        await manager.activate_app("involture")
        await manager.start_keepalive("involture")
        client = InVoltureClient(manager)
        await run_anagrafica_history_job(db, client, job)
        mark_credential_used(db, credential.id)
    except Exception as exc:
        logger.exception("Errore worker job storico anagrafica Capacitas: job_id=%d err=%s", job_id, exc)
        db.rollback()
        if credential_id is not None:
            mark_credential_error(db, credential_id, str(exc))
        job = get_anagrafica_history_job(db, job_id)
        if job is not None and job.status not in TERMINAL_JOB_STATUSES:
            job.status = "failed"
            job.error_detail = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        if manager is not None:
            await manager.close()
        db.close()
