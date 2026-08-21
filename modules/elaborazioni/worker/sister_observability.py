from __future__ import annotations

from dataclasses import dataclass, field
from functools import wraps
import logging
import os
from pathlib import Path
import re
from time import monotonic
from typing import Any, Awaitable, Callable
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from sister_exceptions import SisterServerError
from sister_retention import SisterRetentionConfig, SisterRetentionManager
from sister_telemetry import (
    SisterTelemetryBinding,
    SisterTelemetryRecord,
    SisterTelemetryRecorder,
)


logger = logging.getLogger(__name__)
AsyncMethod = Callable[..., Awaitable[Any]]
FLOW_METHODS = (
    ("start", "session_start", "browser_start"),
    ("stop", "session_stop", "browser_stop"),
    ("ensure_authenticated", "login", "login"),
    ("logout", "logout", "logout"),
    ("open_visura_form", "navigation", "open_visura_form"),
    ("open_subject_form", "navigation", "open_subject_form"),
    ("fill_visura_form", "submit", "fill_visura_form"),
    ("fill_subject_form", "submit", "fill_subject_form"),
    ("search_subject_and_open_visura", "submit", "subject_search"),
    ("prepare_captcha_or_download", "submit", "prepare_download"),
    ("submit_captcha", "submit", "captcha_submit"),
    ("begin_request_correlation", "correlation", "request_correlation"),
    ("poll_richieste_for_download", "polling", "poll_requests"),
    ("download_pdf", "download", "download_pdf"),
)


@dataclass(slots=True)
class WorkerState:
    stop_requested: bool = False


@dataclass(frozen=True, slots=True)
class ObservabilityConfig:
    enabled: bool
    event_retention_days: int
    artifact_retention_days: int
    retention_dry_run: bool
    request_retry_seconds: int
    credential_lock_seconds: int
    server_error_base_seconds: int
    server_error_max_seconds: int


@dataclass(frozen=True, slots=True)
class WorkerRuntimeContext:
    session_factory: Any
    batch_model: Any
    request_model: Any
    debug_root: Path
    report_root: Path
    config: ObservabilityConfig


@dataclass(frozen=True, slots=True)
class RequestInvocation:
    original: AsyncMethod
    worker: object
    browser: object
    credential: object
    batch_id: UUID
    request_id: UUID


@dataclass(frozen=True, slots=True)
class RequestError:
    binding: SisterTelemetryBinding
    worker: object
    credential: object
    exception: Exception


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.lower() == "true"


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _runtime_context(values: dict[str, object], job_families: set[str]) -> WorkerRuntimeContext:
    config = ObservabilityConfig(
        enabled=_env_bool("ELABORAZIONI_SISTER_TELEMETRY_ENABLED", True) and "visure_batches" in job_families,
        event_retention_days=_env_int("ELABORAZIONI_SISTER_EVENT_RETENTION_DAYS", 30),
        artifact_retention_days=_env_int("ELABORAZIONI_SISTER_ARTIFACT_RETENTION_DAYS", 14),
        retention_dry_run=_env_bool("ELABORAZIONI_SISTER_RETENTION_DRY_RUN", False),
        request_retry_seconds=int(values["REQUEST_RETRY_DEFER_SEC"]),
        credential_lock_seconds=int(values["CREDENTIAL_LOCK_COOLDOWN_SEC"]),
        server_error_base_seconds=int(values["SISTER_SERVER_ERROR_BASE_COOLDOWN_SEC"]),
        server_error_max_seconds=int(values["SISTER_SERVER_ERROR_MAX_COOLDOWN_SEC"]),
    )
    return WorkerRuntimeContext(
        session_factory=values["SessionLocal"],
        batch_model=values["CatastoBatch"],
        request_model=values["CatastoVisuraRequest"],
        debug_root=Path(values["DEBUG_ARTIFACTS_PATH"]),
        report_root=Path(values["REPORT_STORAGE_PATH"]),
        config=config,
    )


def instrument_sister_worker(worker_class):
    _wrap_worker_init(worker_class)
    _wrap_browser_factory(worker_class)
    _wrap_process_request(worker_class)
    _wrap_batch_operation(worker_class)
    return worker_class


