"""Original route attribution and separately bounded live-source AST contracts."""

import ast
import copy
import inspect
import math
import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import test_operazioni_analytics as existing
from sqlalchemy import event, select
from test_operazioni_analytics_characterization import database as database
from test_operazioni_analytics_characterization import driver as driver

from app.modules.operazioni.models.vehicles import Vehicle, VehicleFuelLog, VehicleUsageSession
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.routes import analytics

STARTED = datetime(2026, 3, 15, 8)
WC_KEY = uuid.UUID("00000000-0000-0000-0000-000000000014")
VEHICLE_KEY = uuid.UUID("00000000-0000-0000-0000-000000000015")
NO_OPERATOR = "__no_operator__"
ALL_NAMES = (("Mario Rossi", 40, 0), ("Rossi Mario", 60, 1), ("mrossi", 80, 1))


def _compiled_queries(database, vehicles, operator):
    queries = [
        select(VehicleFuelLog).where(
            VehicleFuelLog.fueled_at >= datetime(2026, 1, 1),
            VehicleFuelLog.fueled_at <= datetime(2026, 12, 31, 23, 59, 59, 999999),
        ),
        select(VehicleUsageSession).where(
            VehicleUsageSession.started_at >= datetime(2026, 1, 1),
            VehicleUsageSession.started_at <= datetime(2026, 12, 31, 23, 59, 59, 999999),
            VehicleUsageSession.status != "open",
        ),
        select(Vehicle).where(Vehicle.id.in_({vehicle.id for vehicle in vehicles})),
        select(WCOperator).where(WCOperator.id.in_({operator.id})),
        select(Vehicle).where(Vehicle.id.in_({vehicle.id for vehicle in vehicles})),
    ]
    expected = []
    for query in queries:
        compiled = query.compile(
            dialect=database.bind.dialect, compile_kwargs={"render_postcompile": True}
        )
        parameters = []
        for parameter in compiled.positiontup:
            bind = compiled.binds.get(parameter)
            if bind is None:
                bind = compiled.binds[parameter.rsplit("_", 1)[0]]
            processor = bind.type.dialect_impl(database.bind.dialect).bind_processor(
                database.bind.dialect
            )
            value = compiled.params[parameter]
            parameters.append(processor(value) if processor else value)
        expected.append((str(compiled), tuple(parameters)))
    return expected


def _related(entity_id, label, liters):
    return {
        "id": entity_id,
        "label": label,
        "refuel_count": 1,
        "total_liters": liters,
        "total_cost": liters * 2,
        "avg_price_per_liter": 2,
        "avg_refuel_cost": liters * 2,
        "avg_liters_per_refuel": liters,
    }


def _expected_vehicle(vehicle, distance, liters, target, operator_id, label):
    positive_distance = distance is not None and distance > 0
    consumption = round(liters / distance * 100, 2) if positive_distance else None
    coefficient = round(liters / distance * 100 / target, 3) if positive_distance else None
    raw_coefficient = liters / distance * 100 / target if positive_distance else None
    judgement = None
    if raw_coefficient is not None:
        judgement = (
            "OK" if raw_coefficient <= 1.1 else "Alto" if raw_coefficient <= 1.3 else "Molto alto"
        )
    return {
        **_related(str(vehicle.id), vehicle.plate_number, liters),
        "total_km": round(distance, 1) if distance is not None else None,
        "avg_consumption_l_per_100km": consumption,
        "consumption_coefficient": coefficient,
        "consumption_judgement": judgement,
        "top_stations": [
            {
                "station_name": "R14 station",
                "refuel_count": 1,
                "total_liters": liters,
                "total_cost": liters * 2,
            }
        ],
        "related": [_related(operator_id, label, liters)],
    }


