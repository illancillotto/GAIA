from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import runpy
from types import SimpleNamespace
from uuid import uuid4

import pytest

import test_worker as worker_test_support
from test_worker import worker_db
import worker as worker_module


CatastoWorker = worker_module.CatastoWorker


def run(coro):
    return asyncio.run(coro)


async def async_value(value=None):
    return value


class ScalarRows:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeDb:
    def __init__(self, *, scalar_values=(), scalars_values=(), get_values=()) -> None:
        self.scalar_values = list(scalar_values)
        self.scalars_values = list(scalars_values)
        self.get_values = list(get_values)
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def scalar(self, _query):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, _query):
        values = self.scalars_values.pop(0) if self.scalars_values else []
        return ScalarRows(values)

    def get(self, _model, _identity):
        return self.get_values.pop(0) if self.get_values else None

    def commit(self):
        self.commits += 1


class SessionQueue:
    def __init__(self, *sessions: FakeDb) -> None:
        self.sessions = list(sessions)
        self.created: list[FakeDb] = []

    def __call__(self):
        session = self.sessions.pop(0) if self.sessions else FakeDb()
        self.created.append(session)
        return session


def bare_worker() -> CatastoWorker:
    worker = CatastoWorker.__new__(CatastoWorker)
    worker.state = SimpleNamespace(stop_requested=False)
    worker._scheduled_batch_resume_at = {}
    worker.vault = SimpleNamespace(decrypt=lambda value: f"plain:{value}")
    worker.anti_captcha_client = None
    worker.llm_captcha_solver = None
    return worker


def test_init_builds_optional_clients_and_directories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[tuple[str, object]] = []

    class Vault:
        def __init__(self, key):
            created.append(("vault", key))

    class AntiCaptcha:
        def __init__(self, **kwargs):
            created.append(("anti", kwargs))

    class Llm:
        def __init__(self, **kwargs):
            created.append(("llm", kwargs))

    monkeypatch.setattr(worker_module, "WorkerCredentialVault", Vault)
    monkeypatch.setattr(worker_module, "AntiCaptchaClient", AntiCaptcha)
    monkeypatch.setattr(worker_module, "LLMCaptchaSolver", Llm)
    monkeypatch.setattr(worker_module, "ANTI_CAPTCHA_API_KEY", "key")
    monkeypatch.setattr(worker_module, "CAPTCHA_LLM_ENABLED", True)
    monkeypatch.setattr(worker_module, "DEBUG_ARTIFACTS_PATH", tmp_path / "debug")
    monkeypatch.setattr(worker_module, "REPORT_STORAGE_PATH", tmp_path / "reports")
    worker = CatastoWorker()
    assert worker.anti_captcha_client is not None and worker.llm_captcha_solver is not None

    monkeypatch.setattr(worker_module, "ANTI_CAPTCHA_API_KEY", "")
    monkeypatch.setattr(worker_module, "CAPTCHA_LLM_ENABLED", False)
    worker = CatastoWorker()
    assert worker.anti_captcha_client is None and worker.llm_captcha_solver is None
    assert {item[0] for item in created} == {"vault", "anti", "llm"}


def _configure_run_worker(family: str) -> CatastoWorker:
    worker = bare_worker()
    worker.job_families = {family}
    worker._install_signal_handlers = lambda: None
    worker._recover_stuck_requests = lambda: None
    for name in (
        "_next_connection_test_id",
        "_next_posta_online_job_id",
        "_next_registry_import_job_id",
        "_next_ade_sync_run_id",
        "_next_distretto_export_job_id",
        "_next_bulk_search_job_id",
        "_next_autodoc_sync_job_id",
        "_next_batch_id",
    ):
        setattr(worker, name, lambda: None)
    worker._next_capacitas_job = lambda: None
    return worker


