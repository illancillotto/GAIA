"""Job schedulato dei promemoria WhatsApp e applicazione degli eventi webhook WAHA.

I pendenti vengono ricalcolati sui dati correnti. I tentativi SENDING/UNKNOWN
restano in quarantena, senza retry automatici che possano duplicare un invio.
"""

from __future__ import annotations

import logging
import random
import time as time_module
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, or_, select, text, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.organizational import OperatorProfile
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
)
from app.modules.presenze.services.gate_mobile_payloads import canonical_record_gaia_user_id
from app.modules.presenze.services.punch_reminder_dispatch import (
    OUTCOME_FAILED,
    ROME,
    DispatchHooks,
    DispatchOptions,
    DispatchOutcome,
    dispatch_punch_reminders,
)
from app.modules.presenze.services.punch_reminder_pending import (
    blocked_days,
    forget_message_days,
    link_attempt,
    pending_keys,
    reconcile_pending,
)
from app.modules.presenze.services.punch_reminders import (
    PunchPair,
    PunchReminder,
    ReminderContact,
    ReminderDayInput,
    ReminderPolicy,
    ReminderSkip,
    select_punch_reminders,
)
from app.modules.presenze.services.whatsapp_phone import normalize_whatsapp_phone
from app.modules.presenze.services.whatsapp_receipts import matching_receipts, store_receipt
from app.modules.presenze.services.whatsapp_waha import WhatsAppAck, WhatsAppOptOut, WhatsAppSender
from app.modules.presenze.services.xlsm_export import resolve_export_absence_code
from app.modules.presenze.whatsapp_models import (
    PresenzeWhatsAppMessage,
    PresenzeWhatsAppNotifiedDay,
    PresenzeWhatsAppOptOut,
)

logger = logging.getLogger(__name__)

PUNCH_REMINDER_ADVISORY_LOCK_KEY = 2026091501
_REST_SCHEDULE_CODES = {"SAB", "DOM", "RIPTURN"}
_VALIDATED_STATUSES = {"validated", "validata"}
_ACK_RANK = {"SENT": 1, "DRY_RUN": 1, "DELIVERED": 2, "READ": 3}


@dataclass(frozen=True)
class PunchReminderJobReport:
    outcomes: list[DispatchOutcome]
    skipped: list[ReminderSkip]
    deferred: int
    halted_reason: str | None


def run_punch_reminder_job(
    db: Session, sender: WhatsAppSender, options: DispatchOptions
) -> PunchReminderJobReport | None:
    with _advisory_lock(db) as acquired:
        return _run_locked(db, sender, options) if acquired else None


def _run_locked(
    db: Session, sender: WhatsAppSender, options: DispatchOptions
) -> PunchReminderJobReport:
    replay_receipts(db)
    today = options.now().astimezone(ROME).date()
    first_day = today - timedelta(days=max(1, settings.presenze_whatsapp_lookback_days))
    items = load_reminder_inputs(db, first_day, today)
    notified = load_notified_days(db, date.min)
    reconcile_pending(
        db,
        items,
        include_missing=settings.presenze_whatsapp_include_missing_punches,
        notified=notified,
    )
    policy = ReminderPolicy(
        today=today,
        include_missing_punches=settings.presenze_whatsapp_include_missing_punches,
        notified=notified | blocked_days(db),
        opted_out_user_ids=load_opted_out_user_ids(db),
    )
    contacts = load_reminder_contacts(db, {item.application_user_id for item in items})
    selection = select_punch_reminders(items, contacts, policy)
    result = dispatch_punch_reminders(
        selection.reminders,
        sender,
        options,
        lambda outcome: record_dispatch_outcome(db, sender.provider, outcome),
        hooks=DispatchHooks(
            refresh=lambda reminder: refresh_reminder(db, reminder, options.now()),
            begin=lambda reminder, body: (
                record_dispatch_outcome(
                    db, sender.provider, DispatchOutcome(reminder, body, "SENDING")
                ).id
            ),
        ),
    )
    logger.info(
        "Presenze WhatsApp reminders: attempted=%s skipped=%s deferred=%s halted=%s",
        len(result.outcomes),
        len(selection.skipped),
        len(result.deferred),
        result.halted_reason,
    )
    return PunchReminderJobReport(
        result.outcomes, selection.skipped, len(result.deferred), result.halted_reason
    )


