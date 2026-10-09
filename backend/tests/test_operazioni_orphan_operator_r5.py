"""Persisted contracts for orphan-session operator identity annotations."""

from datetime import UTC, datetime, timedelta

import pytest
import test_operazioni_analytics as existing
from sqlalchemy import event, inspect, select
from test_operazioni_analytics_characterization import database as database
from test_operazioni_analytics_characterization import driver as driver

from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.activities import OperatorActivity
from app.modules.operazioni.models.fuel_cards import FuelCardAssignmentHistory
from app.modules.operazioni.models.vehicles import (
    Vehicle,
    VehicleFuelLog,
    VehicleUsageSession,
    WCRefuelEvent,
)
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.routes import analytics

NOW = datetime(2026, 10, 9, 12, tzinfo=UTC)
FROM_DATE = "2026-10-01"
TO_DATE = "2026-10-02"


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is not None else NOW.replace(tzinfo=None)

    monkeypatch.setattr(analytics, "datetime", FrozenDatetime)


def _operator(database, index, first, last, linked=None):
    return existing._make_wc_operator(
        database,
        wc_id=15000 + index,
        username=f"r5-{index}",
        gaia_user_id=linked,
        first_name=first,
        last_name=last,
    )


def _session(database, driver, vehicle, name, linked=None, hours=30):
    usage = existing._make_session(
        database,
        vehicle,
        driver.id,
        (NOW - timedelta(hours=hours)).replace(tzinfo=None),
        0,
        100,
        "open",
    )
    usage.actual_driver_user_id = linked
    usage.operator_name = name
    usage.wc_id = 0
    database.flush()
    return usage


def _expected_item(usage, vehicle, label, operator_id, hours=30):
    return {
        "id": f"orphan_{usage.id}",
        "type": "orphan_session",
        "severity": "medium" if hours < 48 else "high",
        "description": f"Sessione aperta da {int(hours)}h senza chiusura",
        "entity_id": str(usage.id),
        "entity_label": vehicle.plate_number or str(vehicle.id),
        "detected_at": usage.started_at.isoformat(),
        "details": {
            "hours_open": round(hours, 1),
            "vehicle_id": str(vehicle.id),
            "wc_id": 0,
            "operator_name": label,
            "operator_id": str(operator_id) if operator_id is not None else None,
        },
    }


def _sql(query):
    compiled = query.compile(
        dialect=existing.engine.dialect, compile_kwargs={"render_postcompile": True}
    )
    parameters = []
    for name in compiled.positiontup:
        bind = compiled.binds.get(name)
        if bind is None:
            bind = compiled.binds[name.rsplit("_", 1)[0]]
        processor = bind.type.dialect_impl(existing.engine.dialect).bind_processor(
            existing.engine.dialect
        )
        value = compiled.params[name]
        parameters.append(processor(value) if processor else value)
    return str(compiled), tuple(parameters)


def _orphan_queries(sessions):
    queries = [
        select(VehicleUsageSession).where(
            VehicleUsageSession.status == "open",
            VehicleUsageSession.started_at <= NOW - timedelta(hours=24),
            VehicleUsageSession.started_at >= datetime(2026, 10, 1),
        )
    ]
    vehicle_ids = {usage.vehicle_id for usage in sessions if usage.vehicle_id}
    if vehicle_ids:
        queries.append(select(Vehicle).where(Vehicle.id.in_(vehicle_ids)))
    user_ids = {
        usage.actual_driver_user_id for usage in sessions if usage.actual_driver_user_id is not None
    }
    if user_ids:
        queries.append(select(WCOperator).where(WCOperator.gaia_user_id.in_(user_ids)))
    if any(usage.operator_name and usage.operator_name.strip() for usage in sessions):
        queries.append(select(WCOperator).where(WCOperator.last_name.is_not(None)))
    return queries


def _checked_response(database, expected, queries, kind="orphan_session"):
    database.flush()
    records = list(database.identity_map.values())
    before = [
        tuple(getattr(record, column.key) for column in inspect(record).mapper.column_attrs)
        for record in records
    ]
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append((statement, parameters))

    event.listen(existing.engine, "before_cursor_execute", capture)
    try:
        result = analytics.anomalies_analytics(None, database, FROM_DATE, TO_DATE, kind)
    finally:
        event.remove(existing.engine, "before_cursor_execute", capture)

    assert result.model_dump() == expected
    assert statements == [_sql(query) for query in queries]
    assert not database.new and not database.dirty and not database.deleted
    assert before == [
        tuple(getattr(record, column.key) for column in inspect(record).mapper.column_attrs)
        for record in records
    ]


