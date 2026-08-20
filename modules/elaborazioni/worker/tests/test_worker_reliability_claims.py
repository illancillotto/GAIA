from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import types
import uuid

import pytest

from test_worker import (
    CatastoBatch,
    CatastoBatchStatus,
    CatastoVisuraRequest,
    CatastoVisuraRequestStatus,
    SisterCaptchaClaim,
    SisterRequestCorrelationError,
    _VisuraFlowResult,
    _seed_batch,
    worker_db,
    worker_module,
)


def test_next_request_id_stops_after_maximum_attempts(worker_db, monkeypatch: pytest.MonkeyPatch) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(SessionLocal, request_statuses=[CatastoVisuraRequestStatus.PENDING.value])
    monkeypatch.setattr(worker_module, "MAX_REQUEST_ATTEMPTS", 3)
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.attempts = 3
        db.commit()

    selection = worker._request_repository().claim_next(batch_id)

    assert selection.request_id is None
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == CatastoVisuraRequestStatus.FAILED.value
        assert request.last_error_code == "retry_exhausted"


def test_next_request_id_uses_persisted_retry_deadline(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(SessionLocal, request_statuses=[CatastoVisuraRequestStatus.PENDING.value])
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.retry_not_before = datetime.now(timezone.utc) + timedelta(seconds=90)
        db.commit()

    selection = worker._request_repository().claim_next(batch_id)

    assert selection.request_id is None
    assert selection.wait_reason == "RETRY_LATER"
    assert selection.wait_seconds is not None
    assert 1 <= selection.wait_seconds <= 90


def test_next_request_id_resumes_remote_request_only_with_its_sister_credential(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PENDING.value],
    )
    pinned_credential_id = uuid.uuid4()
    other_credential_id = uuid.uuid4()
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.sister_credential_id = pinned_credential_id
        request.sister_remote_state = "submitted"
        db.commit()

    wrong_credential = worker._request_repository().claim_next(
        batch_id,
        credential_id=other_credential_id,
    )
    matching_credential = worker._request_repository().claim_next(
        batch_id,
        credential_id=pinned_credential_id,
    )

    assert wrong_credential.request_id is None
    assert matching_credential.request_id == request_ids[0]


def test_manual_captcha_wait_is_fenced_and_exposes_current_decision(worker_db) -> None:
    worker, SessionLocal, tmp_path = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    request_id = request_ids[0]
    token = uuid.uuid4()
    deadline = datetime.now(timezone.utc) + timedelta(minutes=5)
    image_path = tmp_path / "captcha.png"
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_id)
        assert request is not None
        request.execution_token = token
        db.commit()

    repository = worker._captcha_wait_repository()
    assert repository.begin(batch_id, request_id, token, image_path, deadline) is True
    waiting = repository.state(batch_id, request_id, token)
    assert waiting.active is True
    assert waiting.solution is None
    assert waiting.skip_requested is False

    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_id)
        assert request is not None
        request.captcha_manual_solution = "ABCDE"
        db.commit()

    solved = repository.state(batch_id, request_id, token)
    assert solved.active is True
    assert solved.solution == "ABCDE"


def test_manual_captcha_wait_cannot_resurrect_cancelled_claim(worker_db) -> None:
    worker, SessionLocal, tmp_path = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.SKIPPED.value],
    )
    request_id = request_ids[0]
    stale_token = uuid.uuid4()
    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        batch.status = CatastoBatchStatus.CANCELLED.value
        db.commit()

    decision = asyncio.run(
        worker._wait_for_manual_captcha(
            SisterCaptchaClaim(batch_id, request_id, stale_token),
            tmp_path / "stale.png",
        )
    )

    assert decision.skip is True
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_id)
        assert request is not None
        assert request.status == CatastoVisuraRequestStatus.SKIPPED.value
        assert request.captcha_image_path is None


