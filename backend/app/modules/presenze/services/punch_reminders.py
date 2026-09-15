"""Selezione dei promemoria WhatsApp per timbrature incomplete.

Regole: solo giornate chiuse nella finestra di lookback, solo errori di timbratura
imputabili all'operaio, niente giornate validate o assenze giustificate, identita
esclusivamente tramite ``presenze_collaborators.application_user_id`` (fail closed)
e telefono dal profilo operatore GAIA.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, time
from uuid import UUID

from app.modules.presenze.services.whatsapp_phone import normalize_whatsapp_phone

PROBLEM_MISSING_PUNCHES = "missing_punches"
PROBLEM_MISSING_ENTRY = "missing_entry"
PROBLEM_MISSING_EXIT = "missing_exit"
PROBLEM_DOUBLE_ENTRY = "double_entry"

SKIP_NOT_LINKED = "operator_not_linked"
SKIP_PROFILE_MISSING = "operator_profile_missing"
SKIP_DISABLED = "operator_disabled"
SKIP_OPTED_OUT = "opted_out"
SKIP_PHONE_MISSING = "phone_missing"
SKIP_PHONE_INVALID = "phone_invalid"

_WEEKDAYS = ("lun", "mar", "mer", "gio", "ven", "sab", "dom")


@dataclass(frozen=True)
class PunchPair:
    entry: time | None
    exit: time | None


@dataclass(frozen=True)
class ReminderDayInput:
    collaborator_id: UUID
    collaborator_name: str
    application_user_id: int | None
    work_date: date
    punches: tuple[PunchPair, ...]
    validated: bool = False
    justified_absence: bool = False
    expected_work_day: bool = False


@dataclass(frozen=True)
class ReminderContact:
    application_user_id: int
    phone: str | None
    active: bool


@dataclass(frozen=True)
class ReminderPolicy:
    today: date
    include_missing_punches: bool
    notified: frozenset[tuple[UUID, date]] = frozenset()
    opted_out_user_ids: frozenset[int] = frozenset()


@dataclass(frozen=True)
class ReminderDay:
    work_date: date
    problem: str
    detail: str


@dataclass(frozen=True)
class PunchReminder:
    collaborator_id: UUID
    collaborator_name: str
    application_user_id: int
    phone_e164: str
    days: tuple[ReminderDay, ...]


@dataclass(frozen=True)
class ReminderSkip:
    collaborator_id: UUID
    collaborator_name: str
    application_user_id: int | None
    reason: str
    days: tuple[ReminderDay, ...]


@dataclass
class ReminderSelection:
    reminders: list[PunchReminder] = field(default_factory=list)
    skipped: list[ReminderSkip] = field(default_factory=list)


def reminder_day(item: ReminderDayInput, *, include_missing_punches: bool) -> ReminderDay | None:
    if item.validated or item.justified_absence:
        return None
    visible = [pair for pair in item.punches if pair.entry or pair.exit]
    if visible:
        return _structural_punch_day(item.work_date, visible)
    if include_missing_punches and item.expected_work_day:
        return ReminderDay(item.work_date, PROBLEM_MISSING_PUNCHES, "nessuna timbratura")
    return None


def _structural_punch_day(work_date: date, visible: list[PunchPair]) -> ReminderDay | None:
    open_entries = [pair.entry for pair in visible if pair.entry and not pair.exit]
    if len(open_entries) > 1:
        entries = ", ".join(_clock(value) for value in open_entries)
        return ReminderDay(
            work_date, PROBLEM_DOUBLE_ENTRY, f"due ingressi senza uscita ({entries})"
        )
    orphan_exit = next((pair.exit for pair in visible if pair.exit and not pair.entry), None)
    if orphan_exit:
        return ReminderDay(
            work_date, PROBLEM_MISSING_ENTRY, f"ingresso mancante (uscita {_clock(orphan_exit)})"
        )
    if open_entries:
        return ReminderDay(
            work_date, PROBLEM_MISSING_EXIT, f"uscita mancante (ingresso {_clock(open_entries[0])})"
        )
    return None


def select_punch_reminders(
    items: Iterable[ReminderDayInput],
    contacts: Mapping[int, ReminderContact],
    policy: ReminderPolicy,
) -> ReminderSelection:
    grouped: dict[UUID, tuple[ReminderDayInput, dict[date, ReminderDay]]] = {}
    for item in items:
        if (
            item.work_date >= policy.today
            or (item.collaborator_id, item.work_date) in policy.notified
        ):
            continue
        day = reminder_day(item, include_missing_punches=policy.include_missing_punches)
        if day is not None:
            grouped.setdefault(item.collaborator_id, (item, {}))[1][item.work_date] = day
    selection = ReminderSelection()
    for first, days_by_date in sorted(
        grouped.values(), key=lambda entry: entry[0].collaborator_name
    ):
        days = tuple(days_by_date[key] for key in sorted(days_by_date))
        _append_candidate(selection, first, days, contacts, policy)
    return selection


def build_punch_reminder_text(reminder: PunchReminder) -> str:
    first_name = reminder.collaborator_name.split()[-1].capitalize()
    subject = "questa giornata" if len(reminder.days) == 1 else "queste giornate"
    lines = [f"Ciao {first_name}, per {subject} la timbratura risulta incompleta:"]
    lines += [
        f"• {_WEEKDAYS[day.work_date.weekday()]} {day.work_date:%d/%m}: {day.detail}"
        for day in reminder.days
    ]
    lines += [
        "",
        "Rivolgiti al tuo capo squadra per regolarizzarla.",
        "Messaggio automatico GAIA. Rispondi STOP per non ricevere più questi avvisi.",
    ]
    return "\n".join(lines)


def _append_candidate(
    selection: ReminderSelection,
    item: ReminderDayInput,
    days: tuple[ReminderDay, ...],
    contacts: Mapping[int, ReminderContact],
    policy: ReminderPolicy,
) -> None:
    user_id = item.application_user_id
    contact = contacts.get(user_id) if user_id is not None else None
    reason, phone = _contact_outcome(user_id, contact, policy)
    if reason is not None:
        selection.skipped.append(
            ReminderSkip(item.collaborator_id, item.collaborator_name, user_id, reason, days)
        )
        return
    selection.reminders.append(
        PunchReminder(item.collaborator_id, item.collaborator_name, user_id, phone, days)
    )


def _contact_outcome(
    user_id: int | None, contact: ReminderContact | None, policy: ReminderPolicy
) -> tuple[str | None, str]:
    if user_id is None:
        return SKIP_NOT_LINKED, ""
    if contact is None:
        return SKIP_PROFILE_MISSING, ""
    if not contact.active:
        return SKIP_DISABLED, ""
    if user_id in policy.opted_out_user_ids:
        return SKIP_OPTED_OUT, ""
    if not (contact.phone or "").strip():
        return SKIP_PHONE_MISSING, ""
    phone = normalize_whatsapp_phone(contact.phone)
    return (None, phone) if phone else (SKIP_PHONE_INVALID, "")


def _clock(value: time) -> str:
    return f"{value:%H:%M}"
