from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
import re
from time import monotonic
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from sqlalchemy import delete
from sqlalchemy.orm import Session, sessionmaker

from app.modules.elaborazioni.telemetry_models import SisterPortalEvent


logger = logging.getLogger(__name__)
SessionFactory = sessionmaker[Session]
ALLOWED_CONTEXT_KEYS = {
    "error_code",
    "resource_type",
    "remote_state",
    "wait_reason",
    "result_status",
}


def sanitize_endpoint(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip()
    parsed = urlsplit(candidate)
    path = parsed.path if parsed.scheme or parsed.netloc else candidate.split("?", maxsplit=1)[0]
    return path[:255] or "/"


def sanitize_context(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    sanitized = {
        key: _sanitize_context_value(value.get(key))
        for key in ALLOWED_CONTEXT_KEYS
        if _sanitize_context_value(value.get(key)) is not None
    }
    return sanitized or None


def _sanitize_context_value(value: object) -> object | None:
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str) and value:
        return value[:200]
    return None


def normalize_step(value: object) -> str:
    text = str(value or "unknown").strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return (normalized or "unknown")[:64]


@dataclass(frozen=True, slots=True)
class SisterTelemetryRecord:
    event_type: str
    step: str
    outcome: str = "info"
    severity: str = "info"
    duration_ms: int | None = None
    http_status: int | None = None
    endpoint: str | None = None
    attempt: int | None = None
    cooldown_seconds: int | None = None
    context: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class SisterTelemetryScope:
    user_id: int | None
    batch_id: UUID | None
    request_id: UUID | None
    credential_id: UUID | None
    session_id: UUID
    run_id: UUID | None


class SisterTelemetryRecorder:
    def __init__(self, session_factory: SessionFactory, *, enabled: bool = True) -> None:
        self._session_factory = session_factory
        self.enabled = enabled

    def record(self, record: SisterTelemetryRecord, scope: SisterTelemetryScope) -> bool:
        if not self.enabled:
            return False
        try:
            self._write(record, scope)
            return True
        except Exception:
            logger.warning("Scrittura telemetria SISTER ignorata per non interrompere il worker", exc_info=True)
            return False

    def _write(self, record: SisterTelemetryRecord, scope: SisterTelemetryScope) -> None:
        with self._session_factory() as db:
            db.add(_build_event(record, scope))
            db.commit()

    def purge_expired(self, retention_days: int, *, now: datetime | None = None) -> int:
        if not self.enabled or retention_days <= 0:
            return 0
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=retention_days)
        try:
            return self._delete_before(cutoff)
        except Exception:
            logger.warning("Retention DB telemetria SISTER non eseguita", exc_info=True)
            return 0

    def _delete_before(self, cutoff: datetime) -> int:
        with self._session_factory() as db:
            result = db.execute(delete(SisterPortalEvent).where(SisterPortalEvent.occurred_at < cutoff))
            db.commit()
            return int(result.rowcount or 0)

    def bind(
        self,
        *,
        user_id: int | None,
        batch_id: UUID | None,
        credential_id: UUID | None,
    ) -> "SisterTelemetryBinding":
        return SisterTelemetryBinding(self, user_id, batch_id, credential_id)


def _build_event(record: SisterTelemetryRecord, scope: SisterTelemetryScope) -> SisterPortalEvent:
    return SisterPortalEvent(
        user_id=scope.user_id,
        batch_id=scope.batch_id,
        request_id=scope.request_id,
        credential_id=scope.credential_id,
        session_id=scope.session_id,
        run_id=scope.run_id,
        event_type=normalize_step(record.event_type),
        step=normalize_step(record.step),
        outcome=normalize_step(record.outcome)[:32],
        severity=normalize_step(record.severity)[:16],
        duration_ms=max(record.duration_ms, 0) if record.duration_ms is not None else None,
        http_status=record.http_status,
        endpoint=sanitize_endpoint(record.endpoint),
        attempt=max(record.attempt, 1) if record.attempt is not None else None,
        cooldown_seconds=max(record.cooldown_seconds, 0) if record.cooldown_seconds is not None else None,
        context_json=sanitize_context(record.context),
    )


@dataclass(slots=True)
class SisterTelemetryBinding:
    recorder: SisterTelemetryRecorder
    user_id: int | None
    batch_id: UUID | None
    credential_id: UUID | None
    session_id: UUID = field(default_factory=uuid4)
    request_id: UUID | None = None
    run_id: UUID | None = None
    _operation_step: str | None = None
    _operation_started: float | None = None

    def begin_request(self, request_id: UUID, run_id: UUID | None) -> None:
        self.request_id = request_id
        self.run_id = run_id or uuid4()
        self.record(SisterTelemetryRecord("execution_start", "execution", outcome="started"))

    def finish_request(self, outcome: str = "completed") -> None:
        self._finish_operation(outcome)
        self.request_id = None
        self.run_id = None

    def operation(self, value: str) -> None:
        self._finish_operation("success")
        self._operation_step = normalize_step(value)
        self._operation_started = monotonic()

    def record(self, record: SisterTelemetryRecord) -> bool:
        return self.recorder.record(record, self.scope())

    def scope(self) -> SisterTelemetryScope:
        return SisterTelemetryScope(
            self.user_id,
            self.batch_id,
            self.request_id,
            self.credential_id,
            self.session_id,
            self.run_id,
        )

    def _finish_operation(self, outcome: str) -> None:
        if self._operation_step is None or self._operation_started is None:
            return
        duration_ms = round((monotonic() - self._operation_started) * 1000)
        self.record(SisterTelemetryRecord(
            "step_completed",
            self._operation_step,
            outcome=outcome,
            duration_ms=duration_ms,
        ))
        self._operation_step = None
        self._operation_started = None


__all__ = [
    "SisterTelemetryBinding",
    "SisterTelemetryRecord",
    "SisterTelemetryRecorder",
    "SisterTelemetryScope",
    "normalize_step",
    "sanitize_context",
    "sanitize_endpoint",
]