def _assert_route_contract(database, driver, linked_distance, names, parts, chosen_km, target):
    vehicles = [
        existing._make_vehicle(database, "R14AUTO"),
        existing._make_vehicle(database, "R14VAN"),
    ]
    vehicles[0].vehicle_type = "auto"
    vehicles[1].vehicle_type = "van"
    operator = existing._make_wc_operator(
        database,
        wc_id=14140,
        username=parts[2],
        gaia_user_id=driver.id,
        first_name=parts[0],
        last_name=parts[1],
    )
    distances = [None, None]
    if linked_distance is not None:
        linked_parts = [(0, linked_distance)] if linked_distance <= 0 else [(0, 25), (1, 75)]
        for vehicle_index, distance in linked_parts:
            usage = existing._make_session(
                database, vehicles[vehicle_index], driver.id, STARTED, 0, 0
            )
            usage.route_distance_km = Decimal(str(distance))
            distances[vehicle_index] = (distances[vehicle_index] or 0) + distance
    for name, distance, vehicle_index in names:
        usage = existing._make_session(database, vehicles[vehicle_index], driver.id, STARTED, 0, 0)
        usage.actual_driver_user_id = None
        usage.operator_name = name
        usage.route_distance_km = Decimal(str(distance))
        distances[vehicle_index] = (distances[vehicle_index] or 0) + distance
    for vehicle, liters in zip(vehicles, [10, 20], strict=True):
        log = existing._make_fuel_log(database, vehicle, driver.id, STARTED, liters, liters * 2)
        log.wc_operator_id = operator.id
        log.station_name = "R14 station"
    database.flush()
    for entity in list(database.identity_map.values()):
        database.refresh(entity)
    before = [(entity, vars(entity).copy()) for entity in database.identity_map.values()]
    expected_sql = _compiled_queries(database, vehicles, operator)
    captured = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        captured.append((statement, parameters))

    event.listen(existing.engine, "before_cursor_execute", capture)
    try:
        result = analytics.fuel_analytics(None, database, "2026-01-01", "2026-12-31", "month")
    finally:
        event.remove(existing.engine, "before_cursor_execute", capture)
    assert captured == expected_sql
    assert all(statement.lstrip().startswith("SELECT") for statement, _parameters in captured)
    assert not database.new and not database.dirty and not database.deleted
    for entity, state in before:
        assert vars(entity) == state
    operator_id = f"wc:{operator.id}"
    label = f"{parts[0] or ''} {parts[1] or ''}".strip() or parts[2] or str(operator.id)
    consumption = round(3000 / chosen_km, 2) if chosen_km > 0 else None
    coefficient = round(consumption / target, 3) if consumption is not None else None
    expected_operator = {
        "id": operator_id,
        "label": label,
        "refuel_count": 2,
        "total_liters": 30,
        "total_cost": 60,
        "total_km": chosen_km if chosen_km > 0 else None,
        "avg_consumption_l_per_100km": consumption,
        "consumption_coefficient": coefficient,
        "consumption_judgement": "Molto alto" if consumption is not None else None,
        "avg_price_per_liter": 2,
        "avg_refuel_cost": 30,
        "avg_liters_per_refuel": 15,
        "top_stations": [
            {"station_name": "R14 station", "refuel_count": 2, "total_liters": 30, "total_cost": 60}
        ],
        "related": [
            _related(str(vehicles[1].id), "R14VAN", 20),
            _related(str(vehicles[0].id), "R14AUTO", 10),
        ],
    }
    assert result.model_dump(mode="json") == {
        "time_series": [{"period": "2026-03", "value": 30}],
        "cost_series": [{"period": "2026-03", "value": 60}],
        "top_vehicles": [
            _expected_vehicle(vehicles[1], distances[1], 20, 11.5, operator_id, label),
            _expected_vehicle(vehicles[0], distances[0], 10, 7.5, operator_id, label),
        ],
        "top_operators": [expected_operator],
        "total_liters": 30,
        "total_cost": 60,
        "avg_liters_per_refuel": 15,
        "storno_count": 0,
        "storno_liters": 0,
        "storno_cost": 0,
    }


