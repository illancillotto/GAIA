"""Persisted public-route contracts for operator weighted fuel targets."""

from datetime import datetime
from decimal import Decimal

import pytest
import test_operazioni_analytics as existing
from sqlalchemy import event
from sqlalchemy.orm import Session
from test_operazioni_analytics_characterization import database as database
from test_operazioni_analytics_characterization import driver as driver
from test_operazioni_operator_km_r14 import _compiled_queries
from test_operazioni_session_distance_r31 import public_database as public_database

from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.vehicles import Vehicle

STARTED = datetime(2026, 3, 15, 8)
PARAMS = {"from_date": "2026-01-01", "to_date": "2026-12-31", "granularity": "month"}


def _seed(
    database: Session,
    driver: ApplicationUser,
    first_type: str,
    second_type: str,
    second_distance: float,
    second_liters: float,
):
    first = existing._make_vehicle(database, "R33AUTO")
    second = existing._make_vehicle(database, "R33VAN")
    first.vehicle_type = first_type
    second.vehicle_type = second_type
    operator = existing._make_wc_operator(
        database,
        wc_id=33001,
        username="r33-operator",
        gaia_user_id=driver.id,
        first_name="R33",
        last_name="Driver",
    )
    existing._make_session(database, first, driver.id, STARTED, 0, 100)
    second_usage = existing._make_session(database, second, driver.id, STARTED, 0, 0)
    second_usage.route_distance_km = Decimal(str(second_distance))
    for vehicle, liters in [(first, 10), (second, second_liters)]:
        log = existing._make_fuel_log(database, vehicle, driver.id, STARTED, liters, liters * 2)
        log.wc_operator_id = operator.id
        log.station_name = "R33 station"
    database.commit()
    return first, second, operator


