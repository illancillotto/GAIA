from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.modules.elaborazioni.capacitas.apps.incass.client import CapacitasInCassSessionExpiredError
from app.modules.elaborazioni.capacitas.export_http import ExportStepError, SessionExpiredError
from app.services.capacitas_ruoli_export_retry import RetryPolicy, is_retryable, is_session_error
from app.services.capacitas_ruoli_export_state import (
    STATUS_COMPLETED,
    STATUS_PARTIAL,
    ExportRunState,
    ExportStateStore,
    WeeklySchedule,
)
from app.services.google_drive import GoogleDriveError


def http_status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://x.test")
    return httpx.HTTPStatusError(
        "boom", request=request, response=httpx.Response(status, request=request)
    )


@pytest.mark.parametrize(
    ("exc", "retryable"),
    [
        (SessionExpiredError("s"), True),
        (CapacitasInCassSessionExpiredError("s"), True),
        (ExportStepError("x"), True),
        (ExportStepError("x", retryable=False), False),
        (GoogleDriveError("d", retryable=True), True),
        (GoogleDriveError("d", retryable=False), False),
        (http_status_error(503), True),
        (http_status_error(429), True),
        (http_status_error(404), False),
        (httpx.ReadTimeout("t"), True),
        (ValueError("v"), False),
    ],
)
def test_is_retryable(exc, retryable):
    assert is_retryable(exc) is retryable


def test_is_session_error():
    assert is_session_error(SessionExpiredError("x")) is True
    assert is_session_error(ExportStepError("x")) is False


def make_policy(max_attempts: int = 3) -> tuple[RetryPolicy, list[float]]:
    delays: list[float] = []

    async def sleep(seconds: float) -> None:
        delays.append(seconds)

    return RetryPolicy(max_attempts=max_attempts, base_delay_seconds=10, sleep=sleep), delays


def test_retry_backs_off_and_relogs_on_session_loss():
    policy, delays = make_policy()
    errors = [SessionExpiredError("expired"), httpx.ConnectError("down")]
    relogins: list[int] = []

    async def operation() -> str:
        if errors:
            raise errors.pop(0)
        return "ok"

    async def relogin() -> None:
        relogins.append(1)

    assert asyncio.run(policy.run(operation, label="t", on_session_lost=relogin)) == "ok"
    assert delays == [10, 20]
    assert relogins == [1]


def test_retry_stops_on_permanent_error_and_after_max_attempts():
    policy, delays = make_policy(max_attempts=2)

    async def permanent() -> None:
        raise ExportStepError("no", retryable=False)

    async def transient() -> None:
        raise httpx.ConnectError("down")

    with pytest.raises(ExportStepError):
        asyncio.run(policy.run(permanent, label="p"))
    assert delays == []
    with pytest.raises(httpx.ConnectError):
        asyncio.run(policy.run(transient, label="t"))
    assert delays == [10]


def test_session_loss_without_relogin_callback_still_retries():
    policy, _ = make_policy()
    errors = [SessionExpiredError("expired")]

    async def operation() -> int:
        if errors:
            raise errors.pop(0)
        return 1

    assert asyncio.run(policy.run(operation, label="t")) == 1


SUNDAY_7 = WeeklySchedule(weekday=6, hour=7, timezone="Europe/Rome")


@pytest.mark.parametrize(
    ("now", "label"),
    [
        (datetime(2026, 11, 1, 6, 30, tzinfo=UTC), "2026-11-01"),  # 07:30 Rome: slot started
        (datetime(2026, 11, 1, 5, 59, tzinfo=UTC), "2026-10-25"),  # 06:59 Rome: still last week
        (datetime(2026, 10, 30, 12, 0, tzinfo=UTC), "2026-10-25"),  # Friday
        (datetime(2026, 11, 2, 0, 0, tzinfo=UTC), "2026-11-01"),  # Monday
    ],
)
def test_weekly_schedule_snapshot_label(now, label):
    assert SUNDAY_7.snapshot_label(now) == label


def test_run_state_lifecycle_and_due_rules():
    now = datetime(2026, 11, 1, 8, 0, tzinfo=UTC)
    retry_after = timedelta(hours=1)
    state = ExportRunState()
    assert state.is_due("2026-11-01", now, retry_after) is True

    state.start("2026-11-01", now)
    state.record("a.xlsx", {"status": "uploaded"})
    state.record("b.xlsx", {"status": "failed"})
    state.finish()
    assert state.status == STATUS_PARTIAL
    assert state.is_done("a.xlsx") and not state.is_done("b.xlsx") and not state.is_done("c.xlsx")
    assert state.is_due("2026-11-01", now + timedelta(minutes=30), retry_after) is False
    assert state.is_due("2026-11-01", now + timedelta(hours=1), retry_after) is True

    state.start("2026-11-01", now)
    assert "a.xlsx" in state.items
    state.record("b.xlsx", {"status": "empty"})
    state.finish()
    assert state.status == STATUS_COMPLETED
    assert state.is_due("2026-11-01", now, retry_after) is False
    assert state.is_due("2026-11-08", now, retry_after) is True

    state.start("2026-11-08", now)
    assert state.items == {}


def test_partial_state_without_attempt_time_is_due():
    state = ExportRunState(snapshot="s", status=STATUS_PARTIAL)
    assert state.is_due("s", datetime.now(UTC), timedelta(hours=1)) is True


def test_state_store_roundtrip(tmp_path):
    store = ExportStateStore(tmp_path / "nested" / "incass.json")
    assert store.load() == ExportRunState()
    state = ExportRunState(
        snapshot="2026-11-01", status=STATUS_PARTIAL, items={"a": {"status": "uploaded"}}
    )

    store.save(state)

    assert store.load() == state
    assert not (tmp_path / "nested" / "incass.tmp").exists()
