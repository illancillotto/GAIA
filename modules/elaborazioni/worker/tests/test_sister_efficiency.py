import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from scripts.sister_autosync_efficiency import report, scheduled_intervals, summarize, union_seconds

import sister_observability as observed
from sister_observability import BrowserTelemetryAdapter


def test_measurement_unions_overlapping_events_and_clips_to_calendar():
    start = datetime(2026, 9, 28, 13, tzinfo=UTC)
    end = start + timedelta(hours=2)
    profile = {
        "schedule_enabled": True,
        "availability_schedule": {"weekly": {"0": [{"start": "15:00", "end": "16:00"}]}},
    }
    request_id = uuid4()

    def event(kind, at, duration=0, cooldown=0):
        return SimpleNamespace(
            id=uuid4(),
            request_id=request_id,
            event_type=kind,
            occurred_at=at,
            outcome="success",
            duration_ms=duration,
            cooldown_seconds=cooldown,
        )

    events = [
        event("download", start),
        event("download", start + timedelta(minutes=1)),
        event("login", start + timedelta(minutes=10), 600_000),
        event("authentication_gate", start + timedelta(minutes=10), 600_000),
        event("polling", start + timedelta(minutes=30), 600_000),
        event("cooldown", start + timedelta(minutes=50), cooldown=1200),
        event("trace", start),
    ]
    result = summarize(profile, events, start, end)
    assert result["pdf"] == 1
    assert result["scheduled_hours"] == 1
    assert result["outside_schedule_hours"] == 1
    assert result["pdf_per_scheduled_hour"] == 1
    assert result["observed_hours_within_schedule"] == {
        "login": 0.167,
        "remote_poll": 0.167,
        "cooldown": 0.167,
    }
    assert summarize({"schedule_enabled": True}, [], start, end)["pdf_per_scheduled_hour"] is None
    assert union_seconds([]) == 0
    assert len(scheduled_intervals({}, start.replace(second=30), start + timedelta(minutes=1))) == 1


@pytest.mark.parametrize(
    "exception", [observed.DocumentNotYetProducedError, observed.SisterDocumentNotReadyError]
)
def test_expected_remote_wait_is_not_a_portal_error(exception):
    browser = SimpleNamespace(poll_richieste_for_download=AsyncMock(side_effect=exception()))
    adapter = BrowserTelemetryAdapter(browser)
    adapter._wrap_async("poll_richieste_for_download", "polling", "poll_requests")
    with pytest.raises(exception):
        asyncio.run(browser.poll_richieste_for_download())
    assert adapter.pending[0].outcome == "waiting"
    assert adapter.pending[0].severity == "info"


def test_current_calendar_report_validates_campaign_and_duplicates():
    start = datetime.now(UTC)
    end = start + timedelta(hours=1)

    class DB:
        config = None
        accounts = []

        def scalar(self, _query):
            return self.config

        def scalars(self, query):
            if "catasto_credentials" in str(query):
                return self.accounts
            return SimpleNamespace(all=lambda: [])

    db = DB()
    with pytest.raises(ValueError, match="campagna"):
        report(db, 1, start, end)
    first, second = uuid4(), uuid4()
    db.config = SimpleNamespace(
        enabled=True,
        credential_profiles={str(first): {"enabled": True}, str(second): {"enabled": True}},
    )
    db.accounts = [
        SimpleNamespace(id=first, label="A", sister_username="a", active=True),
        SimpleNamespace(id=second, label="B", sister_username="a", active=False),
    ]
    with pytest.raises(ValueError, match="duplicati"):
        report(db, 1, start, end)
    db.accounts[1].sister_username = "b"
    result = report(db, 1, start, end)
    assert result["lease_occupancy"] == "unknown"
    assert result["accounts"][0]["scheduled_hours"] == 1
    assert result["accounts"][1]["scheduled_hours"] == 0


def test_command_enters_read_only_transaction(monkeypatch, capsys):
    import runpy
    import sys
    from unittest.mock import MagicMock

    import app.core.database as database

    session = MagicMock()
    session.__enter__.return_value = session
    session.scalar.return_value = SimpleNamespace(
        enabled=True, credential_profiles={str(uuid4()): {"enabled": True}}
    )
    session.scalars.return_value = []
    monkeypatch.setattr(database, "SessionLocal", lambda: session)
    monkeypatch.setattr(sys, "argv", ["report", "--user-id", "1", "--hours", "24"])
    runpy.run_module("scripts.sister_autosync_efficiency", run_name="__main__")
    assert str(session.execute.call_args.args[0]) == "SET TRANSACTION READ ONLY"
    assert '"accounts": []' in capsys.readouterr().out


def test_remote_wait_separates_poll_work_from_waiting_for_next_execution():
    start = datetime.now(UTC)

    def event(kind, minute, request, outcome="success"):
        return SimpleNamespace(
            id=uuid4(),
            request_id=request,
            event_type=kind,
            occurred_at=start + timedelta(minutes=minute),
            outcome=outcome,
            duration_ms=0,
            cooldown_seconds=0,
        )

    events = [
        event("polling", 0, "a", "waiting"),
        event("polling", 1, "a", "waiting"),
        event("execution_start", 10, "a"),
        event("polling", 20, "b", "waiting"),
    ]
    result = summarize({}, events, start, start + timedelta(hours=1))
    assert result["observed_remote_wait_hours"] == 0.833
