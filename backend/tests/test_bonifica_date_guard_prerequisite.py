from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.models.wc_sync_job import WCSyncJob
from app.modules.elaborazioni.bonifica_oristanese.models import BonificaSyncRunRequest
from app.modules.operazioni.models.vehicles import Vehicle
from app.services import elaborazioni_bonifica_sync as sync_service

DATE_ENTITIES = ("reports", "refuels", "taken_charge", "warehouse_requests")


@pytest.fixture
def sync_db(monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    monkeypatch.setattr(sync_service.settings, "wc_sync_default_days", 30)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[ApplicationUser.__table__, WCSyncJob.__table__, Vehicle.__table__],
    )
    statements: list[tuple[str, object]] = []

    def record_select(_connection, _cursor, statement, parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append((statement, parameters))

    event.listen(engine, "before_cursor_execute", record_select)
    try:
        with Session(engine, expire_on_commit=False) as session:
            session.info["select_statements"] = statements
            yield session
    finally:
        event.remove(engine, "before_cursor_execute", record_select)
        engine.dispose()


def persisted_job(
    sync_db: Session,
    *,
    entity: str = "reports",
    params: dict | None = None,
    started_at: datetime | None = None,
    status: str = "completed",
) -> WCSyncJob:
    job = WCSyncJob(
        entity=entity,
        status=status,
        params_json=params,
        started_at=started_at or datetime.now(UTC),
    )
    sync_db.add(job)
    sync_db.commit()
    sync_db.info["select_statements"].clear()
    return job


@pytest.mark.parametrize("entity", DATE_ENTITIES)
@pytest.mark.parametrize("request_kind", ["string", "list"])
@pytest.mark.parametrize(
    "stored_case",
    ["absent", "empty", "malformed", "non_string", "bounded", "only_start", "only_end"],
)
def test_date_aware_inheritance_always_has_two_dates(
    sync_db: Session, entity: str, request_kind: str, stored_case: str
) -> None:
    end = date.today() - timedelta(days=2)
    start = end - timedelta(days=5)
    examples = {
        "absent": (None, date.today() - timedelta(days=30), date.today()),
        "empty": ({}, date.today() - timedelta(days=30), date.today()),
        "malformed": (
            {"date_from": "not-a-date", "date_to": "2026-99-99"},
            date.today() - timedelta(days=30),
            date.today(),
        ),
        "non_string": (
            {"date_from": 7, "date_to": []},
            date.today() - timedelta(days=30),
            date.today(),
        ),
        "bounded": ({"date_from": start.isoformat(), "date_to": end.isoformat()}, start, end),
        "only_start": ({"date_from": start.isoformat()}, start, date.today()),
        "only_end": ({"date_to": end.isoformat()}, end - timedelta(days=30), end),
    }
    params, expected_start, expected_end = examples[stored_case]
    job = persisted_job(sync_db, entity=entity, params=params)
    request = BonificaSyncRunRequest(entities=entity if request_kind == "string" else [entity])

    inherited = sync_service._resolve_date_window_from_job(job, entity)
    assert inherited == (expected_start, expected_end)
    assert all(isinstance(value, date) for value in inherited)
    assert sync_service._resolve_job_params(sync_db, request, entity) == {
        "date_from": expected_start.isoformat(),
        "date_to": expected_end.isoformat(),
    }
    assert len(sync_db.info["select_statements"]) == 1
    assert job.params_json == params
    assert job.status == "completed"
    assert not sync_db.dirty
    assert not sync_db.new


@pytest.mark.parametrize("status", ["queued", "running", "completed", "failed"])
def test_inheritance_selects_latest_same_entity_without_status_filter(
    sync_db: Session, status: str
) -> None:
    now = datetime.now(UTC)
    end = date.today() - timedelta(days=1)
    latest = {"date_from": (end - timedelta(days=3)).isoformat(), "date_to": end.isoformat()}
    persisted_job(sync_db, params={}, started_at=now - timedelta(days=4))
    chosen = persisted_job(
        sync_db, params=latest, started_at=now - timedelta(days=2), status=status
    )
    persisted_job(sync_db, entity="users", params={}, started_at=now)

    result = sync_service._resolve_job_params(
        sync_db, BonificaSyncRunRequest(entities=["reports"]), "reports"
    )

    assert result == latest
    assert chosen.status == status
    statement, parameters = sync_db.info["select_statements"][0]
    assert len(sync_db.info["select_statements"]) == 1
    assert "ORDER BY wc_sync_job.started_at DESC" in statement
    assert "LIMIT" in statement
    assert parameters == ("reports", 1, 0)
    assert "wc_sync_job.status =" not in statement


@pytest.mark.parametrize("entity", DATE_ENTITIES)
def test_missing_job_preserves_default_window(sync_db: Session, entity: str) -> None:
    result = sync_service._resolve_job_params(
        sync_db, BonificaSyncRunRequest(entities=entity), entity
    )

    assert result == {
        "date_from": (date.today() - timedelta(days=30)).isoformat(),
        "date_to": date.today().isoformat(),
    }
    assert len(sync_db.info["select_statements"]) == 1


@pytest.mark.parametrize(
    "entity", ["report_types", "vehicles", "users", "areas", "org_charts", "consorziati"]
)
def test_non_date_aware_entity_does_not_inherit(sync_db: Session, entity: str) -> None:
    job = persisted_job(sync_db, entity=entity, params={"date_from": "invalid"})
    assert sync_service._resolve_date_window_from_job(job, entity) == (None, None)
    assert sync_service._resolve_job_params(
        sync_db, BonificaSyncRunRequest(entities=entity), entity
    ) == {"date_from": None, "date_to": None}
    assert sync_db.info["select_statements"] == []


@pytest.mark.parametrize("request_case", ["only_start", "only_end", "bounded", "all", "multiple"])
def test_explicit_or_multi_entity_window_bypasses_invalid_latest_job(
    sync_db: Session, request_case: str
) -> None:
    today = date.today()
    persisted_job(
        sync_db,
        params={"date_from": today.isoformat(), "date_to": (today - timedelta(days=1)).isoformat()},
    )
    requests = {
        "only_start": BonificaSyncRunRequest(entities="reports", date_from=today),
        "only_end": BonificaSyncRunRequest(entities="reports", date_to=today),
        "bounded": BonificaSyncRunRequest(entities=["reports"], date_from=today, date_to=today),
        "all": BonificaSyncRunRequest(entities="all"),
        "multiple": BonificaSyncRunRequest(entities=["reports", "users"]),
    }
    expected = {
        "date_from": (
            today.isoformat()
            if request_case in {"only_start", "bounded"}
            else (today - timedelta(days=30)).isoformat()
        ),
        "date_to": today.isoformat(),
    }

    assert sync_service._resolve_job_params(sync_db, requests[request_case], "reports") == expected
    assert sync_db.info["select_statements"] == []


@pytest.mark.parametrize("inherited", [False, True])
def test_inverted_window_raises_without_mutation(sync_db: Session, inherited: bool) -> None:
    today = date.today()
    params = {"date_from": today.isoformat(), "date_to": (today - timedelta(days=1)).isoformat()}
    job = persisted_job(sync_db, params=params)
    request = BonificaSyncRunRequest(
        entities="reports",
        date_from=None if inherited else today,
        date_to=None if inherited else today - timedelta(days=1),
    )

    with pytest.raises(RuntimeError, match="`date_from` non può essere successiva a `date_to`"):
        sync_service._resolve_job_params(sync_db, request, "reports")

    assert len(sync_db.info["select_statements"]) == int(inherited)
    assert job.params_json == params
    assert not sync_db.dirty


def test_inherited_date_underflow_raises_instead_of_returning_none(sync_db: Session) -> None:
    job = persisted_job(sync_db, params={"date_to": date.min.isoformat()})

    with pytest.raises(OverflowError):
        sync_service._resolve_job_params(
            sync_db, BonificaSyncRunRequest(entities="reports"), "reports"
        )

    assert len(sync_db.info["select_statements"]) == 1
    assert job.params_json == {"date_to": date.min.isoformat()}
    assert not sync_db.dirty


def test_invalid_request_date_fails_at_real_request_validation() -> None:
    with pytest.raises(ValidationError):
        BonificaSyncRunRequest.model_validate({"entities": "reports", "date_from": "not-a-date"})


@pytest.mark.parametrize("days", [0, -3, 30])
def test_default_day_configuration_still_returns_two_dates(
    sync_db: Session, monkeypatch: pytest.MonkeyPatch, days: int
) -> None:
    monkeypatch.setattr(sync_service.settings, "wc_sync_default_days", days)
    job = persisted_job(sync_db, params={})
    assert sync_service._resolve_date_window_from_job(job, "reports") == (
        date.today() - timedelta(days=days),
        date.today(),
    )


def test_overflowing_default_configuration_raises_before_query(
    sync_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sync_service.settings, "wc_sync_default_days", 2_000_000_000)

    with pytest.raises(OverflowError):
        sync_service._resolve_job_params(
            sync_db, BonificaSyncRunRequest(entities="reports"), "reports"
        )

    assert sync_db.info["select_statements"] == []


@pytest.mark.parametrize("params", [None, {"retained": "existing"}])
@pytest.mark.parametrize("counters", [(0, 0, 0), (4, 5, 6)])
def test_runtime_snapshot_preserves_existing_counters_and_params(
    sync_db: Session, params: dict | None, counters: tuple[int, int, int]
) -> None:
    job = persisted_job(sync_db, params=params)
    job.records_synced, job.records_skipped, job.records_errors = counters
    sync_db.commit()
    transitions: list[str] = []

    def after_commit(_session):
        transitions.append("committed")

    event.listen(sync_db, "after_commit", after_commit)
    try:
        sync_service._persist_job_runtime_snapshot(sync_db, job)
    finally:
        event.remove(sync_db, "after_commit", after_commit)
    sync_db.refresh(job)

    assert (job.records_synced, job.records_skipped, job.records_errors) == counters
    assert job.params_json == params
    assert transitions == ["committed"]


def test_vehicle_search_exhausts_all_real_empty_candidates(sync_db: Session) -> None:
    vehicle = Vehicle(code="   ", name="No search identifier", vehicle_type="attrezzatura", wc_id=1)
    sync_db.add(vehicle)
    sync_db.commit()

    assert sync_service._list_vehicle_refuel_search_codes(sync_db) == []
    assert sync_db.get(Vehicle, vehicle.id) is vehicle


def test_recent_aware_timestamp_retains_running_status(
    sync_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime.now(UTC)
    monkeypatch.setattr(sync_service, "_BACKEND_PROCESS_STARTED_AT", now - timedelta(days=1))
    job = persisted_job(sync_db, started_at=now, status="running")
    job.started_at = now

    sync_service._expire_stale_running_jobs(sync_db)

    assert job.started_at == now
    assert job.started_at.tzinfo is UTC
    assert job.status == "running"
    assert job.finished_at is None
    assert job.error_detail is None