def test_manual_captcha_wait_stops_after_claim_is_cancelled(worker_db) -> None:
    worker, SessionLocal, tmp_path = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    request_id = request_ids[0]
    token = uuid.uuid4()
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_id)
        assert request is not None
        request.execution_token = token
        db.commit()

    repository = worker._captcha_wait_repository()
    original_state = repository.state
    state_reads = 0

    def cancel_before_state_read(current_batch_id, current_request_id, current_token):
        nonlocal state_reads
        state_reads += 1
        with SessionLocal() as db:
            batch = db.get(CatastoBatch, batch_id)
            request = db.get(CatastoVisuraRequest, request_id)
            assert batch is not None and request is not None
            batch.status = CatastoBatchStatus.CANCELLED.value
            request.status = CatastoVisuraRequestStatus.SKIPPED.value
            request.execution_token = None
            db.commit()
        return original_state(current_batch_id, current_request_id, current_token)

    wait_repository = types.SimpleNamespace(begin=repository.begin, state=cancel_before_state_read)
    worker._captcha_wait_repository = lambda: wait_repository
    decision = asyncio.run(
        worker._wait_for_manual_captcha(
            SisterCaptchaClaim(batch_id, request_id, token),
            tmp_path / "captcha.png",
        )
    )

    assert decision.skip is True
    assert state_reads == 1


def test_finalize_batch_does_not_overwrite_cancellation(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, _ = _seed_batch(SessionLocal, request_statuses=[CatastoVisuraRequestStatus.SKIPPED.value])
    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        batch.status = CatastoBatchStatus.CANCELLED.value
        batch.current_operation = "Cancelled by user"
        db.commit()

    worker._finalize_batch(batch_id)

    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        assert batch.status == CatastoBatchStatus.CANCELLED.value
        assert batch.current_operation == "Cancelled by user"


def test_persist_flow_result_discards_stale_cancelled_claim(worker_db) -> None:
    worker, SessionLocal, tmp_path = worker_db
    _, batch_id, request_ids = _seed_batch(SessionLocal, request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value])
    stale_token = uuid.uuid4()
    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert batch is not None and request is not None
        batch.status = CatastoBatchStatus.CANCELLED.value
        request.status = CatastoVisuraRequestStatus.SKIPPED.value
        request.execution_token = None
        db.commit()

    pdf_path = tmp_path / "stale.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    result = _VisuraFlowResult()
    result.file_path = pdf_path
    result.file_size = pdf_path.stat().st_size

    worker._request_repository().persist_flow_result(
        batch_id,
        request_ids[0],
        "USER",
        result,
        stale_token,
    )
    worker._request_repository().persist_flow_result(
        batch_id,
        request_ids[0],
        "USER",
        _VisuraFlowResult(),
        stale_token,
    )

    assert not pdf_path.exists()
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == CatastoVisuraRequestStatus.SKIPPED.value
        assert request.document_id is None


def test_stale_claim_cannot_reset_or_fail_new_execution(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.PROCESSING.value,
            CatastoVisuraRequestStatus.PROCESSING.value,
        ],
    )
    stale_token = uuid.uuid4()
    current_tokens = [uuid.uuid4(), uuid.uuid4()]
    with SessionLocal() as db:
        for request_id, current_token in zip(request_ids, current_tokens, strict=True):
            request = db.get(CatastoVisuraRequest, request_id)
            assert request is not None
            request.execution_token = current_token
        db.commit()

    worker._request_repository().reset_for_retry(
        request_ids[0],
        "retry obsoleto",
        datetime.now(timezone.utc) + timedelta(seconds=30),
        "stale_retry",
        stale_token,
    )
    worker._request_repository().fail_request(batch_id, request_ids[1], "errore obsoleto", stale_token)

    with SessionLocal() as db:
        first = db.get(CatastoVisuraRequest, request_ids[0])
        second = db.get(CatastoVisuraRequest, request_ids[1])
        assert first is not None and second is not None
        assert first.status == CatastoVisuraRequestStatus.PROCESSING.value
        assert first.execution_token == current_tokens[0]
        assert first.retry_not_before is None
        assert second.status == CatastoVisuraRequestStatus.PROCESSING.value
        assert second.execution_token == current_tokens[1]
        assert second.error_message is None


