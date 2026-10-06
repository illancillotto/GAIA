from __future__ import annotations

import asyncio
import logging
import os
from functools import partial

import worker as worker_module
from app.modules.elaborazioni.domande_irrigue_autosync_scheduler import _window_context
from app.modules.elaborazioni.domande_irrigue_parallel import run_parallel_domande_job
from app.modules.utenze.services.registry_prefetch import run_parallel_registry_job
from app.worker_health import WorkerHeartbeat, run_with_heartbeat
from capacitas_lane_gate import LaneGate, job_scope, touch_waiting_job

logger = logging.getLogger(__name__)

DOMANDE_JOBS = (
    (
        "domande_irrigue",
        worker_module.CapacitasDomandeIrrigueSyncJob,
        worker_module.expire_stale_domande_irrigue_sync_jobs,
    ),
)
OTHER_JOBS = (
    (
        "anagrafica_history",
        worker_module.CapacitasAnagraficaHistoryImportJob,
        worker_module.expire_stale_anagrafica_history_jobs,
    ),
    ("incass", worker_module.CapacitasInCassSyncJob, worker_module.expire_stale_incass_sync_jobs),
    (
        "terreni",
        worker_module.CapacitasTerreniSyncJob,
        worker_module.expire_stale_terreni_sync_jobs,
    ),
    (
        "particelle",
        worker_module.CapacitasParticelleSyncJob,
        worker_module.expire_stale_particelle_sync_jobs,
    ),
)


def next_job(worker: worker_module.CatastoWorker, job_specs: tuple) -> tuple[str, int] | None:
    within_window, _ = _window_context()
    with worker_module.SessionLocal() as db:
        for _, _, expire in job_specs:
            expire(db)
        for manual_jobs in (True, False):
            for job_kind, model, _ in job_specs:
                if job_kind == "domande_irrigue" and not manual_jobs and not within_window:
                    continue
                claimed = worker._claim_capacitas_job(db, job_kind, model, manual_jobs=manual_jobs)
                if claimed is not None:
                    return claimed
    return None


async def process_job(worker, job_kind, job_id, workers, gate) -> None:
    if job_kind == "domande_irrigue":
        await run_parallel_domande_job(job_id, workers)
        return
    try:
        scope = job_scope(job_kind, job_id)
    except ValueError:
        await worker._process_capacitas_job(job_kind, job_id)
        return
    if scope is None:
        return
    model, namespace, identifiers = scope

    def heartbeat():
        return not worker.state.stop_requested and touch_waiting_job(model, job_id)

    if not await gate.acquire((job_kind, job_id), namespace, identifiers, heartbeat):
        return
    try:
        await worker._process_capacitas_job(job_kind, job_id)
    finally:
        gate.release((job_kind, job_id))


async def run_lane(
    worker: worker_module.CatastoWorker, job_specs: tuple, workers=1, gate=None
) -> None:
    while not worker.state.stop_requested:
        job = next_job(worker, job_specs)
        if job is None:
            await asyncio.sleep(worker_module.POLL_INTERVAL_SEC)
            continue
        job_kind, job_id = job
        logger.info("Corsia Capacitas %s: job %s prelevato", job_kind, job_id)
        if gate is None:
            await worker._process_capacitas_job(job_kind, job_id)
        else:
            await process_job(worker, job_kind, job_id, workers, gate)


async def run_registry_job(job_id, *, workers) -> None:
    await asyncio.to_thread(run_parallel_registry_job, job_id, workers)


def parallel_workers() -> int:
    workers = int(os.getenv("ELABORAZIONI_RUNTIME_PARALLEL_WORKERS", "4"))
    if not 1 <= workers <= 4:
        raise ValueError("ELABORAZIONI_RUNTIME_PARALLEL_WORKERS must be between 1 and 4")
    return workers


async def run_runtime(worker: worker_module.CatastoWorker) -> None:
    families = sorted(worker.job_families)
    workers = parallel_workers()
    gate = LaneGate()
    operations = [worker.run]
    if "registry" in worker.job_families:
        worker._process_registry_import_job = partial(run_registry_job, workers=workers)
    if "capacitas" in worker.job_families:
        with worker_module.SessionLocal() as db:
            worker._recover_capacitas_jobs(db)
            db.commit()
        worker.job_families = worker.job_families - {"capacitas"}
        operations.append(lambda: run_lane(worker, DOMANDE_JOBS, workers, gate))
        operations.extend(
            partial(run_lane, worker, OTHER_JOBS, workers, gate) for _ in range(workers)
        )
    heartbeat = WorkerHeartbeat(
        os.getenv("GAIA_WORKER_HEALTH_SERVICE", "elaborazioni-worker-runtime"),
        details={
            "families": families,
            "parallel_tasks": len(operations),
            "workers_per_lane": workers,
        },
    )
    async with asyncio.TaskGroup() as tasks:
        for operation in operations:
            tasks.create_task(
                run_with_heartbeat(operation(), heartbeat)
                if operation == worker.run
                else operation()
            )


async def main() -> None:
    worker_module.DOCUMENT_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    worker_module.CAPTCHA_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    await run_runtime(worker_module.CatastoWorker())


if __name__ == "__main__":
    asyncio.run(main())