def _wrap_worker_init(worker_class) -> None:
    original = worker_class.__init__

    @wraps(original)
    def observed(self, *args, **kwargs):
        original(self, *args, **kwargs)
        context = _runtime_context(original.__globals__, self.job_families)
        self._sister_observability = SisterWorkerObservability(context)

    worker_class.__init__ = observed


def _wrap_browser_factory(worker_class) -> None:
    original = worker_class._build_browser_session

    @wraps(original)
    def observed(self):
        browser = original(self)
        observability = getattr(self, "_sister_observability", None)
        if observability is not None:
            observability.instrument_browser(browser)
        return browser

    worker_class._build_browser_session = observed


def _wrap_process_request(worker_class) -> None:
    original = worker_class._process_request

    @wraps(original)
    async def observed(self, *args):
        observability = getattr(self, "_sister_observability", None)
        if observability is None:
            return await original(self, *args)
        return await observability.execute_request(RequestInvocation(original, self, *args))

    worker_class._process_request = observed


def _wrap_batch_operation(worker_class) -> None:
    original = worker_class._set_batch_operation

    @wraps(original)
    def observed(self, batch_id, operation):
        result = original(self, batch_id, operation)
        observability = getattr(self, "_sister_observability", None)
        if observability is not None:
            observability.observe_batch_operation(batch_id, operation)
        return result

    worker_class._set_batch_operation = observed


class SisterWorkerObservability:
    def __init__(self, context: WorkerRuntimeContext) -> None:
        self.context = context
        self.recorder = SisterTelemetryRecorder(context.session_factory, enabled=context.config.enabled)
        retention_config = SisterRetentionConfig(
            context.debug_root,
            context.report_root,
            context.config.artifact_retention_days,
            context.config.event_retention_days,
            context.config.retention_dry_run,
        )
        self.retention = SisterRetentionManager(retention_config, self.recorder.purge_expired)
        self._browser_adapters: dict[int, BrowserTelemetryAdapter] = {}
        self._batch_bindings: dict[object, SisterTelemetryBinding] = {}
        self._server_error_counts: dict[object, int] = {}

    def instrument_browser(self, browser: object) -> "BrowserTelemetryAdapter":
        adapter = self._browser_adapters.get(id(browser))
        if adapter is None:
            adapter = BrowserTelemetryAdapter(browser)
            adapter.install()
            self._browser_adapters[id(browser)] = adapter
        return adapter

    async def execute_request(self, invocation: RequestInvocation) -> Any:
        binding = self._binding(invocation.browser, invocation.credential, invocation.batch_id)
        binding.begin_request(invocation.request_id, uuid4())
        self._batch_bindings[invocation.batch_id] = binding
        self.retention.run_if_due()
        try:
            result = await invocation.original(
                invocation.worker,
                invocation.browser,
                invocation.credential,
                invocation.batch_id,
                invocation.request_id,
            )
        except Exception as exc:
            self._record_request_error(RequestError(binding, invocation.worker, invocation.credential, exc))
            raise
        self._server_error_counts[invocation.credential.id] = 0
        result_status = self._request_status(invocation.request_id)
        binding.record(_execution_result_record(result_status))
        binding.finish_request("success")
        return result

    def observe_batch_operation(self, batch_id: object, operation: str) -> None:
        event = _operation_record(operation)
        if event is None:
            return
        binding = self._batch_bindings.get(batch_id) or self._batch_binding(batch_id)
        if binding is not None:
            binding.record(event)

    def _binding(self, browser: object, credential: object, batch_id: UUID) -> SisterTelemetryBinding:
        adapter = self.instrument_browser(browser)
        binding = self.recorder.bind(
            user_id=getattr(credential, "user_id", None),
            batch_id=batch_id,
            credential_id=getattr(credential, "id", None),
        )
        adapter.set_binding(binding)
        return binding

    def _batch_binding(self, batch_id: object) -> SisterTelemetryBinding | None:
        try:
            with self.context.session_factory() as db:
                batch = db.get(self.context.batch_model, batch_id)
                if batch is None:
                    return None
                return self.recorder.bind(user_id=batch.user_id, batch_id=batch.id, credential_id=None)
        except Exception:
            logger.debug("Contesto batch non disponibile per telemetria", exc_info=True)
            return None

    def _request_status(self, request_id: object) -> str:
        try:
            with self.context.session_factory() as db:
                request = db.get(self.context.request_model, request_id)
                return str(getattr(request, "status", "completed"))
        except Exception:
            logger.debug("Esito richiesta non disponibile per telemetria", exc_info=True)
            return "completed"

    def _record_request_error(self, error: RequestError) -> None:
        if isinstance(error.exception, SisterServerError):
            self._record_server_error(error.binding, error.credential, error.exception)
        elif _is_recoverable(error.worker, error.exception):
            error.binding.record(_retry_record(
                "credential",
                type(error.exception).__name__,
                self.context.config.credential_lock_seconds,
            ))
        else:
            error.binding.record(_error_record(type(error.exception).__name__))
        error.binding.finish_request("error")

    def _record_server_error(
        self,
        binding: SisterTelemetryBinding,
        credential: object,
        exc: SisterServerError,
    ) -> None:
        count = self._server_error_counts.get(credential.id, 0) + 1
        self._server_error_counts[credential.id] = count
        cooldown = _server_error_cooldown(self.context.config, count)
        status = _http_status(str(exc))
        binding.record(SisterTelemetryRecord(
            "http_error",
            "portal_response",
            outcome="error",
            severity="error",
            http_status=status,
            context={"error_code": "sister_server_error"},
        ))
        binding.record(_cooldown_record(count, cooldown))
        binding.record(_retry_record(
            "request",
            "sister_server_error",
            max(self.context.config.request_retry_seconds, cooldown),
        ))