def build_dispatch_options_from_settings(
    now: Callable[[], datetime] | None = None,
    sleep: Callable[[float], None] = time_module.sleep,
) -> DispatchOptions:
    return DispatchOptions(
        now=now or (lambda: datetime.now(UTC)),
        sleep=sleep,
        random=random.random,
        min_delay_seconds=settings.presenze_whatsapp_min_delay_seconds,
        max_delay_seconds=settings.presenze_whatsapp_max_delay_seconds,
        max_per_run=settings.presenze_whatsapp_max_per_run,
        start_hour=settings.presenze_whatsapp_send_start_hour,
        end_hour=settings.presenze_whatsapp_send_end_hour,
    )


def load_reminder_inputs(db: Session, first_day: date, today: date) -> list[ReminderDayInput]:
    rows = db.execute(
        select(PresenzeDailyRecord, PresenzeCollaborator)
        .join(PresenzeCollaborator, PresenzeCollaborator.id == PresenzeDailyRecord.collaborator_id)
        .where(
            or_(
                PresenzeDailyRecord.work_date >= first_day,
                tuple_(PresenzeDailyRecord.collaborator_id, PresenzeDailyRecord.work_date).in_(
                    pending_keys(db)
                ),
            ),
            PresenzeDailyRecord.work_date < today,
            PresenzeCollaborator.is_active.is_(True),
        )
    ).all()
    punches = _punches_by_record(db, [record.id for record, _ in rows])
    return [
        reminder_input(record, collaborator, punches.get(record.id, ()))
        for record, collaborator in rows
    ]


def refresh_reminder(db: Session, reminder: PunchReminder, now: datetime) -> PunchReminder | None:
    # End the previous read transaction and discard identity-map snapshots before sending.
    db.rollback()
    today = now.astimezone(ROME).date()
    items = [
        item
        for item in load_reminder_inputs(db, today, today)
        if item.collaborator_id == reminder.collaborator_id
    ]
    policy = ReminderPolicy(
        today=today,
        include_missing_punches=settings.presenze_whatsapp_include_missing_punches,
        notified=load_notified_days(db, date.min) | blocked_days(db),
        opted_out_user_ids=load_opted_out_user_ids(db),
    )
    contacts = load_reminder_contacts(db, {item.application_user_id for item in items})
    candidates = select_punch_reminders(items, contacts, policy).reminders
    return next(iter(candidates), None)


def reminder_input(
    record: PresenzeDailyRecord, collaborator: PresenzeCollaborator, punches: Sequence[PunchPair]
) -> ReminderDayInput:
    user_id = canonical_record_gaia_user_id(record, collaborator)
    return ReminderDayInput(
        collaborator_id=collaborator.id,
        collaborator_name=collaborator.name,
        application_user_id=int(user_id) if user_id is not None else None,
        work_date=record.work_date,
        punches=tuple(punches),
        validated=_is_validated(record),
        justified_absence=_is_justified_absence(record),
        expected_work_day=_is_expected_work_day(record),
    )


def _is_validated(record: PresenzeDailyRecord) -> bool:
    return record.validation_status in _VALIDATED_STATUSES or record.validated_at is not None


def _is_justified_absence(record: PresenzeDailyRecord) -> bool:
    if resolve_export_absence_code(record) is not None:
        return True
    teo_minutes = record.teo_minutes or 0
    return teo_minutes > 0 and (record.absence_minutes or 0) >= teo_minutes


def _is_expected_work_day(record: PresenzeDailyRecord) -> bool:
    schedule_code = (record.schedule_code or "").strip().upper()
    return (record.teo_minutes or 0) > 0 and schedule_code not in _REST_SCHEDULE_CODES


