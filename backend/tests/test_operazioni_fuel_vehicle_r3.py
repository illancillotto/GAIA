"""Vehicle fuel response precision and ordering contracts."""

import math
from datetime import datetime
from decimal import Decimal

import pytest
import test_operazioni_analytics as existing
from sqlalchemy import select
from test_operazioni_analytics_characterization import database as database
from test_operazioni_analytics_characterization import driver as driver

from app.modules.operazioni.models.vehicles import VehicleFuelLog
from app.modules.operazioni.routes import analytics
from app.modules.operazioni.routes._fuel_vehicle_metrics import vehicle_fuel_consumption


def _fuel(database):
    return analytics.fuel_analytics(None, database, "2026-01-01", "2026-12-31", "month")


@pytest.mark.parametrize(
    ("liters", "consumption", "coefficient", "judgement"),
    [
        ("8.250", 8.25, 1.1, "OK"),
        ("8.251", 8.25, 1.1, "Alto"),
        ("9.750", 9.75, 1.3, "Alto"),
        ("9.751", 9.75, 1.3, "Molto alto"),
        ("0.001", 0.0, 0.0, "OK"),
    ],
)
def test_vehicle_judgement_precedes_coefficient_and_consumption_rounding(
    database, driver, liters, consumption, coefficient, judgement
):
    vehicle = existing._make_vehicle(database)
    vehicle.vehicle_type = "auto"
    started = datetime(2026, 4, 10, 8)
    existing._make_session(database, vehicle, driver.id, started, 0, 100)
    existing._make_fuel_log(database, vehicle, driver.id, started, Decimal(liters), 2)
    database.flush()

    item = _fuel(database).top_vehicles[0]

    assert item.avg_consumption_l_per_100km == consumption
    assert item.consumption_coefficient == coefficient
    assert item.consumption_judgement == judgement


def test_vehicle_positive_means_ignore_storno_zero_and_missing_cost(database, driver):
    vehicle = existing._make_vehicle(database)
    vehicle.vehicle_type = "auto"
    started = datetime(2026, 4, 10, 8)
    existing._make_session(database, vehicle, driver.id, started, 0, 3)
    for liters, cost in [("1.234", "2.22"), ("2.345", None), ("-0.678", "-1.35"), ("0", "100")]:
        log = existing._make_fuel_log(
            database,
            vehicle,
            driver.id,
            started,
            Decimal(liters),
            Decimal(cost) if cost is not None else 0,
        )
        if cost is None:
            log.total_cost = None
    database.flush()

    item = _fuel(database).top_vehicles[0]
    positive_liters = float(Decimal("1.234")) + float(Decimal("2.345"))
    raw_consumption = positive_liters / 3 * 100

    assert item.total_liters == 2.9
    assert item.total_cost == 100.87
    assert item.refuel_count == 4
    assert item.avg_price_per_liter == round(2.22 / positive_liters, 4)
    assert item.avg_refuel_cost == 2.22
    assert item.avg_liters_per_refuel == round(positive_liters / 2, 2)
    assert item.avg_consumption_l_per_100km == round(raw_consumption, 2)
    assert item.consumption_coefficient == round(raw_consumption / 7.5, 3)
    assert item.consumption_judgement == "Molto alto"


@pytest.mark.parametrize("distance", [None, 0, -10])
def test_vehicle_without_positive_distance_keeps_null_consumption(database, driver, distance):
    vehicle = existing._make_vehicle(database)
    started = datetime(2026, 4, 10, 8)
    if distance is not None:
        usage = existing._make_session(database, vehicle, driver.id, started, 10, 10 + distance)
        usage.route_distance_km = None
    existing._make_fuel_log(database, vehicle, driver.id, started, 10, 20)
    database.flush()

    item = _fuel(database).top_vehicles[0]

    assert item.total_km == (None if distance is None else 0.0)
    assert item.avg_consumption_l_per_100km is None
    assert item.consumption_coefficient is None
    assert item.consumption_judgement is None


def test_vehicle_ranking_uses_net_liters_and_retains_input_ties(database, driver):
    first = existing._make_vehicle(database, plate="R3FIRST")
    second = existing._make_vehicle(database, plate="R3SECOND")
    started = datetime(2026, 4, 10, 8)
    for vehicle, liters in [(first, 10), (first, -5), (second, 5)]:
        existing._make_fuel_log(database, vehicle, driver.id, started, liters, liters * 2)
    database.flush()
    input_ids = list(
        dict.fromkeys(log.vehicle_id for log in database.scalars(select(VehicleFuelLog)))
    )

    items = _fuel(database).top_vehicles

    assert [item.id for item in items] == [str(vehicle_id) for vehicle_id in input_ids]
    assert [item.total_liters for item in items] == [5, 5]
    assert [item.refuel_count for item in items] == [2, 1]


@pytest.mark.parametrize(
    ("liters", "distance", "target", "expected_consumption", "expected_coefficient", "judgement"),
    [
        (math.nan, 100, 7.5, None, None, None),
        (10, math.nan, 7.5, None, None, None),
        (math.inf, 100, 7.5, math.inf, math.inf, "Molto alto"),
        (10, math.inf, 7.5, 0.0, 0.0, "OK"),
        (math.inf, math.inf, 7.5, math.nan, math.nan, "Molto alto"),
        (math.inf, 100, None, math.inf, None, None),
        (math.inf, math.inf, None, math.nan, None, None),
        (8.251, 100, 7.5, 8.25, 1.1, "Alto"),
        (9.751, 100, 7.5, 9.75, 1.3, "Molto alto"),
    ],
)
def test_pure_vehicle_consumption_preserves_nonfinite_and_raw_rounding_contract(
    liters, distance, target, expected_consumption, expected_coefficient, judgement
):
    result = vehicle_fuel_consumption(liters, distance, target)

    for actual, expected in [
        (result.consumption, expected_consumption),
        (result.coefficient, expected_coefficient),
    ]:
        if expected is not None and math.isnan(expected):
            assert math.isnan(actual)
        else:
            assert actual == expected
    assert result.judgement == judgement
