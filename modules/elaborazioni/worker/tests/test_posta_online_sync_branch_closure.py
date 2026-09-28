from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

import posta_online_sync
from posta_online_client import PostaOnlineCircuitOpen


def run(coro):
    return asyncio.run(coro)


class FakeDb:
    def __init__(self, values=None) -> None:
        self.values = list(values or [])
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def get(self, _model, _identifier):
        return self.values.pop(0) if self.values else None

    def commit(self):
        self.commits += 1


class SessionFactory:
    def __init__(self, sessions) -> None:
        self.sessions = list(sessions)

    def __call__(self):
        return self.sessions.pop(0)


class Client:
    def __init__(self, _config, *, fail=False) -> None:
        self.fail = fail

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def login(self, _username, _password):
        if self.fail:
            raise RuntimeError("login failed")


def _credential_job():
    return SimpleNamespace(
        payload_json={"credential_id": 7},
        credential_id=7,
        status="processing",
        error_detail=None,
        completed_at=None,
        result_json=None,
    )


def _credential():
    return SimpleNamespace(
        id=7,
        username="user",
        password_encrypted="encrypted",
        min_delay_ms=1,
        max_delay_ms=2,
    )


def test_credential_success_and_failure_when_final_job_disappears(monkeypatch) -> None:
    monkeypatch.setattr(posta_online_sync, "decrypt_posta_online_password", lambda _value: "secret")
    used: list[int] = []
    errors: list[tuple[int, str]] = []
    monkeypatch.setattr(
        posta_online_sync,
        "mark_credential_used",
        lambda _db, credential_id: used.append(credential_id),
    )
    monkeypatch.setattr(
        posta_online_sync,
        "mark_credential_error",
        lambda _db, credential_id, message: errors.append((credential_id, message)),
    )

    success_factory = SessionFactory(
        [FakeDb([_credential_job(), _credential()]), FakeDb([None])]
    )
    run(
        posta_online_sync.run_posta_online_credential_test_job_by_id(
            job_id=1,
            session_factory=success_factory,
            headless=True,
            _client_class=Client,
        )
    )
    assert used == [7]

    class FailingClient(Client):
        def __init__(self, config):
            super().__init__(config, fail=True)

    failure_factory = SessionFactory(
        [FakeDb([_credential_job(), _credential()]), FakeDb([None])]
    )
    run(
        posta_online_sync.run_posta_online_credential_test_job_by_id(
            job_id=2,
            session_factory=failure_factory,
            headless=True,
            _client_class=FailingClient,
        )
    )
    assert errors == [(7, "login failed")]


def _registered_job(*, result_json=None):
    return SimpleNamespace(
        payload_json={"credential_id": 7},
        credential_id=7,
        status="processing",
        error_detail=None,
        completed_at=None,
        result_json=result_json,
    )


class Payload:
    credential_id = 7
    min_delay_ms = None
    max_delay_ms = None

    def model_dump(self, **_kwargs):
        return {"credential_id": 7}


def _prepare_registered_runner(monkeypatch) -> None:
    monkeypatch.setattr(posta_online_sync, "_load_resume_checkpoint", lambda **_kwargs: (None, None))
    monkeypatch.setattr(
        posta_online_sync.PostaOnlineRegisteredMailSyncJobCreateRequest,
        "model_validate",
        lambda _payload: Payload(),
    )
    monkeypatch.setattr(
        posta_online_sync,
        "pick_credential",
        lambda _db, _credential_id: (_credential(), "secret"),
    )
    monkeypatch.setattr(posta_online_sync, "_write_resume_checkpoint", lambda **_kwargs: None)
    monkeypatch.setattr(posta_online_sync, "mark_credential_error", lambda *_args: None)


def test_registered_scrape_failure_when_final_job_disappears(monkeypatch) -> None:
    _prepare_registered_runner(monkeypatch)

    async def fail_scrape(**_kwargs):
        raise RuntimeError("scrape failed")

    monkeypatch.setattr(posta_online_sync, "_scrape_posta_online_payload", fail_scrape)
    factory = SessionFactory([FakeDb([_registered_job()]), FakeDb([None])])

    run(
        posta_online_sync.run_posta_online_registered_mail_job_by_id(
            job_id=3,
            session_factory=factory,
            headless=True,
        )
    )


