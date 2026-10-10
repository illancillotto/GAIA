"""Persisted fuel classification contracts and separate live-source diagnostics."""

import ast
import copy
import inspect
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import test_operazioni_analytics as existing
import test_operazioni_operator_km_r14 as previous
from sqlalchemy import event
from test_operazioni_analytics_characterization import database as database
from test_operazioni_analytics_characterization import driver as driver

from app.modules.operazioni.models.vehicles import Vehicle
from app.modules.operazioni.routes import analytics

STARTED = datetime(2026, 3, 15, 8)


def _expected_related(identifier, label):
    return {
        "id": identifier,
        "label": label,
        "refuel_count": 1,
        "total_liters": 10,
        "total_cost": 20,
        "avg_price_per_liter": 2,
        "avg_refuel_cost": 20,
        "avg_liters_per_refuel": 10,
    }


def _expected_item(identifier, label, coefficient, judgement, related):
    return {
        "id": identifier,
        "label": label,
        "refuel_count": 1,
        "total_liters": 10,
        "total_cost": 20,
        "total_km": 100,
        "avg_consumption_l_per_100km": 10,
        "consumption_coefficient": coefficient,
        "consumption_judgement": judgement,
        "avg_price_per_liter": 2,
        "avg_refuel_cost": 20,
        "avg_liters_per_refuel": 10,
        "top_stations": [
            {
                "station_name": "R24 station",
                "refuel_count": 1,
                "total_liters": 10,
                "total_cost": 20,
            }
        ],
        "related": [related],
    }


@pytest.mark.parametrize(
    ("vehicle_type", "wc_type", "coefficient", "judgement"),
    [
        pytest.param("auto", None, 1.333, "Molto alto", id="alias-auto"),
        pytest.param("berlina", None, 1.333, "Molto alto", id="alias-berlina"),
        pytest.param("utilitaria", None, 1.333, "Molto alto", id="alias-utilitaria"),
        pytest.param("furg", None, 0.87, "OK", id="alias-furg"),
        pytest.param("van", None, 0.87, "OK", id="alias-van"),
        pytest.param("ducato", None, 0.87, "OK", id="alias-ducato"),
        pytest.param("daily", None, 0.87, "OK", id="alias-daily"),
        pytest.param("autocarro", None, 1.333, "Molto alto", id="alias-autocarro-before-truck"),
        pytest.param("camion", None, 0.385, "OK", id="alias-camion"),
        pytest.param("truck", None, 0.385, "OK", id="alias-truck"),
        pytest.param("trattore", None, 0.667, "OK", id="alias-trattore"),
        pytest.param("trattor", None, 0.667, "OK", id="alias-trattor"),
        pytest.param("escavat", None, 0.667, "OK", id="alias-escavat"),
        pytest.param("terna", None, 0.667, "OK", id="alias-terna"),
        pytest.param("auto van", None, 1.333, "Molto alto", id="collision-auto-van"),
        pytest.param("van auto", None, 1.333, "Molto alto", id="collision-reversed-auto-van"),
        pytest.param("van truck", None, 0.87, "OK", id="collision-van-truck"),
        pytest.param("truck trattore", None, 0.385, "OK", id="collision-truck-tractor"),
        pytest.param("truck van", None, 0.87, "OK", id="collision-reversed-van-truck"),
        pytest.param("terna truck van auto", None, 1.333, "Molto alto", id="collision-all"),
        pytest.param("PREFIX AUTO SUFFIX", "truck", 1.333, "Molto alto", id="primary-upper"),
        pytest.param("", "TRUCK", 0.385, "OK", id="wc-upper"),
        pytest.param(" ", "van", None, None, id="space-blocks-wc"),
        pytest.param("speciale", "auto", None, None, id="unknown-blocks-wc"),
        pytest.param("van", "auto", 0.87, "OK", id="primary-before-wc"),
        pytest.param("", None, None, None, id="both-types-missing"),
    ],
)
def test_route_vehicle_and_operator_targets_preserve_full_response_and_queries(
    database, driver, vehicle_type, wc_type, coefficient, judgement
):
    vehicle = existing._make_vehicle(database, "R24TARGET")
    vehicle.vehicle_type = vehicle_type
    vehicle.vehicle_type_wc = wc_type
    operator = existing._make_wc_operator(
        database,
        wc_id=24240,
        username="r24-driver",
        gaia_user_id=driver.id,
        first_name="R24",
        last_name="Driver",
    )
    existing._make_session(database, vehicle, driver.id, STARTED, 0, 100)
    fuel_log = existing._make_fuel_log(database, vehicle, driver.id, STARTED, 10, 20)
    fuel_log.wc_operator_id = operator.id
    fuel_log.station_name = "R24 station"
    database.flush()
    for entity in list(database.identity_map.values()):
        database.refresh(entity)
    before = [(entity, vars(entity).copy()) for entity in database.identity_map.values()]
    expected_queries = previous._compiled_queries(database, [vehicle], operator)
    captured_queries = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        captured_queries.append((statement, parameters))

    event.listen(existing.engine, "before_cursor_execute", capture)
    try:
        result = analytics.fuel_analytics(None, database, "2026-01-01", "2026-12-31", "month")
    finally:
        event.remove(existing.engine, "before_cursor_execute", capture)
    operator_id = f"wc:{operator.id}"
    vehicle_id = str(vehicle.id)
    assert result.model_dump(mode="json") == {
        "time_series": [{"period": "2026-03", "value": 10}],
        "cost_series": [{"period": "2026-03", "value": 20}],
        "top_vehicles": [
            _expected_item(
                vehicle_id,
                "R24TARGET",
                coefficient,
                judgement,
                _expected_related(operator_id, "R24 Driver"),
            )
        ],
        "top_operators": [
            _expected_item(
                operator_id,
                "R24 Driver",
                coefficient,
                judgement,
                _expected_related(vehicle_id, "R24TARGET"),
            )
        ],
        "total_liters": 10,
        "total_cost": 20,
        "avg_liters_per_refuel": 10,
        "storno_count": 0,
        "storno_liters": 0,
        "storno_cost": 0,
    }
    assert captured_queries == expected_queries
    assert not database.new and not database.dirty and not database.deleted
    for entity, state in before:
        assert vars(entity) == state