@pytest.mark.parametrize(
    ("linked_distance", "names", "chosen_km", "target"),
    [
        pytest.param(100, ALL_NAMES, 100, 10.5, id="linked-positive-beats-three-names-and-targets"),
        pytest.param(0, ALL_NAMES, 40, 7.5, id="linked-zero-first-name"),
        pytest.param(-25, ALL_NAMES, 40, 7.5, id="linked-negative-first-name"),
        pytest.param(None, ALL_NAMES, 40, 7.5, id="linked-missing-first-name"),
        pytest.param(None, ALL_NAMES[1:], 60, 11.5, id="reverse-before-username"),
        pytest.param(None, ALL_NAMES[2:], 80, 11.5, id="username-after-missing-display-names"),
        pytest.param(None, (), 0, None, id="all-maps-missing"),
        pytest.param(
            0,
            (("Mario Rossi", 0, 0), *ALL_NAMES[1:]),
            0,
            None,
            id="first-zero-blocks-later-positive",
        ),
        pytest.param(
            0,
            (("Mario Rossi", -40, 0), *ALL_NAMES[1:]),
            -40,
            None,
            id="first-negative-blocks-later-positive",
        ),
    ],
)
def test_route_ordered_kilometres_and_vehicle_targets(
    database, driver, linked_distance, names, chosen_km, target
):
    _assert_route_contract(
        database, driver, linked_distance, names, ("Mario", "Rossi", "mrossi"), chosen_km, target
    )


@pytest.mark.parametrize(
    ("parts", "names", "chosen_km", "target"),
    [
        pytest.param(
            (" Mario", "Rossi ", "mrossi"), ALL_NAMES, 40, 7.5, id="strip-display-outer-whitespace"
        ),
        pytest.param(
            ("Mario ", " Rossi", "mrossi"),
            (("Mario Rossi", 17, 0), ("Mario   Rossi", 23, 1)),
            23,
            11.5,
            id="internal-spaces-exact",
        ),
        pytest.param(
            ("Mario", "Rossi", "mrossi"),
            (("mario rossi", 17, 0), ("ROSSI MARIO", 23, 1), ("MROSSI", 31, 1)),
            0,
            None,
            id="case-mismatch-does-not-match",
        ),
        pytest.param(
            (None, "Rossi", "mrossi"),
            (("Rossi", 17, 0), ("mrossi", 31, 1)),
            17,
            7.5,
            id="nullable-first-name",
        ),
        pytest.param(
            ("Mario", None, "mrossi"),
            (("Mario", 17, 0), ("mrossi", 31, 1)),
            17,
            7.5,
            id="nullable-last-name",
        ),
        pytest.param(
            (None, None, " mrossi "),
            (("mrossi", 17, 0), (" mrossi ", 31, 1)),
            31,
            11.5,
            id="username-whitespace-not-stripped",
        ),
        pytest.param(
            (None, None, ""), (("Mario Rossi", 17, 0),), 0, None, id="empty-variants-skipped"
        ),
    ],
)
def test_route_exact_name_formatting_and_nonmatches(
    database, driver, parts, names, chosen_km, target
):
    _assert_route_contract(database, driver, None, names, parts, chosen_km, target)