@pytest.mark.parametrize(
    ("first_type", "second_type", "second_distance", "coefficient", "judgement"),
    [
        ("auto", "van", 300, 0.714, "OK"),
        ("auto", "speciale", 300, 1.0, "OK"),
        ("speciale", "van", 300, 0.652, "OK"),
        ("speciale", "speciale", 300, None, None),
        ("auto", "van", 0, 4.0, "Molto alto"),
        ("auto", "van", -50, 8.0, "Molto alto"),
        ("speciale", "van", 0, None, None),
    ],
)
def test_public_weighted_target_preserves_response_queries_state_and_lookup_order(
    public_database: Session,
    driver: ApplicationUser,
    first_type: str,
    second_type: str,
    second_distance: float,
    coefficient: float | None,
    judgement: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, second, operator = _seed(
        public_database, driver, first_type, second_type, second_distance, 20
    )
    headers = existing._auth_headers()
    for entity in list(public_database.identity_map.values()):
        public_database.refresh(entity)
    first_id, second_id, operator_id = str(first.id), str(second.id), f"wc:{operator.id}"
    expected_queries = _compiled_queries(public_database, [first, second], operator)
    before = [(entity, vars(entity).copy()) for entity in public_database.identity_map.values()]
    reads = []
    queries = []
    original_getattribute = Vehicle.__getattribute__

    def record_read(instance, name):
        if name == "vehicle_type":
            reads.append(str(original_getattribute(instance, "id")))
        return original_getattribute(instance, name)

    def capture(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("SELECT") and "application_users" not in statement:
            queries.append((statement, parameters))

    monkeypatch.setattr(Vehicle, "__getattribute__", record_read)
    event.listen(existing.engine, "before_cursor_execute", capture)
    try:
        response = existing.client.get("/operazioni/analytics/fuel", params=PARAMS, headers=headers)
    finally:
        event.remove(existing.engine, "before_cursor_execute", capture)

    assert response.status_code == 200
    payload = response.json()
    assert payload["top_operators"] == [
        {
            "id": operator_id,
            "label": "R33 Driver",
            "total_liters": 30,
            "total_cost": 60,
            "refuel_count": 2,
            "total_km": 100 + second_distance,
            "avg_consumption_l_per_100km": round(3000 / (100 + second_distance), 2),
            "consumption_coefficient": coefficient,
            "consumption_judgement": judgement,
            "avg_price_per_liter": 2,
            "avg_refuel_cost": 30,
            "avg_liters_per_refuel": 15,
            "top_stations": [
                {
                    "station_name": "R33 station",
                    "refuel_count": 2,
                    "total_liters": 30,
                    "total_cost": 60,
                }
            ],
            "related": [
                {
                    "id": second_id,
                    "label": "R33VAN",
                    "refuel_count": 1,
                    "total_liters": 20,
                    "total_cost": 40,
                    "avg_price_per_liter": 2,
                    "avg_refuel_cost": 40,
                    "avg_liters_per_refuel": 20,
                },
                {
                    "id": first_id,
                    "label": "R33AUTO",
                    "refuel_count": 1,
                    "total_liters": 10,
                    "total_cost": 20,
                    "avg_price_per_liter": 2,
                    "avg_refuel_cost": 20,
                    "avg_liters_per_refuel": 10,
                },
            ],
        }
    ]
    assert payload["total_liters"] == 30
    assert payload["total_cost"] == 60
    assert reads == [second_id, first_id, first_id, second_id]
    assert queries == expected_queries
    assert not public_database.new and not public_database.dirty and not public_database.deleted
    for entity, state in before:
        assert vars(entity) == state


@pytest.mark.parametrize(
    (
        "vehicle_type",
        "liters",
        "consumption",
        "coefficient",
        "operator_judgement",
        "vehicle_judgement",
    ),
    [
        ("auto", 8.254, 8.25, 1.1, "OK", "Alto"),
        ("auto", 9.754, 9.75, 1.3, "Alto", "Molto alto"),
        ("auto", 8.256, 8.26, 1.101, "Alto", "Alto"),
        ("van", 12.651, 12.65, 1.1, "OK", "Alto"),
        ("van", 14.951, 14.95, 1.3, "Alto", "Molto alto"),
    ],
)
def test_public_operator_rounding_precedes_coefficient_unlike_vehicle_rounding(
    public_database: Session,
    driver: ApplicationUser,
    vehicle_type: str,
    liters: float,
    consumption: float,
    coefficient: float,
    operator_judgement: str,
    vehicle_judgement: str,
) -> None:
    vehicle = existing._make_vehicle(public_database, "R33ROUND")
    vehicle.vehicle_type = vehicle_type
    operator = existing._make_wc_operator(
        public_database, wc_id=33002, username="r33-rounding", gaia_user_id=driver.id
    )
    existing._make_session(public_database, vehicle, driver.id, STARTED, 0, 100)
    log = existing._make_fuel_log(public_database, vehicle, driver.id, STARTED, liters, liters * 2)
    log.wc_operator_id = operator.id
    public_database.commit()
    headers = existing._auth_headers()
    response = existing.client.get("/operazioni/analytics/fuel", params=PARAMS, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    operator_item = payload["top_operators"][0]
    vehicle_item = payload["top_vehicles"][0]
    assert operator_item["total_km"] == 100
    assert operator_item["avg_consumption_l_per_100km"] == consumption
    assert operator_item["consumption_coefficient"] == coefficient
    assert operator_item["consumption_judgement"] == operator_judgement
    assert vehicle_item["consumption_judgement"] == vehicle_judgement
    assert not public_database.new and not public_database.dirty and not public_database.deleted


@pytest.mark.parametrize("second_distance", [-100, -150])
def test_public_nonpositive_operator_distance_has_no_consumption_or_target_lookup(
    public_database: Session,
    driver: ApplicationUser,
    second_distance: float,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, second, _ = _seed(public_database, driver, "auto", "van", second_distance, 20)
    headers = existing._auth_headers()
    reads = []
    original_getattribute = Vehicle.__getattribute__

    def record_read(instance, name):
        if name == "vehicle_type":
            reads.append(str(original_getattribute(instance, "id")))
        return original_getattribute(instance, name)

    monkeypatch.setattr(Vehicle, "__getattribute__", record_read)
    response = existing.client.get("/operazioni/analytics/fuel", params=PARAMS, headers=headers)
    assert response.status_code == 200
    item = response.json()["top_operators"][0]
    assert item["total_km"] is None
    assert item["avg_consumption_l_per_100km"] is None
    assert item["consumption_coefficient"] is None
    assert item["consumption_judgement"] is None
    assert reads == [str(second.id), str(first.id)]


@pytest.mark.parametrize("allowed", [False, True])
def test_public_operator_consumption_requires_real_login_and_module_permission(
    public_database: Session, allowed: bool
) -> None:
    headers = existing._auth_headers(module_operazioni=allowed)
    anonymous = existing.client.get("/operazioni/analytics/fuel", params=PARAMS)
    response = existing.client.get("/operazioni/analytics/fuel", params=PARAMS, headers=headers)
    assert anonymous.status_code == 401
    assert response.status_code == (200 if allowed else 403)


def test_public_session_only_vehicle_stays_outside_fuel_target_map(
    public_database: Session,
    driver: ApplicationUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, second, _ = _seed(public_database, driver, "auto", "van", 300, 20)
    session_only = existing._make_vehicle(public_database, "R33SESSION")
    session_only.vehicle_type = "truck"
    existing._make_session(public_database, session_only, driver.id, STARTED, 0, 600)
    public_database.commit()
    headers = existing._auth_headers()
    reads = []
    original_getattribute = Vehicle.__getattribute__

    def record_read(instance, name):
        if name == "vehicle_type":
            reads.append(str(original_getattribute(instance, "id")))
        return original_getattribute(instance, name)

    monkeypatch.setattr(Vehicle, "__getattribute__", record_read)
    response = existing.client.get("/operazioni/analytics/fuel", params=PARAMS, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    item = payload["top_operators"][0]
    assert item["total_km"] == 1000
    assert item["avg_consumption_l_per_100km"] == 3
    assert item["consumption_coefficient"] == 0.286
    assert item["consumption_judgement"] == "OK"
    assert {vehicle["id"] for vehicle in payload["top_vehicles"]} == {
        str(first.id),
        str(second.id),
    }
    assert reads == [str(second.id), str(first.id), str(first.id), str(second.id)]
    assert not public_database.new and not public_database.dirty and not public_database.deleted
