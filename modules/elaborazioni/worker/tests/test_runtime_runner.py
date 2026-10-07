from __future__ import annotations

import asyncio
import runpy
from contextlib import asynccontextmanager, nullcontext
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import test_worker as worker_test_support  # noqa: F401 - installs isolated worker stubs

import capacitas_lane_gate as gate_module
import runtime_runner


@pytest.fixture(autouse=True)
def isolate_lane_heartbeat(monkeypatch):
    @asynccontextmanager
    async def heartbeat(*args):
        yield

    monkeypatch.setattr(runtime_runner, "job_heartbeat", heartbeat)
    monkeypatch.setenv("ELABORAZIONI_CAPACITAS_PARALLEL_WORKERS", "4")


@pytest.mark.parametrize(
    "timestamp,expected",
    [
        ("2026-10-05T15:59:00", False),
        ("2026-10-05T16:00:00", True),
        ("2026-10-06T04:59:00", True),
        ("2026-10-06T05:00:00", False),
        ("2026-12-05T17:00:00", True),
        ("2026-12-06T06:00:00", False),
    ],
)
def test_production_window_uses_rome_timezone(monkeypatch, timestamp, expected) -> None:
    from app.modules.elaborazioni import domande_irrigue_autosync_scheduler

    settings = domande_irrigue_autosync_scheduler.settings
    monkeypatch.setattr(settings, "capacitas_domande_irrigue_autosync_window_enabled", True)
    monkeypatch.setattr(settings, "capacitas_domande_irrigue_autosync_windows", "")
    monkeypatch.setattr(settings, "capacitas_domande_irrigue_autosync_start_hour", 18)
    monkeypatch.setattr(settings, "capacitas_domande_irrigue_autosync_end_hour", 7)
    monkeypatch.setattr(settings, "capacitas_domande_irrigue_autosync_timezone", "Europe/Rome")

    assert (
        runtime_runner._window_context(datetime.fromisoformat(timestamp).replace(tzinfo=UTC))[0]
        is expected
    )


def test_next_job_isolates_models_and_prioritizes_manual_jobs(monkeypatch) -> None:
    db = MagicMock()
    worker = MagicMock()
    expire_first, expire_second = MagicMock(), MagicMock()
    specs = (("incass", "first", expire_first), ("particelle", "second", expire_second))
    monkeypatch.setattr(runtime_runner.worker_module, "SessionLocal", lambda: nullcontext(db))
    monkeypatch.setattr(runtime_runner, "_window_context", lambda: (True, "cycle"))
    worker._claim_capacitas_job.side_effect = [None, None, None, ("particelle", 12)]

    assert runtime_runner.next_job(worker, specs) == ("particelle", 12)
    expire_first.assert_called_once_with(db)
    expire_second.assert_called_once_with(db)
    assert [call.kwargs["manual_jobs"] for call in worker._claim_capacitas_job.call_args_list] == [
        True,
        True,
        False,
        False,
    ]
    assert [call.args[2] for call in worker._claim_capacitas_job.call_args_list] == [
        "first",
        "second",
        "first",
        "second",
    ]


@pytest.mark.parametrize("within_window,claims", [(True, 2), (False, 1)])
def test_domande_schedule_preserves_manual_requests(monkeypatch, within_window, claims) -> None:
    worker = MagicMock()
    worker._claim_capacitas_job.return_value = None
    monkeypatch.setattr(
        runtime_runner.worker_module, "SessionLocal", lambda: nullcontext(MagicMock())
    )
    monkeypatch.setattr(runtime_runner, "_window_context", lambda: (within_window, "cycle"))

    assert runtime_runner.next_job(worker, (("domande_irrigue", "model", MagicMock()),)) is None
    assert worker._claim_capacitas_job.call_count == claims
    assert worker._claim_capacitas_job.call_args_list[0].kwargs["manual_jobs"] is True


