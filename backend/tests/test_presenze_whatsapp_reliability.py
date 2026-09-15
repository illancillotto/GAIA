from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_presenze_punch_reminder_job import (
    NOW,
    RecordingSender,
    _collaborator,
    _options,
    _record,
    _user,
    db,
    setup_database,
)

from app.modules.operazioni.models.organizational import OperatorProfile
from app.modules.presenze.models import PresenzeDailyPunch
from app.modules.presenze.services import punch_reminder_job as job
from app.modules.presenze.services.punch_reminder_pending import blocked_days, pending_keys
from app.modules.presenze.services.whatsapp_waha import (
    DryRunWhatsAppSender,
    WhatsAppAck,
    WhatsAppOptOut,
    WhatsAppSendError,
)
from app.modules.presenze.whatsapp_models import (
    PresenzeWhatsAppMessage,
    PresenzeWhatsAppNotifiedDay,
)

__all__ = ["db", "setup_database"]


def profile(db, user):
    return db.scalar(select(OperatorProfile).where(OperatorProfile.user_id == user.id))


def seed(db, name="A", day=date(2026, 9, 14)):
    user = _user(db, name, phone="+39333000000" + str(len(name)))
    collaborator = _collaborator(db, name, user, name)
    record = _record(db, collaborator, day, [(time(7), None)])
    db.commit()
    return user, collaborator, record


def test_deferred_days_survive_lookback_and_resolved_days_are_removed(db):
    friday = date(2026, 9, 11)
    seed(db, "A", friday)
    _, second, _ = seed(db, "BB", friday)
    _, corrected, corrected_record = seed(db, "CCC", friday)
    monday = datetime(2026, 9, 14, 8, tzinfo=UTC)
    first = job.run_punch_reminder_job(
        db, RecordingSender(), replace(_options(), now=lambda: monday, max_per_run=1)
    )
    assert first.deferred == 2
    corrected_record.validated_at = NOW
    db.commit()
    sender = RecordingSender()
    # Use a distinct provider ID, as two real WAHA runs would do.
    sender.sent.append(("prior", "prior"))
    report = job.run_punch_reminder_job(db, sender, _options())
    assert [out.reminder.collaborator_id for out in report.outcomes] == [second.id]
    assert (corrected.id, friday) not in pending_keys(db)
    assert pending_keys(db) == set()


def test_not_on_whatsapp_is_not_notified_and_can_retry_after_phone_correction(db):
    user, collaborator, _ = seed(db)
    sender = RecordingSender()
    sender.check_number = lambda phone: False
    result = job.run_punch_reminder_job(db, sender, _options())
    assert result.outcomes[0].status == "NOT_ON_WHATSAPP"
    assert job.load_notified_days(db, date.min) == frozenset()
    assert (collaborator.id, date(2026, 9, 14)) in pending_keys(db)
    profile(db, user).phone = "+393339999999"
    db.commit()
    later = NOW + timedelta(days=7)
    report = job.run_punch_reminder_job(
        db, RecordingSender(), replace(_options(), now=lambda: later)
    )
    assert report.outcomes[0].reminder.phone_e164 == "+393339999999"


@pytest.mark.parametrize("change", ["stop", "validated", "punch", "inactive", "phone", "absence"])
def test_queue_revalidates_after_pause(db, change):
    seed(db, "A")
    user, collaborator, record = seed(db, "BB")

    def pause(seconds):
        if change == "stop":
            job.apply_whatsapp_webhook_events(db, [WhatsAppOptOut(profile(db, user).phone, "STOP")])
        elif change == "validated":
            record.validated_at = NOW
        elif change == "punch":
            db.scalar(
                select(PresenzeDailyPunch).where(PresenzeDailyPunch.daily_record_id == record.id)
            ).exit_time = time(13)
        elif change == "inactive":
            collaborator.is_active = False
        elif change == "phone":
            profile(db, user).phone = None
        else:
            record.request_description = "FERIE - Ferie"
        db.commit()

    sender = RecordingSender()
    report = job.run_punch_reminder_job(db, sender, replace(_options(), sleep=pause))
    assert [out.status for out in report.outcomes] == ["SENT", "CANCELLED"]
    assert len(sender.sent) == 1


def test_revalidates_after_check_number_and_retries_updated_phone_next_run(db):
    user, _, _ = seed(db)
    sender = RecordingSender()

    def check(phone):
        profile(db, user).phone = "+393338888888"
        db.commit()
        return True

    sender.check_number = check
    report = job.run_punch_reminder_job(db, sender, _options())
    assert report.outcomes[0].status == "CANCELLED"
    assert sender.sent == []
    report = job.run_punch_reminder_job(db, RecordingSender(), _options())
    assert report.outcomes[0].reminder.phone_e164 == "+393338888888"


def test_uncertain_send_is_durable_and_never_automatically_retried(db):
    _, collaborator, _ = seed(db)
    seed(db, "BB")

    class Uncertain(RecordingSender):
        def send_text(self, phone, text):
            attempt = db.scalar(select(PresenzeWhatsAppMessage))
            assert attempt.status == "SENDING"
            assert blocked_days(db) == {(collaborator.id, date(2026, 9, 14))}
            raise WhatsAppSendError("timeout", code="network_error", retryable=True, uncertain=True)

    report = job.run_punch_reminder_job(db, Uncertain(), _options())
    assert [out.status for out in report.outcomes] == ["UNKNOWN"]
    assert report.halted_reason == "channel_unavailable"
    attempt = db.scalar(select(PresenzeWhatsAppMessage))
    assert attempt.id == report.outcomes[0].attempt_id
    second = job.run_punch_reminder_job(db, RecordingSender(), _options())
    assert len(second.outcomes) == 1
    assert second.outcomes[0].reminder.collaborator_id != collaborator.id
    assert len(db.scalars(select(PresenzeWhatsAppMessage)).all()) == 2


