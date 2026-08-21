from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest


WORKER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = next((path for path in WORKER_ROOT.parents if (path / "backend").exists()), WORKER_ROOT.parents[-1])
BACKEND_ROOT = REPO_ROOT / "backend"
for path in (WORKER_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


import sister_observability as observability_module
from sister_observability import (
    BrowserTelemetryAdapter,
    ObservabilityConfig,
    RequestInvocation,
    SisterWorkerObservability,
    WorkerRuntimeContext,
    instrument_sister_worker,
)
from sister_telemetry import SisterTelemetryRecord


def run(coro):
    return asyncio.run(coro)


class RecordingBinding:
    def __init__(self) -> None:
        self.events: list[SisterTelemetryRecord] = []
        self.begun: list[tuple[object, object]] = []
        self.finished: list[str] = []

    def begin_request(self, request_id, run_id) -> None:
        self.begun.append((request_id, run_id))

    def record(self, record: SisterTelemetryRecord) -> bool:
        self.events.append(record)
        return True

    def finish_request(self, outcome: str) -> None:
        self.finished.append(outcome)


class RecordingRecorder:
    def __init__(self, binding: RecordingBinding | None = None) -> None:
        self.binding = binding or RecordingBinding()
        self.bind_calls: list[dict[str, object]] = []

    def bind(self, **values):
        self.bind_calls.append(values)
        return self.binding

    def purge_expired(self, _days: int) -> int:
        return 0


class RetentionProbe:
    def __init__(self) -> None:
        self.calls = 0

    def run_if_due(self) -> bool:
        self.calls += 1
        return True


class FakeDb:
    def __init__(self, value=None, error: Exception | None = None) -> None:
        self.value = value
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def get(self, _model, _identity):
        if self.error is not None:
            raise self.error
        return self.value


def config(**overrides) -> ObservabilityConfig:
    values = {
        "enabled": True,
        "event_retention_days": 30,
        "artifact_retention_days": 14,
        "retention_dry_run": False,
        "request_retry_seconds": 20,
        "credential_lock_seconds": 60,
        "server_error_base_seconds": 10,
        "server_error_max_seconds": 15,
    }
    values.update(overrides)
    return ObservabilityConfig(**values)


def context(session_factory=lambda: FakeDb(), **config_overrides) -> WorkerRuntimeContext:
    return WorkerRuntimeContext(
        session_factory=session_factory,
        batch_model=object(),
        request_model=object(),
        debug_root=Path("/tmp/gaia-sister-debug"),
        report_root=Path("/tmp/gaia-sister-reports"),
        config=config(**config_overrides),
    )


def bare_observability(
    *,
    session_factory=lambda: FakeDb(),
    binding: RecordingBinding | None = None,
) -> SisterWorkerObservability:
    instance = SisterWorkerObservability.__new__(SisterWorkerObservability)
    instance.context = context(session_factory)
    instance.recorder = RecordingRecorder(binding)
    instance.retention = RetentionProbe()
    instance._browser_adapters = {}
    instance._batch_bindings = {}
    instance._server_error_counts = {}
    return instance


def test_runtime_context_reads_defaults_and_environment(monkeypatch) -> None:
    values = {
        "SessionLocal": "factory",
        "CatastoBatch": "batch-model",
        "CatastoVisuraRequest": "request-model",
        "DEBUG_ARTIFACTS_PATH": "/debug",
        "REPORT_STORAGE_PATH": "/reports",
        "REQUEST_RETRY_DEFER_SEC": 21,
        "CREDENTIAL_LOCK_COOLDOWN_SEC": 61,
        "SISTER_SERVER_ERROR_BASE_COOLDOWN_SEC": 31,
        "SISTER_SERVER_ERROR_MAX_COOLDOWN_SEC": 301,
    }
    for name in (
        "ELABORAZIONI_SISTER_TELEMETRY_ENABLED",
        "ELABORAZIONI_SISTER_EVENT_RETENTION_DAYS",
        "ELABORAZIONI_SISTER_ARTIFACT_RETENTION_DAYS",
        "ELABORAZIONI_SISTER_RETENTION_DRY_RUN",
    ):
        monkeypatch.delenv(name, raising=False)

    runtime = observability_module._runtime_context(values, {"visure_batches"})
    assert runtime.session_factory == "factory"
    assert runtime.debug_root == Path("/debug")
    assert runtime.config.enabled is True
    assert runtime.config.event_retention_days == 30
    assert runtime.config.artifact_retention_days == 14
    assert runtime.config.retention_dry_run is False
    assert runtime.config.request_retry_seconds == 21

    monkeypatch.setenv("ELABORAZIONI_SISTER_TELEMETRY_ENABLED", "false")
    monkeypatch.setenv("ELABORAZIONI_SISTER_EVENT_RETENTION_DAYS", "45")
    monkeypatch.setenv("ELABORAZIONI_SISTER_ARTIFACT_RETENTION_DAYS", "9")
    monkeypatch.setenv("ELABORAZIONI_SISTER_RETENTION_DRY_RUN", "true")
    runtime = observability_module._runtime_context(values, {"other"})
    assert runtime.config.enabled is False
    assert runtime.config.event_retention_days == 45
    assert runtime.config.artifact_retention_days == 9
    assert runtime.config.retention_dry_run is True


def test_observability_initializes_recorder_and_retention(monkeypatch) -> None:
    created = {}

    class Recorder:
        def __init__(self, factory, *, enabled):
            created["recorder"] = (factory, enabled)
            self.purge_expired = lambda _days: 0

    class Retention:
        def __init__(self, retention_config, purge):
            created["retention"] = (retention_config, purge)

    factory = lambda: FakeDb()
    monkeypatch.setattr(observability_module, "SisterTelemetryRecorder", Recorder)
    monkeypatch.setattr(observability_module, "SisterRetentionManager", Retention)
    instance = SisterWorkerObservability(context(factory))

    assert created["recorder"] == (factory, True)
    retention_config, purge = created["retention"]
    assert retention_config.artifact_retention_days == 14
    assert retention_config.event_retention_days == 30
    assert purge == instance.recorder.purge_expired


def test_worker_decorator_observes_all_entry_points(monkeypatch) -> None:
    calls = []
    runtime = context()

    class Probe:
        def __init__(self, received_context):
            calls.append(("init-observer", received_context))

        def instrument_browser(self, browser):
            calls.append(("browser", browser))

        async def execute_request(self, invocation):
            calls.append(("request", invocation))
            return "observed-request"

        def observe_batch_operation(self, batch_id, operation):
            calls.append(("operation", batch_id, operation))

    monkeypatch.setattr(observability_module, "_runtime_context", lambda _values, _families: runtime)
    monkeypatch.setattr(observability_module, "SisterWorkerObservability", Probe)

    @instrument_sister_worker
    class Worker:
        def __init__(self):
            self.job_families = {"visure_batches"}

        def _build_browser_session(self):
            return "browser"

        async def _process_request(self, browser, credential, batch_id, request_id):
            return (browser, credential, batch_id, request_id)

        def _set_batch_operation(self, batch_id, operation):
            return f"{batch_id}:{operation}"

    worker = Worker()
    assert calls[0] == ("init-observer", runtime)
    assert worker._build_browser_session() == "browser"
    assert run(worker._process_request("browser", "credential", "batch", "request")) == "observed-request"
    assert worker._set_batch_operation("batch", "waiting") == "batch:waiting"
    invocation = next(value for name, value in calls if name == "request")
    assert invocation.worker is worker
    assert invocation.browser == "browser"

    del worker._sister_observability
    assert worker._build_browser_session() == "browser"
    assert run(worker._process_request("b", "c", "batch", "request")) == ("b", "c", "batch", "request")
    assert worker._set_batch_operation("batch", "plain") == "batch:plain"


def test_browser_adapter_records_success_error_trace_and_server_response(monkeypatch) -> None:
    class Browser:
        def __init__(self) -> None:
            self.fail = False
            self.responses = []

        async def start(self):
            if self.fail:
                raise RuntimeError("start failed")
            return "started"

        async def _trace_state(self, label):
            return f"trace:{label}"

        def _track_response(self, response):
            self.responses.append(response)
            return "tracked"

    browser = Browser()
    ticks = iter([10.0, 10.25, 20.0, 20.5])
    monkeypatch.setattr(observability_module, "monotonic", lambda: next(ticks))
    adapter = BrowserTelemetryAdapter(browser)
    adapter.install()
    adapter.install()

    assert run(browser.start()) == "started"
    browser.fail = True
    with pytest.raises(RuntimeError, match="start failed"):
        run(browser.start())
    assert run(browser._trace_state("logged-in")) == "trace:logged-in"

    def response(status, url, resource_type="xhr"):
        return SimpleNamespace(
            status=status,
            url=url,
            request=SimpleNamespace(resource_type=resource_type),
        )

    assert browser._track_response(response(200, "https://sister.agenziaentrate.gov.it/ok")) == "tracked"
    browser._track_response(response(503, "https://example.test/fail"))
    browser._track_response(response(503, "https://agenziaentrate.gov.it/fail?secret=1", "document"))
    browser._track_response(object())

    assert [record.event_type for record in adapter.pending] == [
        "session_start",
        "session_start",
        "browser_trace",
        "http_error",
    ]
    assert adapter.pending[0].outcome == "success"
    assert adapter.pending[0].duration_ms == 250
    assert adapter.pending[1].outcome == "error"
    assert adapter.pending[1].duration_ms == 500
    assert adapter.pending[-1].http_status == 503

    binding = RecordingBinding()
    adapter.set_binding(binding)
    adapter.emit(SisterTelemetryRecord("manual", "after-binding"))
    assert not adapter.pending
    assert [record.event_type for record in binding.events][-1] == "manual"

    empty_browser = SimpleNamespace()
    BrowserTelemetryAdapter(empty_browser).install()
    BrowserTelemetryAdapter(object()).install()


def test_instrument_browser_reuses_adapter_and_binding_uses_safe_identity() -> None:
    instance = bare_observability()
    browser = SimpleNamespace()
    first = instance.instrument_browser(browser)
    assert instance.instrument_browser(browser) is first

    credential = SimpleNamespace()
    batch_id = uuid4()
    binding = instance._binding(browser, credential, batch_id)
    assert first.binding is binding
    assert instance.recorder.bind_calls == [{
        "user_id": None,
        "batch_id": batch_id,
        "credential_id": None,
    }]


def test_execute_request_records_success_and_status() -> None:
    binding = RecordingBinding()
    instance = bare_observability(binding=binding)
    instance._request_status = lambda _request_id: "NOT_FOUND"
    credential = SimpleNamespace(id=uuid4(), user_id=7)
    batch_id = uuid4()
    request_id = uuid4()

    async def original(worker, browser, received_credential, received_batch, received_request):
        assert worker == "worker"
        assert browser is browser_marker
        assert received_credential is credential
        assert (received_batch, received_request) == (batch_id, request_id)
        return "result"

    browser_marker = SimpleNamespace()
    invocation = RequestInvocation(original, "worker", browser_marker, credential, batch_id, request_id)
    assert run(instance.execute_request(invocation)) == "result"
    assert instance.retention.calls == 1
    assert binding.begun[0][0] == request_id
    assert binding.begun[0][1] is not None
    assert binding.events[-1].context == {"result_status": "not_found"}
    assert binding.finished == ["success"]
    assert instance._server_error_counts[credential.id] == 0


@pytest.mark.parametrize(("recoverable", "expected_code"), [(True, "RuntimeError"), (False, "RuntimeError")])
def test_execute_request_records_recoverable_and_generic_errors(recoverable, expected_code) -> None:
    binding = RecordingBinding()
    instance = bare_observability(binding=binding)
    credential = SimpleNamespace(id=uuid4(), user_id=7)
    worker = SimpleNamespace(_is_recoverable_credential_error=lambda _exc: recoverable)

    async def original(*_args):
        raise RuntimeError("portal failed")

    invocation = RequestInvocation(original, worker, SimpleNamespace(), credential, uuid4(), uuid4())
    with pytest.raises(RuntimeError, match="portal failed"):
        run(instance.execute_request(invocation))

    assert binding.finished == ["error"]
    assert binding.events[-1].context == {"error_code": expected_code}
    assert binding.events[-1].event_type == ("retry" if recoverable else "execution_complete")


def test_execute_request_records_server_error_backoff_and_resets_after_success() -> None:
    binding = RecordingBinding()
    instance = bare_observability(binding=binding)
    credential = SimpleNamespace(id=uuid4(), user_id=7)

    async def failing(*_args):
        raise observability_module.SisterServerError("HTTP 503")

    for expected_cooldown in (10, 15):
        invocation = RequestInvocation(failing, object(), SimpleNamespace(), credential, uuid4(), uuid4())
        with pytest.raises(observability_module.SisterServerError):
            run(instance.execute_request(invocation))
        cooldown = [event for event in binding.events if event.event_type == "cooldown"][-1]
        retry = [event for event in binding.events if event.event_type == "retry"][-1]
        assert cooldown.cooldown_seconds == expected_cooldown
        assert retry.cooldown_seconds == max(20, expected_cooldown)

    assert instance._server_error_counts[credential.id] == 2
    assert [event.http_status for event in binding.events if event.event_type == "http_error"] == [503, 503]


def test_batch_and_request_database_context_are_fail_open() -> None:
    batch_id = uuid4()
    batch = SimpleNamespace(id=batch_id, user_id=11)
    instance = bare_observability(session_factory=lambda: FakeDb(batch))
    binding = instance._batch_binding(batch_id)
    assert binding is instance.recorder.binding
    assert instance.recorder.bind_calls[-1] == {
        "user_id": 11,
        "batch_id": batch_id,
        "credential_id": None,
    }

    instance.context = context(lambda: FakeDb(None))
    assert instance._batch_binding(batch_id) is None
    instance.context = context(lambda: FakeDb(error=RuntimeError("db down")))
    assert instance._batch_binding(batch_id) is None
    assert instance._request_status(uuid4()) == "completed"

    instance.context = context(lambda: FakeDb(SimpleNamespace(status="FAILED")))
    assert instance._request_status(uuid4()) == "FAILED"
    instance.context = context(lambda: FakeDb(None))
    assert instance._request_status(uuid4()) == "completed"


def test_batch_operations_use_cached_or_loaded_binding() -> None:
    instance = bare_observability()
    batch_id = uuid4()
    cached = RecordingBinding()
    instance._batch_bindings[batch_id] = cached
    instance.observe_batch_operation(batch_id, "Pausa globale SISTER 45s")
    assert cached.events[-1].event_type == "global_pause"
    assert cached.events[-1].cooldown_seconds == 45

    loaded = RecordingBinding()
    instance._batch_binding = lambda _batch_id: loaded
    instance.observe_batch_operation(uuid4(), "Credenziale in cooldown 20s")
    instance.observe_batch_operation(uuid4(), "Richieste differite 9s")
    assert [event.event_type for event in loaded.events] == ["cooldown", "retry"]

    instance._batch_binding = lambda _batch_id: None
    instance.observe_batch_operation(uuid4(), "Richieste differite")
    instance.observe_batch_operation(uuid4(), "Operazione normale")


@pytest.mark.parametrize(
    ("status", "outcome", "severity"),
    [
        ("completed", "success", "info"),
        ("not_found", "success", "info"),
        ("failed", "error", "error"),
        ("non_evadibile", "error", "error"),
        ("processing", "info", "info"),
    ],
)
def test_execution_result_mapping(status, outcome, severity) -> None:
    record = observability_module._execution_result_record(status)
    assert (record.outcome, record.severity) == (outcome, severity)


def test_observability_helpers_cover_endpoint_status_and_cooldown() -> None:
    assert observability_module._response_values(object()) is None
    assert observability_module._is_sister_server_error((500, "https://agenziaentrate.gov.it/x", "xhr"))
    assert observability_module._is_sister_server_error((599, "https://sister.agenziaentrate.gov.it/x", "xhr"))
    assert not observability_module._is_sister_server_error((499, "https://agenziaentrate.gov.it/x", "xhr"))
    assert not observability_module._is_sister_server_error((500, "https://notagenziaentrate.gov.it/x", "xhr"))
    assert observability_module._response_error_record(object()) is None
    assert observability_module._operation_seconds("attesa") is None
    assert observability_module._http_status("SISTER HTTP500") == 500
    assert observability_module._http_status("SISTER unavailable") is None
    assert observability_module._server_error_cooldown(config(), 0) == 10
    assert observability_module._server_error_cooldown(config(), 10) == 15
    assert observability_module._is_recoverable(object(), RuntimeError()) is False