def test_lane_waits_then_processes_until_graceful_stop(monkeypatch) -> None:
    state = SimpleNamespace(stop_requested=False)
    processed = []
    sleeps = []

    async def process(kind, job_id):
        processed.append((kind, job_id))
        state.stop_requested = True

    async def sleep(delay):
        sleeps.append(delay)

    worker = SimpleNamespace(state=state, _process_capacitas_job=process)
    jobs = iter((None, ("domande_irrigue", 57)))
    monkeypatch.setattr(runtime_runner, "next_job", lambda *_args: next(jobs))
    monkeypatch.setattr(runtime_runner.asyncio, "sleep", sleep)

    asyncio.run(runtime_runner.run_lane(worker, runtime_runner.DOMANDE_JOBS))

    assert processed == [("domande_irrigue", 57)]
    assert sleeps == [runtime_runner.worker_module.POLL_INTERVAL_SEC]


def test_runtime_lanes_run_concurrently_with_single_recovery(monkeypatch) -> None:
    db = MagicMock()
    recovered = []
    heartbeat_details = []
    entered = []

    async def scenario():
        all_entered = asyncio.Event()

        async def enter(label):
            entered.append(label)
            if len(entered) == 6:
                all_entered.set()
            await asyncio.wait_for(all_entered.wait(), timeout=1)

        async def registry():
            assert worker.job_families == {"registry"}
            await enter("registry")

        async def lane(_worker, specs, workers, gate):
            assert workers == 4
            await enter("domande" if specs is runtime_runner.DOMANDE_JOBS else "other")

        worker = SimpleNamespace(
            job_families={"capacitas", "registry"},
            run=registry,
            _recover_capacitas_jobs=lambda session: recovered.append(session),
        )
        monkeypatch.setattr(runtime_runner, "run_lane", lane)
        await runtime_runner.run_runtime(worker)

    async def heartbeat(operation, _heartbeat):
        await operation

    monkeypatch.setattr(runtime_runner.worker_module, "SessionLocal", lambda: nullcontext(db))
    monkeypatch.setattr(runtime_runner, "run_with_heartbeat", heartbeat)
    monkeypatch.setattr(
        runtime_runner,
        "WorkerHeartbeat",
        lambda service, **kwargs: heartbeat_details.append((service, kwargs)),
    )
    monkeypatch.setenv("GAIA_WORKER_HEALTH_SERVICE", "runtime-test")
    asyncio.run(scenario())

    assert set(entered) == {"registry", "domande", "other"}
    assert recovered == [db]
    db.commit.assert_called_once_with()
    assert heartbeat_details == [
        (
            "runtime-test",
            {
                "details": {
                    "families": ["capacitas", "registry"],
                    "parallel_tasks": 6,
                    "workers_per_lane": 4,
                    "capacitas_workers_per_lane": 4,
                }
            },
        )
    ]


@pytest.mark.parametrize("family", ["registry", "autodoc"])
def test_runtime_without_capacitas_keeps_families(monkeypatch, family) -> None:
    worker = SimpleNamespace(job_families={family})
    ran = []

    async def run():
        ran.append(True)

    async def heartbeat(operation, _heartbeat):
        await operation

    worker.run = run
    monkeypatch.delenv("GAIA_WORKER_HEALTH_SERVICE", raising=False)
    monkeypatch.setattr(runtime_runner, "WorkerHeartbeat", lambda *args, **kwargs: None)
    monkeypatch.setattr(runtime_runner, "run_with_heartbeat", heartbeat)

    asyncio.run(runtime_runner.run_runtime(worker))

    assert ran == [True]
    assert worker.job_families == {family}