@pytest.mark.parametrize(
    ("family", "next_name", "process_name", "next_value", "expected"),
    [
        ("connection_tests", "_next_connection_test_id", "_process_connection_test", 1, (1,)),
        ("capacitas", "_next_capacitas_job", "_process_capacitas_job", ("incass", 2), ("incass", 2)),
        ("posta_online", "_next_posta_online_job_id", "_process_posta_online_job", 3, (3,)),
        ("registry", "_next_registry_import_job_id", "_process_registry_import_job", 4, (4,)),
        ("ade_sync", "_next_ade_sync_run_id", "_process_ade_sync_run", "5", ("5",)),
        ("bulk_search", "_next_distretto_export_job_id", "_process_distretto_export_job", "6", ("6",)),
        ("autodoc", "_next_autodoc_sync_job_id", "_process_autodoc_sync_job", "7", ("7",)),
        ("visure_batches", "_next_batch_id", "_process_batch", 8, (8,)),
    ],
)
def test_run_dispatches_each_job_family(
    family: str,
    next_name: str,
    process_name: str,
    next_value,
    expected: tuple,
) -> None:
    worker = _configure_run_worker(family)
    calls: list[tuple] = []
    setattr(worker, next_name, lambda: next_value)

    async def process(*args):
        calls.append(args)
        worker.state.stop_requested = True

    setattr(worker, process_name, process)
    run(worker.run())
    assert calls == [expected]


def test_run_dispatches_bulk_fallback_and_idle_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = _configure_run_worker("bulk_search")
    worker._next_bulk_search_job_id = lambda: "bulk"
    calls: list[str] = []

    async def process(job_id):
        calls.append(job_id)
        worker.state.stop_requested = True

    worker._process_bulk_search_job = process
    run(worker.run())
    assert calls == ["bulk"]

    worker = _configure_run_worker("connection_tests")

    async def stop_on_sleep(_seconds):
        worker.state.stop_requested = True

    monkeypatch.setattr(worker_module.asyncio, "sleep", stop_on_sleep)
    run(worker.run())
    assert worker.state.stop_requested
    run(worker.run())

    worker = _configure_run_worker("connection_tests")
    worker.job_families = set(worker_module.ALL_JOB_FAMILIES)

    async def stop_all_families(_seconds):
        worker.state.stop_requested = True

    monkeypatch.setattr(worker_module.asyncio, "sleep", stop_all_families)
    run(worker.run())


def test_signal_handlers_stop_and_job_family_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = bare_worker()
    handlers: list[tuple[object, object]] = []
    loop = SimpleNamespace(add_signal_handler=lambda signal, callback: handlers.append((signal, callback)))
    monkeypatch.setattr(worker_module.asyncio, "get_running_loop", lambda: loop)
    worker._install_signal_handlers()
    assert len(handlers) == 2
    worker._request_stop()
    assert worker.state.stop_requested

    assert CatastoWorker._parse_job_families("  ") == worker_module.ALL_JOB_FAMILIES
    assert CatastoWorker._parse_job_families("registry") == {"registry"}
    worker.job_families = {"registry"}
    assert worker._handles_job_family("registry")
    assert not worker._handles_job_family("autodoc")


