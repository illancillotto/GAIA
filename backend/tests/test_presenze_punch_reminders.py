from __future__ import annotations

from datetime import date, time
from uuid import uuid4

from app.modules.presenze.services.punch_reminders import (
    PunchPair,
    PunchReminder,
    ReminderContact,
    ReminderDay,
    ReminderDayInput,
    ReminderPolicy,
    build_punch_reminder_text,
    reminder_day,
    select_punch_reminders,
)
from app.modules.presenze.services.whatsapp_phone import normalize_whatsapp_phone

COLLABORATOR = uuid4()
TODAY = date(2026, 9, 15)


def _item(**overrides) -> ReminderDayInput:
    values = {
        "collaborator_id": COLLABORATOR,
        "collaborator_name": "SASSU ANGELO",
        "application_user_id": 238,
        "work_date": date(2026, 9, 14),
        "punches": (PunchPair(time(7, 2), None),),
    }
    values.update(overrides)
    return ReminderDayInput(**values)


def _contacts(**overrides) -> dict[int, ReminderContact]:
    values = {"application_user_id": 238, "phone": "333 123 4567", "active": True}
    values.update(overrides)
    return {238: ReminderContact(**values)}


def test_normalize_whatsapp_phone_accepts_mobiles_and_rejects_landlines() -> None:
    assert normalize_whatsapp_phone("333 123 4567") == "+393331234567"
    assert normalize_whatsapp_phone("0039 (333) 123-4567") == "+393331234567"
    assert normalize_whatsapp_phone("+44 7700 900123") == "+447700900123"
    assert normalize_whatsapp_phone(None) is None
    assert normalize_whatsapp_phone("abc") is None
    assert normalize_whatsapp_phone("+39 070 123456") is None


def test_reminder_day_describes_structural_punch_problems() -> None:
    assert reminder_day(_item(), include_missing_punches=False) == ReminderDay(
        date(2026, 9, 14), "missing_exit", "uscita mancante (ingresso 07:02)"
    )
    orphan_exit = _item(punches=(PunchPair(None, time(13, 5)),))
    assert (
        reminder_day(orphan_exit, include_missing_punches=False).detail
        == "ingresso mancante (uscita 13:05)"
    )
    double = _item(punches=(PunchPair(time(7, 0), None), PunchPair(time(12, 0), None)))
    assert (
        reminder_day(double, include_missing_punches=False).detail
        == "due ingressi senza uscita (07:00, 12:00)"
    )


def test_reminder_day_ignores_complete_validated_justified_and_rest_days() -> None:
    complete = _item(punches=(PunchPair(time(7, 0), time(13, 0)), PunchPair(None, None)))
    assert reminder_day(complete, include_missing_punches=True) is None
    assert reminder_day(_item(validated=True), include_missing_punches=True) is None
    assert reminder_day(_item(justified_absence=True), include_missing_punches=True) is None
    assert reminder_day(_item(punches=()), include_missing_punches=False) is None
    assert reminder_day(_item(punches=()), include_missing_punches=True) is None
    missing = reminder_day(_item(punches=(), expected_work_day=True), include_missing_punches=True)
    assert missing == ReminderDay(date(2026, 9, 14), "missing_punches", "nessuna timbratura")


def test_select_groups_days_per_collaborator_and_filters_window_and_notified() -> None:
    other = uuid4()
    selection = select_punch_reminders(
        [
            _item(),
            _item(work_date=date(2026, 9, 12), punches=(PunchPair(None, time(13, 0)),)),
            _item(work_date=date(2026, 9, 12), punches=(PunchPair(None, time(13, 10)),)),
            _item(work_date=TODAY),
            _item(work_date=date(2026, 9, 11)),
            _item(collaborator_id=other, punches=(PunchPair(time(7, 0), time(13, 0)),)),
        ],
        _contacts(),
        ReminderPolicy(
            today=TODAY,
            include_missing_punches=False,
            notified=frozenset({(COLLABORATOR, date(2026, 9, 11))}),
        ),
    )
    assert selection.skipped == []
    assert selection.reminders == [
        PunchReminder(
            COLLABORATOR,
            "SASSU ANGELO",
            238,
            "+393331234567",
            (
                ReminderDay(date(2026, 9, 12), "missing_entry", "ingresso mancante (uscita 13:10)"),
                ReminderDay(date(2026, 9, 14), "missing_exit", "uscita mancante (ingresso 07:02)"),
            ),
        )
    ]


def test_select_fails_closed_and_reports_skip_reasons() -> None:
    policy = ReminderPolicy(today=TODAY, include_missing_punches=False)

    def reason(
        item: ReminderDayInput, contacts: dict[int, ReminderContact], active_policy=policy
    ) -> str:
        return select_punch_reminders([item], contacts, active_policy).skipped[0].reason

    assert reason(_item(application_user_id=None), _contacts()) == "operator_not_linked"
    assert reason(_item(), {}) == "operator_profile_missing"
    assert reason(_item(), _contacts(active=False)) == "operator_disabled"
    opted = ReminderPolicy(
        today=TODAY, include_missing_punches=False, opted_out_user_ids=frozenset({238})
    )
    assert reason(_item(), _contacts(), opted) == "opted_out"
    assert reason(_item(), _contacts(phone="  ")) == "phone_missing"
    assert reason(_item(), _contacts(phone=None)) == "phone_missing"
    assert reason(_item(), _contacts(phone="070 123456")) == "phone_invalid"
    ordered = select_punch_reminders(
        [_item(collaborator_id=uuid4(), collaborator_name="ZETA"), _item(collaborator_name="ALFA")],
        {},
        policy,
    )
    assert [skip.collaborator_name for skip in ordered.skipped] == ["ALFA", "ZETA"]


def test_build_punch_reminder_text_is_readable() -> None:
    reminder = PunchReminder(
        COLLABORATOR,
        "SASSU ANGELO",
        238,
        "+393331234567",
        (ReminderDay(date(2026, 9, 14), "missing_exit", "uscita mancante (ingresso 07:02)"),),
    )
    assert build_punch_reminder_text(reminder) == "\n".join(
        [
            "Ciao Angelo, per questa giornata la timbratura risulta incompleta:",
            "• lun 14/09: uscita mancante (ingresso 07:02)",
            "",
            "Rivolgiti al tuo capo squadra per regolarizzarla.",
            "Messaggio automatico GAIA. Rispondi STOP per non ricevere più questi avvisi.",
        ]
    )
    two_days = PunchReminder(
        COLLABORATOR,
        "SASSU ANGELO",
        238,
        "+393331234567",
        (ReminderDay(date(2026, 9, 13), "missing_punches", "nessuna timbratura"), *reminder.days),
    )
    assert (
        "per queste giornate la timbratura risulta incompleta:\n• dom 13/09: nessuna timbratura"
        in build_punch_reminder_text(two_days)
    )
