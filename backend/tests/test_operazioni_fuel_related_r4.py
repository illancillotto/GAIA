"""Related fuel response mapping contracts against persisted records."""

from datetime import datetime
from decimal import Decimal

import pytest
import test_operazioni_analytics as existing
from sqlalchemy import event, select
from test_operazioni_analytics_characterization import database as database
from test_operazioni_analytics_characterization import driver as driver

from app.modules.operazioni.models.vehicles import Vehicle, VehicleFuelLog, VehicleUsageSession
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.routes import analytics


def _fuel(database):
    return analytics.fuel_analytics(None, database, "2026-01-01", "2026-12-31", "month")


def _log(database, driver, vehicle, liters, cost, name="R4 operator", operator=None):
    log = existing._make_fuel_log(
        database,
        vehicle,
        driver.id,
        datetime(2026, 4, 10, 8),
        Decimal(liters),
        Decimal(cost) if cost is not None else 0,
    )
    log.total_cost = Decimal(cost) if cost is not None else None
    log.operator_name = name
    log.wc_operator_id = operator.id if operator is not None else None
    database.flush()
    return log


@pytest.mark.parametrize(
    ("records", "total_liters", "total_cost", "price", "refuel_cost", "liters_mean"),
    [
        (
            [("1.234", "2.22"), ("2.345", None), ("-0.678", "-1.35"), ("0", "100")],
            2.9,
            100.87,
            round(2.22 / (1.234 + 2.345), 4),
            2.22,
            1.79,
        ),
        ([("1.234", None), ("2.345", None)], 3.58, 0, 0, None, 1.79),
        ([("0", "10"), ("-1.234", "-2.22")], -1.23, 7.78, None, None, None),
        ([("1.234", "0")], 1.23, 0, 0, 0, 1.23),
        ([("1.234", "-2.22")], 1.23, -2.22, round(-2.22 / 1.234, 4), -2.22, 1.23),
    ],
)
def test_related_and_top_fields_share_positive_only_nullable_mean_contract(
    database, driver, records, total_liters, total_cost, price, refuel_cost, liters_mean
):
    vehicle = existing._make_vehicle(database)
    for liters, cost in records:
        _log(database, driver, vehicle, liters, cost)

    result = _fuel(database)

    vehicle_item = result.top_vehicles[0]
    operator_item = result.top_operators[0]
    for item in [vehicle_item, operator_item, vehicle_item.related[0], operator_item.related[0]]:
        assert item.total_liters == total_liters
        assert item.total_cost == total_cost
        assert item.refuel_count == len(records)
        assert item.avg_price_per_liter == price
        assert item.avg_refuel_cost == refuel_cost
        assert item.avg_liters_per_refuel == liters_mean
    assert vehicle_item.related[0].id == "name:R4 operator"
    assert operator_item.related[0].id == str(vehicle.id)
    assert not database.dirty


@pytest.mark.parametrize("direction", ["vehicles", "operators"])
def test_related_ranking_uses_net_liters_stable_ties_and_five_item_limit(
    database, driver, direction
):
    shared_vehicle = existing._make_vehicle(database, plate="R4-SHARED")
    entities = []
    for index in range(7):
        vehicle = (
            existing._make_vehicle(database, plate=f"R4-{index}")
            if direction == "vehicles"
            else shared_vehicle
        )
        name = "R4 operator" if direction == "vehicles" else f"R4-{index}"
        entities.append(str(vehicle.id) if direction == "vehicles" else f"name:{name}")
        _log(database, driver, vehicle, "10" if index == 0 else str(index + 1), "2", name)
        if index == 0:
            _log(database, driver, vehicle, "-5", "-1", name)

    result = _fuel(database)

    related = (
        result.top_operators[0].related
        if direction == "vehicles"
        else result.top_vehicles[0].related
    )
    assert [item.id for item in related] == [entities[index] for index in [6, 5, 0, 4, 3]]
    assert [item.total_liters for item in related] == [7, 6, 5, 5, 4]
    assert related[2].refuel_count == 2


