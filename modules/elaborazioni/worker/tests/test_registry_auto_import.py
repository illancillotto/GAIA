from __future__ import annotations

from datetime import time
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
import test_worker

worker_module = test_worker.worker_module
CatastoWorker = worker_module.CatastoWorker


class FakeSession:
    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def test_registry_auto_import_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession()
    job_id = uuid4()
    calls: list[tuple[FakeSession, bool, time, ZoneInfo]] = []
    monkeypatch.setattr(worker_module, "SessionLocal", lambda: db)
    monkeypatch.setattr(worker_module, "REGISTRY_AUTO_IMPORT_ENABLED", True)
    monkeypatch.setattr(worker_module, "REGISTRY_AUTO_IMPORT_TIME", time(22))
    monkeypatch.setattr(worker_module, "REGISTRY_AUTO_IMPORT_TIMEZONE", ZoneInfo("Europe/Rome"))
    monkeypatch.setattr(
        worker_module,
        "claim_next_registry_import_job",
        lambda session, **kwargs: (
            calls.append(
                (
                    session,
                    kwargs["auto_import_enabled"],
                    kwargs["schedule_time"],
                    kwargs["schedule_timezone"],
                )
            )
            or job_id
        ),
    )

    worker = CatastoWorker.__new__(CatastoWorker)
    assert worker._next_registry_import_job_id() == job_id
    assert calls == [(db, True, time(22), ZoneInfo("Europe/Rome"))]
