"""Persisted operator-key precedence and grouping contracts for fuel analytics."""

from datetime import datetime, timedelta
from uuid import UUID

import pytest
import test_operazioni_analytics as existing
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_operazioni_analytics_characterization import database as database
from test_operazioni_analytics_characterization import driver as driver

from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.vehicles import Vehicle, VehicleFuelLog, VehicleUsageSession
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.routes import analytics

STARTED = datetime(2026, 3, 15, 8)


def _related(identifier: str, label: str, count: int = 1) -> dict:
    return {
        "id": identifier,
        "label": label,
        "refuel_count": count,
        "total_liters": 10 * count,
        "total_cost": 20 * count,
        "avg_price_per_liter": 2,
        "avg_refuel_cost": 20,
        "avg_liters_per_refuel": 10,
    }


def _top(identifier: str, label: str, related: list[dict], count: int = 1) -> dict:
    return {
        **_related(identifier, label, count),
        "total_km": None,
        "avg_consumption_l_per_100km": None,
        "consumption_coefficient": None,
        "consumption_judgement": None,
        "top_stations": [
            {
                "station_name": "R28 station",
                "refuel_count": count,
                "total_liters": 10 * count,
                "total_cost": 20 * count,
            }
        ],
        "related": related,
    }


def _fuel(database: Session) -> dict:
    return analytics.fuel_analytics(None, database, "2026-03-15", "2026-03-15", "month").model_dump(
        mode="json"
    )


def _log(database: Session, vehicle: Vehicle, driver: ApplicationUser) -> VehicleFuelLog:
    log = existing._make_fuel_log(database, vehicle, driver.id, STARTED, 10, 20)
    log.station_name = "R28 station"
    return log


def _record_queries(database: Session, monkeypatch: pytest.MonkeyPatch) -> list:
    queries = []
    actual_scalars = database.scalars

    def record(statement, *arguments, **keywords):
        queries.append((str(statement), statement.compile().params))
        return actual_scalars(statement, *arguments, **keywords)

    monkeypatch.setattr(database, "scalars", record)
    return queries


@pytest.mark.parametrize("identified", [None, "regular", "zero"])
@pytest.mark.parametrize(
    ("name", "legacy_id", "legacy_label"),
    [
        (None, "unknown", "Non identificato"),
        ("", "unknown", "Non identificato"),
        (" ", "name: ", " "),
        ("Mario Rossi", "name:Mario Rossi", "Mario Rossi"),
        ("mario rossi", "name:mario rossi", "mario rossi"),
        (" Mario Rossi ", "name: Mario Rossi ", " Mario Rossi "),
        ("__no_operator__", "unknown", "Non identificato"),
        (
            "00000000-0000-0000-0000-000000000028",
            "name:00000000-0000-0000-0000-000000000028",
            "00000000-0000-0000-0000-000000000028",
        ),
    ],
)
def test_uuid_precedence_and_raw_name_fallback_preserve_full_response_and_queries(
    database: Session,
    driver: ApplicationUser,
    monkeypatch: pytest.MonkeyPatch,
    identified: str | None,
    name: str | None,
    legacy_id: str,
    legacy_label: str,
) -> None:
    vehicle = existing._make_vehicle(database, "R28001AA")
    operator = existing._make_wc_operator(
        database,
        wc_id=28001,
        username="r28operator",
        gaia_user_id=None,
        first_name="Mario",
        last_name="Rossi",
    )
    if identified == "zero":
        operator.id = UUID(int=0)
    log = _log(database, vehicle, driver)
    log.operator_name = name
    log.wc_operator_id = operator.id if identified else None
    database.flush()
    before = (log.operator_name, log.wc_operator_id, log.liters, log.total_cost)
    queries = _record_queries(database, monkeypatch)

    result = _fuel(database)

    identifier = f"wc:{operator.id}" if identified else legacy_id
    label = "Mario Rossi" if identified else legacy_label
    assert result == {
        "time_series": [{"period": "2026-03", "value": 10}],
        "cost_series": [{"period": "2026-03", "value": 20}],
        "top_vehicles": [_top(str(vehicle.id), "R28001AA", [_related(identifier, label)])],
        "top_operators": [_top(identifier, label, [_related(str(vehicle.id), "R28001AA")])],
        "total_liters": 10,
        "total_cost": 20,
        "avg_liters_per_refuel": 10,
        "storno_count": 0,
        "storno_liters": 0,
        "storno_cost": 0,
    }
    expected = [
        select(VehicleFuelLog).where(
            VehicleFuelLog.fueled_at >= datetime(2026, 3, 15),
            VehicleFuelLog.fueled_at <= datetime(2026, 3, 15, 23, 59, 59, 999999),
        ),
        select(VehicleUsageSession).where(
            VehicleUsageSession.started_at >= datetime(2026, 3, 15),
            VehicleUsageSession.started_at <= datetime(2026, 3, 15, 23, 59, 59, 999999),
            VehicleUsageSession.status != "open",
        ),
        select(Vehicle).where(Vehicle.id.in_({vehicle.id})),
    ]
    if identified:
        expected.append(select(WCOperator).where(WCOperator.id.in_({operator.id})))
    expected.append(select(Vehicle).where(Vehicle.id.in_({vehicle.id})))
    assert queries == [(str(statement), statement.compile().params) for statement in expected]
    assert before == (log.operator_name, log.wc_operator_id, log.liters, log.total_cost)
    assert not database.new and not database.dirty and not database.deleted


