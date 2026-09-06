from test_worker import *  # noqa: F403
from test_worker import _VisuraFlowResult, _seed_batch

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

    invalid_document_token = uuid.uuid4()
    with SessionLocal() as db:
        first = db.get(CatastoVisuraRequest, request_ids[0])
        assert first is not None
        first.status = CatastoVisuraRequestStatus.PROCESSING.value
        first.execution_token = invalid_document_token
        first.sister_credential_id = uuid.uuid4()
        first.sister_remote_request_id = "STALE"
        first.sister_remote_request_url = "https://sister/stale"
        first.sister_remote_state = "submitted"
        first.sister_remote_baseline_keys = ["STALE"]
        db.commit()
    repository.reset_for_retry(
        request_ids[0],
        "invalid document",
        retry_at,
        "sister_invalid_document",
        invalid_document_token,
    )
    with SessionLocal() as db:
        first = db.get(CatastoVisuraRequest, request_ids[0])
        assert first is not None
        assert first.sister_credential_id is not None
        assert first.sister_remote_request_id == "STALE"
        assert first.sister_remote_request_url == "https://sister/stale"
        assert first.sister_remote_state == "submitted"
        assert first.sister_remote_baseline_keys == ["STALE"]

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
    result.document_audit_payload = {
        "classification": "suppressed",
        "document_request_type": {"observed": "STORICA"},
        "suppression": {"suppressed_from": "09/12/2025"},
    }
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
        assert document.content_request_type == "STORICA"
        assert document.parcel_classification == "suppressed"
        assert document.parcel_suppressed_at.isoformat() == "2025-12-09"
        assert log.manual_text == "1234"
        request.status = CatastoVisuraRequestStatus.PROCESSING.value
        request.execution_token = token
        db.commit()

    second_path = tmp_path / "second.pdf"
    second_path.write_bytes(b"%PDF-1.4\nsecond")
    result.file_path = second_path
    result.file_size = second_path.stat().st_size
    result.captcha_image_path = None
    result.document_audit_payload = {
        "classification": "current",
        "document_request_type": {"observed": "ATTUALITA"},
    }
    repository.persist_flow_result(batch_id, request_ids[0], "USER", result, token)

    with SessionLocal() as db:
        documents = list(db.scalars(select(CatastoDocument).where(CatastoDocument.request_id == request_ids[0])))
        assert len(documents) == 1
        assert documents[0].id == document_id
        assert documents[0].filename == "second.pdf"
        assert documents[0].content_request_type == "ATTUALITA"
        assert documents[0].parcel_classification == "current"
        assert documents[0].parcel_suppressed_at is None


def test_request_repository_persists_queued_sister_for_retry(worker_db, tmp_path: Path) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    token = uuid.uuid4()
    result = _VisuraFlowResult()
    result.status = "queued_sister"
    result.remote_request_id = "REMOTE-QUEUED"
    result.remote_request_url = "https://sister/queued"
    result.captcha_image_path = tmp_path / "captcha.png"
    result.last_ocr_text = "1234"
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.execution_token = token
        request.retry_not_before = datetime.now(timezone.utc)
        request.captcha_manual_solution = "9999"
        request.captcha_skip_requested = True
        db.commit()

    worker._request_repository().persist_flow_result(batch_id, request_ids[0], "USER", result, token)

    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        log = db.scalar(select(CatastoCaptchaLog).where(CatastoCaptchaLog.request_id == request_ids[0]))
        assert request is not None and log is not None
        assert request.status == CatastoVisuraRequestStatus.PENDING.value
        assert request.current_operation == "In coda SISTER, prossimo recupero differito"
        assert request.sister_remote_request_id == "REMOTE-QUEUED"
        assert request.execution_token is None
        assert request.retry_not_before > datetime.now(timezone.utc).replace(tzinfo=None)
        assert request.captcha_manual_solution is None
        assert request.captcha_skip_requested is False


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

    assert immobile_path.name == "ORISTANO_1_1_7.pdf"
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
