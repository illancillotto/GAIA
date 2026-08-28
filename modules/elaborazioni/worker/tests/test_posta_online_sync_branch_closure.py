from __future__ import annotations

import asyncio
from types import SimpleNamespace

import posta_online_sync


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