def test_lane_failure_cancels_other_operations(monkeypatch) -> None:
    cancelled = []

    async def registry():
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append("registry")

    async def lane(_worker, specs, workers, gate):
        if specs is runtime_runner.DOMANDE_JOBS:
            raise RuntimeError("claim failed")
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append("other")

    async def heartbeat(operation, _heartbeat):
        await operation

    worker = SimpleNamespace(
        job_families={"capacitas", "registry"},
        run=registry,
        _recover_capacitas_jobs=lambda _db: None,
    )
    monkeypatch.setattr(
        runtime_runner.worker_module, "SessionLocal", lambda: nullcontext(MagicMock())
    )
    monkeypatch.setattr(runtime_runner, "run_lane", lane)
    monkeypatch.setattr(runtime_runner, "WorkerHeartbeat", lambda *args, **kwargs: None)
    monkeypatch.setattr(runtime_runner, "run_with_heartbeat", heartbeat)

    with pytest.raises(ExceptionGroup, match="unhandled errors"):
        asyncio.run(runtime_runner.run_runtime(worker))

    assert set(cancelled) == {"registry", "other"}


def test_main_creates_storage(monkeypatch, tmp_path) -> None:
    documents, captcha = tmp_path / "documents", tmp_path / "captcha"
    worker = object()
    captured = []

    async def run(instance):
        captured.append(instance)

    monkeypatch.setattr(runtime_runner.worker_module, "DOCUMENT_STORAGE_PATH", documents)
    monkeypatch.setattr(runtime_runner.worker_module, "CAPTCHA_STORAGE_PATH", captcha)
    monkeypatch.setattr(runtime_runner.worker_module, "CatastoWorker", lambda: worker)
    monkeypatch.setattr(runtime_runner, "run_runtime", run)

    asyncio.run(runtime_runner.main())

    assert documents.is_dir() and captcha.is_dir()
    assert captured == [worker]


def test_module_main_guard(monkeypatch) -> None:
    called = []
    monkeypatch.setattr(asyncio, "run", lambda coro: (called.append(coro), coro.close()))
    runpy.run_module("runtime_runner", run_name="__main__")
    assert len(called) == 1


@pytest.mark.parametrize(
    "value,expected", [("1", 1), ("4", 4), ("0", None), ("5", None), ("bad", None)]
)
def test_parallel_worker_configuration(monkeypatch, value, expected) -> None:
    monkeypatch.setenv("ELABORAZIONI_RUNTIME_PARALLEL_WORKERS", value)
    if expected is None:
        with pytest.raises(ValueError):
            runtime_runner.parallel_workers()
    else:
        assert runtime_runner.parallel_workers() == expected


@pytest.mark.parametrize(
    "kind", ["incass", "terreni", "particelle", "anagrafica_history", "missing"]
)
def test_job_scope_protects_subjects_and_catalog(monkeypatch, kind) -> None:
    from uuid import uuid4

    identifier = uuid4()
    job = SimpleNamespace(payload_json={"subject_ids": [str(identifier)]})
    db = MagicMock()
    db.get.return_value = None if kind == "missing" else job
    monkeypatch.setattr(gate_module.worker_module, "SessionLocal", lambda: nullcontext(db))
    monkeypatch.setattr(
        gate_module,
        "_resolve_subjects",
        lambda *args: [(SimpleNamespace(id=identifier), "cf", "name")],
    )
    result = gate_module.job_scope("incass" if kind == "missing" else kind, 1)
    if kind == "missing":
        assert result is None
    elif kind == "incass":
        assert result[1:] == ("subjects", {str(identifier)})
    else:
        assert result[1:] == ("subjects" if kind == "anagrafica_history" else "catalog", None)


@pytest.mark.parametrize("empty", [False, True])
def test_dynamic_incass_scope_freezes_selected_subjects(monkeypatch, empty) -> None:
    from uuid import uuid4

    identifier = uuid4()
    job = SimpleNamespace(payload_json={})
    db = MagicMock()
    db.get.return_value = job
    monkeypatch.setattr(gate_module.worker_module, "SessionLocal", lambda: nullcontext(db))
    monkeypatch.setattr(
        gate_module,
        "_resolve_subjects",
        lambda *args: [] if empty else [(SimpleNamespace(id=identifier), "cf", "name")],
    )
    result = gate_module.job_scope("incass", 1)
    if empty:
        assert result[2] is None
        db.commit.assert_not_called()
    else:
        assert job.payload_json["subject_ids"] == [str(identifier)]
        db.commit.assert_called_once()


