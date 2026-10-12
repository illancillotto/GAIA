"""Persisted inactive-vehicle emission and public-route contracts."""

from collections.abc import Generator
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
import test_operazioni_analytics as existing
from sqlalchemy import event, inspect
from sqlalchemy.orm import ORMExecuteState, Session
from test_operazioni_analytics_characterization import database as database
from test_operazioni_analytics_characterization import driver as driver

from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.vehicles import (
    Vehicle,
    VehicleFuelLog,
    VehicleUsageSession,
    WCRefuelEvent,
)
from app.modules.operazioni.routes import analytics

DAY = date.today() - timedelta(days=10)
STARTED = datetime.combine(DAY, datetime.min.time()) + timedelta(hours=8)
EMPTY_RESPONSE = {"items": [], "total": 0, "by_type": {}, "by_severity": {}}


def _vehicle(database: Session, plate: str | None = "R5800AA", code: str = "R58") -> Vehicle:
    vehicle = Vehicle(
        code=code,
        name="R58 inactive vehicle",
        plate_number=plate,
        vehicle_type="autocarro",
        current_status="available",
        is_active=False,
    )
    database.add(vehicle)
    database.flush()
    return vehicle


def _fuel(
    database: Session,
    vehicle: Vehicle,
    driver: ApplicationUser,
    liters: Decimal = Decimal("10.125"),
    moment: datetime = STARTED,
) -> VehicleFuelLog:
    fuel = VehicleFuelLog(
        vehicle_id=vehicle.id,
        recorded_by_user_id=driver.id,
        fueled_at=moment,
        liters=liters,
        total_cost=None,
    )
    database.add(fuel)
    database.flush()
    return fuel


def _session(
    database: Session,
    vehicle: Vehicle,
    driver: ApplicationUser,
    moment: datetime = STARTED,
    status: str = "closed",
) -> VehicleUsageSession:
    usage = VehicleUsageSession(
        vehicle_id=vehicle.id,
        started_by_user_id=driver.id,
        actual_driver_user_id=driver.id,
        started_at=moment,
        ended_at=moment + timedelta(hours=1),
        start_odometer_km=Decimal("0"),
        status=status,
    )
    database.add(usage)
    database.flush()
    return usage


def _result(
    database: Session,
    kind: str | None = "inactive_vehicle",
    dates: tuple[str | None, str | None] = (DAY.isoformat(), DAY.isoformat()),
) -> dict[str, Any]:
    return analytics.anomalies_analytics(
        current_user=None,
        db=database,
        from_date=dates[0],
        to_date=dates[1],
        anomaly_type=kind,
    ).model_dump(mode="json")


def _fuel_item(vehicle: Vehicle, fuel: VehicleFuelLog, label: str) -> dict[str, Any]:
    return {
        "id": f"inact_v_log_{fuel.id}",
        "type": "inactive_vehicle",
        "severity": "high",
        "description": "Rifornimento registrato su mezzo dismesso",
        "entity_id": str(vehicle.id),
        "entity_label": label,
        "detected_at": fuel.fueled_at.isoformat(),
        "details": {"liters": float(fuel.liters), "vehicle_code": vehicle.code},
    }


def _session_item(vehicle: Vehicle, usage: VehicleUsageSession, label: str) -> dict[str, Any]:
    return {
        "id": f"inact_v_sess_{usage.id}",
        "type": "inactive_vehicle",
        "severity": "high",
        "description": "Sessione d'uso registrata su mezzo dismesso",
        "entity_id": str(vehicle.id),
        "entity_label": label,
        "detected_at": usage.started_at.isoformat(),
        "details": {"vehicle_code": vehicle.code},
    }


@pytest.mark.parametrize("plate", ["R5800AA", "", None])
@pytest.mark.parametrize("code", ["R58", ""])
@pytest.mark.parametrize("liters", [Decimal("10.125"), Decimal("0"), Decimal("-1.250")])
def test_persisted_labels_falsy_liters_exact_payload_and_active_control(
    database: Session, driver: ApplicationUser, plate: str | None, code: str, liters: Decimal
) -> None:
    vehicle = _vehicle(database, plate, code)
    active = _vehicle(database, "ACTIVE", "ACTIVE")
    active.is_active = True
    usage = _session(database, vehicle, driver, STARTED - timedelta(hours=1))
    fuel = _fuel(database, vehicle, driver, liters)
    _session(database, active, driver)
    _fuel(database, active, driver)
    database.flush()
    label = plate or code or str(vehicle.id)

    assert _result(database) == {
        "items": [_fuel_item(vehicle, fuel, label), _session_item(vehicle, usage, label)],
        "total": 2,
        "by_type": {"inactive_vehicle": 2},
        "by_severity": {"high": 2},
    }