def test_recovery_resets_all_enabled_job_types(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = SimpleNamespace(status="processing", message=None)
    request = SimpleNamespace(
        status="processing",
        current_operation="x",
        execution_token="token",
        retry_not_before=datetime.now(timezone.utc),
    )
    db = FakeDb(scalars_values=([connection], [request]))
    monkeypatch.setattr(worker_module, "SessionLocal", SessionQueue(db))
    worker = bare_worker()
    worker.job_families = set(worker_module.ALL_JOB_FAMILIES)
    values = {
        "prepare_anagrafica_history_jobs_for_recovery": [1],
        "prepare_incass_sync_jobs_for_recovery": [2],
        "prepare_terreni_sync_jobs_for_recovery": [3],
        "prepare_particelle_sync_jobs_for_recovery": [4],
        "prepare_registered_mail_sync_jobs_for_recovery": [5],
        "prepare_bulk_search_jobs_for_recovery": 1,
        "prepare_distretto_export_jobs_for_recovery": 1,
        "prepare_registry_import_jobs_for_recovery": [6],
        "prepare_ade_sync_runs_for_recovery": 1,
    }
    for name, value in values.items():
        monkeypatch.setattr(worker_module, name, lambda _db, result=value: result)
    worker._recover_stuck_requests()
    assert connection.status == worker_module.CatastoConnectionTestStatus.PENDING.value
    assert request.status == worker_module.CatastoVisuraRequestStatus.PENDING.value
    assert request.execution_token is None and request.retry_not_before is None
    assert db.commits == 1

    empty_db = FakeDb()
    monkeypatch.setattr(worker_module, "SessionLocal", SessionQueue(empty_db))
    worker.job_families = set()
    worker._recover_stuck_requests()
    assert empty_db.commits == 1


@pytest.mark.parametrize(
    ("method", "value", "expected"),
    [
        ("_next_connection_test_id", SimpleNamespace(id=11), 11),
        ("_next_connection_test_id", None, None),
        ("_next_ade_sync_run_id", SimpleNamespace(id=uuid4()), "id"),
        ("_next_ade_sync_run_id", None, None),
        ("_next_batch_id", SimpleNamespace(id=12), 12),
        ("_next_batch_id", None, None),
    ],
)
def test_simple_next_id_queries(method: str, value, expected, monkeypatch: pytest.MonkeyPatch) -> None:
    if method == "_next_ade_sync_run_id" and value is not None:
        expected = str(value.id)
    db = FakeDb(scalar_values=[value])
    if method == "_next_batch_id":
        db = FakeDb(scalars_values=[[value] if value is not None else []])
    monkeypatch.setattr(worker_module, "SessionLocal", SessionQueue(db))
    assert getattr(bare_worker(), method)() == expected


@pytest.mark.parametrize(
    ("method", "status_value", "identifier"),
    [
        ("_next_registry_import_job_id", worker_module.CatastoVisuraRequestStatus.PENDING.value, 21),
        ("_next_bulk_search_job_id", "pending", uuid4()),
        ("_next_distretto_export_job_id", "pending", uuid4()),
        ("_next_autodoc_sync_job_id", "queued", uuid4()),
    ],
)
def test_claiming_next_job_queries(method: str, status_value: str, identifier, monkeypatch: pytest.MonkeyPatch) -> None:
    job = SimpleNamespace(id=identifier, status=status_value, started_at=None, error_message="old")
    db = FakeDb(scalar_values=[job])
    monkeypatch.setattr(worker_module, "SessionLocal", SessionQueue(db))
    assert getattr(bare_worker(), method)() == (identifier if isinstance(identifier, int) else str(identifier))
    assert db.commits == 1

    monkeypatch.setattr(worker_module, "SessionLocal", SessionQueue(FakeDb(scalar_values=[None])))
    assert getattr(bare_worker(), method)() is None


def test_credential_id_fallbacks() -> None:
    assert CatastoWorker._posta_online_job_credential_id(SimpleNamespace(credential_id=7, payload_json=None)) == 7
    assert CatastoWorker._posta_online_job_credential_id(SimpleNamespace(credential_id=7, payload_json={"credential_id": "8"})) == 8


def test_processing_delegates_and_failure_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = bare_worker()
    calls: list[tuple[str, object]] = []

    def async_recorder(label):
        async def record(value, *args, **kwargs):
            calls.append((label, value))

        return record

    monkeypatch.setattr(worker_module, "run_anagrafica_history_job_by_id", async_recorder("history"))
    monkeypatch.setattr(worker_module, "run_incass_job_by_id", async_recorder("incass"))
    monkeypatch.setattr(worker_module, "run_terreni_job_by_id", async_recorder("terreni"))
    monkeypatch.setattr(worker_module, "run_particelle_job_by_id", async_recorder("particelle"))
    for kind in ("anagrafica_history", "incass", "terreni", "particelle", "unknown"):
        run(worker._process_capacitas_job(kind, 31))

    monkeypatch.setattr(worker_module.asyncio, "to_thread", async_recorder("thread"))
    run(worker._process_registry_import_job(32))

    run_id = str(uuid4())
    monkeypatch.setattr(worker_module, "SessionLocal", SessionQueue(FakeDb()))
    monkeypatch.setattr(worker_module, "execute_ade_sync_run", lambda _db, value: calls.append(("ade", value)))
    run(worker._process_ade_sync_run(run_id))
    monkeypatch.setattr(worker_module, "execute_ade_sync_run", lambda *_args: (_ for _ in ()).throw(RuntimeError("ade")))
    run(worker._process_ade_sync_run(run_id))

    monkeypatch.setattr(worker_module, "run_bulk_search_job_by_id", async_recorder("bulk"))
    run(worker._process_bulk_search_job(run_id))
    monkeypatch.setattr(worker_module, "run_bulk_search_job_by_id", async_recorder("bulk-fail"))
    run(worker._process_bulk_search_job("invalid"))

    async def to_thread(function, value):
        return function(value)

    monkeypatch.setattr(worker_module.asyncio, "to_thread", to_thread)
    monkeypatch.setattr(worker_module, "run_distretto_export_job_by_id", lambda value: calls.append(("distretto", value)))
    run(worker._process_distretto_export_job(run_id))
    run(worker._process_distretto_export_job("invalid"))

    monkeypatch.setattr(worker_module, "run_autodoc_sync_job_by_id", async_recorder("autodoc"))
    run(worker._process_autodoc_sync_job("job"))

    async def fail(*_args, **_kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(worker_module, "run_autodoc_sync_job_by_id", fail)
    run(worker._process_autodoc_sync_job("job"))
    assert {label for label, _value in calls} >= {"history", "incass", "terreni", "particelle", "ade", "bulk", "distretto", "autodoc"}


def test_static_helpers_and_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    worker = bare_worker()
    monkeypatch.setattr(worker_module, "OPERATION_WINDOW_ENABLED", False)
    assert worker._next_operating_resume_at() is None
    monkeypatch.setattr(worker_module, "OPERATION_WINDOW_ENABLED", True)
    monkeypatch.setattr(worker_module, "OPERATION_WINDOW_TIMEZONE", "invalid")
    assert worker._operation_window_zone().key == "Europe/Rome"
    now = datetime(2026, 1, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(worker_module, "OPERATION_WINDOW_START_HOUR", 8)
    assert worker._next_operating_resume_at(now) > now
    assert worker._next_operating_resume_at(datetime(2026, 1, 1, 10, tzinfo=timezone.utc)) > now

    browser_marker = object()
    monkeypatch.setattr(worker_module, "BrowserSessionConfig", lambda **values: values)
    monkeypatch.setattr(worker_module, "BrowserSession", lambda config: (browser_marker, config))
    assert worker._build_browser_session()[0] is browser_marker
    artifact_dir = tmp_path / "artifact"
    worker._write_request_error_artifact(artifact_dir, RuntimeError("boom"))
    assert "boom" in (artifact_dir / "error.txt").read_text()
    batch = SimpleNamespace(user_id=3, id=4)
    monkeypatch.setattr(worker_module, "REPORT_STORAGE_PATH", tmp_path)
    assert worker._build_batch_report_dir(batch) == tmp_path / "3" / "4"
    assert worker._slugify("  Profilo A / Oristano ") == "PROFILO_A_ORISTANO"
    for message in (
        "SISTER_SESSION_LOCKED",
        "Utente SISTER bloccato sul portale Agenzia delle Entrate",
        "Utente gia' in sessione",
        "Utente già in sessione",
        "error_locked.jsp",
        "Credenziali SISTER rifiutate",
        "generic",
    ):
        assert worker._to_user_message(message)


class FakeBrowser:
    instances: list["FakeBrowser"] = []
    result = SimpleNamespace(reachable=True, authenticated=True, message="ok")
    start_error: Exception | None = None

    def __init__(self, _config=None) -> None:
        self.started = 0
        self.stopped = 0
        self.auth_calls: list[tuple[str, str]] = []
        self.snapshots: list[tuple[Path, str]] = []
        self.previews: list[Path] = []
        type(self).instances.append(self)

    async def start(self):
        self.started += 1
        if type(self).start_error is not None:
            raise type(self).start_error

    async def stop(self):
        self.stopped += 1

    async def logout(self):
        return None

    async def test_connection(self, _username, _password):
        return type(self).result

    async def ensure_authenticated(self, username, password):
        self.auth_calls.append((username, password))

    async def capture_subject_not_found_preview(self, path):
        self.previews.append(path)

    async def capture_debug_snapshot(self, path, label):
        self.snapshots.append((path, label))


def _connection_test(**values):
    defaults = {
        "status": "pending",
        "started_at": None,
        "message": None,
        "sister_password_encrypted": "encrypted",
        "sister_username": "username",
        "persist_verification": True,
        "credential_id": uuid4(),
        "mode": None,
        "reachable": None,
        "authenticated": None,
        "completed_at": None,
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def _install_fake_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeBrowser.instances.clear()
    FakeBrowser.start_error = None
    FakeBrowser.result = SimpleNamespace(reachable=True, authenticated=True, message="ok")
    monkeypatch.setattr(worker_module, "BrowserSessionConfig", lambda **values: values)
    monkeypatch.setattr(worker_module, "BrowserSession", FakeBrowser)


def test_connection_test_success_failure_and_missing_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_browser(monkeypatch)
    worker = bare_worker()

    monkeypatch.setattr(worker_module, "SessionLocal", SessionQueue(FakeDb(get_values=[None])))
    run(worker._process_connection_test(1))
    assert FakeBrowser.instances[-1].stopped == 0

    test = _connection_test()
    monkeypatch.setattr(
        worker_module,
        "SessionLocal",
        SessionQueue(FakeDb(get_values=[test]), FakeDb(get_values=[None])),
    )
    run(worker._process_connection_test(2))
    assert FakeBrowser.instances[-1].stopped == 1

    test = _connection_test()
    credential = SimpleNamespace(verified_at=None)
    sessions = SessionQueue(
        FakeDb(get_values=[test]),
        FakeDb(get_values=[test]),
        FakeDb(get_values=[test, credential]),
    )
    monkeypatch.setattr(worker_module, "SessionLocal", sessions)
    run(worker._process_connection_test(3))
    assert test.status == worker_module.CatastoConnectionTestStatus.COMPLETED.value
    assert credential.verified_at == test.completed_at

    FakeBrowser.result = SimpleNamespace(reachable=True, authenticated=False, message="denied")
    test = _connection_test(persist_verification=False, credential_id=None)
    monkeypatch.setattr(
        worker_module,
        "SessionLocal",
        SessionQueue(FakeDb(get_values=[test]), FakeDb(get_values=[test]), FakeDb(get_values=[test])),
    )
    run(worker._process_connection_test(4))
    assert test.status == worker_module.CatastoConnectionTestStatus.FAILED.value

    FakeBrowser.result = SimpleNamespace(reachable=True, authenticated=True, message="ok")
    test = _connection_test()
    monkeypatch.setattr(
        worker_module,
        "SessionLocal",
        SessionQueue(FakeDb(get_values=[test]), FakeDb(get_values=[test]), FakeDb(get_values=[test, None])),
    )
    run(worker._process_connection_test(5))

    test = _connection_test()
    monkeypatch.setattr(
        worker_module,
        "SessionLocal",
        SessionQueue(FakeDb(get_values=[test]), FakeDb(get_values=[test]), FakeDb(get_values=[None])),
    )
    run(worker._process_connection_test(51))


def test_connection_test_exception_persists_when_row_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_browser(monkeypatch)
    worker = bare_worker()
    test = _connection_test()
    FakeBrowser.start_error = RuntimeError("browser")
    monkeypatch.setattr(
        worker_module,
        "SessionLocal",
        SessionQueue(FakeDb(get_values=[test]), FakeDb(get_values=[test])),
    )
    run(worker._process_connection_test(6))
    assert test.status == worker_module.CatastoConnectionTestStatus.FAILED.value
    assert "browser" in test.message

    test = _connection_test()
    monkeypatch.setattr(
        worker_module,
        "SessionLocal",
        SessionQueue(FakeDb(get_values=[test]), FakeDb(get_values=[None])),
    )
    run(worker._process_connection_test(7))


class FakeRequestRepository:
    def __init__(self, prepared) -> None:
        self.prepared = prepared
        self.operations: list[tuple] = []
        self.remote_states: list[tuple] = []
        self.baselines: list[tuple] = []
        self.persisted: list[tuple] = []

    def prepare_execution(self, *_args):
        return self.prepared

    def set_operation(self, *args):
        self.operations.append(args)

    def set_remote_state(self, *args):
        self.remote_states.append(args)

    def set_correlation_baseline(self, *args):
        self.baselines.append(args)

    def build_document_path(self, *_args):
        return Path("/tmp/document.pdf")

    def persist_flow_result(self, *args):
        self.persisted.append(args)


def _request_snapshot(*, artifact_dir: str | None, status: str = "not_found", search_mode: str = "soggetto"):
    request = SimpleNamespace(
        id=uuid4(),
        row_index=1,
        search_mode=search_mode,
        comune="ORISTANO",
        foglio="1",
        particella="2",
        subject_id="ABC",
        artifact_dir=artifact_dir,
    )
    result = SimpleNamespace(status=status, error_message=None)
    return request, result


def test_process_request_handles_missing_and_full_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    worker = bare_worker()
    repository = FakeRequestRepository(None)
    worker._request_repository = lambda: repository
    browser = FakeBrowser()
    credential = SimpleNamespace(id=uuid4(), sister_username="user", sister_password_encrypted="secret")
    run(worker._process_request(browser, credential, uuid4(), uuid4()))
    assert not repository.operations

    request, result = _request_snapshot(artifact_dir=str(tmp_path), status="not_found", search_mode="soggetto")
    prepared = SimpleNamespace(request=request, execution_token=uuid4())
    repository = FakeRequestRepository(prepared)
    worker._request_repository = lambda: repository
    worker.llm_captcha_solver = object()
    worker.anti_captcha_client = object()

    async def execute(**kwargs):
        callbacks = kwargs["callbacks"]
        callbacks.update_operation("step")
        callbacks.update_remote_state("remote", "url", "ready")
        callbacks.update_correlation_baseline({"key"})
        assert kwargs["solve_llm_captcha"] is not None
        assert kwargs["solve_external_captcha"] is not None
        return result

    monkeypatch.setattr(worker_module, "execute_visura_flow", execute)
    run(worker._process_request(browser, credential, uuid4(), request.id))
    assert browser.previews and browser.snapshots and repository.persisted
    assert repository.remote_states and repository.baselines

    request, result = _request_snapshot(artifact_dir=str(tmp_path), status="completed", search_mode="immobile")
    repository = FakeRequestRepository(SimpleNamespace(request=request, execution_token=uuid4()))
    worker._request_repository = lambda: repository
    worker.llm_captcha_solver = None
    worker.anti_captcha_client = None
    monkeypatch.setattr(worker_module, "execute_visura_flow", lambda **_kwargs: async_value(result))
    audit_payload = {"classification": "suppressed"}
    emitted: list[dict] = []
    monkeypatch.setattr(worker_module, "audit_downloaded_document", lambda *_args: audit_payload)
    monkeypatch.setattr(worker_module, "emit_pdf_parcel_status", lambda _browser, payload: emitted.append(payload))
    run(worker._process_request(browser, credential, uuid4(), request.id))
    assert len(browser.previews) == 1
    assert result.document_audit_payload == audit_payload
    assert emitted == [audit_payload]

    request, result = _request_snapshot(artifact_dir=None, status="completed", search_mode="immobile")
    repository = FakeRequestRepository(SimpleNamespace(request=request, execution_token=uuid4()))
    worker._request_repository = lambda: repository
    monkeypatch.setattr(worker_module, "audit_downloaded_document", lambda *_args: None)
    monkeypatch.setattr(worker_module, "execute_visura_flow", lambda **_kwargs: async_value(result))
    run(worker._process_request(browser, credential, uuid4(), request.id))


def test_reject_unexpected_document_type_deletes_only_untrusted_pdf(tmp_path: Path) -> None:
    untouched = SimpleNamespace(document_audit_payload=None, file_path=None)
    worker_module.reject_unexpected_document_type(untouched)

    trusted_path = tmp_path / "trusted.pdf"
    trusted_path.write_bytes(b"pdf")
    trusted = SimpleNamespace(
        document_audit_payload={"document_request_type": {"matches": True}},
        file_path=trusted_path,
    )
    worker_module.reject_unexpected_document_type(trusted)
    assert trusted_path.exists()

    mismatched_path = tmp_path / "mismatched.pdf"
    mismatched_path.write_bytes(b"pdf")
    mismatched = SimpleNamespace(
        document_audit_payload={
            "document_request_type": {
                "expected": "STORICA",
                "observed": "ATTUALITA",
                "matches": False,
            }
        },
        file_path=mismatched_path,
    )
    with pytest.raises(worker_module.SisterInvalidDocumentError, match="richiesto STORICA"):
        worker_module.reject_unexpected_document_type(mismatched)
    assert not mismatched_path.exists()


class CaptchaRepository:
    def __init__(self, states, *, begins=True) -> None:
        self.states = iter(states)
        self.begins = begins

    def begin(self, *_args):
        return self.begins

    def state(self, *_args):
        return next(self.states)


@pytest.mark.parametrize(
    ("state", "expected_text", "expected_skip"),
    [
        (SimpleNamespace(active=True, skip_requested=True, solution=None), None, True),
        (SimpleNamespace(active=True, skip_requested=False, solution="ABCDE"), "ABCDE", False),
    ],
)
def test_manual_captcha_decisions(state, expected_text, expected_skip, monkeypatch: pytest.MonkeyPatch) -> None:
    worker = bare_worker()
    worker._captcha_wait_repository = lambda: CaptchaRepository([state])
    claim = worker_module.SisterCaptchaClaim(uuid4(), uuid4(), uuid4())
    decision = run(worker._wait_for_manual_captcha(claim, Path("captcha.png")))
    assert decision.text == expected_text and decision.skip is expected_skip


def test_manual_captcha_timeout_and_solver_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = bare_worker()
    worker.state.stop_requested = True
    worker._captcha_wait_repository = lambda: CaptchaRepository([])
    claim = worker_module.SisterCaptchaClaim(uuid4(), uuid4(), uuid4())
    decision = run(worker._wait_for_manual_captcha(claim, Path("captcha.png")))
    assert decision.text is None and not decision.skip

    assert run(worker._solve_llm_captcha(b"x")) is None
    assert run(worker._solve_external_captcha(b"x")) is None
    worker.llm_captcha_solver = SimpleNamespace(solve=lambda _image: async_value("LLM"))
    worker.anti_captcha_client = SimpleNamespace(solve_image_to_text=lambda _image: async_value("EXT"))
    assert run(worker._solve_llm_captcha(b"x")) == "LLM"
    assert run(worker._solve_external_captcha(b"x")) == "EXT"

    worker.state.stop_requested = False
    waiting = SimpleNamespace(active=True, skip_requested=False, solution=None)
    worker._captcha_wait_repository = lambda: CaptchaRepository([waiting])

    async def stop_after_wait(_seconds):
        worker.state.stop_requested = True

    monkeypatch.setattr(worker_module.asyncio, "sleep", stop_after_wait)
    decision = run(worker._wait_for_manual_captcha(claim, Path("captcha.png")))
    assert decision.text is None and not decision.skip


def test_repository_helpers_set_operation_and_finalize_edges(worker_db, monkeypatch: pytest.MonkeyPatch) -> None:
    worker, session_factory, _tmp_path = worker_db
    repository = SimpleNamespace(persist_flow_result=lambda *args: setattr(repository, "args", args))
    worker._request_repository = lambda: repository
    worker._persist_flow_result(1, 2, "CF", SimpleNamespace())
    assert repository.args[:3] == (1, 2, "CF")

    _user_id, batch_id, request_ids = worker_test_support._seed_batch(
        session_factory,
        request_statuses=[worker_module.CatastoVisuraRequestStatus.COMPLETED.value],
    )
    worker._finalize_batch(batch_id)
    with session_factory() as db:
        batch = db.get(worker_module.CatastoBatch, batch_id)
        assert batch.status == worker_module.CatastoBatchStatus.COMPLETED.value

    with session_factory() as db:
        batch = db.get(worker_module.CatastoBatch, batch_id)
        request = db.get(worker_module.CatastoVisuraRequest, request_ids[0])
        batch.status = worker_module.CatastoBatchStatus.PROCESSING.value
        request.status = worker_module.CatastoVisuraRequestStatus.FAILED.value
        db.commit()
    worker._finalize_batch(batch_id)
    with session_factory() as db:
        batch = db.get(worker_module.CatastoBatch, batch_id)
        assert batch.status == worker_module.CatastoBatchStatus.FAILED.value

    missing = FakeDb(get_values=[None])
    monkeypatch.setattr(worker_module, "SessionLocal", SessionQueue(missing))
    worker._set_batch_operation(uuid4(), "none")
    batch = SimpleNamespace(current_operation=None)
    db = FakeDb(get_values=[batch])
    monkeypatch.setattr(worker_module, "SessionLocal", SessionQueue(db))
    worker._set_batch_operation(uuid4(), "running")
    assert batch.current_operation == "running" and db.commits == 1


def test_main_creates_storage_and_runs_worker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_module, "DOCUMENT_STORAGE_PATH", tmp_path / "documents")
    monkeypatch.setattr(worker_module, "CAPTCHA_STORAGE_PATH", tmp_path / "captcha")
    called: list[bool] = []

    class MainWorker:
        async def run(self):
            called.append(True)

    monkeypatch.setattr(worker_module, "CatastoWorker", MainWorker)
    run(worker_module.main())
    assert called and (tmp_path / "documents").is_dir() and (tmp_path / "captcha").is_dir()


def test_queue_messages_already_persisted_do_not_trigger_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = bare_worker()
    worker._is_within_incass_autosync_window = lambda: False
    worker._incass_autosync_window_label = lambda: "window"
    autosync_message = "Autosync inCASS in pausa fuori finestra oraria window"
    incass = SimpleNamespace(
        requested_by_user_id=None,
        credential_id=1,
        payload_json=None,
        error_detail=autosync_message,
    )
    db = FakeDb(scalars_values=[[], [incass], [], []])
    monkeypatch.setattr(worker_module, "SessionLocal", SessionQueue(db))
    for name in (
        "expire_stale_anagrafica_history_jobs",
        "expire_stale_incass_sync_jobs",
        "expire_stale_terreni_sync_jobs",
        "expire_stale_particelle_sync_jobs",
    ):
        monkeypatch.setattr(worker_module, name, lambda _db: None)
    assert worker._next_capacitas_job() is None
    assert db.commits == 0

    waiting_message = "In attesa di una credenziale Capacitas disponibile"
    history = SimpleNamespace(credential_id=2, payload_json=None, error_detail=waiting_message)
    db = FakeDb(scalars_values=[[history], [], [], []])
    monkeypatch.setattr(worker_module, "SessionLocal", SessionQueue(db))
    monkeypatch.setattr(worker_module, "has_available_credential", lambda *_args: False)
    assert worker._next_capacitas_job() is None
    assert db.commits == 0

    posta_message = "In attesa di una credenziale Poste Online disponibile"
    posta = SimpleNamespace(
        credential_id=3,
        payload_json=None,
        error_detail=posta_message,
        mode="registered_mail_sync",
    )
    db = FakeDb(scalars_values=[[posta]])
    monkeypatch.setattr(worker_module, "SessionLocal", SessionQueue(db))
    monkeypatch.setattr(worker_module, "expire_stale_registered_mail_sync_jobs", lambda _db: None)
    monkeypatch.setattr(worker_module, "has_available_posta_online_credential", lambda *_args: False)
    assert worker._next_posta_online_job_id() is None
    assert db.commits == 0


def test_module_entrypoint_invokes_asyncio_run(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def fake_run(coro):
        calls.append(coro)
        coro.close()

    monkeypatch.setattr(asyncio, "run", fake_run)
    runpy.run_path(worker_module.__file__, run_name="__main__")
    assert len(calls) == 1