@pytest.mark.parametrize("status", [None, "failed", "processing"])
def test_waiting_job_heartbeat(monkeypatch, status) -> None:
    db = MagicMock()
    job = SimpleNamespace(status=status)
    db.get.return_value = None if status is None else job
    monkeypatch.setattr(gate_module.worker_module, "SessionLocal", lambda: nullcontext(db))
    assert gate_module.touch_waiting_job("model", 1) is (status == "processing")
    if status == "processing":
        assert job.updated_at is not None
        db.commit.assert_called_once()


def test_gate_serializes_overlaps_but_allows_four_distinct_subjects(monkeypatch) -> None:
    async def scenario():
        gate = gate_module.LaneGate()
        for identifier in range(4):
            assert await gate.acquire(identifier, "subjects", {identifier}, lambda: True)
        assert len(gate._active) == 4
        assert gate._conflicts("subjects", {0})
        assert not gate._conflicts("catalog", None)
        assert not gate._conflicts("subjects", {5})
        assert gate._conflicts("subjects", None)
        assert not await gate.acquire("cancelled", "subjects", {0}, lambda: False)

        async def release_on_sleep(delay):
            gate.release(0)

        monkeypatch.setattr(gate_module.asyncio, "sleep", release_on_sleep)
        assert await gate.acquire("overlap", "subjects", {0}, lambda: True)
        for key in list(gate._active):
            gate.release(key)
        assert await gate.acquire("catalog", "catalog", None, lambda: True)
        assert gate._conflicts("catalog", {1})

    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["domande", "missing", "cancelled", "success", "failure", "stop"])
def test_process_job_uses_gate_and_releases_after_errors(monkeypatch, mode) -> None:
    from unittest.mock import AsyncMock

    worker = SimpleNamespace(
        state=SimpleNamespace(stop_requested=mode == "stop"), _process_capacitas_job=AsyncMock()
    )
    if mode == "failure":
        worker._process_capacitas_job.side_effect = RuntimeError("processor failed")
    gate = SimpleNamespace(acquire=AsyncMock(return_value=mode != "cancelled"), release=MagicMock())
    touched = MagicMock(return_value=True)
    monkeypatch.setattr(runtime_runner, "touch_waiting_job", touched)
    monkeypatch.setattr(
        runtime_runner,
        "job_scope",
        lambda *args: None if mode == "missing" else ("model", "subjects", {1}),
    )
    domande = AsyncMock()
    monkeypatch.setattr(runtime_runner, "run_parallel_domande_job", domande)
    kind = "domande_irrigue" if mode == "domande" else "incass"
    if mode == "failure":
        with pytest.raises(RuntimeError, match="processor failed"):
            asyncio.run(runtime_runner.process_job(worker, kind, 1, 4, gate))
    else:
        asyncio.run(runtime_runner.process_job(worker, kind, 1, 4, gate))
    if mode == "domande":
        domande.assert_awaited_once_with(1, 4)
    elif mode != "missing":
        assert gate.acquire.call_args.args[3]() is (mode != "stop")
    assert gate.release.call_count == (1 if mode in {"success", "failure", "stop"} else 0)


