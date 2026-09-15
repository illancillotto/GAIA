from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Generator
from datetime import UTC, date, datetime, time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import get_db
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.operazioni.models.organizational import OperatorProfile
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
)
from app.modules.presenze.router.routes.whatsapp_webhook import router as webhook_router
from app.modules.presenze.services import punch_reminder_job as job
from app.modules.presenze.services.punch_reminder_dispatch import DispatchOptions, DispatchOutcome
from app.modules.presenze.services.punch_reminders import PunchReminder, ReminderDay
from app.modules.presenze.services.whatsapp_waha import (
    DryRunWhatsAppSender,
    WhatsAppAck,
    WhatsAppOptOut,
)
from app.modules.presenze.whatsapp_models import (
    PresenzeWhatsAppMessage,
    PresenzeWhatsAppNotifiedDay,
    PresenzeWhatsAppOptOut,
)

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
NOW = datetime(2026, 9, 15, 8, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _user(
    db: Session, username: str, *, phone: str | None = "3331234567", profile: bool = True
) -> ApplicationUser:
    user = ApplicationUser(
        username=username,
        email=f"{username}@example.local",
        password_hash="x",
        role=ApplicationUserRole.OPERATOR.value,
        is_active=True,
    )
    db.add(user)
    db.flush()
    if profile:
        db.add(OperatorProfile(user_id=user.id, phone=phone, is_active=True))
    return user


def _collaborator(
    db: Session, name: str, user: ApplicationUser | None, code: str
) -> PresenzeCollaborator:
    collaborator = PresenzeCollaborator(
        employee_code=code, name=name, application_user_id=user.id if user else None, is_active=True
    )
    db.add(collaborator)
    db.flush()
    return collaborator


def _record(
    db: Session, collaborator: PresenzeCollaborator, work_date: date, punches, **fields
) -> PresenzeDailyRecord:
    record = PresenzeDailyRecord(collaborator_id=collaborator.id, work_date=work_date, **fields)
    db.add(record)
    db.flush()
    for sequence, (entry, exit_) in enumerate(punches, start=1):
        db.add(
            PresenzeDailyPunch(
                daily_record_id=record.id, sequence=sequence, entry_time=entry, exit_time=exit_
            )
        )
    return record


def _options() -> DispatchOptions:
    return DispatchOptions(now=lambda: NOW, sleep=lambda seconds: None, random=lambda: 0.0)


class RecordingSender(DryRunWhatsAppSender):
    provider = "waha"

    def send_text(self, phone_e164: str, text: str):
        result = super().send_text(phone_e164, text)
        return type(result)("SENT", "waha", f"wamid-{len(self.sent)}")


def test_job_sends_once_per_day_and_records_outcomes(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "presenze_whatsapp_lookback_days", 3)
    monkeypatch.setattr(settings, "presenze_whatsapp_include_missing_punches", True)
    angelo = _collaborator(db, "SASSU ANGELO", _user(db, "angelo"), "1423")
    unlinked = _collaborator(db, "SPANU SALVATORE", None, "83")
    _record(db, angelo, date(2026, 9, 14), [(time(7, 2), None)])
    _record(db, angelo, date(2026, 9, 11), [(time(7, 2), None)])
    _record(db, angelo, date(2026, 9, 13), [], teo_minutes=390, schedule_code="DOM")
    _record(db, angelo, date(2026, 9, 12), [], teo_minutes=390, schedule_code="OPE")
    _record(db, angelo, date(2026, 9, 15), [(time(7, 0), None)])
    _record(db, unlinked, date(2026, 9, 14), [(None, time(13, 0))])
    inactive = _collaborator(db, "EX DIPENDENTE", _user(db, "ex"), "9")
    inactive.is_active = False
    _record(db, inactive, date(2026, 9, 14), [(time(7, 0), None)])
    db.commit()

    sender = RecordingSender()
    report = job.run_punch_reminder_job(db, sender, _options())

    assert [outcome.status for outcome in report.outcomes] == ["SENT"]
    assert [skip.reason for skip in report.skipped] == ["operator_not_linked"]
    assert (report.deferred, report.halted_reason) == (0, None)
    assert sender.sent[0][0] == "+393331234567"
    message = db.scalar(select(PresenzeWhatsAppMessage))
    assert (message.status, message.provider, message.provider_message_id) == (
        "SENT",
        "waha",
        "wamid-1",
    )
    assert [day["problem"] for day in message.days_json] == ["missing_punches", "missing_exit"]
    assert sorted(day.work_date for day in db.scalars(select(PresenzeWhatsAppNotifiedDay))) == [
        date(2026, 9, 12),
        date(2026, 9, 14),
    ]

    second = job.run_punch_reminder_job(db, RecordingSender(), _options())
    assert second.outcomes == []


def test_job_returns_none_when_lock_is_busy(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    class BusyLock:
        def __enter__(self) -> bool:
            return False

        def __exit__(self, *args) -> None:
            return None

    monkeypatch.setattr(job, "_advisory_lock", lambda session: BusyLock())
    assert job.run_punch_reminder_job(db, RecordingSender(), _options()) is None


def test_reminder_input_marks_validated_and_justified_days(db: Session) -> None:
    user = _user(db, "mario")
    collaborator = _collaborator(db, "ROSSI MARIO", user, "1")
    validated = _record(
        db, collaborator, date(2026, 9, 10), [], validation_status="validated", teo_minutes=390
    )
    ferie = _record(db, collaborator, date(2026, 9, 9), [], request_description="FERIE - Ferie")
    absence = _record(db, collaborator, date(2026, 9, 8), [], teo_minutes=390, absence_minutes=390)
    mismatch = _record(db, collaborator, date(2026, 9, 7), [], application_user_id=999)
    assert job.reminder_input(validated, collaborator, ()).validated is True
    assert job.reminder_input(ferie, collaborator, ()).justified_absence is True
    assert job.reminder_input(absence, collaborator, ()).justified_absence is True
    assert job.reminder_input(mismatch, collaborator, ()).application_user_id is None
    assert job.load_reminder_contacts(db, [None]) == {}
    assert job._punches_by_record(db, []) == {}


def test_record_outcome_skips_notified_days_for_failures_and_dry_run(db: Session) -> None:
    collaborator = _collaborator(db, "ROSSI MARIO", _user(db, "mario"), "1")
    db.commit()
    day = ReminderDay(date(2026, 9, 14), "missing_exit", "uscita mancante (ingresso 07:00)")
    reminder = PunchReminder(collaborator.id, "ROSSI MARIO", 1, "+393331234567", (day,))
    job.record_dispatch_outcome(
        db, "waha", DispatchOutcome(reminder, "t", "FAILED", error_code="http_502")
    )
    job.record_dispatch_outcome(db, "dry_run", DispatchOutcome(reminder, "t", "DRY_RUN"))
    job.record_dispatch_outcome(db, "waha", DispatchOutcome(reminder, "t", "NOT_ON_WHATSAPP"))
    assert [row.status for row in db.scalars(select(PresenzeWhatsAppMessage))] == [
        "FAILED",
        "DRY_RUN",
        "NOT_ON_WHATSAPP",
    ]
    assert len(db.scalars(select(PresenzeWhatsAppNotifiedDay)).all()) == 0


def _message(
    db: Session, provider_message_id: str, status: str = "SENT"
) -> PresenzeWhatsAppMessage:
    collaborator = _collaborator(db, "ROSSI MARIO", None, provider_message_id)
    message = PresenzeWhatsAppMessage(
        collaborator_id=collaborator.id,
        phone_e164="+393331234567",
        text_body="t",
        days_json=[],
        status=status,
        provider="waha",
        provider_message_id=provider_message_id,
    )
    db.add(message)
    db.commit()
    return message


def test_webhook_acks_update_status_without_downgrade(db: Session) -> None:
    message = _message(db, "wamid-1")
    failed = _message(db, "wamid-2")
    job.apply_whatsapp_webhook_events(
        db, [WhatsAppAck("wamid-1", "DELIVERED"), WhatsAppAck("unknown", "READ")], NOW
    )
    assert (message.status, message.delivered_at is not None, message.read_at) == (
        "DELIVERED",
        True,
        None,
    )
    job.apply_whatsapp_webhook_events(
        db, [WhatsAppAck("wamid-1", "READ"), WhatsAppAck("wamid-1", "SENT")]
    )
    assert (message.status, message.read_at is not None) == ("READ", True)
    job.apply_whatsapp_webhook_events(db, [WhatsAppAck("wamid-2", "FAILED")])
    assert (failed.status, failed.error_code) == ("FAILED", "waha_ack_failed")


def test_webhook_opt_out_matches_normalized_profile_phones(db: Session) -> None:
    first = _user(db, "a", phone="+39 333 123 4567")
    second = _user(db, "b", phone="3331234567")
    _user(db, "c", phone="3339999999")
    _user(db, "d", phone=None)
    db.commit()
    job.apply_whatsapp_webhook_events(db, [WhatsAppOptOut("+393331234567", "STOP")])
    job.apply_whatsapp_webhook_events(db, [WhatsAppOptOut("+393331234567", "STOP")])
    assert sorted(
        row.application_user_id for row in db.scalars(select(PresenzeWhatsAppOptOut))
    ) == [first.id, second.id]
    assert job.load_opted_out_user_ids(db) == frozenset({first.id, second.id})


def test_advisory_lock_uses_a_dedicated_transaction() -> None:
    calls: list[str] = []

    class FakeResult:
        def __init__(self, value: bool) -> None:
            self.value = value

        def scalar(self) -> bool:
            return self.value

    class FakeSession:
        def __init__(self, acquired: bool) -> None:
            self.acquired = acquired

        def get_bind(self):
            return self

        dialect = type("Dialect", (), {"name": "postgresql"})()

        def connect(self):
            return self

        def begin(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, statement, params):
            calls.append(str(statement))
            return FakeResult(self.acquired)

    with job._advisory_lock(FakeSession(True)) as acquired:
        assert acquired is True
    with job._advisory_lock(FakeSession(False)) as acquired:
        assert acquired is False
    assert calls == [
        "SELECT pg_try_advisory_xact_lock(:lock_key)",
        "SELECT pg_try_advisory_xact_lock(:lock_key)",
    ]


def test_build_dispatch_options_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "presenze_whatsapp_max_per_run", 7)
    options = job.build_dispatch_options_from_settings()
    assert options.max_per_run == 7
    assert options.now().tzinfo is not None
    fixed = job.build_dispatch_options_from_settings(now=lambda: NOW, sleep=lambda seconds: None)
    assert fixed.now() == NOW


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(webhook_router)

    def override_db() -> Generator[Session, None, None]:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def test_webhook_route_verifies_signature_and_applies_events(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client()
    monkeypatch.setattr(settings, "presenze_whatsapp_waha_hmac_key", "")
    assert client.post("/presenze/whatsapp/webhook", content=b"{}").status_code == 503
    monkeypatch.setattr(settings, "presenze_whatsapp_waha_hmac_key", "secret")
    assert (
        client.post(
            "/presenze/whatsapp/webhook", content=b"{}", headers={"x-webhook-hmac": "bad"}
        ).status_code
        == 401
    )

    def signed(body: bytes) -> dict[str, str]:
        return {"x-webhook-hmac": hmac.new(b"secret", body, hashlib.sha512).hexdigest()}

    assert (
        client.post(
            "/presenze/whatsapp/webhook", content=b"{bad", headers=signed(b"{bad")
        ).status_code
        == 400
    )
    assert (
        client.post("/presenze/whatsapp/webhook", content=b"", headers=signed(b"")).status_code
        == 204
    )
    _message(db, "wamid-9")
    body = json.dumps({"event": "message.ack", "payload": {"id": "wamid-9", "ack": 2}}).encode()
    assert (
        client.post("/presenze/whatsapp/webhook", content=body, headers=signed(body)).status_code
        == 204
    )
    db.expire_all()
    assert db.scalar(select(PresenzeWhatsAppMessage)).status == "DELIVERED"
