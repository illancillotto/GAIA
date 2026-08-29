from __future__ import annotations

import asyncio
import os

from app.worker_health import WorkerHeartbeat, run_with_heartbeat

import worker as worker_module


async def run_worker(worker: worker_module.CatastoWorker) -> None:
    heartbeat = WorkerHeartbeat(
        os.getenv("GAIA_WORKER_HEALTH_SERVICE", "elaborazioni-worker"),
        details={"families": sorted(getattr(worker, "job_families", ()))},
    )
    await run_with_heartbeat(worker.run(), heartbeat)


async def main() -> None:
    worker_module.DOCUMENT_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    worker_module.CAPTCHA_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    await run_worker(worker_module.CatastoWorker())


if __name__ == "__main__":
    asyncio.run(main())