@pytest.fixture
def nested_ast_factory():
    """Compile the live nested node with original closure names, not an implementation copy."""
    source_path = Path(inspect.getsourcefile(analytics.fuel_analytics))
    tree = ast.parse(source_path.read_text())
    outer = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "fuel_analytics"
    )
    nested = next(
        node for node in outer.body if isinstance(node, ast.FunctionDef) and node.name == "_op_km"
    )
    variants = next(
        node
        for node in outer.body
        if isinstance(node, ast.FunctionDef) and node.name == "_operator_name_variants"
    )
    closure_names = [
        "_uuid",
        "_NO_OPERATOR",
        "wc_ops_map",
        "km_by_gaia_user",
        "km_by_gaia_user_vehicle",
        "km_by_op_name",
        "km_by_op_name_vehicle",
    ]
    factory = ast.FunctionDef(
        name="capture_original_nested_contract",
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg=name) for name in closure_names],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        ),
        body=[
            copy.deepcopy(variants),
            copy.deepcopy(nested),
            ast.Return(value=ast.Name(id="_op_km", ctx=ast.Load())),
        ],
        decorator_list=[],
    )
    module = ast.fix_missing_locations(ast.Module(body=[factory], type_ignores=[]))
    namespace = {"WCOperator": WCOperator}
    exec(compile(module, "<r14-live-source-nested-contract>", "exec"), namespace)
    return namespace[factory.name]


def _nested_contract(
    factory, operator=None, gaia=None, names=None, gaia_vehicle=None, name_vehicle=None
):
    return factory(
        uuid,
        NO_OPERATOR,
        {WC_KEY: operator} if operator is not None else {},
        {} if gaia is None else gaia,
        {} if gaia_vehicle is None else gaia_vehicle,
        {} if names is None else names,
        {} if name_vehicle is None else name_vehicle,
    )


def _operator(link=None, first="Mario", last="Rossi", username="mrossi"):
    return SimpleNamespace(gaia_user_id=link, first_name=first, last_name=last, username=username)


@pytest.mark.parametrize("distance", [0.0, -4.0, math.nan])
def test_nested_ast_nonpositive_link_falls_back_to_first_name(nested_ast_factory, distance):
    function = _nested_contract(
        nested_ast_factory,
        _operator(7),
        {7: distance},
        {"Mario Rossi": 11, "Rossi Mario": 12},
        name_vehicle={"Mario Rossi": {VEHICLE_KEY: 11}, "Rossi Mario": {VEHICLE_KEY: 12}},
    )
    assert function(WC_KEY) == (11, {VEHICLE_KEY: 11})


@pytest.mark.parametrize("distance", [0.0, -4.0, math.nan])
def test_nested_ast_first_existing_name_stops_even_for_nonpositive_or_nan(
    nested_ast_factory, distance
):
    vehicles = {VEHICLE_KEY: distance}
    function = _nested_contract(
        nested_ast_factory,
        _operator(),
        names={"Mario Rossi": distance, "Rossi Mario": 12, "mrossi": 13},
        name_vehicle={"Mario Rossi": vehicles, "Rossi Mario": {}, "mrossi": {}},
    )
    total, copied = function(WC_KEY)
    if math.isnan(distance):
        assert math.isnan(total)
        assert math.isnan(copied[VEHICLE_KEY])
    else:
        assert total == distance
        assert copied == vehicles
    assert copied is not vehicles


@pytest.mark.parametrize(
    ("link", "gaia", "expected"),
    [
        (None, {0: 99}, 11),
        (0, {0: 99}, 11),
        ("", {0: 99}, 11),
        ("0", {0: 99}, 99),
        ("7", {7: 17}, 17),
        ("-7", {-7: 19}, 19),
    ],
)
def test_nested_ast_truthiness_precedes_integer_link_conversion(
    nested_ast_factory, link, gaia, expected
):
    function = _nested_contract(
        nested_ast_factory,
        _operator(link),
        gaia,
        {"Mario Rossi": 11},
        name_vehicle={"Mario Rossi": {}},
    )
    assert function(WC_KEY) == (expected, {})