@pytest.mark.parametrize("variant", ["Mario Rossi", "Rossi Mario", "mrossi"])
def test_top_groups_consolidate_names_but_related_vehicle_keys_remain_raw(
    database: Session, driver: ApplicationUser, variant: str
) -> None:
    vehicle = existing._make_vehicle(database, "R28002AA")
    operator = existing._make_wc_operator(
        database,
        wc_id=28002,
        username="mrossi",
        gaia_user_id=None,
        first_name="Mario",
        last_name="Rossi",
    )
    legacy = _log(database, vehicle, driver)
    legacy.operator_name = variant
    identified = _log(database, vehicle, driver)
    identified.wc_operator_id = operator.id
    identified.operator_name = "Ignored legacy label"
    database.flush()

    result = _fuel(database)

    assert result["top_operators"] == [
        _top(
            f"wc:{operator.id}",
            "Mario Rossi",
            [_related(str(vehicle.id), "R28002AA", 2)],
            2,
        )
    ]
    assert result["top_vehicles"][0]["related"] == [
        _related(f"name:{variant}", variant),
        _related(f"wc:{operator.id}", "Mario Rossi"),
    ]


def test_sentinel_collision_is_not_consolidated_into_operator_username(
    database: Session, driver: ApplicationUser
) -> None:
    vehicle = existing._make_vehicle(database, "R28003AA")
    operator = existing._make_wc_operator(
        database, wc_id=28003, username="__no_operator__", gaia_user_id=None
    )
    identified = _log(database, vehicle, driver)
    identified.wc_operator_id = operator.id
    for name in [None, "", "__no_operator__"]:
        _log(database, vehicle, driver).operator_name = name
    database.flush()

    result = _fuel(database)

    assert result["top_operators"] == [
        _top("unknown", "Non identificato", [_related(str(vehicle.id), "R28003AA", 3)], 3),
        _top(f"wc:{operator.id}", "__no_operator__", [_related(str(vehicle.id), "R28003AA")]),
    ]
    assert result["top_vehicles"][0]["related"] == [
        _related("unknown", "Non identificato", 3),
        _related(f"wc:{operator.id}", "__no_operator__"),
    ]


def test_equal_liters_keep_first_seen_order_and_only_related_groups_are_limited(
    database: Session, driver: ApplicationUser
) -> None:
    vehicle = existing._make_vehicle(database, "R28004AA")
    names = [
        "omega",
        "Alpha",
        "alpha",
        " ",
        " Beta ",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
    ]
    for name in names:
        _log(database, vehicle, driver).operator_name = name
    database.flush()

    result = _fuel(database)

    assert result["top_operators"] == [
        _top(f"name:{name}", name, [_related(str(vehicle.id), "R28004AA")]) for name in names
    ]
    assert result["top_vehicles"][0]["related"] == [
        _related(f"name:{name}", name) for name in names[:5]
    ]
    assert result["total_liters"] == 120
    assert result["total_cost"] == 240


@pytest.mark.parametrize("allowed", [False, True])
def test_public_route_enforces_permission_and_inclusive_date_filter(
    database: Session, driver: ApplicationUser, allowed: bool
) -> None:
    vehicle = existing._make_vehicle(database, "R28005AA")
    for fueled_at in [
        datetime(2026, 3, 15) - timedelta(microseconds=1),
        datetime(2026, 3, 15),
        datetime(2026, 3, 15, 23, 59, 59, 999999),
        datetime(2026, 3, 16),
    ]:
        log = _log(database, vehicle, driver)
        log.fueled_at = fueled_at
        log.operator_name = " Raw name "
    database.commit()
    previous = existing.app.dependency_overrides.get(get_db)
    existing.app.dependency_overrides[get_db] = lambda: database
    try:
        headers = existing._auth_headers(module_operazioni=allowed)
        anonymous = existing.client.get("/operazioni/analytics/fuel")
        response = existing.client.get(
            "/operazioni/analytics/fuel",
            params={"from_date": "2026-03-15", "to_date": "2026-03-15", "granularity": "month"},
            headers=headers,
        )
    finally:
        if previous is None:
            existing.app.dependency_overrides.pop(get_db, None)
        else:
            existing.app.dependency_overrides[get_db] = previous

    assert anonymous.status_code == 401
    assert response.status_code == (200 if allowed else 403)
    if allowed:
        assert response.json() == _fuel(database)
        assert response.json()["top_operators"] == [
            _top("name: Raw name ", " Raw name ", [_related(str(vehicle.id), "R28005AA", 2)], 2)
        ]
        assert response.json()["total_liters"] == 20
    assert not database.new and not database.dirty and not database.deleted