def test_registered_persist_failure_with_missing_and_non_resumable_job(monkeypatch) -> None:
    _prepare_registered_runner(monkeypatch)

    async def scrape(**_kwargs):
        return {"archive_ids": []}

    monkeypatch.setattr(posta_online_sync, "_scrape_posta_online_payload", scrape)
    monkeypatch.setattr(
        posta_online_sync,
        "_persist_scrape_payload",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("persist failed")),
    )

    missing_factory = SessionFactory([FakeDb([_registered_job()]), FakeDb([None])])
    run(
        posta_online_sync.run_posta_online_registered_mail_job_by_id(
            job_id=4,
            session_factory=missing_factory,
            headless=True,
        )
    )

    final_job = _registered_job(result_json=None)
    present_factory = SessionFactory([FakeDb([_registered_job()]), FakeDb([final_job])])
    run(
        posta_online_sync.run_posta_online_registered_mail_job_by_id(
            job_id=5,
            session_factory=present_factory,
            headless=True,
        )
    )
    assert final_job.status == "failed"
    assert final_job.result_json["error"] == "persist failed"
    assert "resume_state" not in final_job.result_json


def test_partial_import_keeps_checkpoint_and_schedules_resume(monkeypatch) -> None:
    job = _registered_job(result_json={"resume_state": {"stage": "scraping", "path": "/tmp/checkpoint"}})
    job.requested_by_user_id = None
    imported = []

    class ImportJob:
        id = uuid4()
        status = "completed"
        records_total = 1
        records_imported = 1
        records_matched = 0
        records_ambiguous = 0
        records_unmatched = 1
        records_errors = 0

    def fake_import(_db, **kwargs):
        imported.append(kwargs)
        return ImportJob()

    monkeypatch.setattr(posta_online_sync, "_import_tributi_registered_mails", fake_import)
    result = posta_online_sync._persist_scrape_payload(
        session_factory=SessionFactory([FakeDb([job])]),
        job_id=9,
        credential_id=7,
        requested_payload={"annualita": [2022, 2023]},
        scrape_payload={"archive_ids": ["1234", "5678"], "details": [{"idInvio": "1234", "html": "valid"}]},
        started_at=datetime.now(UTC),
    )
    assert job.status == "queued_resume"
    assert result["remaining_ids_count"] == 1
    assert result["resume_state"]["stage"] == "scraping"
    assert imported[0]["preserve_associations"] is True

    paused = _registered_job(result_json={"recovery_rounds": 2})
    posta_online_sync._pause_registered_mail_job(
        session_factory=SessionFactory([FakeDb([paused])]), job_id=9, reason="HTTP 500"
    )
    assert paused.status == "paused"
    assert paused.result_json["recovery_rounds"] == 3


def test_persist_scrape_payload_sums_import_batch_counters(monkeypatch) -> None:
    job = _registered_job()
    job.requested_by_user_id = None
    batches = [
        SimpleNamespace(id=uuid4(), records_total=2, records_imported=1, records_matched=None,
                        records_ambiguous=1, records_unmatched=0, records_errors=None),
        SimpleNamespace(id=uuid4(), records_total=3, records_imported=2, records_matched=2,
                        records_ambiguous=0, records_unmatched=1, records_errors=0),
    ]
    monkeypatch.setattr(posta_online_sync, "_import_scraped_details", lambda *_args: batches)
    monkeypatch.setattr(posta_online_sync, "mark_credential_used", lambda *_args: None)
    monkeypatch.setattr(posta_online_sync, "_delete_resume_checkpoint", lambda *_args: None)

    result = posta_online_sync._persist_scrape_payload(
        session_factory=SessionFactory([FakeDb([job])]), job_id=9, credential_id=7,
        requested_payload={}, scrape_payload={"details": [{"idInvio": "1234"}]},
        started_at=datetime.now(UTC),
    )

    assert result["tributi_import_job_ids"] == [str(item.id) for item in batches]
    assert {key: result[key] for key in (
        "records_total", "records_imported", "records_matched", "records_ambiguous",
        "records_unmatched", "records_errors",
    )} == {
        "records_total": 5, "records_imported": 3, "records_matched": 2,
        "records_ambiguous": 1, "records_unmatched": 1, "records_errors": 0,
    }


