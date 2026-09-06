"""Failure snapshots must be captured before a claim is released."""

import asyncio
import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from test_worker import CatastoVisuraRequest, _seed_batch, worker_db  # noqa: F401 - pytest fixture.
from sister_request_diagnostics import capture_request_error
from sister_worker_types import ClaimedRequestSelection


@pytest.mark.parametrize("token_kind", ["active", "stale", "missing"])
def test_diagnostics_are_fenced(worker_db, tmp_path, token_kind):
    _, sessions, _ = worker_db
    _, _, ids = _seed_batch(sessions, request_statuses=["processing"])
    token = uuid.uuid4()
    with sessions() as db:
        request = db.get(CatastoVisuraRequest, ids[0])
        request.execution_token = None if token_kind == "missing" else token
        request.artifact_dir = str(tmp_path)
        db.commit()
    supplied = {"active": token, "stale": uuid.uuid4(), "missing": None}[token_kind]
    selection = ClaimedRequestSelection(ids[0], execution_token=supplied)
    browser = Mock(capture_debug_snapshot=AsyncMock())
    write = Mock()
    asyncio.run(
        capture_request_error(sessions, browser, selection, RuntimeError("poll failure"), write)
    )
    assert write.call_count == int(token_kind == "active")
    assert browser.capture_debug_snapshot.await_count == int(token_kind == "active")
    with sessions() as db:
        assert db.get(CatastoVisuraRequest, ids[0]).error_message == (
            "poll failure" if token_kind == "active" else None
        )


@pytest.mark.parametrize("artifact", [True, False])
def test_capture_failure_does_not_mask_original_error(worker_db, tmp_path, artifact):
    _, sessions, _ = worker_db
    _, _, ids = _seed_batch(sessions, request_statuses=["processing"])
    token = uuid.uuid4()
    with sessions() as db:
        request = db.get(CatastoVisuraRequest, ids[0])
        request.execution_token = token
        request.artifact_dir = str(tmp_path) if artifact else None
        db.commit()
    selection = ClaimedRequestSelection(ids[0], execution_token=token)
    browser = Mock(capture_debug_snapshot=AsyncMock(side_effect=TimeoutError("browser closed")))
    write = Mock(side_effect=OSError("disk full"))
    asyncio.run(
        capture_request_error(sessions, browser, selection, RuntimeError("original"), write)
    )
    with sessions() as db:
        assert db.get(CatastoVisuraRequest, ids[0]).error_message == "original"


def test_database_error_does_not_mask_original_error(caplog):
    sessions = Mock(side_effect=RuntimeError("database unavailable"))
    selection = ClaimedRequestSelection(uuid.uuid4(), execution_token=uuid.uuid4())
    asyncio.run(capture_request_error(sessions, None, selection, RuntimeError("original"), Mock()))
    assert "Cattura diagnostica SISTER fallita" in caplog.text


def test_no_capacitas_recovery_is_a_noop(worker_db, monkeypatch):
    worker, _, _ = worker_db
    import worker as worker_module

    for name in (
        "prepare_anagrafica_history_jobs_for_recovery", "prepare_incass_sync_jobs_for_recovery",
        "prepare_domande_irrigue_sync_jobs_for_recovery", "prepare_terreni_sync_jobs_for_recovery",
        "prepare_particelle_sync_jobs_for_recovery",
    ):
        monkeypatch.setattr(worker_module, name, lambda _db: [])
    worker._recover_capacitas_jobs(None)
