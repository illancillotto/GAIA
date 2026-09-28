from __future__ import annotations

import importlib
import os
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize(
    ("status", "result", "ready"),
    [
        ("pending", {"retry_not_before": "2999-01-01T00:00:00+00:00"}, True),
        ("queued_resume", [], True),
        ("queued_resume", {}, True),
        ("queued_resume", {"retry_not_before": "invalid"}, False),
        ("queued_resume", {"retry_not_before": "2000-01-01T00:00:00"}, False),
        ("queued_resume", {"retry_not_before": "2999-01-01T00:00:00+00:00"}, False),
        ("queued_resume", {"retry_not_before": "2000-01-01T00:00:00+00:00"}, True),
    ],
)
def test_posta_online_retry_ready(status: str, result: object, ready: bool) -> None:
    os.environ.setdefault("CREDENTIAL_MASTER_KEY", "WnCjZ2L63B1kIh_2mDkk8j5M6Bf0dzxN3Qv8QbQwB0A=")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./.pytest-worker.db")
    worker = importlib.import_module("worker")

    job = SimpleNamespace(id=9, status=status, result_json=result)
    assert worker.CatastoWorker._posta_online_retry_ready(job) is ready
