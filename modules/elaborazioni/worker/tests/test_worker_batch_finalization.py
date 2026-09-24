"""Finalization must keep an active SISTER batch open for planner refill."""

from pathlib import Path

import pytest
import test_worker as worker_support

from app.models.catasto import CatastoBatch, CatastoBatchStatus, CatastoVisuraRequestStatus


@pytest.fixture
def worker_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    yield from worker_support.worker_db.__wrapped__(tmp_path, monkeypatch)


def test_pending_request_keeps_batch_open(worker_db) -> None:
    worker, sessions, _ = worker_db
    _, batch_id, _ = worker_support._seed_batch(
        sessions,
        request_statuses=[
            CatastoVisuraRequestStatus.COMPLETED.value,
            CatastoVisuraRequestStatus.PENDING.value,
        ],
    )

    worker._finalize_batch(batch_id)

    with sessions() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        assert batch.status == CatastoBatchStatus.PROCESSING.value
        assert batch.completed_at is None


def test_terminal_batch_records_completion_time(worker_db) -> None:
    worker, sessions, _ = worker_db
    _, batch_id, _ = worker_support._seed_batch(
        sessions,
        request_statuses=[CatastoVisuraRequestStatus.COMPLETED.value],
    )

    worker._finalize_batch(batch_id)

    with sessions() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        assert batch.status == CatastoBatchStatus.COMPLETED.value
        assert batch.completed_at is not None
