"""Bounded parallel browser work, with draining shutdown and per-account ownership."""

import asyncio
import logging
import os

from posta_online_queue import PosteQueue

logger = logging.getLogger(__name__)


def concurrent_account_limit() -> int:
    limit = int(os.getenv("POSTA_ONLINE_MAX_CONCURRENT_ACCOUNTS", "3"))
    if not 1 <= limit <= 32:
        raise ValueError("POSTA_ONLINE_MAX_CONCURRENT_ACCOUNTS deve essere tra 1 e 32")
    return limit


class PostePool:
    def __init__(self, queue, process, state, *, limit: int, poll_interval: float) -> None:
        self.queue = queue
        self.process = process
        self.state = state
        self.limit = limit
        self.poll_interval = poll_interval
        self.tasks: set[asyncio.Task] = set()
        self.leases: dict[asyncio.Task, object] = {}

    async def _execute(self, claimed) -> None:
        try:
            await self.process(claimed.id)
        except Exception as exc:
            logger.exception("Job Poste Online %s fallito nel pool", claimed.id)
            self.queue.fail(claimed.id, str(exc))
        finally:
            claimed.lease.close()

    def _fill(self) -> None:
        while len(self.tasks) < self.limit and not self.state.stop_requested:
            claimed = self.queue.claim()
            if claimed is None:
                return
            logger.info("Job Poste Online %s prelevato dal pool", claimed.id)
            task = asyncio.create_task(self._execute(claimed))
            self.tasks.add(task)
            self.leases[task] = claimed.lease

    async def run(self) -> None:
        try:
            while not self.state.stop_requested:
                self._fill()
                if not self.tasks:
                    await asyncio.sleep(self.poll_interval)
                    continue
                done, self.tasks = await asyncio.wait(
                    self.tasks, timeout=self.poll_interval, return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    self.leases.pop(task)
                    task.result()
            await asyncio.gather(*self.tasks)
        finally:
            for task in self.leases:
                task.cancel()
            await asyncio.gather(*self.leases, return_exceptions=True)
            for lease in self.leases.values():
                lease.close()


async def run_with_poste_pool(worker, runtime) -> None:
    families = worker.job_families
    if "posta_online" not in families:
        await worker.run()
        return
    queue = PosteQueue(
        runtime.SessionLocal,
        worker._posta_online_retry_ready,
        worker._posta_online_job_credential_id,
    )
    pool = PostePool(
        queue,
        worker._process_posta_online_job,
        worker.state,
        limit=concurrent_account_limit(),
        poll_interval=runtime.POLL_INTERVAL_SEC,
    )
    worker.job_families = families - {"posta_online"}
    try:
        if worker.job_families:
            async with asyncio.TaskGroup() as group:
                group.create_task(worker.run())
                group.create_task(pool.run())
        else:
            worker._install_signal_handlers()
            await pool.run()
    finally:
        worker.job_families = families
