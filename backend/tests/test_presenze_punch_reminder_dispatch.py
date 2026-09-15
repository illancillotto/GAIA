from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from app.modules.presenze.services.punch_reminder_dispatch import (
    DispatchOptions,
    dispatch_punch_reminders,
    is_within_send_window,
)
from app.modules.presenze.services.punch_reminders import PunchReminder, ReminderDay
from app.modules.presenze.services.whatsapp_waha import WhatsAppSendError, WhatsAppSendResult

WORKING_TIME = datetime(2026, 9, 15, 8, 0, tzinfo=UTC)  # martedi 10:00 a Roma


def _reminder(suffix: str) -> PunchReminder:
    day = ReminderDay(date(2026, 9, 14), "missing_exit", "uscita mancante (ingresso 07:00)")
    return PunchReminder(uuid4(), "ROSSI MARIO", int(suffix), "+39333000000" + suffix, (day,))


class FakeSender:
    provider = "waha"

    def __init__(self, check=None, send=None) -> None:
        self.check = check or (lambda phone: True)
        self.send = send or (lambda phone, text: WhatsAppSendResult("SENT", "waha", "id-" + phone))
        self.sent: list[str] = []

    def check_number(self, phone_e164: str) -> bool:
        return self.check(phone_e164)

    def send_text(self, phone_e164: str, text: str) -> WhatsAppSendResult:
        self.sent.append(phone_e164)
        return self.send(phone_e164, text)


def _options(sleeps: list[float], **overrides) -> DispatchOptions:
    values = {"now": lambda: WORKING_TIME, "sleep": sleeps.append, "random": lambda: 0.5}
    values.update(overrides)
    return DispatchOptions(**values)


def test_dispatch_paces_messages_and_caps_the_run() -> None:
    sleeps: list[float] = []
    recorded: list[str] = []
    sender = FakeSender(check=lambda phone: not phone.endswith("2"))
    reminders = [_reminder("1"), _reminder("2"), _reminder("3"), _reminder("4")]
    result = dispatch_punch_reminders(
        reminders,
        sender,
        _options(sleeps, max_per_run=2),
        lambda outcome: recorded.append(outcome.status),
    )
    assert recorded == ["SENT", "NOT_ON_WHATSAPP"]
    assert result.halted_reason == "max_per_run"
    assert result.deferred == reminders[2:]
    assert result.outcomes[0].provider_message_id == "id-+393330000001"
    assert "uscita mancante" in result.outcomes[0].text
    assert sleeps == [50.0]
    assert sender.sent == ["+393330000001"]


def test_dispatch_defers_outside_send_window() -> None:
    evening = datetime(2026, 9, 15, 18, 30, tzinfo=UTC)
    result = dispatch_punch_reminders(
        [_reminder("1")], FakeSender(), _options([], now=lambda: evening), lambda outcome: None
    )
    assert (result.halted_reason, len(result.deferred), result.outcomes) == (
        "outside_send_window",
        1,
        [],
    )


def test_dispatch_halts_on_channel_errors() -> None:
    def broken(phone: str, text: str) -> WhatsAppSendResult:
        raise WhatsAppSendError("session", retryable=False, code="http_422")

    options = _options([], min_delay_seconds=10, max_delay_seconds=5)
    result = dispatch_punch_reminders(
        [_reminder("1"), _reminder("2")], FakeSender(send=broken), options, lambda outcome: None
    )
    assert result.halted_reason == "channel_unavailable"
    assert (
        result.outcomes[0].status,
        result.outcomes[0].error_code,
        result.outcomes[0].error_message,
    ) == ("FAILED", "http_422", "session")
    assert len(result.deferred) == 1


def test_dispatch_halts_after_consecutive_transient_failures_and_resets_on_success() -> None:
    calls = {"count": 0}

    def flaky(phone: str) -> bool:
        calls["count"] += 1
        if calls["count"] == 2:
            return True
        raise WhatsAppSendError("down", retryable=True, code="http_502")

    reminders = [_reminder(str(index)) for index in range(1, 6)]
    result = dispatch_punch_reminders(
        reminders,
        FakeSender(check=flaky),
        _options([], max_consecutive_failures=2),
        lambda outcome: None,
    )
    assert [outcome.status for outcome in result.outcomes] == ["FAILED", "SENT", "FAILED", "FAILED"]
    assert (result.halted_reason, result.deferred) == ("channel_unavailable", reminders[4:])


def test_dispatch_completes_without_halting() -> None:
    result = dispatch_punch_reminders(
        [_reminder("1")], FakeSender(), _options([]), lambda outcome: None
    )
    assert (result.halted_reason, result.deferred, len(result.outcomes)) == (None, [], 1)


def test_send_window_uses_rome_weekday_hours() -> None:
    assert is_within_send_window(datetime(2026, 9, 15, 6, 0, tzinfo=UTC), 8, 19) is True
    assert is_within_send_window(datetime(2026, 9, 15, 5, 59, tzinfo=UTC), 8, 19) is False
    assert is_within_send_window(datetime(2026, 9, 15, 17, 0, tzinfo=UTC), 8, 19) is False
    assert is_within_send_window(datetime(2026, 9, 19, 8, 0, tzinfo=UTC), 8, 19) is False


def test_pause_crossing_end_of_window_defers_without_sending():
    clock = [datetime(2026, 9, 15, 16, 59, 50, tzinfo=UTC)]

    def pause(seconds):
        clock[0] = datetime(2026, 9, 15, 17, 0, 10, tzinfo=UTC)

    sender = FakeSender()
    result = dispatch_punch_reminders(
        [_reminder("1"), _reminder("2")],
        sender,
        _options([], now=lambda: clock[0], sleep=pause),
        lambda outcome: None,
    )
    assert result.halted_reason == "outside_send_window"
    assert len(sender.sent) == 1
