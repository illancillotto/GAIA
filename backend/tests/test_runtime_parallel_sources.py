from __future__ import annotations

import asyncio
from contextlib import nullcontext
from threading import Barrier, Lock, get_ident
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.elaborazioni import domande_irrigue_parallel as domande
from app.modules.elaborazioni.capacitas.apps.involture.client import CapacitasSessionExpiredError
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagrafica,
    CapacitasDomandeIrrigueAnagraficaSearch,
    CapacitasDomandeIrrigueSyncJobCreateRequest,
)
from app.modules.elaborazioni.ordered_prefetch import OrderedPrefetch
from app.modules.utenze.services import registry_prefetch as registry


def test_prefetch_runs_four_resources_and_preserves_order() -> None:
    async def scenario():
        entered = []
        released = asyncio.Event()
        active = set()

        async def fetch(item, resource):
            assert resource not in active
            active.add(resource)
            entered.append(item)
            if len(entered) == 4:
                released.set()
            await asyncio.wait_for(released.wait(), 1)
            await asyncio.sleep(0)
            active.remove(resource)
            return item

        prefetch = OrderedPrefetch(range(9), list(range(4)), fetch)
        results = [await prefetch.take() for _ in range(9)]
        await prefetch.close()
        assert results == list(range(9))
        assert entered[:4] == list(range(4))

    asyncio.run(scenario())


def test_prefetch_error_and_cancellation_cleanup() -> None:
    async def scenario():
        cancelled = []

        async def fetch(item, _resource):
            if item == 0:
                raise RuntimeError("remote failed")
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(item)

        prefetch = OrderedPrefetch(range(3), [1, 2], fetch)
        with pytest.raises(RuntimeError, match="remote failed"):
            await prefetch.take()
        await asyncio.sleep(0)
        await prefetch.close()
        assert set(cancelled) == {1, 2}

    with pytest.raises(ValueError, match="resource"):
        OrderedPrefetch([], [], None)
    asyncio.run(scenario())


def _row(identifier, context="same"):
    return CapacitasAnagrafica(id=identifier, cco=context, com="001", pvc="097", fraz="01")


@pytest.mark.parametrize("deduplicate,expected", [(True, 1), (False, 2)])
def test_domande_source_keeps_metadata_and_context_deduplication(deduplicate, expected) -> None:
    async def scenario():
        searches = [
            CapacitasDomandeIrrigueAnagraficaSearch(q=value)
            for value in ("12345678901", "12345678902")
        ]
        clients = [
            SimpleNamespace(
                search_anagrafica=AsyncMock(return_value=SimpleNamespace(rows=[_row(str(index))]))
            )
            for index in range(2)
        ]
        scraper = SimpleNamespace(
            fetch_for_anagrafica_rows=AsyncMock(side_effect=lambda rows, **kwargs: rows)
        )
        payload = CapacitasDomandeIrrigueSyncJobCreateRequest(
            searches=searches, deduplicate_contexts=deduplicate
        )
        source = domande.ParallelDomandeSource(searches, clients, [scraper], payload)
        for search in searches:
            await source.search_anagrafica(q=search.q)
        rows = list(source._rows)
        if deduplicate:
            rows = domande.service._deduplicate_rows(rows)
        received = [await source.fetch_for_anagrafica_rows([row]) for row in rows]
        assert len(received) == expected
        if deduplicate:
            assert received[0][0].source_search_codici_fiscali == [search.q for search in searches]
        await source.close()
        assert scraper.fetch_for_anagrafica_rows.await_count == expected

    asyncio.run(scenario())


def test_domande_search_renews_its_own_session_and_fails_after_second_expiry() -> None:
    async def scenario():
        search = CapacitasDomandeIrrigueAnagraficaSearch(q="12345678901")
        client = SimpleNamespace(
            search_anagrafica=AsyncMock(
                side_effect=[CapacitasSessionExpiredError("expired"), "result"]
            ),
            relogin=AsyncMock(),
        )
        source = domande.ParallelDomandeSource(
            [], [client], [], CapacitasDomandeIrrigueSyncJobCreateRequest(searches=[search])
        )
        assert await source._search(search, client) == (search, "result")
        client.relogin.assert_awaited_once()
        with pytest.raises(CapacitasSessionExpiredError, match="rinnovo"):
            await source.relogin()
        await source.close()

    asyncio.run(scenario())


def test_domande_prefetch_fails_closed_on_changed_search_or_context() -> None:
    async def scenario():
        search = CapacitasDomandeIrrigueAnagraficaSearch(q="12345678901")
        client = SimpleNamespace(
            search_anagrafica=AsyncMock(return_value=SimpleNamespace(rows=[_row("1")]))
        )
        scraper = SimpleNamespace(fetch_for_anagrafica_rows=AsyncMock(return_value="batch"))
        payload = CapacitasDomandeIrrigueSyncJobCreateRequest(searches=[search])
        changed_search = domande.ParallelDomandeSource([search], [client], [scraper], payload)
        with pytest.raises(RuntimeError, match="sequenza"):
            await changed_search.search_anagrafica(q="different")
        assert changed_search._rows == []
        await changed_search.close()
        changed_row = domande.ParallelDomandeSource([search], [client], [scraper], payload)
        await changed_row.search_anagrafica(q=search.q)
        with pytest.raises(RuntimeError, match="contesto"):
            await changed_row.fetch_for_anagrafica_rows([_row("other", "different")])
        await changed_row.close()

    asyncio.run(scenario())


