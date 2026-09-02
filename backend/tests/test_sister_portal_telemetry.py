from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoCredential, CatastoDocument
from app.modules.elaborazioni.router import router as elaborazioni_module_router
from app.modules.elaborazioni.telemetry_models import SisterPortalEvent
from app.modules.elaborazioni.telemetry_routes import (
    read_sister_portal_events,
    read_sister_portal_health,
)
from app.modules.elaborazioni.telemetry_service import get_portal_health, list_portal_events


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _user(db, username: str = "telemetry-user") -> ApplicationUser:
    user = ApplicationUser(
        username=username,
        email=f"{username}@example.local",
        password_hash="hash",
        role="operator",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _event(
    user_id: int,
    occurred_at: datetime,
    *,
    outcome: str = "success",
    event_type: str = "execution_complete",
    step: str = "download",
    duration_ms: int | None = 1000,
    credential_id=None,
    http_status: int | None = None,
    cooldown_seconds: int | None = None,
    run_id=None,
) -> SisterPortalEvent:
    return SisterPortalEvent(
        user_id=user_id,
        occurred_at=occurred_at,
        credential_id=credential_id,
        session_id=uuid4(),
        run_id=run_id or uuid4(),
        event_type=event_type,
        step=step,
        outcome=outcome,
        severity="error" if outcome == "error" else "info",
        duration_ms=duration_ms,
        http_status=http_status,
        endpoint="/Visure/test.do" if http_status else None,
        cooldown_seconds=cooldown_seconds,
    )


def _document(
    user_id: int,
    created_at: datetime,
    *,
    tipo_visura: str,
    request_type: str | None,
    content_request_type: str | None = None,
) -> CatastoDocument:
    return CatastoDocument(
        user_id=user_id,
        tipo_visura=tipo_visura,
        request_type=request_type,
        content_request_type=content_request_type,
        filename=f"{uuid4()}.pdf",
        filepath=f"/tmp/{uuid4()}.pdf",
        created_at=created_at,
    )


def test_portal_health_aggregates_metrics_alerts_and_user_scope() -> None:
    db = _session()
    now = datetime.now(UTC)
    user = _user(db)
    other_user = _user(db, "other-user")
    credential = CatastoCredential(
        user_id=user.id,
        label="Profilo A",
        sister_username="user",
        sister_password_encrypted=b"secret",
        active=True,
        is_default=True,
    )
    db.add(credential)
    db.flush()
    events = [
        _event(user.id, now - timedelta(hours=1), credential_id=credential.id, duration_ms=180_000),
        _event(user.id, now - timedelta(hours=2), outcome="completed", credential_id=credential.id),
        _event(
            user.id,
            now - timedelta(hours=3),
            outcome="error",
            event_type="http_error",
            http_status=500,
        ),
        _event(
            user.id,
            now - timedelta(hours=4),
            outcome="failed",
            event_type="http_error",
            http_status=502,
        ),
        _event(
            user.id,
            now - timedelta(hours=5),
            outcome="timeout",
            event_type="http_error",
            http_status=503,
        ),
        _event(
            user.id,
            now - timedelta(hours=6),
            outcome="waiting",
            event_type="cooldown",
            cooldown_seconds=90,
            duration_ms=None,
            credential_id=uuid4(),
        ),
        _event(user.id, now - timedelta(hours=7), event_type="retry", outcome="scheduled"),
        _event(
            other_user.id,
            now - timedelta(minutes=5),
            outcome="error",
            event_type="http_error",
            http_status=500,
        ),
    ]
    db.add_all(events)
    db.add_all(
        [
            _document(
                user.id, now - timedelta(hours=1), tipo_visura="Sintetica", request_type="ATTUALITA"
            ),
            _document(
                user.id,
                now - timedelta(hours=2),
                tipo_visura="Completa",
                request_type="ATTUALITA",
                content_request_type="STORICA",
            ),
            _document(user.id, now - timedelta(hours=3), tipo_visura="", request_type=None),
            _document(
                other_user.id,
                now - timedelta(hours=1),
                tipo_visura="Analitica",
                request_type="STORICA",
            ),
            _document(
                user.id, now - timedelta(hours=25), tipo_visura="Analitica", request_type="STORICA"
            ),
        ]
    )
    db.commit()

    result = get_portal_health(db, user_id=user.id, window_hours=24, now=now)

    assert result.status == "critical"
    assert result.totals.events == 7
    assert result.totals.successes == 2
    assert result.totals.errors == 3
    assert result.totals.retries == 1
    assert result.totals.cooldowns == 1
    assert result.totals.success_rate == 40.0
    assert result.totals.p95_duration_ms == 180_000
    assert result.downloads.total == 3
    assert result.downloads.by_visura_type == {"Sintetica": 1, "Completa": 1, "Non classificata": 1}
    assert result.downloads.by_request_type == {"ATTUALITA": 1, "STORICA": 1, "NON_CLASSIFICATA": 1}
    assert len(result.timeline) == 7
    assert result.steps[0].errors == 3
    assert result.errors[0].count == 1
    assert {alert.id for alert in result.alerts} == {
        "sister-http-5xx",
        "sister-error-rate",
        "sister-high-latency",
        "sister-cooldown-active",
    }
    assert result.credentials[0].label in {"Profilo A", "Sessione non associata"}
    assert result.recent_events[0].credential_label == "Profilo A"
    assert any(item.credential_label is None for item in result.recent_events)
    assert len(result.recent_events) == 7

    daily = get_portal_health(db, user_id=user.id, window_hours=168, now=now)
    assert sum(point.events for point in daily.timeline) == 7
    assert all(point.bucket.hour == 0 for point in daily.timeline)

    listed = list_portal_events(db, user_id=user.id, window_hours=24, limit=2)
    assert listed.total == 7
    assert len(listed.items) == 2
    assert listed.items[0].credential_label == "Profilo A"

    assert read_sister_portal_health(user, db, hours=24).window_hours == 24
    assert read_sister_portal_events(user, db, hours=24, limit=1).total == 7
    db.close()


def test_portal_health_covers_unknown_healthy_and_degraded_states() -> None:
    db = _session()
    now = datetime.now(UTC)
    user = _user(db)
    db.commit()

    empty = get_portal_health(db, user_id=user.id, window_hours=24, now=now)
    assert empty.status == "unknown"
    assert empty.totals.success_rate == 0
    assert empty.totals.average_duration_ms is None
    assert empty.totals.p95_duration_ms is None
    assert empty.downloads.total == 0
    assert empty.downloads.by_visura_type == {}
    assert empty.downloads.by_request_type == {}
    assert empty.timeline == []
    assert empty.credentials == []
    assert empty.alerts == []

    db.add(_event(user.id, now - timedelta(minutes=5), duration_ms=100))
    db.commit()
    healthy = get_portal_health(db, user_id=user.id, window_hours=24, now=now)
    assert healthy.status == "healthy"
    assert healthy.totals.success_rate == 100

    db.add(_event(user.id, now - timedelta(minutes=4), duration_ms=120_000))
    db.commit()
    degraded = get_portal_health(db, user_id=user.id, window_hours=24, now=now)
    assert degraded.status == "degraded"
    assert [alert.id for alert in degraded.alerts] == ["sister-high-latency"]
    db.close()


def test_elaborazioni_router_registers_portal_health_endpoints() -> None:
    paths = {route.path for route in elaborazioni_module_router.routes}
    assert "/elaborazioni/portal-health" in paths
    assert "/elaborazioni/portal-health/events" in paths