def test_circuit_breaker_keeps_partial_progress(monkeypatch) -> None:
    _prepare_registered_runner(monkeypatch)
    payload = {"archive_ids": ["1234", "5678"], "details": [{"idInvio": "1234", "html": "valid"}]}
    monkeypatch.setattr(posta_online_sync, "_load_resume_checkpoint", lambda **_kwargs: (None, payload))

    async def stop_scrape(**_kwargs):
        raise PostaOnlineCircuitOpen("Poste unavailable")

    persisted = []
    monkeypatch.setattr(posta_online_sync, "_scrape_posta_online_payload", stop_scrape)
    monkeypatch.setattr(posta_online_sync, "_persist_scrape_payload", lambda **kwargs: persisted.append(kwargs))
    job = _registered_job()
    run(posta_online_sync.run_posta_online_registered_mail_job_by_id(
        job_id=9, session_factory=SessionFactory([FakeDb([job])]), headless=True
    ))
    assert persisted[0]["scrape_payload"] == payload

    monkeypatch.setattr(posta_online_sync, "_load_resume_checkpoint", lambda **_kwargs: (None, {"archive_ids": ["1234"]}))
    paused = []
    monkeypatch.setattr(posta_online_sync, "_pause_registered_mail_job", lambda **kwargs: paused.append(kwargs))
    run(posta_online_sync.run_posta_online_registered_mail_job_by_id(
        job_id=9, session_factory=SessionFactory([FakeDb([_registered_job()])]), headless=True
    ))
    assert paused[0]["job_id"] == 9


def test_import_errors_and_contacts_only(monkeypatch) -> None:
    job = _registered_job()
    job.requested_by_user_id = None

    class ImportJob:
        id = uuid4()
        status = "failed"
        records_total = 0
        records_imported = 0
        records_matched = 0
        records_ambiguous = 0
        records_unmatched = 0
        records_errors = 1

    monkeypatch.setattr(posta_online_sync, "_import_tributi_registered_mails", lambda *_args, **_kwargs: ImportJob())
    with pytest.raises(RuntimeError, match="batch 0 fallito"):
        posta_online_sync._persist_scrape_payload(
            session_factory=SessionFactory([FakeDb([job])]), job_id=9, credential_id=7,
            requested_payload={}, scrape_payload={"details": [{"idInvio": "1234", "html": "valid"}]},
            started_at=datetime.now(UTC),
        )
    ImportJob.status = "completed"
    with pytest.raises(RuntimeError, match="batch 0 incompleto"):
        posta_online_sync._persist_scrape_payload(
            session_factory=SessionFactory([FakeDb([job])]), job_id=9, credential_id=7,
            requested_payload={}, scrape_payload={"details": [{"idInvio": "1234", "html": "valid"}]},
            started_at=datetime.now(UTC),
        )
    ImportJob.status = "failed"
    with pytest.raises(RuntimeError, match="contatti Poste fallito"):
        posta_online_sync._persist_scrape_payload(
            session_factory=SessionFactory([FakeDb([job])]), job_id=9, credential_id=7,
            requested_payload={"include_details": False}, scrape_payload={"contacts": [{"id": "c"}]},
            started_at=datetime.now(UTC),
        )
    with pytest.raises(RuntimeError, match="senza dettagli validi"):
        posta_online_sync._persist_scrape_payload(
            session_factory=SessionFactory([FakeDb([job])]), job_id=9, credential_id=7,
            requested_payload={}, scrape_payload={}, started_at=datetime.now(UTC),
        )

    ImportJob.status = "completed"
    with pytest.raises(RuntimeError, match="contatti Poste incompleto"):
        posta_online_sync._persist_scrape_payload(
            session_factory=SessionFactory([FakeDb([job])]), job_id=9, credential_id=7,
            requested_payload={"include_details": False}, scrape_payload={"contacts": [{"id": "c"}]},
            started_at=datetime.now(UTC),
        )
    ImportJob.records_errors = 0
    monkeypatch.setattr(posta_online_sync, "mark_credential_used", lambda *_args: None)
    result = posta_online_sync._persist_scrape_payload(
        session_factory=SessionFactory([FakeDb([job])]), job_id=9, credential_id=7,
        requested_payload={"include_details": False}, scrape_payload={"contacts": [{"id": "c"}]},
        started_at=datetime.now(UTC),
    )
    assert result["records_errors"] == 0

    posta_online_sync._pause_registered_mail_job(
        session_factory=SessionFactory([FakeDb([None])]), job_id=9, reason="HTTP 500"
    )


def test_checkpoint_copies_discovered_ids_into_job_payload(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(posta_online_sync, "POSTA_ONLINE_RESUME_STORAGE_PATH", tmp_path)
    job = _registered_job()
    db = FakeDb([job])
    posta_online_sync._write_resume_checkpoint(
        session_factory=SessionFactory([db]), job_id=9,
        scrape_payload={"archive_ids": ["1234", "5678"], "details": []},
        stage="scraping", started_at=datetime.now(UTC),
    )
    assert job.payload_json["shipment_ids"] == ["1234", "5678"]
    assert job.result_json["resume_state"]["archive_ids_count"] == 2