def test_existing_domande_job_coordinator_keeps_order_counters_and_single_writer(
    monkeypatch,
) -> None:
    from app.modules.catasto.services.domande_irrigue import DomandeIrriguePersistSummary
    from app.modules.elaborazioni.capacitas.apps.involture.domande_irrigue import (
        CapacitasDomandeIrrigueBatchResult,
        result_from_anagrafica_row,
    )

    async def scenario():
        searches = [
            CapacitasDomandeIrrigueAnagraficaSearch(q=f"1234567890{index}") for index in range(4)
        ]
        rows = [_row(str(index), str(index)) for index in range(4)]
        clients = [
            SimpleNamespace(search_anagrafica=AsyncMock(return_value=SimpleNamespace(rows=[row])))
            for row in rows
        ]
        entered = []
        ready = asyncio.Event()

        async def fetch(items, **kwargs):
            row = items[0]
            entered.append(row.id)
            if len(entered) == 4:
                ready.set()
            await asyncio.wait_for(ready.wait(), 1)
            item = result_from_anagrafica_row(row)
            return CapacitasDomandeIrrigueBatchResult(
                source_total=1, checked_records=1, records_with_domande=0, items=[item]
            )

        payload = CapacitasDomandeIrrigueSyncJobCreateRequest(
            searches=searches, run_anomaly_checks=False, throttle_ms=0
        )
        source = domande.ParallelDomandeSource(
            searches,
            clients,
            [SimpleNamespace(fetch_for_anagrafica_rows=fetch) for _ in range(4)],
            payload,
        )
        db = MagicMock()
        job = SimpleNamespace(id=1, payload_json=payload.model_dump(mode="json"), result_json=None)
        persisted = []

        def persist(session, batch, **kwargs):
            assert session is db
            persisted.append(batch.items[0].source_row_id)
            return DomandeIrriguePersistSummary(1, 0, 0, 0, 0, 0, 0, 0)

        monkeypatch.setattr(domande.service, "persist_capacitas_domande_irrigue_batch", persist)
        await domande.service.run_domande_irrigue_sync_job(db, source, source, job)
        await source.close()
        assert entered == [row.id for row in rows]
        assert persisted == [row.id for row in rows]
        assert job.status == "succeeded"
        assert job.result_json["searches_completed"] == 4
        assert job.result_json["processed_rows"] == 4
        assert job.result_json["failed_items"] == 0

    asyncio.run(scenario())


@pytest.mark.parametrize("failure", [None, 2])
def test_open_sources_closes_all_sessions_after_partial_login_failure(monkeypatch, failure) -> None:
    entered, closed = [], []

    class Manager:
        def __init__(self, username, password):
            self.index = len(entered)

        async def __aenter__(self):
            entered.append(self.index)
            return self

        async def __aexit__(self, *args):
            closed.append(self.index)

        async def activate_app(self, app):
            if self.index == failure:
                raise RuntimeError("activate failed")

        async def start_keepalive(self, app):
            pass

    monkeypatch.setattr(domande, "CapacitasSessionManager", Manager)
    monkeypatch.setattr(domande, "InVoltureClient", lambda manager: manager)
    monkeypatch.setattr(domande, "DomandeIrrigueScraper", lambda manager: manager)

    async def scenario():
        expectation = (
            pytest.raises(RuntimeError, match="activate failed")
            if failure is not None
            else nullcontext()
        )
        with expectation:
            async with domande.AsyncExitStack() as stack:
                await domande.open_sources(stack, "user", "password", 4)

    asyncio.run(scenario())
    assert entered == ([0, 1, 2] if failure is not None else [0, 1, 2, 3])
    assert closed == list(reversed(entered))


@pytest.mark.parametrize("status,credential", [("processing", 7), ("failed", None)])
def test_failure_preserves_terminal_status(monkeypatch, status, credential) -> None:
    db, job = MagicMock(), SimpleNamespace(status=status)
    mark = MagicMock()
    monkeypatch.setattr(domande, "mark_credential_error", mark)
    domande.fail_job(db, job, credential, RuntimeError("failed"))
    db.rollback.assert_called_once()
    if status == "processing":
        assert job.status == "failed" and job.error_detail == "failed"
        assert job.completed_at is not None
        mark.assert_called_once_with(db, 7, "failed")
    else:
        db.commit.assert_not_called()
        mark.assert_not_called()


