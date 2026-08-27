from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.services.elaborazioni_batch_statistics import build_batch_statistics


class FakeResult:
    def __init__(self, rows) -> None:
        self.rows = list(rows)

    def all(self):
        return self.rows


class FakeDb:
    def __init__(self, *, events=(), credentials=()) -> None:
        self.events = events
        self.credentials = credentials
        self.scalar_queries = 0

    def execute(self, _statement):
        return FakeResult(self.events)

    def scalars(self, _statement):
        self.scalar_queries += 1
        return FakeResult(self.credentials)


def request(status: str, attempts: int, credential_id: UUID | None = None):
    return SimpleNamespace(
        id=uuid4(),
        status=status,
        attempts=attempts,
        sister_credential_id=credential_id,
    )


def batch(*, started_at: datetime | None, completed_at: datetime | None = None, status: str = "processing"):
    return SimpleNamespace(id=uuid4(), started_at=started_at, completed_at=completed_at, status=status)


def test_build_batch_statistics_reports_live_rates_eta_and_historical_credentials() -> None:
    now = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)
    first_credential_id = uuid4()
    removed_credential_id = uuid4()
    requests = [
        request("completed", 2, first_credential_id),
        request("failed", 1),
        request("pending", -1),
        request("processing", 0),
    ]
    events = [
        (first_credential_id, requests[0].id, now - timedelta(hours=2)),
        (first_credential_id, requests[0].id, now - timedelta(hours=1)),
        (removed_credential_id, requests[1].id, now - timedelta(hours=3)),
        (removed_credential_id, None, now - timedelta(minutes=30)),
        (None, None, now - timedelta(hours=4)),
    ]
    credential = SimpleNamespace(
        id=first_credential_id,
        label="Alessandro",
        sister_username="USR-ALE",
    )

    result = build_batch_statistics(
        FakeDb(events=events, credentials=[credential]),
        batch(started_at=(now - timedelta(hours=2)).replace(tzinfo=None)),
        requests,
        now=now,
    )

    assert result == {
        "duration_seconds": 14400,
        "processed_items": 2,
        "remaining_items": 2,
        "progress_percent": 50.0,
        "success_rate_percent": 50.0,
        "completed_per_hour": 0.25,
        "processed_per_hour": 0.5,
        "estimated_remaining_seconds": 14400,
        "total_attempts": 3,
        "average_attempts": 1.5,
        "credentials_used": [
            {
                "credential_id": first_credential_id,
                "label": "Alessandro",
                "sister_username": "USR-ALE",
                "request_count": 1,
                "execution_count": 2,
            },
            {
                "credential_id": removed_credential_id,
                "label": "Credenziale rimossa",
                "sister_username": None,
                "request_count": 1,
                "execution_count": 2,
            },
        ],
    }


def test_build_batch_statistics_handles_empty_and_completed_batches() -> None:
    now = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)
    empty_db = FakeDb()

    empty = build_batch_statistics(empty_db, batch(started_at=None), [], now=now)

    assert empty["duration_seconds"] == 0
    assert empty["progress_percent"] == 0.0
    assert empty["success_rate_percent"] is None
    assert empty["completed_per_hour"] is None
    assert empty["processed_per_hour"] is None
    assert empty["estimated_remaining_seconds"] == 0
    assert empty["average_attempts"] == 0.0
    assert empty["credentials_used"] == []
    assert empty_db.scalar_queries == 0

    fallback_credential_id = uuid4()
    fallback_request = request("completed", 1, fallback_credential_id)
    fallback_credential = SimpleNamespace(
        id=fallback_credential_id,
        label="Marco",
        sister_username="USR-MARCO",
    )
    fallback = build_batch_statistics(
        FakeDb(credentials=[fallback_credential]),
        batch(started_at=now - timedelta(hours=1), completed_at=now, status="completed"),
        [fallback_request],
    )
    assert fallback["credentials_used"][0]["execution_count"] == 1

    restarted = build_batch_statistics(
        FakeDb(),
        batch(started_at=now - timedelta(hours=4), completed_at=now - timedelta(hours=3)),
        [request("processing", 1)],
        now=now,
    )
    assert restarted["duration_seconds"] == 14400

    completed_request = request("not_found", 0)
    completed = build_batch_statistics(
        FakeDb(events=[(None, None, now + timedelta(hours=2))]),
        batch(started_at=now + timedelta(hours=1), completed_at=now, status="completed"),
        [completed_request],
        now=now + timedelta(hours=3),
    )

    assert completed["duration_seconds"] == 0
    assert completed["progress_percent"] == 100.0
    assert completed["success_rate_percent"] == 0.0
    assert completed["estimated_remaining_seconds"] == 0