def test_new_correlation_baseline_clears_deleted_remote_identity(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, _, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.PROCESSING.value,
            CatastoVisuraRequestStatus.PROCESSING.value,
        ],
    )
    execution_tokens = [uuid.uuid4(), uuid.uuid4()]
    with SessionLocal() as db:
        deleted = db.get(CatastoVisuraRequest, request_ids[0])
        active = db.get(CatastoVisuraRequest, request_ids[1])
        assert deleted is not None and active is not None
        deleted.execution_token = execution_tokens[0]
        deleted.sister_remote_request_id = "OLD-1"
        deleted.sister_remote_request_url = "https://sister/old"
        deleted.sister_remote_state = "deleted"
        deleted.sister_credential_id = uuid.uuid4()
        active.execution_token = execution_tokens[1]
        active.sister_remote_request_id = "ACTIVE-2"
        active.sister_remote_request_url = "https://sister/active"
        active.sister_remote_state = "pending"
        active.sister_credential_id = uuid.uuid4()
        active_credential_id = active.sister_credential_id
        db.commit()

    worker._request_repository().set_correlation_baseline(request_ids[0], execution_tokens[0], ["BASE-NEW"])
    worker._request_repository().set_correlation_baseline(request_ids[1], execution_tokens[1], ["BASE-ACTIVE"])

    with SessionLocal() as db:
        deleted = db.get(CatastoVisuraRequest, request_ids[0])
        active = db.get(CatastoVisuraRequest, request_ids[1])
        assert deleted is not None and active is not None
        assert deleted.sister_remote_request_id is None
        assert deleted.sister_remote_request_url is None
        assert deleted.sister_remote_state is None
        assert deleted.sister_credential_id is None
        assert deleted.sister_remote_baseline_keys == ["BASE-NEW"]
        assert active.sister_remote_request_id == "ACTIVE-2"
        assert active.sister_remote_request_url == "https://sister/active"
        assert active.sister_remote_state == "pending"
        assert active.sister_credential_id == active_credential_id
        assert active.sister_remote_baseline_keys == ["BASE-ACTIVE"]


def test_document_paths_are_unique_per_request_and_execution(worker_db, monkeypatch: pytest.MonkeyPatch) -> None:
    worker, SessionLocal, tmp_path = worker_db
    monkeypatch.setattr(worker_module, "DOCUMENT_STORAGE_PATH", tmp_path / "documents")
    _, _, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value, CatastoVisuraRequestStatus.PROCESSING.value],
    )
    with SessionLocal() as db:
        first = db.get(CatastoVisuraRequest, request_ids[0])
        second = db.get(CatastoVisuraRequest, request_ids[1])
        assert first is not None and second is not None
        first.execution_token = uuid.uuid4()
        second.execution_token = uuid.uuid4()
        first_path = worker._request_repository().build_document_path("USER", first)
        second_path = worker._request_repository().build_document_path("USER", second)

    assert first_path != second_path
    assert str(request_ids[0]) in str(first_path)
    assert str(request_ids[1]) in str(second_path)


