from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

import pytest
from sqlalchemy import select

from test_worker import (
    CatastoCaptchaLog,
    CatastoDocument,
    CatastoVisuraRequest,
    CatastoVisuraRequestStatus,
    _VisuraFlowResult,
    _seed_batch,
    worker_db,
    worker_module,
)


def test_request_repository_fences_operation_and_remote_updates(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, _, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    token = uuid.uuid4()
    credential_id = uuid.uuid4()
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.execution_token = token
        request.sister_remote_request_id = "OLD"
        request.sister_remote_request_url = "https://old"
        request.sister_remote_state = "deleted"
        db.commit()

    repository = worker._request_repository()
    repository.set_operation(uuid.uuid4(), "missing", token)
    repository.set_operation(request_ids[0], "stale", uuid.uuid4())
    repository.set_operation(request_ids[0], "running", token)
    repository.set_remote_state(
        request_ids[0], None, worker_module.SisterRemoteStateUpdate("NO-TOKEN", None, "pending")
    )
    repository.set_remote_state(
        request_ids[0], uuid.uuid4(), worker_module.SisterRemoteStateUpdate("STALE", None, "pending")
    )
    repository.set_remote_state(
        request_ids[0], token, worker_module.SisterRemoteStateUpdate(None, None, "ready")
    )
    repository.set_remote_state(
        request_ids[0],
        token,
        worker_module.SisterRemoteStateUpdate("NEW", "https://new", "submitted", credential_id),
    )
    repository.set_correlation_baseline(request_ids[0], uuid.uuid4(), ["STALE"])
    repository.set_correlation_baseline(request_ids[0], token, ["BASE"])

    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.current_operation == "running"
        assert request.sister_remote_request_id == "NEW"
        assert request.sister_remote_request_url == "https://new"
        assert request.sister_remote_state == "submitted"
        assert request.sister_credential_id == credential_id
        assert request.sister_remote_baseline_keys == ["BASE"]


def test_request_repository_persists_completed_document_idempotently(worker_db, tmp_path: Path) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    token = uuid.uuid4()
    pdf_path = tmp_path / "first.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\nfirst")
    result = _VisuraFlowResult()
    result.file_path = pdf_path
    result.file_size = pdf_path.stat().st_size
    result.remote_request_id = "REMOTE-1"
    result.remote_request_url = "https://sister/1"
    result.captcha_image_path = tmp_path / "captcha_manual.png"
    result.captcha_method = "manual"
    result.last_ocr_text = "1234"
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.execution_token = token
        db.commit()

    repository = worker._request_repository()
    repository.persist_flow_result(batch_id, request_ids[0], "USER", result, token)

    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        document = db.scalar(select(CatastoDocument).where(CatastoDocument.request_id == request_ids[0]))
        log = db.scalar(select(CatastoCaptchaLog).where(CatastoCaptchaLog.request_id == request_ids[0]))
        assert request is not None and document is not None and log is not None
        document_id = document.id
        assert request.status == CatastoVisuraRequestStatus.COMPLETED.value
        assert document.sha256 is not None and len(document.sha256) == 64
        assert log.manual_text == "1234"
        request.status = CatastoVisuraRequestStatus.PROCESSING.value
        request.execution_token = token
        db.commit()

    second_path = tmp_path / "second.pdf"
    second_path.write_bytes(b"%PDF-1.4\nsecond")
    result.file_path = second_path
    result.file_size = second_path.stat().st_size
    result.captcha_image_path = None
    repository.persist_flow_result(batch_id, request_ids[0], "USER", result, token)

    with SessionLocal() as db:
        documents = list(db.scalars(select(CatastoDocument).where(CatastoDocument.request_id == request_ids[0])))
        assert len(documents) == 1
        assert documents[0].id == document_id
        assert documents[0].filename == "second.pdf"


def test_request_repository_infers_captcha_log_method(worker_db, tmp_path: Path) -> None:
    worker, SessionLocal, _ = worker_db
    _, _, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    repository = worker._request_repository()
    for filename, expected_method in (("captcha_manual.png", "manual"), ("captcha.png", "ocr")):
        result = _VisuraFlowResult()
        result.captcha_image_path = tmp_path / filename
        result.last_ocr_text = "9876"
        with SessionLocal() as db:
            repository._log_captcha_attempt(db, request_ids[0], result)
            db.commit()
            log = db.scalar(
                select(CatastoCaptchaLog)
                .where(
                    CatastoCaptchaLog.request_id == request_ids[0],
                    CatastoCaptchaLog.method == expected_method,
                )
            )
            assert log is not None
            assert log.method == expected_method