@pytest.mark.parametrize("mode", ["missing", "success", "credentials", "remote"])
def test_parallel_domande_entrypoint(monkeypatch, mode) -> None:
    job = SimpleNamespace(
        payload_json={"role_anno_campagna": 2025}, credential_id=7, status="processing"
    )
    db = MagicMock()
    db.get.return_value = None if mode == "missing" else job
    monkeypatch.setattr(domande, "SessionLocal", lambda: nullcontext(db))
    credential = SimpleNamespace(id=7, username="user")
    pick = MagicMock(return_value=(credential, "password"))
    if mode == "credentials":
        pick.side_effect = RuntimeError("unavailable")
    monkeypatch.setattr(domande, "pick_credential", pick)
    monkeypatch.setattr(domande.service, "_job_searches", lambda *args: [])
    monkeypatch.setattr(domande, "open_sources", AsyncMock(return_value=([object()], [object()])))
    run = AsyncMock()
    if mode == "remote":
        run.side_effect = RuntimeError("remote failed")
    monkeypatch.setattr(domande.service, "run_domande_irrigue_sync_job", run)
    used, failed = MagicMock(), MagicMock()
    monkeypatch.setattr(domande, "mark_credential_used", used)
    monkeypatch.setattr(domande, "fail_job", failed)

    asyncio.run(domande.run_parallel_domande_job(57, 4))

    if mode == "missing":
        pick.assert_not_called()
    elif mode == "success":
        used.assert_called_once_with(db, 7)
    else:
        assert failed.call_args.args[2] == (None if mode == "credentials" else 7)


def test_registry_prefetch_uses_four_separate_connectors_and_bounded_window(monkeypatch) -> None:
    subjects = list(range(6))
    db = MagicMock()
    db.scalars.return_value.all.return_value = subjects
    job = SimpleNamespace(id=1, log_json={})
    lock, barrier = Lock(), Barrier(4, timeout=3)
    connections, visits = [], []

    class PreviewService:
        def __init__(self, connector):
            self.connector = connector

        def match_existing_subject_folder(self, session, subject):
            return SimpleNamespace(id=subject.id)

        def preview_subject_folder(self, matched, *, strict):
            with lock:
                visits.append((matched.id, get_ident()))
            if matched.id < 4:
                barrier.wait()
            return matched.id

    def connector():
        result = MagicMock()
        connections.append(result)
        return result

    def session():
        result = MagicMock()
        result.get.side_effect = lambda model, subject_id: SimpleNamespace(id=subject_id)
        return nullcontext(result)

    monkeypatch.setattr(registry, "SessionLocal", session)
    monkeypatch.setattr(registry.service, "get_nas_client", connector)
    monkeypatch.setattr(registry.service, "AnagraficaImportPreviewService", PreviewService)
    prefetch = registry.RegistryPrefetch(db, job, 4)
    results = []
    for subject_id in subjects:
        matched = prefetch.match_existing_subject_folder(db, SimpleNamespace(id=subject_id))
        results.append(prefetch.preview_subject_folder(matched, strict=True))
        assert len(prefetch._pending) <= 4
    prefetch.close()
    prefetch.close()
    assert results == subjects
    assert len({thread for identifier, thread in visits if identifier < 4}) == 4
    assert len(connections) == 4
    for connection in connections:
        connection.close.assert_called_once()


def test_registry_resume_skips_completed_and_handles_new_subject(monkeypatch) -> None:
    db = MagicMock()
    db.scalars.return_value.all.return_value = [1, 2]
    monkeypatch.setattr(registry.service, "registry_job_completed_subject_ids", lambda *args: {1})
    monkeypatch.setattr(
        registry.RegistryPrefetch, "_fetch", lambda self, subject_id: (subject_id, subject_id)
    )
    prefetch = registry.RegistryPrefetch(
        db, SimpleNamespace(id=1, log_json={"mode": "registry_import_resume"}), 4
    )
    assert prefetch.match_existing_subject_folder(db, SimpleNamespace(id=2)) == 2
    assert prefetch.match_existing_subject_folder(db, SimpleNamespace(id=3)) == 3
    prefetch.close()
    non_dict = registry.RegistryPrefetch(db, SimpleNamespace(id=1, log_json=None), 1)
    non_dict.close()


@pytest.mark.parametrize("mode", ["missing", "wrong_letter", "success", "failure"])
def test_registry_entrypoint_closes_prefetch_even_on_failure(monkeypatch, mode) -> None:
    db = MagicMock()
    db.get.return_value = (
        None
        if mode == "missing"
        else SimpleNamespace(letter="REGISTRY" if mode != "wrong_letter" else "A")
    )
    prefetch = MagicMock()
    process = MagicMock()
    if mode == "failure":
        process.side_effect = RuntimeError("failed")
    monkeypatch.setattr(registry, "SessionLocal", lambda: nullcontext(db))
    monkeypatch.setattr(registry, "RegistryPrefetch", lambda *args: prefetch)
    monkeypatch.setattr(registry.service, "process_registry_bulk_import_job", process)
    if mode == "failure":
        with pytest.raises(RuntimeError, match="failed"):
            registry.run_parallel_registry_job(1, 4)
    else:
        registry.run_parallel_registry_job(1, 4)
    assert prefetch.close.call_count == (1 if mode in {"success", "failure"} else 0)