def test_retry_coordinator_persists_deadline_and_fencing_token() -> None:
    from sister_worker_reliability import (
        ClaimedRequestSelection,
        SisterRequestClaimCoordinator,
        SisterRequestRetryCoordinator,
        recoverable_retry_metadata,
    )

    calls: list[tuple[object, ...]] = []
    deferred: dict[uuid.UUID, datetime] = {}
    request_id = uuid.uuid4()
    execution_token = uuid.uuid4()
    coordinator = SisterRequestRetryCoordinator(
        asyncio.Lock(),
        deferred,
        lambda *args: calls.append(args),
        30,
    )

    asyncio.run(coordinator.defer(request_id, execution_token, 30, "retry", "temporary"))

    assert request_id in deferred
    assert deferred[request_id] > datetime.now(timezone.utc)
    assert calls[0][0:2] == (request_id, "retry")
    assert calls[0][3:] == ("temporary", execution_token)
    asyncio.run(
        coordinator.defer_recoverable(
            request_id,
            execution_token,
            SisterRequestCorrelationError("ambigua"),
            "USER",
        )
    )
    assert calls[-1][1] == "Correlazione SISTER non sicura, retry differito"
    assert calls[-1][3] == "sister_correlation_error"
    assert ClaimedRequestSelection(None).resolved_wait_seconds(7) == 7
    assert ClaimedRequestSelection(None, wait_seconds=3).resolved_wait_seconds(7) == 3

    class _Repository:
        selections = [ClaimedRequestSelection(request_id), ClaimedRequestSelection(None)]

        def claim_next(self, *_args):
            return self.selections.pop(0)

    coordinator = SisterRequestClaimCoordinator(asyncio.Lock(), asyncio.Lock(), deferred, set())
    claimed = asyncio.run(coordinator.claim_next(_Repository(), uuid.uuid4(), uuid.uuid4()))
    empty = asyncio.run(coordinator.claim_next(_Repository(), uuid.uuid4(), uuid.uuid4()))
    asyncio.run(coordinator.release(None))
    asyncio.run(coordinator.release(request_id))

    assert claimed.request_id == request_id
    assert empty.request_id is None
    assert request_id not in coordinator.claimed_request_ids
    assert request_id not in deferred
    assert recoverable_retry_metadata(
        SisterRequestCorrelationError("ambigua"), "USER"
    ) == ("Correlazione SISTER non sicura, retry differito", "sister_correlation_error")
    assert recoverable_retry_metadata(RuntimeError("timeout"), "USER") == (
        "Sessione/timeout su USER, retry differito",
        "session_recovery",
    )


def test_request_repository_fails_active_batch_and_preserves_terminal_items(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.PENDING.value,
            CatastoVisuraRequestStatus.COMPLETED.value,
            CatastoVisuraRequestStatus.PROCESSING.value,
        ],
    )
    ade_calls: list[dict[str, object]] = []
    monkeypatch.setattr(worker_module, "persist_ade_status_scan_result", lambda _db, **kwargs: ade_calls.append(kwargs))
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.purpose = worker_module.ADE_SCAN_PURPOSE
        request.target_ruolo_particella_id = uuid.uuid4()
        request.execution_token = uuid.uuid4()
        request.retry_not_before = datetime.now(timezone.utc)
        db.commit()

    worker._request_repository().fail_batch(batch_id, "SISTER_SESSION_LOCKED")

    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        failed = db.get(CatastoVisuraRequest, request_ids[0])
        completed = db.get(CatastoVisuraRequest, request_ids[1])
        assert batch is not None and failed is not None and completed is not None
        assert batch.status == CatastoBatchStatus.FAILED.value
        assert failed.status == CatastoVisuraRequestStatus.FAILED.value
        assert failed.execution_token is None and failed.retry_not_before is None
        assert completed.status == CatastoVisuraRequestStatus.COMPLETED.value
    assert ade_calls[0]["classification"] == "blocked"

    worker._request_repository().fail_batch(uuid.uuid4(), "ignored")
    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        batch.status = CatastoBatchStatus.CANCELLED.value
        db.commit()
    worker._request_repository().fail_batch(batch_id, "ignored")