@pytest.mark.parametrize("label_source", ["plate", "name", "id"])
def test_related_vehicle_label_preserves_fallback_precedence(database, driver, label_source):
    vehicle = existing._make_vehicle(database)
    vehicle.plate_number = "R4-PLATE" if label_source == "plate" else None
    vehicle.name = "R4 vehicle" if label_source != "id" else ""
    _log(database, driver, vehicle, "1", "2")

    item = _fuel(database).top_operators[0].related[0]

    assert item.id == str(vehicle.id)
    assert (
        item.label
        == {
            "plate": "R4-PLATE",
            "name": "R4 vehicle",
            "id": str(vehicle.id),
        }[label_source]
    )


def test_vehicle_related_identity_remains_unconsolidated_and_unknown_is_explicit(database, driver):
    vehicle = existing._make_vehicle(database)
    operator = existing._make_wc_operator(
        database,
        wc_id=14001,
        username="r4rossi",
        gaia_user_id=driver.id,
        first_name="Mario",
        last_name="Rossi",
    )
    _log(database, driver, vehicle, "5", "10", None, operator)
    _log(database, driver, vehicle, "4", "8", "Mario Rossi")
    _log(database, driver, vehicle, "3", "6", None)

    result = _fuel(database)

    assert [
        (item.id, item.label, item.total_liters) for item in result.top_vehicles[0].related
    ] == [
        (f"wc:{operator.id}", "Mario Rossi", 5),
        ("name:Mario Rossi", "Mario Rossi", 4),
        ("unknown", "Non identificato", 3),
    ]
    assert [(item.id, item.total_liters) for item in result.top_operators] == [
        (f"wc:{operator.id}", 9),
        ("unknown", 3),
    ]


def test_related_response_keeps_exact_select_order_and_does_not_write(database, driver):
    vehicle = existing._make_vehicle(database)
    operator = existing._make_wc_operator(
        database, wc_id=14002, username="r4-query", gaia_user_id=None
    )
    log = _log(database, driver, vehicle, "1.234", None, None, operator)
    expected_queries = [
        select(VehicleFuelLog).where(
            VehicleFuelLog.fueled_at >= datetime(2026, 1, 1),
            VehicleFuelLog.fueled_at <= datetime(2026, 12, 31, 23, 59, 59, 999999),
        ),
        select(VehicleUsageSession).where(
            VehicleUsageSession.started_at >= datetime(2026, 1, 1),
            VehicleUsageSession.started_at <= datetime(2026, 12, 31, 23, 59, 59, 999999),
            VehicleUsageSession.status != "open",
        ),
        select(Vehicle).where(Vehicle.id.in_({vehicle.id})),
        select(WCOperator).where(WCOperator.id.in_({operator.id})),
        select(Vehicle).where(Vehicle.id.in_({vehicle.id})),
    ]
    before = (log.liters, log.total_cost, log.operator_name, log.wc_operator_id, log.vehicle_id)
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append((statement, parameters))

    event.listen(existing.engine, "before_cursor_execute", capture)
    try:
        result = _fuel(database)
    finally:
        event.remove(existing.engine, "before_cursor_execute", capture)

    expected_statements = []
    for query in expected_queries:
        compiled = query.compile(
            dialect=existing.engine.dialect, compile_kwargs={"render_postcompile": True}
        )
        parameters = []
        for parameter in compiled.positiontup:
            bind = compiled.binds.get(parameter)
            if bind is None:
                bind = compiled.binds[parameter.rsplit("_", 1)[0]]
            processor = bind.type.dialect_impl(existing.engine.dialect).bind_processor(
                existing.engine.dialect
            )
            value = compiled.params[parameter]
            parameters.append(processor(value) if processor else value)
        expected_statements.append((str(compiled), tuple(parameters)))
    assert statements == expected_statements
    assert (
        log.liters,
        log.total_cost,
        log.operator_name,
        log.wc_operator_id,
        log.vehicle_id,
    ) == before
    assert not database.dirty
    assert result.top_operators[0].related[0].avg_refuel_cost is None
