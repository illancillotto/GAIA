from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from datetime import UTC, datetime

from app.core.database import SessionLocal
from app.models.capacitas import CapacitasDomandeIrrigueSyncJob
from app.modules.elaborazioni.capacitas.apps.involture.client import (
    CapacitasSessionExpiredError,
    InVoltureClient,
)
from app.modules.elaborazioni.capacitas.apps.involture.domande_irrigue import DomandeIrrigueScraper
from app.modules.elaborazioni.capacitas.models import CapacitasDomandeIrrigueSyncJobCreateRequest
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
from app.modules.elaborazioni.ordered_prefetch import OrderedPrefetch
from app.services import elaborazioni_capacitas_domande_irrigue as service
from app.services.elaborazioni_capacitas import (
    mark_credential_error,
    mark_credential_used,
    pick_credential,
)

logger = logging.getLogger(__name__)


class ParallelDomandeSource:
    def __init__(self, searches, clients, scrapers, payload) -> None:
        self._payload = payload
        self._scrapers = scrapers
        self._rows = []
        self._searches = OrderedPrefetch(searches, clients, self._search)
        self._details = None

    async def _search(self, search, client):
        try:
            result = await client.search_anagrafica(
                q=search.q, tipo=search.tipo_ricerca, solo_con_beni=search.solo_con_beni
            )
        except CapacitasSessionExpiredError:
            await client.relogin()
            result = await client.search_anagrafica(
                q=search.q, tipo=search.tipo_ricerca, solo_con_beni=search.solo_con_beni
            )
        return search, result

    async def search_anagrafica(self, **kwargs):
        search, result = await self._searches.take()
        expected = (search.q, search.tipo_ricerca, search.solo_con_beni)
        actual = (kwargs.get("q"), kwargs.get("tipo", 1), kwargs.get("solo_con_beni", False))
        if actual != expected:
            raise RuntimeError("La sequenza delle ricerche e cambiata durante il prefetch")
        self._rows.extend(service._tag_search_rows(result.rows, search))
        return result

    async def relogin(self) -> None:
        raise CapacitasSessionExpiredError("Sessione scaduta anche dopo il rinnovo")

    async def fetch_for_anagrafica_rows(self, rows, **_kwargs):
        if self._details is None:
            source_rows = self._rows
            if self._payload.deduplicate_contexts:
                source_rows = service._deduplicate_rows(source_rows)
            self._details = OrderedPrefetch(source_rows, self._scrapers, self._fetch)
        source_row, batch = await self._details.take()
        if source_row.model_dump() != rows[0].model_dump():
            raise RuntimeError("Il contesto della domanda non corrisponde al prefetch")
        return batch

    async def _fetch(self, row, scraper):
        batch = await scraper.fetch_for_anagrafica_rows(
            [row],
            include_details=self._payload.include_details,
            continue_on_error=self._payload.continue_on_error,
        )
        return row, batch

    async def close(self) -> None:
        await self._searches.close()
        if self._details is not None:
            await self._details.close()


async def open_sources(stack, username, password, workers):
    clients, scrapers = [], []
    for _ in range(workers):
        manager = await stack.enter_async_context(CapacitasSessionManager(username, password))
        await manager.activate_app("involture")
        await manager.start_keepalive("involture")
        clients.append(InVoltureClient(manager))
        scrapers.append(DomandeIrrigueScraper(manager))
    return clients, scrapers


def fail_job(db, job, credential_id, error) -> None:
    db.rollback()
    if credential_id is not None:
        mark_credential_error(db, credential_id, str(error))
    db.refresh(job)
    if job.status not in {"succeeded", "completed_with_errors", "failed"}:
        job.status = "failed"
        job.error_detail = str(error)
        job.completed_at = datetime.now(UTC)
        db.commit()


async def run_parallel_domande_job(job_id: int, workers: int) -> None:
    with SessionLocal() as db:
        job = db.get(CapacitasDomandeIrrigueSyncJob, job_id)
        if job is None:
            return
        credential_id = None
        try:
            payload = CapacitasDomandeIrrigueSyncJobCreateRequest.model_validate(
                job.payload_json or {}
            )
            credential, password = pick_credential(db, payload.credential_id or job.credential_id)
            credential_id = credential.id
            searches = service._job_searches(db, payload)
            async with AsyncExitStack() as stack:
                clients, scrapers = await open_sources(
                    stack, credential.username, password, min(workers, max(1, len(searches)))
                )
                source = ParallelDomandeSource(searches, clients, scrapers, payload)
                stack.push_async_callback(source.close)
                logger.info("Domande irrigue job %s: %s sessioni parallele", job_id, len(clients))
                await service.run_domande_irrigue_sync_job(db, source, source, job)
                mark_credential_used(db, credential.id)
        except Exception as error:
            fail_job(db, job, credential_id, error)