def test_request_repository_fails_remote_requests_without_their_pinned_credential(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.PENDING.value,
            CatastoVisuraRequestStatus.PENDING.value,
            CatastoVisuraRequestStatus.PENDING.value,
        ],
    )
    available_credential_id = uuid.uuid4()
    with SessionLocal() as db:
        orphaned = db.get(CatastoVisuraRequest, request_ids[0])
        available = db.get(CatastoVisuraRequest, request_ids[1])
        assert orphaned is not None and available is not None
        orphaned.sister_remote_state = "submitted"
        orphaned.sister_credential_id = uuid.uuid4()
        available.sister_remote_state = "pending"
        available.sister_credential_id = available_credential_id
        db.commit()

    repository = worker._request_repository()
    assert repository.fail_unavailable_pinned_requests(uuid.uuid4(), {available_credential_id}) == 0
    assert repository.fail_unavailable_pinned_requests(batch_id, {available_credential_id}) == 1
    assert repository.fail_unavailable_pinned_requests(batch_id, {available_credential_id}) == 0

    with SessionLocal() as db:
        orphaned = db.get(CatastoVisuraRequest, request_ids[0])
        available = db.get(CatastoVisuraRequest, request_ids[1])
        unsubmitted = db.get(CatastoVisuraRequest, request_ids[2])
        batch = db.get(CatastoBatch, batch_id)
        assert orphaned is not None and available is not None and unsubmitted is not None and batch is not None
        assert orphaned.status == CatastoVisuraRequestStatus.FAILED.value
        assert orphaned.sister_remote_state == "orphaned"
        assert orphaned.last_error_code == "sister_credential_unavailable"
        assert available.status == CatastoVisuraRequestStatus.PENDING.value
        assert unsubmitted.status == CatastoVisuraRequestStatus.PENDING.value
        batch.status = CatastoBatchStatus.CANCELLED.value
        db.commit()

    assert repository.fail_unavailable_pinned_requests(batch_id, {available_credential_id}) == 0


def test_request_repository_fails_only_current_execution(worker_db, monkeypatch: pytest.MonkeyPatch) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    token = uuid.uuid4()
    ade_calls: list[dict[str, object]] = []
    monkeypatch.setattr(worker_module, "persist_ade_status_scan_result", lambda _db, **kwargs: ade_calls.append(kwargs))
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.execution_token = token
        request.purpose = worker_module.ADE_SCAN_PURPOSE
        request.target_ruolo_particella_id = uuid.uuid4()
        db.commit()

    repository = worker._request_repository()
    repository.fail_request(batch_id, request_ids[0], "stale", uuid.uuid4())
    repository.fail_request(batch_id, request_ids[0], "fatal", token)

    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == CatastoVisuraRequestStatus.FAILED.value
        assert request.error_message == "fatal"
        assert request.execution_token is None
    assert ade_calls[-1]["classification"] == "blocked"


def test_request_repository_reset_for_retry_handles_release_and_guards(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.PROCESSING.value,
            CatastoVisuraRequestStatus.PROCESSING.value,
            CatastoVisuraRequestStatus.COMPLETED.value,
        ],
    )
    tokens = [uuid.uuid4(), uuid.uuid4()]
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=20)
    with SessionLocal() as db:
        first = db.get(CatastoVisuraRequest, request_ids[0])
        released = db.get(CatastoVisuraRequest, request_ids[1])
        assert first is not None and released is not None
        first.execution_token = tokens[0]
        released.execution_token = tokens[1]
        released.error_message = worker_module.RELEASE_REQUESTED_MESSAGE
        db.commit()

    repository = worker._request_repository()
    repository.reset_for_retry(request_ids[0], "stale", retry_at, "stale", uuid.uuid4())
    repository.reset_for_retry(request_ids[2], "terminal")
    repository.reset_for_retry(request_ids[1], "ignored", execution_token=tokens[1])
    repository.reset_for_retry(request_ids[0], "retry", retry_at, "temporary", tokens[0])
    repository.reset_for_retry(uuid.uuid4(), "missing")

    with SessionLocal() as db:
        first = db.get(CatastoVisuraRequest, request_ids[0])
        released = db.get(CatastoVisuraRequest, request_ids[1])
        assert first is not None and released is not None
        assert first.status == CatastoVisuraRequestStatus.PENDING.value
        assert first.retry_not_before == retry_at.replace(tzinfo=None)
        assert first.last_error_code == "temporary"
        assert released.status == CatastoVisuraRequestStatus.SKIPPED.value
        assert released.current_operation == worker_module.RELEASE_REQUESTED_OPERATION

    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        first = db.get(CatastoVisuraRequest, request_ids[0])
        assert batch is not None and first is not None
        batch.status = CatastoBatchStatus.CANCELLED.value
        first.status = CatastoVisuraRequestStatus.PROCESSING.value
        db.commit()
    repository.reset_for_retry(request_ids[0], "cancelled")