@pytest.mark.parametrize("status", ["open", "closed", "cancelled"])
def test_inactive_usage_status_does_not_filter_the_emission(
    database: Session, driver: ApplicationUser, status: str
) -> None:
    vehicle = _vehicle(database)
    usage = _session(database, vehicle, driver, status=status)
    assert _result(database)["items"] == [_session_item(vehicle, usage, "R5800AA")]


@pytest.mark.parametrize("kind", [None, "", "inactive_vehicle", "unsupported", "inactive_operator"])
def test_filter_dispatch_does_not_confuse_inactive_vehicle_and_active_operator(
    database: Session, driver: ApplicationUser, kind: str | None
) -> None:
    vehicle = _vehicle(database)
    fuel = _fuel(database, vehicle, driver)
    assert _result(database, kind)["items"] == (
        [_fuel_item(vehicle, fuel, "R5800AA")] if kind in (None, "", "inactive_vehicle") else []
    )


def test_inclusive_day_boundaries_keep_both_event_families(
    database: Session, driver: ApplicationUser
) -> None:
    vehicle = _vehicle(database)
    start = datetime.combine(DAY, datetime.min.time())
    end = datetime.combine(DAY, datetime.max.time())
    fuels = [_fuel(database, vehicle, driver, moment=moment) for moment in (start, end)]
    sessions = [_session(database, vehicle, driver, moment) for moment in (start, end)]
    for moment in (start - timedelta(microseconds=1), end + timedelta(microseconds=1)):
        _fuel(database, vehicle, driver, moment=moment)
        _session(database, vehicle, driver, moment)

    assert _result(database)["items"] == [
        *[_fuel_item(vehicle, fuel, "R5800AA") for fuel in fuels],
        *[_session_item(vehicle, usage, "R5800AA") for usage in sessions],
    ]


@pytest.mark.parametrize("dates", [(None, None), ("", ""), ("invalid", "not-a-date")])
def test_missing_or_invalid_dates_use_default_window_for_both_events(
    database: Session, driver: ApplicationUser, dates: tuple[str | None, str | None]
) -> None:
    vehicle = _vehicle(database)
    fuel = _fuel(database, vehicle, driver)
    usage = _session(database, vehicle, driver)
    old = datetime.combine(date.today() - timedelta(days=31), datetime.min.time())
    _fuel(database, vehicle, driver, moment=old)
    _session(database, vehicle, driver, old)
    assert _result(database, dates=dates)["items"] == [
        _fuel_item(vehicle, fuel, "R5800AA"),
        _session_item(vehicle, usage, "R5800AA"),
    ]


def test_reversed_dates_do_not_reorder_bounds(database: Session, driver: ApplicationUser) -> None:
    vehicle = _vehicle(database)
    _fuel(database, vehicle, driver)
    _session(database, vehicle, driver)
    dates = ((DAY + timedelta(days=1)).isoformat(), (DAY - timedelta(days=1)).isoformat())
    assert _result(database, dates=dates) == EMPTY_RESPONSE


@pytest.mark.parametrize("has_inactive", [False, True])
def test_empty_event_queries_keep_loading_order_and_transaction_clean(
    database: Session, has_inactive: bool
) -> None:
    vehicle = _vehicle(database)
    vehicle.is_active = not has_inactive
    database.flush()
    records: list[type] = []

    def record(execution: ORMExecuteState) -> None:
        records.append(execution.statement.column_descriptions[0]["entity"])

    event.listen(database, "do_orm_execute", record)
    try:
        result = _result(database)
    finally:
        event.remove(database, "do_orm_execute", record)

    assert result == EMPTY_RESPONSE
    assert records == (
        [Vehicle, VehicleFuelLog, VehicleUsageSession, Vehicle] if has_inactive else [Vehicle]
    )
    assert not database.new
    assert not database.dirty
    assert not database.deleted
    assert database.in_transaction()