@dataclass(slots=True)
class BrowserTelemetryAdapter:
    browser: object
    binding: SisterTelemetryBinding | None = None
    pending: list[SisterTelemetryRecord] = field(default_factory=list)

    def install(self) -> None:
        if getattr(self.browser, "_gaia_sister_telemetry_installed", False):
            return
        try:
            setattr(self.browser, "_gaia_sister_telemetry_installed", True)
        except Exception:
            return
        for method_name, event_type, step in FLOW_METHODS:
            self._wrap_async(method_name, event_type, step)
        self._wrap_trace()
        self._wrap_response()

    def set_binding(self, binding: SisterTelemetryBinding) -> None:
        self.binding = binding
        for record in self.pending:
            binding.record(record)
        self.pending.clear()

    def emit(self, record: SisterTelemetryRecord) -> None:
        if self.binding is None:
            self.pending.append(record)
        else:
            self.binding.record(record)

    def _wrap_async(self, method_name: str, event_type: str, step: str) -> None:
        original = getattr(self.browser, method_name, None)
        if not callable(original):
            return

        @wraps(original)
        async def observed(*args, **kwargs):
            started_at = monotonic()
            try:
                result = await original(*args, **kwargs)
            except Exception:
                self.emit(_timed_record(event_type, step, started_at, "error"))
                raise
            self.emit(_timed_record(event_type, step, started_at, "success"))
            return result

        setattr(self.browser, method_name, observed)

    def _wrap_trace(self) -> None:
        original = getattr(self.browser, "_trace_state", None)
        if not callable(original):
            return

        @wraps(original)
        async def observed(label: str):
            result = await original(label)
            self.emit(SisterTelemetryRecord("browser_trace", label, outcome="success"))
            return result

        setattr(self.browser, "_trace_state", observed)

    def _wrap_response(self) -> None:
        original = getattr(self.browser, "_track_response", None)
        if not callable(original):
            return

        @wraps(original)
        def observed(response):
            result = original(response)
            record = _response_error_record(response)
            if record is not None:
                self.emit(record)
            return result

        setattr(self.browser, "_track_response", observed)