@pytest.mark.parametrize(
    ("status", "expected_status", "expected_error_code"),
    [
        ("skipped", CatastoVisuraRequestStatus.SKIPPED.value, None),
        ("not_found", CatastoVisuraRequestStatus.NOT_FOUND.value, None),
        ("failed", CatastoVisuraRequestStatus.FAILED.value, "flow_failed"),
    ],
)
def test_request_repository_persists_terminal_statuses(
    worker_db,
    status: str,
    expected_status: str,
    expected_error_code: str | None,
) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    result = _VisuraFlowResult()
    result.status = status
    result.error_message = "detail" if status != "failed" else None

    worker._request_repository().persist_flow_result(batch_id, request_ids[0], "USER", result)

    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == expected_status
        assert request.last_error_code == expected_error_code


@pytest.mark.parametrize(("attempts", "is_ade"), [(1, True), (3, True), (3, False)])
def test_request_repository_persists_non_evadibile_retry_and_terminal(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
    attempts: int,
    is_ade: bool,
) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    ade_calls: list[dict[str, object]] = []
    monkeypatch.setattr(worker_module, "persist_ade_status_scan_result", lambda _db, **kwargs: ade_calls.append(kwargs))
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.attempts = attempts
        if is_ade:
            request.purpose = worker_module.ADE_SCAN_PURPOSE
            request.target_ruolo_particella_id = uuid.uuid4()
        db.commit()
    result = _VisuraFlowResult()
    result.status = "non_evadibile"
    result.error_message = "not possible"

    worker._request_repository().persist_flow_result(batch_id, request_ids[0], "USER", result)

    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.sister_remote_state == "deleted"
        assert request.last_error_code == "non_evadibile"
        if attempts < 3:
            assert request.status == CatastoVisuraRequestStatus.PENDING.value
            assert request.retry_not_before is not None
            assert not ade_calls
        else:
            assert request.status == CatastoVisuraRequestStatus.FAILED.value
            if is_ade:
                assert ade_calls[0]["classification"] == "non_evadibile"
            else:
                assert not ade_calls


@pytest.mark.parametrize("parse_fails", [False, True])
def test_request_repository_persists_ade_document_payload(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    parse_fails: bool,
) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    ade_calls: list[dict[str, object]] = []
    monkeypatch.setattr(worker_module, "persist_ade_status_scan_result", lambda _db, **kwargs: ade_calls.append(kwargs))
    monkeypatch.setattr(
        worker_module,
        "parse_historical_visura_pdf",
        (lambda _path: (_ for _ in ()).throw(ValueError("parse boom")))
        if parse_fails
        else (lambda _path: {"classification": "active"}),
    )
    pdf_path = tmp_path / "ade.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\nade")
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.purpose = worker_module.ADE_SCAN_PURPOSE
        request.target_ruolo_particella_id = uuid.uuid4()
        db.commit()
    result = _VisuraFlowResult()
    result.file_path = pdf_path
    result.file_size = pdf_path.stat().st_size

    worker._request_repository().persist_flow_result(batch_id, request_ids[0], "USER", result)

    expected = "parse_failed" if parse_fails else "active"
    assert ade_calls[0]["classification"] == expected
    assert ade_calls[0]["document_id"] is not None


def test_request_repository_persists_ade_payload_without_document(worker_db, monkeypatch: pytest.MonkeyPatch) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.PROCESSING.value,
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
        no_target = db.get(CatastoVisuraRequest, request_ids[1])
        assert no_target is not None
        no_target.purpose = worker_module.ADE_SCAN_PURPOSE
        db.commit()
    result = _VisuraFlowResult()
    result.status = "not_found"
    result.ade_status_payload = {"classification": "missing"}

    worker._request_repository().persist_flow_result(batch_id, request_ids[0], "USER", result)
    worker._request_repository().persist_flow_result(batch_id, request_ids[1], "USER", result)

    assert ade_calls[0]["classification"] == "missing"
    assert ade_calls[0]["document_id"] is None
    assert len(ade_calls) == 1


def test_document_path_builders_cover_subject_and_immobile_fallbacks(worker_db, tmp_path: Path) -> None:
    from sister_worker_reliability import _future_retry_seconds, build_document_path, is_expired, sha256_file

    _, SessionLocal, _ = worker_db
    _, _, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.subalterno = "7"
        immobile_path = build_document_path(tmp_path, "", request)
        request.search_mode = "soggetto"
        request.subject_kind = None
        request.subject_id = None
        request.request_type = None
        subject_path = build_document_path(tmp_path, "USER", request)

    assert immobile_path.name == "SISTER_ORISTANO_1_1_7.pdf"
    assert subject_path.name == "SOGGETTO_UNKNOWN_ATTUALITA.pdf"
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"abc")
    assert sha256_file(payload) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert not is_expired(None)
    assert is_expired(datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1))
    assert not is_expired(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=30))
    assert not is_expired(datetime.now(timezone.utc) + timedelta(seconds=30))
    now = datetime.now(timezone.utc)
    assert _future_retry_seconds(now - timedelta(seconds=1), now) is None
