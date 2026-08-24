from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


WORKER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = next((path for path in WORKER_ROOT.parents if (path / "backend").exists()), WORKER_ROOT.parents[-1])
BACKEND_ROOT = REPO_ROOT / "backend"
for path in (WORKER_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoBatch, CatastoCredential, CatastoVisuraRequest
from app.modules.elaborazioni.telemetry_models import SisterPortalEvent
import sister_telemetry as telemetry_module
from sister_telemetry import (
    SisterTelemetryRecord,
    SisterTelemetryRecorder,
    SisterTelemetryScope,
    normalize_step,
    sanitize_context,
    sanitize_endpoint,
)


def _factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'telemetry.sqlite3'}")
    ApplicationUser.__table__.create(engine)
    CatastoCredential.__table__.create(engine)
    CatastoBatch.__table__.create(engine)
    CatastoVisuraRequest.__table__.create(engine)
    SisterPortalEvent.__table__.create(engine)
    return sessionmaker(bind=engine)


def test_sanitizers_keep_only_operational_data() -> None:
    assert sanitize_endpoint(None) is None
    assert sanitize_endpoint("  ") is None
    assert sanitize_endpoint("https://example.test/path?q=secret") == "/path"
    assert sanitize_endpoint("/relative?q=secret") == "/relative"
    assert sanitize_endpoint("https://example.test") == "/"
    assert sanitize_context("invalid") is None
    assert sanitize_context({"secret": "no"}) is None
    sanitized = sanitize_context({
        "error_code": "x" * 250,
        "resource_type": "xhr",
        "remote_state": 4,
        "wait_reason": 1.5,
        "result_status": True,
        "parcel_classification": "suppressed",
        "parcel_suppressed_from": "09/12/2025",
        "expected_request_type": "STORICA",
        "observed_request_type": "ATTUALITA",
        "password": "hidden",
    })
    assert sanitized == {
        "error_code": "x" * 200,
        "resource_type": "xhr",
        "remote_state": 4,
        "wait_reason": 1.5,
        "result_status": True,
        "parcel_classification": "suppressed",
        "parcel_suppressed_from": "09/12/2025",
        "expected_request_type": "STORICA",
        "observed_request_type": "ATTUALITA",
    }
    assert normalize_step("  Login SISTER / Profilo A ") == "login_sister_profilo_a"
    assert normalize_step("***") == "unknown"
    assert len(normalize_step("x" * 80)) == 64


def test_recorder_persists_clamps_and_purges_events(tmp_path) -> None:
    factory = _factory(tmp_path)
    recorder = SisterTelemetryRecorder(factory)
    session_id = uuid4()
    assert recorder.record(
        SisterTelemetryRecord(
            event_type="HTTP Error",
            step="Portal response",
            outcome="error",
            severity="error",
            duration_ms=-1,
            attempt=0,
            cooldown_seconds=-2,
            endpoint="https://sister.test/path?token=secret",
            context={"error_code": "server", "password": "hidden"},
        ),
        SisterTelemetryScope(None, None, None, None, session_id, None),
    )
    with factory() as db:
        event = db.scalar(select(SisterPortalEvent))
        assert event is not None
        assert event.event_type == "http_error"
        assert event.duration_ms == 0
        assert event.attempt == 1
        assert event.cooldown_seconds == 0
        assert event.endpoint == "/path"
        assert event.context_json == {"error_code": "server"}
        event.occurred_at = datetime.now(timezone.utc) - timedelta(days=40)
        db.commit()
    assert recorder.purge_expired(30) == 1
    assert recorder.purge_expired(0) == 0

    disabled = SisterTelemetryRecorder(factory, enabled=False)
    assert disabled.record(
        SisterTelemetryRecord("event", "step"),
        SisterTelemetryScope(None, None, None, None, session_id, None),
    ) is False
    assert disabled.purge_expired(30) == 0


def test_recorder_is_fail_open() -> None:
    def broken_factory():
        raise RuntimeError("db unavailable")

    recorder = SisterTelemetryRecorder(broken_factory)
    assert recorder.record(
        SisterTelemetryRecord("event", "step"),
        SisterTelemetryScope(None, None, None, None, uuid4(), None),
    ) is False
    assert recorder.purge_expired(30) == 0


def test_binding_tracks_operations_and_browser_payloads(tmp_path, monkeypatch) -> None:
    factory = _factory(tmp_path)
    recorder = SisterTelemetryRecorder(factory)
    binding = recorder.bind(user_id=7, batch_id=uuid4(), credential_id=uuid4())
    ticks = iter([10.0, 10.25, 11.0, 11.5])
    monkeypatch.setattr(telemetry_module, "monotonic", lambda: next(ticks))

    request_id = uuid4()
    run_id = uuid4()
    binding.begin_request(request_id, run_id)
    binding.operation("Login")
    binding.operation("Download")
    binding.record(SisterTelemetryRecord(
        "http_error",
        "portal",
        outcome="error",
        severity="error",
        http_status=503,
        endpoint="https://sister.test/fail?q=1",
        cooldown_seconds=90,
        context={"resource_type": "xhr"},
    ))
    binding.finish_request("error")
    binding.finish_request()

    with factory() as db:
        events = db.scalars(select(SisterPortalEvent).order_by(SisterPortalEvent.occurred_at)).all()
    assert [event.event_type for event in events] == [
        "execution_start",
        "step_completed",
        "http_error",
        "step_completed",
    ]
    assert events[1].duration_ms == 250
    assert events[2].http_status == 503
    assert events[2].duration_ms is None
    assert events[3].duration_ms == 500
    assert binding.request_id is None