def _timed_record(event_type: str, step: str, started_at: float, outcome: str) -> SisterTelemetryRecord:
    return SisterTelemetryRecord(
        event_type,
        step,
        outcome=outcome,
        severity="error" if outcome == "error" else "info",
        duration_ms=round((monotonic() - started_at) * 1000),
    )


def _response_error_record(response: object) -> SisterTelemetryRecord | None:
    response_values = _response_values(response)
    if response_values is None or not _is_sister_server_error(response_values):
        return None
    status, endpoint, resource_type = response_values
    return SisterTelemetryRecord(
        "http_error",
        "portal_response",
        outcome="error",
        severity="error",
        http_status=status,
        endpoint=endpoint,
        context={"resource_type": resource_type},
    )


def _response_values(response: object) -> tuple[int, str, str] | None:
    try:
        return int(response.status), str(response.url), str(response.request.resource_type)
    except Exception:
        return None


def _is_sister_server_error(response_values: tuple[int, str, str]) -> bool:
    status, endpoint, _resource_type = response_values
    hostname = (urlsplit(endpoint).hostname or "").lower()
    is_sister = hostname == "agenziaentrate.gov.it" or hostname.endswith(".agenziaentrate.gov.it")
    return is_sister and status >= 500


def _execution_result_record(status: str) -> SisterTelemetryRecord:
    normalized = status.lower()
    if normalized in {"completed", "not_found"}:
        outcome, severity = "success", "info"
    elif normalized in {"failed", "non_evadibile"}:
        outcome, severity = "error", "error"
    else:
        outcome, severity = "info", "info"
    return SisterTelemetryRecord(
        "execution_complete",
        "execution",
        outcome=outcome,
        severity=severity,
        context={"result_status": normalized},
    )


def _operation_record(operation: str) -> SisterTelemetryRecord | None:
    normalized = operation.lower()
    seconds = _operation_seconds(normalized)
    if "pausa globale" in normalized:
        return SisterTelemetryRecord(
            "global_pause", "portal_protection", outcome="waiting",
            severity="warning", cooldown_seconds=seconds,
        )
    if "in cooldown" in normalized:
        return SisterTelemetryRecord(
            "cooldown", "credential", outcome="waiting",
            severity="warning", cooldown_seconds=seconds,
        )
    if "richieste differite" in normalized:
        return SisterTelemetryRecord(
            "retry", "request", outcome="waiting",
            severity="warning", cooldown_seconds=seconds,
        )
    return None


def _operation_seconds(operation: str) -> int | None:
    match = re.search(r"(\d+)s", operation)
    return int(match.group(1)) if match else None


def _server_error_cooldown(config: ObservabilityConfig, consecutive_errors: int) -> int:
    exponent = max(consecutive_errors - 1, 0)
    return min(config.server_error_base_seconds * (2 ** exponent), config.server_error_max_seconds)


def _http_status(message: str) -> int | None:
    match = re.search(r"(?:HTTP\s*)?(5\d{2})", message, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _retry_record(step: str, error_code: str, seconds: int) -> SisterTelemetryRecord:
    return SisterTelemetryRecord(
        "retry",
        step,
        outcome="scheduled",
        severity="warning",
        cooldown_seconds=seconds,
        context={"error_code": error_code},
    )


def _cooldown_record(attempt: int, seconds: int) -> SisterTelemetryRecord:
    return SisterTelemetryRecord(
        "cooldown",
        "sister_server_error",
        outcome="error",
        severity="error",
        attempt=attempt,
        cooldown_seconds=seconds,
        context={"error_code": "sister_server_error"},
    )


def _error_record(error_code: str) -> SisterTelemetryRecord:
    return SisterTelemetryRecord(
        "execution_complete",
        "execution",
        outcome="error",
        severity="error",
        context={"error_code": error_code},
    )


def _is_recoverable(worker: object, exc: Exception) -> bool:
    classifier = getattr(worker, "_is_recoverable_credential_error", None)
    return bool(callable(classifier) and classifier(exc))


__all__ = [
    "BrowserTelemetryAdapter",
    "ObservabilityConfig",
    "SisterWorkerObservability",
    "WorkerRuntimeContext",
    "WorkerState",
    "instrument_sister_worker",
]