@pytest.mark.parametrize(
    ("first", "last", "raw", "matches", "label"),
    [
        ("Mario", "Rossi", "Mario Rossi", True, "Mario Rossi"),
        ("Mario", "Rossi", "Rossi Mario", True, "Mario Rossi"),
        ("Mario", "Rossi", "  mARIO rOSSI  ", True, "Mario Rossi"),
        ("Mario", "Rossi", "Mario  Rossi", False, "Mario  Rossi"),
        (" Mario ", "Rossi", "Mario  Rossi", True, "Mario  Rossi"),
        ("Mario", " Rossi ", "Rossi  Mario", True, "Mario  Rossi"),
        (None, "Rossi", "ROSSI", True, "Rossi"),
        ("", "Rossi", "rossi", True, "Rossi"),
        ("Mario", "", "Mario", True, "Mario"),
        ("Mario", None, "Mario", False, "Mario"),
        (None, None, "r5-0", False, "r5-0"),
        ("", "", "unknown", False, "unknown"),
        ("Mario", "Rossi", None, False, None),
        ("Mario", "Rossi", "", False, None),
        ("Mario", "Rossi", " \t ", False, " \t "),
        ("Mario", "Rossi", "r5-0", False, "r5-0"),
        ("Mario", "Rossi", "Mario\tRossi", False, "Mario\tRossi"),
    ],
)
def test_name_matching_preserves_nullable_parts_case_and_internal_whitespace(
    database, driver, first, last, raw, matches, label
):
    vehicle = existing._make_vehicle(database)
    operator = _operator(database, 0, first, last)
    usage = _session(database, driver, vehicle, raw)
    expected = _expected_item(usage, vehicle, label, operator.id if matches else None)
    _checked_response(
        database,
        {
            "items": [expected],
            "total": 1,
            "by_type": {"orphan_session": 1},
            "by_severity": {"medium": 1},
        },
        _orphan_queries([usage]),
    )


@pytest.mark.parametrize("reverse_first", [False, True])
def test_name_collisions_keep_first_candidate_across_forward_and_reverse(
    database, driver, reverse_first
):
    vehicle = existing._make_vehicle(database)
    first = _operator(
        database, 0, "Rossi" if reverse_first else "Mario", "Mario" if reverse_first else "Rossi"
    )
    _operator(database, 1, "Mario", "Rossi")
    _operator(database, 2, "Rossi", "Mario")
    usages = [_session(database, driver, vehicle, name) for name in ["Mario Rossi", "Rossi Mario"]]
    label = "Rossi Mario" if reverse_first else "Mario Rossi"
    _checked_response(
        database,
        {
            "items": [_expected_item(usage, vehicle, label, first.id) for usage in usages],
            "total": 2,
            "by_type": {"orphan_session": 2},
            "by_severity": {"medium": 2},
        },
        _orphan_queries(usages),
    )


@pytest.mark.parametrize("linked", [None, "driver", 0, 99999])
@pytest.mark.parametrize("linked_names", [("Linked", "Last"), (None, None), ("", ""), (" ", " ")])
def test_linked_precedence_last_wins_zero_and_missing_link_name_fallback(
    database, driver, linked, linked_names
):
    vehicle = existing._make_vehicle(database)
    name_match = _operator(database, 0, "Mario", "Rossi")
    link_id = driver.id if linked == "driver" else linked
    if linked == 0:
        database.add(
            ApplicationUser(
                id=0,
                username="r5-zero",
                email="zero@example.local",
                password_hash="unused",
                role="viewer",
                is_active=True,
            )
        )
        database.flush()
    linked_match = None
    if linked in ["driver", 0]:
        _operator(database, 1, "Earlier", "Link", link_id)
        linked_match = _operator(database, 2, *linked_names, linked=link_id)
    usage = _session(database, driver, vehicle, "Mario Rossi", linked=link_id)
    winner = linked_match if linked_match is not None else name_match
    label = (
        " ".join(filter(None, linked_names)).strip() if linked_match is not None else "Mario Rossi"
    )
    _checked_response(
        database,
        {
            "items": [_expected_item(usage, vehicle, label, winner.id)],
            "total": 1,
            "by_type": {"orphan_session": 1},
            "by_severity": {"medium": 1},
        },
        _orphan_queries([usage]),
    )