@pytest.mark.parametrize(
    ("operator", "gaia", "names", "gaia_vehicle", "name_vehicle", "exception", "message"),
    [
        (
            _operator("invalid"),
            {},
            {"Mario Rossi": 11},
            {},
            {},
            ValueError,
            "invalid literal for int() with base 10: 'invalid'",
        ),
        (
            _operator(7),
            {7: "100"},
            {"Mario Rossi": 11},
            {},
            {},
            TypeError,
            "'>' not supported between instances of 'str' and 'int'",
        ),
        (_operator(), {}, {"Mario Rossi": 11}, {}, {}, KeyError, "'Mario Rossi'"),
        (
            _operator(),
            {},
            {"Mario Rossi": 11},
            {},
            {"Mario Rossi": None},
            TypeError,
            "'NoneType' object is not iterable",
        ),
        (_operator(7), {7: 11}, {}, {7: None}, {}, TypeError, "'NoneType' object is not iterable"),
    ],
)
def test_nested_ast_conversion_comparison_and_map_exceptions_are_not_swallowed(
    nested_ast_factory, operator, gaia, names, gaia_vehicle, name_vehicle, exception, message
):
    function = _nested_contract(
        nested_ast_factory, operator, gaia, names, gaia_vehicle, name_vehicle
    )
    with pytest.raises(exception) as captured:
        function(WC_KEY)
    assert str(captured.value) == message


@pytest.mark.parametrize("path", ["linked", "name", "legacy"])
def test_nested_ast_returns_fresh_shallow_vehicle_dictionary(nested_ast_factory, path):
    nested_value = {"mutable": 7}
    source = {VEHICLE_KEY: nested_value}
    function = _nested_contract(
        nested_ast_factory,
        _operator(7 if path == "linked" else None),
        {7: Decimal("2.5")} if path == "linked" else {},
        {"Mario Rossi": 11},
        {7: source},
        {"Mario Rossi": source},
    )
    key = "Mario Rossi" if path == "legacy" else WC_KEY
    total, copied = function(key)
    assert total == (Decimal("2.5") if path == "linked" else 11)
    if path == "linked":
        assert isinstance(total, Decimal)
    assert copied == source and copied is not source
    assert copied[VEHICLE_KEY] is nested_value
    copied["added"] = 3
    assert "added" not in source
    copied[VEHICLE_KEY]["mutable"] = 8
    assert nested_value == {"mutable": 8}


def test_nested_ast_defaults_keep_totals_and_vehicle_maps_independent(nested_ast_factory):
    linked = _nested_contract(nested_ast_factory, _operator(7), {7: 17})
    assert linked(WC_KEY) == (17, {})
    legacy = _nested_contract(nested_ast_factory, name_vehicle={"legacy": {VEHICLE_KEY: 17}})
    assert legacy("legacy") == (0.0, {VEHICLE_KEY: 17})


@pytest.mark.parametrize("path", ["linked", "name", "legacy"])
def test_nested_ast_defaultdict_get_and_direct_index_insertion_differ(nested_ast_factory, path):
    vehicles = defaultdict(lambda: defaultdict(float))
    function = _nested_contract(
        nested_ast_factory,
        _operator(7 if path == "linked" else None),
        {7: 17},
        {"Mario Rossi": 11},
        vehicles,
        vehicles,
    )
    key = "Mario Rossi" if path == "legacy" else WC_KEY
    assert function(key) == (17 if path == "linked" else 11, {})
    assert list(vehicles) == (["Mario Rossi"] if path == "name" else [])


@pytest.mark.parametrize(
    ("key", "names", "expected"),
    [
        (WC_KEY, {"Mario Rossi": 77}, 0),
        (str(WC_KEY), {str(WC_KEY): 77}, 77),
        ("", {"": 77}, 77),
        (NO_OPERATOR, {NO_OPERATOR: 77}, 0),
        (None, {"Mario Rossi": 77}, 0),
        (14, {"Mario Rossi": 77}, 0),
        (False, {"Mario Rossi": 77}, 0),
        ([], {"Mario Rossi": 77}, 0),
        ({}, {"Mario Rossi": 77}, 0),
    ],
)
def test_nested_ast_key_kind_legacy_and_sentinel_contract(nested_ast_factory, key, names, expected):
    function = _nested_contract(nested_ast_factory, names=names)
    assert function(key) == (expected, {})


