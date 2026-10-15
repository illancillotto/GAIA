"""R110 characterization: id-keyed lookups issued by the anomalies endpoint."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
import test_operazioni_analytics as existing
from sqlalchemy import event
from test_operazioni_analytics_characterization import database as database
from test_operazioni_analytics_characterization import driver as driver

from app.modules.operazioni.models.activities import ActivityCatalog
from app.modules.operazioni.models.fuel_cards import FuelCard, FuelCardAssignmentHistory
from app.modules.operazioni.routes import analytics

_FROM = re.compile(r"\bFROM (\w+)")


@contextmanager
def _recorded_selects() -> Iterator[list[tuple[str, bool, tuple[str, ...]]]]:
    """Record (table, filters-by-primary-key, sorted id parameters) per SELECT."""
    recorded: list[tuple[str, bool, tuple[str, ...]]] = []

    def record(connection, cursor, statement, parameters, context, executemany):
        if not statement.lstrip().upper().startswith("SELECT"):
            return
        table = _FROM.search(statement).group(1)
        by_id = f"WHERE {table}.id IN" in statement
        params = tuple(sorted(str(value) for value in parameters)) if by_id else ()
        recorded.append((table, by_id, params))

    event.listen(existing.engine, "before_cursor_execute", record)
    try:
        yield recorded
    finally:
        event.remove(existing.engine, "before_cursor_execute", record)


def _anomalies(session, kind=None):
    return analytics.anomalies_analytics(None, session, "2025-01-01", "2027-12-31", kind)


def _seed_every_id_map(session, driver):
    """Seed rows so every guarded id lookup has a non-empty id set."""
    now = datetime.now(UTC).replace(tzinfo=None)
    vehicle = existing._make_vehicle(session, plate="R110AA")
    retired = existing._make_vehicle(session, plate="R110OP")
    gone = existing._make_user(session, "r110-gone")
    gone.is_active = False
    orphan = existing._make_session(
        session, vehicle, driver.id, now - timedelta(hours=30), 0, 10, "open"
    )
    excess = existing._make_fuel_log(session, vehicle, driver.id, now - timedelta(days=1), 150, 300)
    catalog = ActivityCatalog(code="R110", name="R110", category="test")
    session.add(catalog)
    session.flush()
    activity = existing._make_activity(
        session, catalog, driver.id, now - timedelta(days=2), 200, 30
    )
    gone_log = existing._make_fuel_log(session, retired, gone.id, now - timedelta(days=3), 5, 10)
    operator = existing._make_wc_operator(
        session, wc_id=11010, username="r110-unmapped", gaia_user_id=None
    )
    card = FuelCard(pan="r110-card", codice="R110-CARD")
    session.add(card)
    session.flush()
    assignment = FuelCardAssignmentHistory(
        fuel_card_id=card.id, wc_operator_id=operator.id, start_at=datetime(2026, 3, 15)
    )
    session.add(assignment)
    session.flush()
    return {
        "vehicle": vehicle,
        "retired": retired,
        "gone": gone,
        "orphan": orphan,
        "excess": excess,
        "activity": activity,
        "gone_log": gone_log,
        "operator": operator,
        "card": card,
        "assignment": assignment,
    }


def test_populated_id_maps_issue_same_selects_in_same_order(database, driver):
    seeded = _seed_every_id_map(database, driver)

    with _recorded_selects() as recorded:
        result = _anomalies(database)

    vehicle = (seeded["vehicle"].id.hex,)
    driver_id = (str(driver.id),)
    assert recorded == [
        ("vehicle_usage_session", False, ()),
        ("vehicle", True, vehicle),
        ("wc_operator", False, ()),
        ("vehicle_usage_session", False, ()),
        ("vehicle", True, vehicle),
        ("application_users", True, driver_id),
        ("vehicle_assignment", False, ()),
        ("vehicle_fuel_log", False, ()),
        ("vehicle", True, vehicle),
        ("wc_refuel_event", False, ()),
        ("operator_activity", False, ()),
        ("application_users", True, driver_id),
        ("vehicle", False, ()),
        ("application_users", False, ()),
        ("vehicle_fuel_log", False, ()),
        ("vehicle_usage_session", False, ()),
        ("application_users", True, (str(seeded["gone"].id),)),
        ("vehicle", True, (seeded["retired"].id.hex,)),
        ("fuel_card_assignment_history", False, ()),
        ("wc_operator", True, (seeded["operator"].id.hex,)),
        ("fuel_card", True, (seeded["card"].id.hex,)),
    ]
    labels = {item.id: item for item in result.items}
    assert labels[f"orphan_{seeded['orphan'].id}"].entity_label == "R110AA"
    assert labels[f"fuel_{seeded['excess'].id}"].entity_label == "R110AA"
    assert labels[f"hours_{seeded['activity'].id}"].entity_label == "characterization-driver"
    gone_item = labels[f"inact_op_log_{seeded['gone_log'].id}"]
    assert gone_item.entity_label == "r110-gone"
    assert gone_item.details["vehicle"] == "R110OP"
    card_item = labels[f"orphan_card_{seeded['assignment'].id}"]
    assert card_item.entity_label == "R110-CARD"
    assert card_item.details["operator"] == "r110-unmapped"


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("orphan_session", [("vehicle_usage_session", False, ())]),
        ("excessive_fuel", [("vehicle_fuel_log", False, ())]),
        ("hours_discrepancy", [("operator_activity", False, ())]),
        ("orphan_fuel_card", [("fuel_card_assignment_history", False, ())]),
    ],
)
def test_empty_id_sets_issue_no_lookup_select(database, driver, kind, expected):
    with _recorded_selects() as recorded:
        result = _anomalies(database, kind)

    assert recorded == expected
    assert result.items == []
    assert result.total == 0


def test_inactive_operator_without_rows_skips_only_guarded_vehicle_lookup(database, driver):
    driver.is_active = False
    database.flush()

    with _recorded_selects() as recorded:
        result = _anomalies(database, "inactive_operator")

    assert recorded == [
        ("application_users", False, ()),
        ("vehicle_fuel_log", False, ()),
        ("vehicle_usage_session", False, ()),
        ("application_users", True, ()),
    ]
    assert result.items == []