@pytest.fixture
def original_nested_classifier():
    source_path = Path(inspect.getsourcefile(analytics.fuel_analytics))
    source_tree = ast.parse(source_path.read_text())
    outer = next(
        node
        for node in source_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "fuel_analytics"
    )
    nested = next(
        node
        for node in outer.body
        if isinstance(node, ast.FunctionDef) and node.name == "_target_consumption_l_per_100km"
    )
    module = ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(nested)], type_ignores=[]))
    namespace = {"Vehicle": Vehicle}
    exec(compile(module, "<r24-live-source-nested-contract>", "exec"), namespace)
    return namespace[nested.name]


class ObservedVehicle:
    def __init__(self, events, primary, fallback=None):
        self.events = events
        self.primary = primary
        self.fallback = fallback

    @property
    def vehicle_type(self):
        self.events.append("primary:get")
        if isinstance(self.primary, Exception):
            raise self.primary
        return self.primary

    @property
    def vehicle_type_wc(self):
        self.events.append("fallback:get")
        if isinstance(self.fallback, Exception):
            raise self.fallback
        return self.fallback


class FalsyVehicle(ObservedVehicle):
    def __bool__(self):
        raise AssertionError("vehicle truthiness must not be evaluated")


class ObservedType:
    def __init__(self, events, label, lowered):
        self.events = events
        self.label = label
        self.lowered = lowered

    def __bool__(self):
        self.events.append(f"{self.label}:bool")
        return True

    def lower(self):
        self.events.append(f"{self.label}:lower")
        if isinstance(self.lowered, Exception):
            raise self.lowered
        return self.lowered


class ObservedNormalized:
    def __init__(self, events, match=None, failure_keyword=None, failure=None):
        self.events = events
        self.match = match
        self.failure_keyword = failure_keyword
        self.failure = failure

    def __bool__(self):
        self.events.append("normalized:bool")
        return True

    def __contains__(self, keyword):
        self.events.append(f"contains:{keyword}")
        if keyword == self.failure_keyword:
            raise self.failure
        return keyword == self.match


@pytest.mark.parametrize("vehicle", [None, SimpleNamespace()], ids=["none", "missing-fields"])
def test_synthetic_missing_vehicle_returns_none(original_nested_classifier, vehicle):
    assert original_nested_classifier(vehicle) is None


def test_synthetic_vehicle_truthiness_is_not_evaluated(original_nested_classifier):
    events = []
    vehicle = FalsyVehicle(events, "auto", RuntimeError("fallback must not be accessed"))
    assert original_nested_classifier(vehicle) == 7.5
    assert events == ["primary:get"]


@pytest.mark.parametrize(
    ("primary", "fallback", "target", "expected_events"),
    [
        (None, "van", 11.5, ["primary:get", "fallback:get"]),
        ("", "TRUCK", 26.0, ["primary:get", "fallback:get"]),
        ("speciale", "van", None, ["primary:get"]),
        (" ", "van", None, ["primary:get"]),
    ],
)
def test_synthetic_fallback_access_is_conditional(
    original_nested_classifier, primary, fallback, target, expected_events
):
    events = []
    assert original_nested_classifier(ObservedVehicle(events, primary, fallback)) == target
    assert events == expected_events