def load_reminder_contacts(
    db: Session, user_ids: Iterable[int | None]
) -> dict[int, ReminderContact]:
    ids = sorted({user_id for user_id in user_ids if user_id is not None})
    if not ids:
        return {}
    rows = db.execute(
        select(OperatorProfile, ApplicationUser)
        .join(ApplicationUser, ApplicationUser.id == OperatorProfile.user_id)
        .where(OperatorProfile.user_id.in_(ids))
    ).all()
    return {
        profile.user_id: ReminderContact(
            profile.user_id, profile.phone, profile.is_active and user.is_active
        )
        for profile, user in rows
    }


def load_notified_days(db: Session, first_day: date) -> frozenset[tuple[UUID, date]]:
    rows = db.execute(
        select(
            PresenzeWhatsAppNotifiedDay.collaborator_id, PresenzeWhatsAppNotifiedDay.work_date
        ).where(PresenzeWhatsAppNotifiedDay.work_date >= first_day)
    ).all()
    return frozenset((collaborator_id, work_date) for collaborator_id, work_date in rows)


def load_opted_out_user_ids(db: Session) -> frozenset[int]:
    return frozenset(db.scalars(select(PresenzeWhatsAppOptOut.application_user_id)).all())


def record_dispatch_outcome(
    db: Session, provider: str, outcome: DispatchOutcome
) -> PresenzeWhatsAppMessage:
    message = db.get(PresenzeWhatsAppMessage, outcome.attempt_id) if outcome.attempt_id else None
    if message is None:
        message = _new_message(provider, outcome)
        db.add(message)
    message.status = outcome.status
    message.provider_message_id = outcome.provider_message_id
    message.error_code = outcome.error_code
    message.error_message = outcome.error_message
    db.flush()
    if outcome.status == "SENDING":
        link_attempt(db, message)
    if outcome.status == "SENT":
        _mark_notified(db, message)
        forget_message_days(db, message.id)
    replay_receipts(db)
    db.commit()
    return message


def _new_message(provider: str, outcome: DispatchOutcome) -> PresenzeWhatsAppMessage:
    reminder = outcome.reminder
    return PresenzeWhatsAppMessage(
        collaborator_id=reminder.collaborator_id,
        application_user_id=reminder.application_user_id,
        phone_e164=reminder.phone_e164,
        text_body=outcome.text,
        days_json=[
            {"work_date": day.work_date.isoformat(), "problem": day.problem, "detail": day.detail}
            for day in reminder.days
        ],
        status=outcome.status,
        provider=provider,
        provider_message_id=outcome.provider_message_id,
        error_code=outcome.error_code,
        error_message=outcome.error_message,
    )


def reconcile_uncertain_attempt(
    db: Session,
    attempt_id: UUID,
    *,
    sent: bool,
    evidence: str,
    provider_message_id: str | None = None,
) -> None:
    """Administrative recovery after checking WAHA; never called by automatic retries."""
    if not evidence.strip() or (sent and not provider_message_id):
        raise ValueError("Documentare la verifica WAHA e l'ID degli invii confermati")
    with _advisory_lock(db) as acquired:
        if not acquired:
            raise ValueError("Job promemoria in corso")
        message = db.scalar(
            select(PresenzeWhatsAppMessage)
            .where(PresenzeWhatsAppMessage.id == attempt_id)
            .with_for_update()
        )
        if message is None or message.status not in {"SENDING", "UNKNOWN"}:
            raise ValueError("Il tentativo non richiede riconciliazione")
        message.status = "SENT" if sent else "FAILED"
        message.provider_message_id = provider_message_id
        message.error_code = "manual_reconciliation"
        message.error_message = evidence.strip()
        if sent:
            _mark_notified(db, message)
            forget_message_days(db, message.id)
        db.flush()
        replay_receipts(db)
        db.commit()


