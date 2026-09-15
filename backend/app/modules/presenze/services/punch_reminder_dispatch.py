"""Invio dosato dei promemoria: con un canale non ufficiale il blocco del numero
arriva da volumi e ritmi da bot. Pochi messaggi per esecuzione, pause casuali,
solo in orario lavorativo, niente invii a numeri senza WhatsApp e stop immediato
quando la sessione non risponde.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from app.modules.presenze.services.punch_reminders import PunchReminder, build_punch_reminder_text
from app.modules.presenze.services.whatsapp_waha import WhatsAppSender, WhatsAppSendError

ROME = ZoneInfo("Europe/Rome")
OUTCOME_NOT_ON_WHATSAPP = "NOT_ON_WHATSAPP"
OUTCOME_FAILED = "FAILED"
HALT_MAX_PER_RUN = "max_per_run"
HALT_OUTSIDE_WINDOW = "outside_send_window"
HALT_CHANNEL = "channel_unavailable"
# 401/403: API key errata; 404/422: sessione assente o da ricollegare via QR.
_CHANNEL_ERROR_CODES = {"http_401", "http_403", "http_404", "http_422"}


@dataclass(frozen=True)
class DispatchOptions:
    now: Callable[[], datetime]
    sleep: Callable[[float], None]
    random: Callable[[], float]
    min_delay_seconds: float = 25
    max_delay_seconds: float = 75
    max_per_run: int = 40
    start_hour: int = 8
    end_hour: int = 19
    max_consecutive_failures: int = 3


@dataclass(frozen=True)
class DispatchOutcome:
    reminder: PunchReminder
    text: str
    status: str
    provider_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    attempt_id: UUID | None = None


@dataclass(frozen=True)
class DispatchHooks:
    refresh: Callable[[PunchReminder], PunchReminder | None]
    begin: Callable[[PunchReminder, str], UUID]


@dataclass(frozen=True)
class DispatchResult:
    outcomes: list[DispatchOutcome]
    deferred: list[PunchReminder]
    halted_reason: str | None


def dispatch_punch_reminders(
    reminders: Sequence[PunchReminder],
    sender: WhatsAppSender,
    options: DispatchOptions,
    on_outcome: Callable[[DispatchOutcome], None],
    hooks: DispatchHooks | None = None,
) -> DispatchResult:
    outcomes: list[DispatchOutcome] = []
    failures = 0
    for index, reminder in enumerate(reminders):
        halted = _halt_before_send(index, failures, options, outcomes)
        if halted:
            return DispatchResult(outcomes, list(reminders[index:]), halted)
        if index:
            options.sleep(_pause_seconds(options))
        if not is_within_send_window(options.now(), options.start_hour, options.end_hour):
            return DispatchResult(outcomes, list(reminders[index:]), HALT_OUTSIDE_WINDOW)
        outcome = _send_one(reminder, sender, hooks)
        on_outcome(outcome)
        outcomes.append(outcome)
        failures = failures + 1 if outcome.status == OUTCOME_FAILED else 0
    return DispatchResult(outcomes, [], None)


def is_within_send_window(now: datetime, start_hour: int, end_hour: int) -> bool:
    local = now.astimezone(ROME)
    return local.weekday() < 5 and start_hour <= local.hour < end_hour


def _halt_before_send(
    index: int, failures: int, options: DispatchOptions, outcomes: list[DispatchOutcome]
) -> str | None:
    last = outcomes[-1] if outcomes else None
    if last and last.status == "UNKNOWN":
        return HALT_CHANNEL
    if failures >= options.max_consecutive_failures or (
        last and last.error_code in _CHANNEL_ERROR_CODES
    ):
        return HALT_CHANNEL
    if index >= options.max_per_run:
        return HALT_MAX_PER_RUN
    if not is_within_send_window(options.now(), options.start_hour, options.end_hour):
        return HALT_OUTSIDE_WINDOW
    return None


def _pause_seconds(options: DispatchOptions) -> float:
    span = max(0.0, options.max_delay_seconds - options.min_delay_seconds)
    return options.min_delay_seconds + options.random() * span


def _send_one(
    reminder: PunchReminder, sender: WhatsAppSender, hooks: DispatchHooks | None = None
) -> DispatchOutcome:
    if hooks:
        refreshed = hooks.refresh(reminder)
        if refreshed is None:
            return DispatchOutcome(reminder, "", "CANCELLED")
        reminder = refreshed
    text = build_punch_reminder_text(reminder)
    attempt_id = None
    try:
        if not sender.check_number(reminder.phone_e164):
            return DispatchOutcome(reminder, text, OUTCOME_NOT_ON_WHATSAPP)
        if hooks:
            if hooks.refresh(reminder) != reminder:
                return DispatchOutcome(reminder, "", "CANCELLED")
            attempt_id = hooks.begin(reminder, text)
        result = sender.send_text(reminder.phone_e164, text)
    except WhatsAppSendError as exc:
        return DispatchOutcome(
            reminder,
            text,
            "UNKNOWN" if exc.uncertain else OUTCOME_FAILED,
            error_code=exc.code,
            error_message=str(exc),
            attempt_id=attempt_id,
        )
    return DispatchOutcome(
        reminder,
        text,
        result.status,
        provider_message_id=result.provider_message_id,
        attempt_id=attempt_id,
    )
