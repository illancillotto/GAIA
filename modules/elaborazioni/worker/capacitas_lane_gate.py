from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import worker as worker_module
from app.modules.elaborazioni.capacitas.models import CapacitasInCassSyncJobCreateRequest
from app.services.elaborazioni_capacitas_incass import _resolve_subjects

JOB_MODELS = {
    "incass": worker_module.CapacitasInCassSyncJob,
    "terreni": worker_module.CapacitasTerreniSyncJob,
    "particelle": worker_module.CapacitasParticelleSyncJob,
    "anagrafica_history": worker_module.CapacitasAnagraficaHistoryImportJob,
    "domande_irrigue": worker_module.CapacitasDomandeIrrigueSyncJob,
}


def job_scope(job_kind, job_id):
    model = JOB_MODELS[job_kind]
    with worker_module.SessionLocal() as db:
        job = db.get(model, job_id)
        if job is None:
            return None
        if job_kind == "incass":
            payload = CapacitasInCassSyncJobCreateRequest.model_validate(job.payload_json or {})
            identifiers = {str(subject.id) for subject, _, _ in _resolve_subjects(db, payload)}
            if not payload.subject_ids and identifiers:
                job.payload_json = {**(job.payload_json or {}), "subject_ids": sorted(identifiers)}
                db.commit()
            return model, "subjects", identifiers or None
    namespace = "subjects" if job_kind == "anagrafica_history" else "catalog"
    return model, namespace, None


def touch_waiting_job(model, job_id) -> bool:
    with worker_module.SessionLocal() as db:
        job = db.get(model, job_id)
        if job is None or job.status != "processing":
            return False
        job.updated_at = datetime.now(UTC)
        db.commit()
    return True


async def maintain_job_heartbeat(model, job_id) -> None:
    while touch_waiting_job(model, job_id):
        await asyncio.sleep(60)


@asynccontextmanager
async def job_heartbeat(job_kind, job_id):
    async with asyncio.TaskGroup() as tasks:
        task = tasks.create_task(maintain_job_heartbeat(JOB_MODELS[job_kind], job_id))
        try:
            yield
        finally:
            task.cancel()


class LaneGate:
    def __init__(self) -> None:
        self._active = {}

    def _conflicts(self, namespace, identifiers) -> bool:
        for active_namespace, active_ids in self._active.values():
            if namespace != active_namespace:
                continue
            if identifiers is None or active_ids is None or identifiers & active_ids:
                return True
        return False

    async def acquire(self, key, namespace, identifiers, heartbeat) -> bool:
        while self._conflicts(namespace, identifiers):
            if not heartbeat():
                return False
            await asyncio.sleep(worker_module.POLL_INTERVAL_SEC)
        self._active[key] = (namespace, identifiers)
        return True

    def release(self, key) -> None:
        del self._active[key]