def test_orphan_boundaries_no_upper_date_bound_and_stable_severity_order(database, driver):
    vehicle = existing._make_vehicle(database)
    operator = _operator(database, 0, "Mario", "Rossi")
    hours = [24, 47.99, 48, 60, 24.01]
    usages = [_session(database, driver, vehicle, "Mario Rossi", hours=age) for age in hours]
    _session(database, driver, vehicle, "Mario Rossi", hours=23.99)
    _session(database, driver, vehicle, "Mario Rossi", hours=240)
    closed = _session(database, driver, vehicle, "Mario Rossi", hours=30)
    closed.status = "closed"
    expected = [
        _expected_item(usages[index], vehicle, "Mario Rossi", operator.id, hours[index])
        for index in [2, 3, 0, 1, 4]
    ]
    _checked_response(
        database,
        {
            "items": expected,
            "total": 5,
            "by_type": {"orphan_session": 5},
            "by_severity": {"medium": 3, "high": 2},
        },
        _orphan_queries(usages),
    )


def test_empty_orphan_population_runs_only_session_select(database):
    _checked_response(
        database, {"items": [], "total": 0, "by_type": {}, "by_severity": {}}, _orphan_queries([])
    )


def test_mixed_anomaly_response_keeps_phase_query_order_and_stable_sort(database, driver):
    vehicle = existing._make_vehicle(database)
    vehicle.plate_number = None
    usages = [_session(database, driver, vehicle, None, hours=age) for age in [30, 60]]
    fueled_at = datetime(2026, 10, 2, 12)
    log = existing._make_fuel_log(database, vehicle, driver.id, fueled_at, 150, 225)
    refuel = WCRefuelEvent(wc_id=15099, vehicle_code="R5-WC", fueled_at=fueled_at)
    database.add(refuel)
    database.flush()
    queries = _orphan_queries(usages)
    start, end = datetime(2026, 10, 1), datetime(2026, 10, 2, 23, 59, 59, 999999)
    queries.extend(
        [
            select(VehicleUsageSession).where(
                VehicleUsageSession.started_at >= start,
                VehicleUsageSession.started_at <= end,
                VehicleUsageSession.actual_driver_user_id.isnot(None),
            ),
            select(VehicleFuelLog).where(
                VehicleFuelLog.fueled_at >= start,
                VehicleFuelLog.fueled_at <= end,
                VehicleFuelLog.liters > 120.0,
            ),
            select(Vehicle).where(Vehicle.id.in_({vehicle.id})),
            select(WCRefuelEvent).where(
                WCRefuelEvent.matched_fuel_log_id.is_(None),
                WCRefuelEvent.fueled_at >= start,
                WCRefuelEvent.fueled_at <= end,
            ),
            select(OperatorActivity).where(
                OperatorActivity.started_at >= start,
                OperatorActivity.started_at <= end,
                OperatorActivity.duration_minutes_declared.isnot(None),
                OperatorActivity.duration_minutes_calculated.isnot(None),
            ),
            select(Vehicle).where(Vehicle.is_active.is_(False)),
            select(ApplicationUser).where(ApplicationUser.is_active.is_(False)),
            select(FuelCardAssignmentHistory).where(
                FuelCardAssignmentHistory.end_at.is_(None),
                FuelCardAssignmentHistory.wc_operator_id.isnot(None),
            ),
        ]
    )
    items = [
        _expected_item(usages[1], vehicle, None, None, 60),
        _expected_item(usages[0], vehicle, None, None, 30),
    ]
    items.extend(
        [
            {
                "id": f"fuel_{log.id}",
                "type": "excessive_fuel",
                "severity": "medium",
                "description": "Rifornimento anomalo: 150.0L (soglia 120.0L)",
                "entity_id": str(log.id),
                "entity_label": str(vehicle.id),
                "detected_at": fueled_at.isoformat(),
                "details": {"liters": 150.0, "cost": 225.0, "station": None},
            },
            {
                "id": f"wc_{refuel.id}",
                "type": "unmatched_refuel",
                "severity": "low",
                "description": "Evento rifornimento WC non abbinato a nessun log interno",
                "entity_id": str(refuel.id),
                "entity_label": "R5-WC",
                "detected_at": fueled_at.isoformat(),
                "details": {"wc_id": 15099, "operator": None},
            },
        ]
    )
    _checked_response(
        database,
        {
            "items": items,
            "total": 4,
            "by_type": {"orphan_session": 2, "excessive_fuel": 1, "unmatched_refuel": 1},
            "by_severity": {"medium": 2, "high": 1, "low": 1},
        },
        queries,
        kind=None,
    )