def test_lane_uses_parallel_dispatch_and_registry_runs_in_thread(monkeypatch) -> None:
    from unittest.mock import AsyncMock

    worker = SimpleNamespace(state=SimpleNamespace(stop_requested=False))

    async def process(*args):
        worker.state.stop_requested = True

    monkeypatch.setattr(runtime_runner, "next_job", lambda *args: ("incass", 1))
    monkeypatch.setattr(runtime_runner, "process_job", process)
    asyncio.run(runtime_runner.run_lane(worker, runtime_runner.OTHER_JOBS, 4, object()))
    thread = AsyncMock()
    monkeypatch.setattr(runtime_runner.asyncio, "to_thread", thread)
    asyncio.run(runtime_runner.run_registry_job(1, workers=4))
    thread.assert_awaited_once_with(runtime_runner.run_parallel_registry_job, 1, 4)


def test_invalid_payload_is_handled_by_existing_processor(monkeypatch) -> None:
    from unittest.mock import AsyncMock

    worker = SimpleNamespace(_process_capacitas_job=AsyncMock())

    def invalid_scope(*args):
        raise ValueError("invalid payload")

    monkeypatch.setattr(runtime_runner, "job_scope", invalid_scope)
    asyncio.run(runtime_runner.process_job(worker, "incass", 1, 4, None))
    worker._process_capacitas_job.assert_awaited_once_with("incass", 1)


def test_polite_capacitas_default_does_not_reduce_registry_parallelism(monkeypatch):
    monkeypatch.delenv("ELABORAZIONI_CAPACITAS_PARALLEL_WORKERS")
    monkeypatch.setenv("ELABORAZIONI_RUNTIME_PARALLEL_WORKERS", "4")
    calls = []

    async def lane(worker, specs, workers, gate):
        calls.append(workers)

    async def run():
        pass

    async def heartbeat(operation, _heartbeat):
        await operation

    worker = SimpleNamespace(
        job_families={"registry", "capacitas"}, run=run, _recover_capacitas_jobs=MagicMock()
    )
    monkeypatch.setattr(runtime_runner, "run_lane", lane)
    monkeypatch.setattr(runtime_runner, "run_with_heartbeat", heartbeat)
    monkeypatch.setattr(runtime_runner, "WorkerHeartbeat", MagicMock())
    monkeypatch.setattr(
        runtime_runner.worker_module, "SessionLocal", lambda: nullcontext(MagicMock())
    )
    asyncio.run(runtime_runner.run_runtime(worker))
    assert calls == [1, 1]
    assert worker._process_registry_import_job.keywords == {"workers": 4}


def test_job_heartbeat_runs_through_cooldown_and_cleans_up(monkeypatch):
    touches = []

    async def scenario():
        pulsed = asyncio.Event()

        async def sleep(seconds):
            assert seconds == 60
            pulsed.set()
            await asyncio.Event().wait()

        monkeypatch.setattr(gate_module.asyncio, "sleep", sleep)
        monkeypatch.setattr(
            gate_module,
            "touch_waiting_job",
            lambda model, job_id: touches.append((model, job_id)) or True,
        )
        async with gate_module.job_heartbeat("domande_irrigue", 113):
            await pulsed.wait()
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]

    asyncio.run(scenario())
    assert touches == [(gate_module.JOB_MODELS["domande_irrigue"], 113)]


def test_job_heartbeat_stops_for_terminal_job(monkeypatch):
    monkeypatch.setattr(gate_module, "touch_waiting_job", lambda *args: False)
    asyncio.run(gate_module.maintain_job_heartbeat("model", 1))


def test_job_heartbeat_failure_cancels_work_and_propagates(monkeypatch):
    def failed_heartbeat(*args):
        raise RuntimeError("heartbeat failed")

    async def scenario():
        async with gate_module.job_heartbeat("domande_irrigue", 113):
            await asyncio.Event().wait()

    monkeypatch.setattr(gate_module, "touch_waiting_job", failed_heartbeat)
    with pytest.raises(ExceptionGroup) as raised:
        asyncio.run(scenario())
    assert isinstance(raised.value.exceptions[0], RuntimeError)
    assert str(raised.value.exceptions[0]) == "heartbeat failed"
