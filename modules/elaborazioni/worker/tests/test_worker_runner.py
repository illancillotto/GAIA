from __future__ import annotations

import asyncio
import runpy

import pytest
import test_worker as worker_test_support  # noqa: F401 - installs isolated worker stubs
import worker_runner


def test_run_worker_publishes_family_heartbeat(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class Worker:
        job_families = {"runtime", "poste"}

        async def run(self) -> None:
            captured["ran"] = True

    class Heartbeat:
        def __init__(self, service: str, *, details: dict[str, object]) -> None:
            captured["service"] = service
            captured["details"] = details

    async def run_with_heartbeat(coro, heartbeat) -> None:
        captured["heartbeat"] = heartbeat
        await coro

    monkeypatch.setenv("GAIA_WORKER_HEALTH_SERVICE", "worker-test")
    monkeypatch.setattr(worker_runner, "WorkerHeartbeat", Heartbeat)
    monkeypatch.setattr(worker_runner, "run_with_heartbeat", run_with_heartbeat)

    asyncio.run(worker_runner.run_worker(Worker()))

    assert captured["ran"] is True
    assert captured["service"] == "worker-test"
    assert captured["details"] == {"families": ["poste", "runtime"]}


def test_main_creates_storage_and_runs_worker(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    documents = tmp_path / "documents"
    captcha = tmp_path / "captcha"
    captured: list[object] = []

    class Worker:
        pass

    async def run_worker(instance) -> None:
        captured.append(instance)

    monkeypatch.setattr(worker_runner.worker_module, "DOCUMENT_STORAGE_PATH", documents)
    monkeypatch.setattr(worker_runner.worker_module, "CAPTCHA_STORAGE_PATH", captcha)
    monkeypatch.setattr(worker_runner.worker_module, "CatastoWorker", Worker)
    monkeypatch.setattr(worker_runner, "run_worker", run_worker)

    asyncio.run(worker_runner.main())

    assert documents.is_dir()
    assert captcha.is_dir()
    assert isinstance(captured[0], Worker)


def test_module_main_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[object] = []

    monkeypatch.setattr(asyncio, "run", lambda coro: (called.append(coro), coro.close()))
    runpy.run_module("worker_runner", run_name="__main__")

    assert len(called) == 1