def test_crash_after_send_leaves_sending_quarantined(db, monkeypatch):
    seed(db)
    original = job.record_dispatch_outcome

    def record(db, provider, outcome):
        if outcome.status == "SENT":
            raise RuntimeError("crash before saving result")
        return original(db, provider, outcome)

    monkeypatch.setattr(job, "record_dispatch_outcome", record)
    with pytest.raises(RuntimeError):
        job.run_punch_reminder_job(db, RecordingSender(), _options())
    assert db.scalar(select(PresenzeWhatsAppMessage)).status == "SENDING"
    monkeypatch.setattr(job, "record_dispatch_outcome", original)
    assert job.run_punch_reminder_job(db, RecordingSender(), _options()).outcomes == []


def test_failed_ack_reopens_day_and_retries_outside_lookback(db):
    seed(db)
    report = job.run_punch_reminder_job(db, RecordingSender(), _options())
    message_id = report.outcomes[0].provider_message_id
    job.apply_whatsapp_webhook_events(db, [WhatsAppAck(message_id, "FAILED")])
    assert job.load_notified_days(db, date.min) == frozenset()
    assert len(pending_keys(db)) == 1
    sender = RecordingSender()
    sender.sent.append(("old", "old"))
    result = job.run_punch_reminder_job(
        db, sender, replace(_options(), now=lambda: NOW + timedelta(days=7))
    )
    assert result.outcomes[0].status == "SENT"
    assert len(job.load_notified_days(db, date.min)) == 1
    # Late delivery from the old attempt must not violate uniqueness or erase newer state.
    job.apply_whatsapp_webhook_events(
        db, [WhatsAppAck(message_id, "READ"), WhatsAppAck(message_id, "FAILED")]
    )
    assert (
        db.scalar(
            select(PresenzeWhatsAppMessage).where(
                PresenzeWhatsAppMessage.provider_message_id == message_id
            )
        ).status
        == "READ"
    )
    assert len(job.load_notified_days(db, date.min)) == 1


def test_early_failed_receipt_is_replayed_after_response(db):
    seed(db)

    class EarlyAck(RecordingSender):
        def send_text(self, phone, text):
            result = super().send_text(phone, text)
            job.apply_whatsapp_webhook_events(
                db, [WhatsAppAck(result.provider_message_id, "FAILED")]
            )
            return result

    job.run_punch_reminder_job(db, EarlyAck(), _options())
    assert db.scalar(select(PresenzeWhatsAppMessage)).status == "FAILED"
    assert job.load_notified_days(db, date.min) == frozenset()
    assert len(pending_keys(db)) == 1


@pytest.mark.parametrize("sent", [False, True])
def test_manual_reconciliation_requires_evidence_and_releases_quarantine(db, sent):
    seed(db)
    job.run_punch_reminder_job(db, DryRunWhatsAppSender(), _options())
    message = db.scalar(select(PresenzeWhatsAppMessage))
    message.status = "UNKNOWN"
    job.link_attempt(db, message)
    db.commit()
    with pytest.raises(ValueError):
        job.reconcile_uncertain_attempt(db, message.id, sent=sent, evidence="")
    with pytest.raises(ValueError):
        job.reconcile_uncertain_attempt(db, message.id, sent=True, evidence="checked")
    job.reconcile_uncertain_attempt(
        db,
        message.id,
        sent=sent,
        evidence="admin: WAHA checked",
        provider_message_id="confirmed" if sent else None,
    )
    assert message.status == ("SENT" if sent else "FAILED")
    assert not blocked_days(db)
    assert bool(job.load_notified_days(db, date.min)) is sent
    with pytest.raises(ValueError):
        job.reconcile_uncertain_attempt(
            db, message.id, sent=sent, evidence="checked", provider_message_id="id"
        )
    with pytest.raises(ValueError):
        job.reconcile_uncertain_attempt(db, uuid4(), sent=False, evidence="checked")


def test_ack_non_downgrade_and_recovery_without_delivery_timestamp_on_sent(db):
    seed(db)
    report = job.run_punch_reminder_job(db, RecordingSender(), _options())
    message = db.scalar(select(PresenzeWhatsAppMessage))
    job._apply_ack(db, WhatsAppAck("absent", "READ"), NOW)
    job._apply_ack(db, WhatsAppAck(message.provider_message_id, "SENT"), NOW)
    job._apply_ack(db, WhatsAppAck(message.provider_message_id, "READ"), NOW)
    job._apply_ack(db, WhatsAppAck(message.provider_message_id, "FAILED"), NOW)
    assert message.status == "READ"
    message.status = "FAILED"
    job._apply_ack(db, WhatsAppAck(message.provider_message_id, "FAILED"), NOW)
    assert message.status == "FAILED"
    db.execute(PresenzeWhatsAppNotifiedDay.__table__.delete())
    message.delivered_at = None
    job._apply_ack(db, WhatsAppAck(report.outcomes[0].provider_message_id, "SENT"), NOW)
    assert message.status == "SENT"
    assert message.delivered_at is None
    db.commit()


def test_manual_reconciliation_refuses_a_busy_job(db, monkeypatch):
    from contextlib import contextmanager

    @contextmanager
    def busy(db):
        yield False

    monkeypatch.setattr(job, "_advisory_lock", busy)
    with pytest.raises(ValueError, match="in corso"):
        job.reconcile_uncertain_attempt(db, uuid4(), sent=False, evidence="checked")