def _mark_notified(db: Session, message: PresenzeWhatsAppMessage) -> None:
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
    for day in message.days_json:
        db.execute(
            insert(PresenzeWhatsAppNotifiedDay)
            .values(
                collaborator_id=message.collaborator_id,
                work_date=date.fromisoformat(day["work_date"]),
                problem=day["problem"],
                message_id=message.id,
            )
            .on_conflict_do_nothing()
        )


def apply_whatsapp_webhook_events(
    db: Session, events: Iterable[WhatsAppAck | WhatsAppOptOut], now: datetime | None = None
) -> None:
    moment = now or datetime.now(UTC)
    for event in events:
        if isinstance(event, WhatsAppAck):
            store_receipt(db, event, moment)
        else:
            _apply_opt_out(db, event)
    replay_receipts(db)
    db.commit()


def replay_receipts(db: Session) -> None:
    for receipt in matching_receipts(db):
        _apply_ack(
            db, WhatsAppAck(receipt.provider_message_id, receipt.status), receipt.received_at
        )
    db.flush()


def _apply_ack(db: Session, event: WhatsAppAck, moment: datetime) -> None:
    message = db.scalar(
        select(PresenzeWhatsAppMessage)
        .where(PresenzeWhatsAppMessage.provider_message_id == event.provider_message_id)
        .with_for_update()
    )
    if message is None:
        return
    if event.status == "FAILED":
        if message.status in {"DELIVERED", "READ", "FAILED"}:
            return
        message.status = OUTCOME_FAILED
        message.error_code = "waha_ack_failed"
        db.execute(
            delete(PresenzeWhatsAppNotifiedDay).where(
                PresenzeWhatsAppNotifiedDay.message_id == message.id
            )
        )
        link_attempt(db, message)
        return
    if _ACK_RANK.get(event.status, 0) <= _ACK_RANK.get(message.status, 0):
        return
    if message.status in {"FAILED", "SENDING", "UNKNOWN"}:
        _mark_notified(db, message)
        forget_message_days(db, message.id)
    message.status = event.status
    if event.status in {"DELIVERED", "READ"}:
        message.delivered_at = message.delivered_at or moment
    if event.status == "READ":
        message.read_at = moment


def _apply_opt_out(db: Session, event: WhatsAppOptOut) -> None:
    opted_out = set(load_opted_out_user_ids(db))
    for profile in db.scalars(
        select(OperatorProfile).where(OperatorProfile.phone.is_not(None))
    ).all():
        if (
            profile.user_id in opted_out
            or normalize_whatsapp_phone(profile.phone) != event.phone_e164
        ):
            continue
        db.add(
            PresenzeWhatsAppOptOut(
                application_user_id=profile.user_id,
                phone_e164=event.phone_e164,
                source="whatsapp_reply",
            )
        )
        opted_out.add(profile.user_id)
    logger.info("Presenze WhatsApp opt-out received from %s", event.phone_e164)


def _punches_by_record(db: Session, record_ids: list[UUID]) -> dict[UUID, list[PunchPair]]:
    if not record_ids:
        return {}
    result: dict[UUID, list[PunchPair]] = {}
    punches = db.scalars(
        select(PresenzeDailyPunch)
        .where(PresenzeDailyPunch.daily_record_id.in_(record_ids))
        .order_by(PresenzeDailyPunch.daily_record_id, PresenzeDailyPunch.sequence)
    ).all()
    for punch in punches:
        result.setdefault(punch.daily_record_id, []).append(
            PunchPair(punch.entry_time, punch.exit_time)
        )
    return result


@contextmanager
def _advisory_lock(db: Session) -> Iterator[bool]:
    # Dedicated connection: application commits cannot release or migrate this lock.
    if db.get_bind().dialect.name != "postgresql":
        yield True
        return
    params = {"lock_key": PUNCH_REMINDER_ADVISORY_LOCK_KEY}
    with db.get_bind().connect() as connection, connection.begin():
        acquired = connection.execute(
            text("SELECT pg_try_advisory_xact_lock(:lock_key)"), params
        ).scalar()
        yield bool(acquired)