def test_real_query_predicates_binds_loading_order_and_orm_state(
    database: Session, driver: ApplicationUser
) -> None:
    vehicle = _vehicle(database)
    fuel = _fuel(database, vehicle, driver)
    usage = _session(database, vehicle, driver)
    entities = [vehicle, fuel, usage]
    before = [
        {column.key: getattr(entity, column.key) for column in inspect(entity).mapper.columns}
        for entity in entities
    ]
    records: list[tuple[type, dict[str, Any], str]] = []

    def record(execution: ORMExecuteState) -> None:
        statement = execution.statement
        records.append(
            (
                statement.column_descriptions[0]["entity"],
                statement.compile().params,
                str(statement.whereclause),
            )
        )

    event.listen(database, "do_orm_execute", record)
    try:
        result = _result(database)
    finally:
        event.remove(database, "do_orm_execute", record)

    assert result["items"] == [
        _fuel_item(vehicle, fuel, "R5800AA"),
        _session_item(vehicle, usage, "R5800AA"),
    ]
    assert [record[0] for record in records] == [
        Vehicle,
        VehicleFuelLog,
        VehicleUsageSession,
        Vehicle,
    ]
    assert records[0][1:] == ({}, "vehicle.is_active IS false")
    assert records[1][1] == {
        "fueled_at_1": datetime.combine(DAY, datetime.min.time()),
        "fueled_at_2": datetime.combine(DAY, datetime.max.time()),
        "vehicle_id_1": [vehicle.id],
    }
    assert records[1][2] == (
        "vehicle_fuel_log.fueled_at >= :fueled_at_1 AND "
        "vehicle_fuel_log.fueled_at <= :fueled_at_2 AND "
        "vehicle_fuel_log.vehicle_id IN (__[POSTCOMPILE_vehicle_id_1])"
    )
    assert records[2][1] == {
        "started_at_1": datetime.combine(DAY, datetime.min.time()),
        "started_at_2": datetime.combine(DAY, datetime.max.time()),
        "vehicle_id_1": [vehicle.id],
    }
    assert records[2][2] == (
        "vehicle_usage_session.started_at >= :started_at_1 AND "
        "vehicle_usage_session.started_at <= :started_at_2 AND "
        "vehicle_usage_session.vehicle_id IN (__[POSTCOMPILE_vehicle_id_1])"
    )
    assert records[3][1:] == (
        {"id_1": [vehicle.id]},
        "vehicle.id IN (__[POSTCOMPILE_id_1])",
    )
    assert before == [
        {column.key: getattr(entity, column.key) for column in inspect(entity).mapper.columns}
        for entity in entities
    ]
    assert not database.new
    assert not database.dirty
    assert not database.deleted


def test_stable_high_first_sort_keeps_fuel_before_session_and_count_insertion_order(
    database: Session, driver: ApplicationUser
) -> None:
    vehicle = _vehicle(database)
    usage = _session(database, vehicle, driver, STARTED - timedelta(hours=1))
    fuel = _fuel(database, vehicle, driver, Decimal("121"))
    unmatched = WCRefuelEvent(wc_id=58001, fueled_at=STARTED, vehicle_code="WC-R58")
    database.add(unmatched)
    database.flush()
    result = _result(database, None)

    assert result["items"][:2] == [
        _fuel_item(vehicle, fuel, "R5800AA"),
        _session_item(vehicle, usage, "R5800AA"),
    ]
    assert [item["type"] for item in result["items"]] == [
        "inactive_vehicle",
        "inactive_vehicle",
        "excessive_fuel",
        "unmatched_refuel",
    ]
    assert result["total"] == 4
    assert result["by_type"] == {"excessive_fuel": 1, "unmatched_refuel": 1, "inactive_vehicle": 2}
    assert result["by_severity"] == {"medium": 1, "low": 1, "high": 2}
    assert list(result["by_type"]) == ["excessive_fuel", "unmatched_refuel", "inactive_vehicle"]
    assert list(result["by_severity"]) == ["medium", "low", "high"]


@pytest.mark.parametrize("allowed", [False, True])
def test_real_public_login_permissions_type_alias_and_exact_response(
    database: Session, driver: ApplicationUser, allowed: bool
) -> None:
    vehicle = _vehicle(database)
    fuel = _fuel(database, vehicle, driver)
    usage = _session(database, vehicle, driver)
    database.commit()

    def real_database() -> Generator[Session, None, None]:
        yield database

    params = {"from_date": DAY.isoformat(), "to_date": DAY.isoformat(), "type": "inactive_vehicle"}
    with pytest.MonkeyPatch.context() as overrides:
        overrides.setitem(existing.app.dependency_overrides, get_db, real_database)
        headers = existing._auth_headers(module_operazioni=allowed)
        anonymous = existing.client.get("/operazioni/analytics/anomalies", params=params)
        response = existing.client.get(
            "/operazioni/analytics/anomalies", params=params, headers=headers
        )

    assert anonymous.status_code == 401
    assert response.status_code == (200 if allowed else 403)
    if allowed:
        assert response.json() == {
            "items": [
                _fuel_item(vehicle, fuel, "R5800AA"),
                _session_item(vehicle, usage, "R5800AA"),
            ],
            "total": 2,
            "by_type": {"inactive_vehicle": 2},
            "by_severity": {"high": 2},
        }