@pytest.mark.parametrize(
    ("match", "target", "expected_memberships"),
    [
        ("auto", 7.5, ["contains:auto"]),
        ("berlina", 7.5, ["contains:auto", "contains:berlina"]),
        (
            "van",
            11.5,
            [
                "contains:auto",
                "contains:berlina",
                "contains:utilitaria",
                "contains:furg",
                "contains:van",
            ],
        ),
        (
            "truck",
            26.0,
            [
                "contains:auto",
                "contains:berlina",
                "contains:utilitaria",
                "contains:furg",
                "contains:van",
                "contains:ducato",
                "contains:daily",
                "contains:autocarro",
                "contains:camion",
                "contains:truck",
            ],
        ),
        (
            "terna",
            15.0,
            [
                "contains:auto",
                "contains:berlina",
                "contains:utilitaria",
                "contains:furg",
                "contains:van",
                "contains:ducato",
                "contains:daily",
                "contains:autocarro",
                "contains:camion",
                "contains:truck",
                "contains:trattore",
                "contains:trattor",
                "contains:escavat",
                "contains:terna",
            ],
        ),
        (
            None,
            None,
            [
                "contains:auto",
                "contains:berlina",
                "contains:utilitaria",
                "contains:furg",
                "contains:van",
                "contains:ducato",
                "contains:daily",
                "contains:autocarro",
                "contains:camion",
                "contains:truck",
                "contains:trattore",
                "contains:trattor",
                "contains:escavat",
                "contains:terna",
            ],
        ),
    ],
)
def test_synthetic_membership_preserves_exact_prefix_and_short_circuit(
    original_nested_classifier, match, target, expected_memberships
):
    events = []
    normalized = ObservedNormalized(events, match)
    primary = ObservedType(events, "primary", normalized)
    vehicle = ObservedVehicle(events, primary, RuntimeError("fallback must not be accessed"))
    assert original_nested_classifier(vehicle) == target
    assert events == [
        "primary:get",
        "primary:bool",
        "primary:lower",
        "normalized:bool",
        "normalized:bool",
        *expected_memberships,
    ]


@pytest.mark.parametrize(
    ("boundary", "expected_events"),
    [
        ("primary-get", ["primary:get"]),
        ("fallback-get", ["primary:get", "fallback:get"]),
        ("primary-lower", ["primary:get", "primary:bool", "primary:lower"]),
        (
            "membership",
            [
                "primary:get",
                "primary:bool",
                "primary:lower",
                "normalized:bool",
                "normalized:bool",
                "contains:auto",
                "contains:berlina",
                "contains:utilitaria",
                "contains:furg",
                "contains:van",
                "contains:ducato",
                "contains:daily",
                "contains:autocarro",
                "contains:camion",
                "contains:truck",
            ],
        ),
    ],
)
def test_synthetic_failure_propagates_before_later_access(
    original_nested_classifier, boundary, expected_events
):
    events = []
    failure = RuntimeError("r24-boundary")
    vehicles = {
        "primary-get": ObservedVehicle(events, failure),
        "fallback-get": ObservedVehicle(events, "", failure),
        "primary-lower": ObservedVehicle(events, ObservedType(events, "primary", failure)),
        "membership": ObservedVehicle(
            events,
            ObservedType(events, "primary", ObservedNormalized(events, None, "truck", failure)),
        ),
    }
    with pytest.raises(RuntimeError, match="r24-boundary") as raised:
        original_nested_classifier(vehicles[boundary])
    assert raised.value is failure
    assert events == expected_events


def test_synthetic_truthy_nonstring_is_not_coerced(original_nested_classifier):
    events = []
    vehicle = ObservedVehicle(events, 1, RuntimeError("fallback must not be accessed"))
    with pytest.raises(AttributeError, match="lower"):
        original_nested_classifier(vehicle)
    assert events == ["primary:get"]


def test_synthetic_empty_lower_result_triggers_fallback(original_nested_classifier):
    events = []
    primary = ObservedType(events, "primary", "")
    fallback = ObservedType(events, "fallback", "van")
    assert original_nested_classifier(ObservedVehicle(events, primary, fallback)) == 11.5
    assert events == [
        "primary:get",
        "primary:bool",
        "primary:lower",
        "fallback:get",
        "fallback:bool",
        "fallback:lower",
    ]


def test_synthetic_getattr_attribute_error_uses_default(original_nested_classifier):
    events = []
    vehicle = ObservedVehicle(events, AttributeError("missing primary"), "van")
    assert original_nested_classifier(vehicle) == 11.5
    assert events == ["primary:get", "fallback:get"]