def test_nested_ast_unsupported_key_does_not_access_any_map(nested_ast_factory):
    class NoLookup(dict):
        def get(self, key, default=None):
            pytest.fail("Unsupported key must not look up any map")

    forbidden = NoLookup()
    function = nested_ast_factory(
        uuid, NO_OPERATOR, forbidden, forbidden, forbidden, forbidden, forbidden
    )
    assert function([]) == (0.0, {})


def test_nested_ast_positive_link_does_not_read_display_properties(nested_ast_factory):
    class PositiveOperator:
        gaia_user_id = 7

        @property
        def first_name(self):
            pytest.fail("Positive linked kilometres must short-circuit display properties")

        @property
        def last_name(self):
            pytest.fail("Positive linked kilometres must short-circuit display properties")

        @property
        def username(self):
            pytest.fail("Positive linked kilometres must short-circuit display properties")

    function = _nested_contract(nested_ast_factory, PositiveOperator(), {7: 17})
    assert function(WC_KEY) == (17, {})


@pytest.mark.parametrize("distance", [100, 0, -4, math.nan])
def test_nested_ast_property_and_mapping_access_order(nested_ast_factory, distance):
    observed = []

    class TracedOperator:
        def __getattribute__(self, name):
            observed.append(("operator", name))
            return {
                "gaia_user_id": 7,
                "first_name": "Mario",
                "last_name": "Rossi",
                "username": "mrossi",
            }[name]

    class TracedMap(dict):
        def __init__(self, label, values):
            self.label = label
            super().__init__(values)

        def get(self, key, default=None):
            observed.append((self.label, "get", key))
            return super().get(key, default)

        def __contains__(self, key):
            observed.append((self.label, "contains", key))
            return super().__contains__(key)

        def __getitem__(self, key):
            observed.append((self.label, "item", key))
            return super().__getitem__(key)

    function = nested_ast_factory(
        uuid,
        NO_OPERATOR,
        TracedMap("wc", {WC_KEY: TracedOperator()}),
        TracedMap("gaia", {7: distance}),
        TracedMap("gaia_vehicle", {7: {VEHICLE_KEY: distance}}),
        TracedMap("names", {"Mario Rossi": 11, "Rossi Mario": 12, "mrossi": 13}),
        TracedMap("name_vehicle", {"Mario Rossi": {VEHICLE_KEY: 11}}),
    )
    expected = [
        ("wc", "get", WC_KEY),
        ("operator", "gaia_user_id"),
        ("operator", "gaia_user_id"),
        ("gaia", "get", 7),
    ]
    if distance > 0:
        assert function(WC_KEY) == (100, {VEHICLE_KEY: 100})
        expected.append(("gaia_vehicle", "get", 7))
    else:
        assert function(WC_KEY) == (11, {VEHICLE_KEY: 11})
        expected.extend(
            [
                ("operator", "first_name"),
                ("operator", "last_name"),
                ("operator", "last_name"),
                ("operator", "first_name"),
                ("operator", "username"),
                ("names", "contains", "Mario Rossi"),
                ("names", "item", "Mario Rossi"),
                ("name_vehicle", "item", "Mario Rossi"),
            ]
        )
    assert observed == expected


def test_nested_ast_name_variants_are_eager_before_first_existing_match(nested_ast_factory):
    class EagerOperator:
        gaia_user_id = None
        first_name = "Mario"
        last_name = "Rossi"

        @property
        def username(self):
            raise RuntimeError("username evaluated before name membership")

    function = _nested_contract(
        nested_ast_factory,
        EagerOperator(),
        names={"Mario Rossi": 11},
        name_vehicle={"Mario Rossi": {}},
    )
    with pytest.raises(RuntimeError, match=r"^username evaluated before name membership$"):
        function(WC_KEY)