@pytest.mark.parametrize(
    ("captcha_mode", "expected_status", "expected_operation"),
    [
        ("manual", CatastoVisuraRequestStatus.PROCESSING.value, "Ripresa con CAPTCHA manuale"),
        ("expired", CatastoVisuraRequestStatus.FAILED.value, "Timeout CAPTCHA manuale"),
        ("skip", CatastoVisuraRequestStatus.SKIPPED.value, "Saltata dall'utente"),
    ],
)
def test_prepare_execution_resolves_captcha_states(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    captcha_mode: str,
    expected_status: str,
    expected_operation: str,
) -> None:
    worker, SessionLocal, _ = worker_db
    monkeypatch.setattr(worker_module, "DEBUG_ARTIFACTS_PATH", tmp_path / "debug")
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value],
    )
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.captcha_manual_solution = "1234" if captcha_mode == "manual" else None
        request.captcha_skip_requested = captcha_mode == "skip"
        request.captcha_expires_at = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
            if captcha_mode == "expired"
            else datetime.now(timezone.utc) + timedelta(minutes=5)
        )
        db.commit()

    prepared = worker._request_repository().prepare_execution(batch_id, request_ids[0])

    assert (prepared is not None) == (captcha_mode == "manual")
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == expected_status
        assert request.current_operation == expected_operation


def test_prepare_execution_claims_pending_subject_and_handles_missing(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker, SessionLocal, tmp_path = worker_db
    monkeypatch_root = tmp_path / "debug"
    monkeypatch.setattr(worker_module, "DEBUG_ARTIFACTS_PATH", monkeypatch_root)
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PENDING.value],
    )
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.search_mode = "soggetto"
        request.subject_kind = "PF"
        request.subject_id = "ABC"
        db.commit()

    repository = worker._request_repository()
    assert repository.prepare_execution(uuid.uuid4(), uuid.uuid4()) is None
    prepared = repository.prepare_execution(batch_id, request_ids[0])

    assert prepared is not None
    assert prepared.request.execution_token == prepared.execution_token
    assert prepared.request.artifact_dir is not None
    assert Path(prepared.request.artifact_dir).is_dir()
    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        assert batch.current_operation == "Lavorazione PF ABC"


def test_prepare_execution_keeps_unresolved_captcha_waiting(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker, SessionLocal, tmp_path = worker_db
    monkeypatch.setattr(worker_module, "DEBUG_ARTIFACTS_PATH", tmp_path / "debug")
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value],
    )
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.captcha_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        db.commit()

    prepared = worker._request_repository().prepare_execution(batch_id, request_ids[0])

    assert prepared is None
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value

def test_finalize_batch_marks_completed_for_not_found_and_skipped(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, _ = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.COMPLETED.value,
            CatastoVisuraRequestStatus.NOT_FOUND.value,
            CatastoVisuraRequestStatus.SKIPPED.value,
        ],
    )

    worker._finalize_batch(batch_id)

    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        assert batch.status == CatastoBatchStatus.COMPLETED.value
        assert batch.completed_items == 1
        assert batch.not_found_items == 1
        assert batch.skipped_items == 1
def test_finalize_batch_keeps_processing_when_pending_requests_remain(worker_db) -> None:
    worker, SessionLocal, tmp_path = worker_db
    _, batch_id, _ = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.COMPLETED.value,
            CatastoVisuraRequestStatus.PENDING.value,
        ],
    )

    worker._finalize_batch(batch_id)

    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        assert batch.status == CatastoBatchStatus.PROCESSING.value
        assert batch.report_json_path is not None
        assert batch.report_md_path is not None
        assert Path(batch.report_json_path).exists()
        assert Path(batch.report_md_path).exists()
