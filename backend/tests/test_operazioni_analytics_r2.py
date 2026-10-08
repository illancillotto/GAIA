"""Analytics readiness contracts against persisted domain data."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import test_operazioni_analytics as existing
from sqlalchemy import event, select
from test_operazioni_analytics_characterization import database as database
from test_operazioni_analytics_characterization import driver as driver

from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.activities import ActivityCatalog
from app.modules.operazioni.models.fuel_cards import FuelCard, FuelCardAssignmentHistory
from app.modules.operazioni.models.organizational import Team
from app.modules.operazioni.models.vehicles import VehicleAssignment, VehicleFuelLog, WCRefuelEvent
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.routes import analytics


def _anomalies(session, kind=None):
    return analytics.anomalies_analytics(None, session, "2025-01-01", "2027-12-31", kind)


def _fuel(session):
    return analytics.fuel_analytics(None, session, "2026-01-01", "2026-12-31", "month")


@pytest.mark.parametrize("name", ["Mario Rossi", "Rossi Mario", "unknown", None, " "])
def test_orphan_sessions_match_linked_or_name_operator_without_mutation(database, driver, name):
    now = datetime.now(UTC).replace(tzinfo=None)
    vehicle = existing._make_vehicle(database)
    operator = existing._make_wc_operator(
        database,
        wc_id=10001,
        username="mrossi",
        gaia_user_id=driver.id,
        first_name="Mario",
        last_name="Rossi",
    )
    linked = existing._make_session(
        database, vehicle, driver.id, now - timedelta(hours=30), 0, 100, "open"
    )
    linked.operator_name = name
    legacy = existing._make_session(
        database, vehicle, driver.id, now - timedelta(hours=60), 0, 100, "open"
    )
    legacy.actual_driver_user_id = None
    legacy.operator_name = name
    existing._make_session(database, vehicle, driver.id, now - timedelta(hours=12), 0, 100, "open")
    database.flush()

    result = _anomalies(database, "orphan_session")

    assert result.total == 2
    assert result.by_type == {"orphan_session": 2}
    assert result.by_severity == {"high": 1, "medium": 1}
    assert [item.entity_id for item in result.items] == [str(legacy.id), str(linked.id)]
    assert result.items[1].details["operator_id"] == str(operator.id)
    assert result.items[1].details["operator_name"] == "Mario Rossi"
    legacy_matches = name in ["Mario Rossi", "Rossi Mario"]
    assert result.items[0].details["operator_id"] == (str(operator.id) if legacy_matches else None)
    assert result.items[0].details["operator_name"] == (
        "Mario Rossi" if legacy_matches else name or None
    )
    assert not database.dirty


@pytest.mark.parametrize("kind", ["inactive_vehicle", "inactive_operator"])
def test_inactive_entity_anomalies_include_fuel_and_sessions_in_period(database, driver, kind):
    vehicle = existing._make_vehicle(database)
    vehicle.is_active = kind != "inactive_vehicle"
    driver.is_active = kind != "inactive_operator"
    base = datetime(2026, 3, 15, 8)
    log = existing._make_fuel_log(database, vehicle, driver.id, base, 10, 20)
    usage = existing._make_session(database, vehicle, driver.id, base, 0, 100)
    existing._make_fuel_log(database, vehicle, driver.id, datetime(2024, 1, 1), 50, 100)
    database.flush()

    result = _anomalies(database, kind)

    assert result.total == 2
    assert result.by_type == {kind: 2}
    assert result.by_severity == {"high": 2}
    assert result.items[0].id.endswith(str(log.id))
    assert result.items[1].id.endswith(str(usage.id))
    if kind == "inactive_vehicle":
        assert all(item.entity_id == str(vehicle.id) for item in result.items)
        assert result.items[0].details == {"liters": 10, "vehicle_code": vehicle.code}
    else:
        assert all(item.entity_id == str(driver.id) for item in result.items)
        assert result.items[0].details == {"liters": 10, "vehicle": vehicle.plate_number}


@pytest.mark.parametrize(
    ("enabled", "linked"), [(False, False), (False, True), (True, False), (True, True)]
)
def test_orphan_fuel_card_classification_preserves_disabled_and_unmapped_reasons(
    database, driver, enabled, linked
):
    operator = existing._make_wc_operator(
        database,
        wc_id=10002,
        username="mrossi",
        gaia_user_id=driver.id if linked else None,
        first_name="Mario",
        last_name="Rossi",
    )
    operator.enabled = enabled
    card = FuelCard(pan="r2-card", codice="CARD-01")
    database.add(card)
    database.flush()
    open_assignment = FuelCardAssignmentHistory(
        fuel_card_id=card.id, wc_operator_id=operator.id, start_at=datetime(2026, 3, 15)
    )
    database.add(open_assignment)
    database.add(
        FuelCardAssignmentHistory(
            fuel_card_id=card.id,
            wc_operator_id=operator.id,
            start_at=datetime(2026, 3, 1),
            end_at=datetime(2026, 3, 14),
        )
    )
    database.add(
        FuelCardAssignmentHistory(
            fuel_card_id=card.id, wc_operator_id=None, start_at=datetime(2026, 3, 15)
        )
    )
    database.flush()

    result = _anomalies(database, "orphan_fuel_card")

    if enabled and linked:
        assert result.items == []
        return
    expected = []
    if not enabled:
        expected.append("operatore WC disabilitato")
    if not linked:
        expected.append("operatore non collegato a utente GAIA")
    assert result.total == 1
    item = result.items[0]
    assert item.id == f"orphan_card_{open_assignment.id}"
    assert item.entity_label == "CARD-01"
    assert item.details == {"operator": "Rossi Mario", "reasons": expected}
    assert item.severity == "medium"


def test_driver_mismatch_respects_assignment_dates_and_ignores_team_assignments(database, driver):
    vehicle = existing._make_vehicle(database)
    base = datetime(2026, 3, 15, 8)
    session = existing._make_session(database, vehicle, driver.id, base, 0, 100)
    other = ApplicationUser(
        username="assigned-other",
        email="assigned@example.local",
        password_hash="unused",
        role="viewer",
        is_active=True,
    )
    database.add(other)
    database.flush()
    for start, end, target in [
        (base - timedelta(days=1), None, "operator"),
        (base - timedelta(days=2), base - timedelta(hours=1), "operator"),
        (base + timedelta(hours=1), None, "operator"),
        (base - timedelta(days=1), None, "team"),
    ]:
        database.add(
            VehicleAssignment(
                vehicle_id=vehicle.id,
                assignment_target_type=target,
                operator_user_id=other.id,
                assigned_by_user_id=driver.id,
                start_at=start,
                end_at=end,
            )
        )
    database.flush()

    result = _anomalies(database, "driver_mismatch")

    assert result.total == 1
    assert result.items[0].entity_id == str(session.id)
    assert result.items[0].details == {
        "actual_driver": driver.username,
        "assigned_operator_ids": [str(other.id)],
    }


def test_hours_discrepancy_exact_thresholds_and_severity(database, driver):
    catalog = ActivityCatalog(code="r2-hours", name="Hours")
    database.add(catalog)
    database.flush()
    base = datetime(2026, 3, 15, 8)
    for difference in [60, 61, 119, 120]:
        existing._make_activity(database, catalog, driver.id, base, difference, calculated_min=0)
    database.flush()

    result = _anomalies(database, "hours_discrepancy")

    assert result.total == 3
    assert [item.details["diff_min"] for item in result.items] == [120, 61, 119]
    assert result.by_severity == {"low": 2, "medium": 1}


@pytest.mark.parametrize(
    ("vehicle_code", "operator_name", "label"),
    [("V1", "Mario", "V1"), (None, "Mario", "Mario"), (None, None, "\u2013")],
)
def test_unmatched_refuel_labels_follow_existing_priority(
    database, vehicle_code, operator_name, label
):
    event = WCRefuelEvent(
        wc_id=10003,
        fueled_at=datetime(2026, 3, 15),
        vehicle_code=vehicle_code,
        operator_name=operator_name,
    )
    database.add(event)
    database.flush()

    result = _anomalies(database, "unmatched_refuel")

    assert result.total == 1
    assert result.items[0].entity_label == label
    assert result.items[0].details == {"wc_id": 10003, "operator": operator_name}


def test_unknown_anomaly_type_returns_no_records(database):
    result = _anomalies(database, "unsupported")
    assert result.items == []
    assert result.total == 0
    assert result.by_type == {}
    assert result.by_severity == {}


@pytest.mark.parametrize(
    ("gaia_link", "session_name"), [(True, None), (False, "legacy"), (False, None)]
)
def test_fuel_operator_without_positive_distance_has_no_consumption(
    database, driver, gaia_link, session_name
):
    vehicle = existing._make_vehicle(database)
    base = datetime(2026, 3, 15, 8)
    operator = existing._make_wc_operator(
        database, wc_id=10004, username="legacy", gaia_user_id=driver.id if gaia_link else None
    )
    usage = existing._make_session(database, vehicle, driver.id, base, 0, 0)
    usage.actual_driver_user_id = driver.id if gaia_link else None
    usage.operator_name = session_name
    log = existing._make_fuel_log(database, vehicle, driver.id, base, 10, 20)
    log.wc_operator_id = operator.id
    database.flush()

    item = _fuel(database).top_operators[0]

    assert item.label == "legacy"
    assert item.total_km is None
    assert item.avg_consumption_l_per_100km is None
    assert item.consumption_coefficient is None
    assert item.consumption_judgement is None


def test_fuel_legacy_operator_distance_and_weighted_unknown_vehicle_type(database, driver):
    vehicle = existing._make_vehicle(database)
    vehicle.vehicle_type = "unknown"
    base = datetime(2026, 3, 15, 8)
    usage = existing._make_session(database, vehicle, driver.id, base, 0, 100)
    usage.actual_driver_user_id = None
    usage.operator_name = "legacy"
    log = existing._make_fuel_log(database, vehicle, driver.id, base, 10, 20)
    log.operator_name = "legacy"
    database.flush()

    item = _fuel(database).top_operators[0]

    assert item.id == "name:legacy"
    assert item.total_km == 100
    assert item.avg_consumption_l_per_100km == 10
    assert item.consumption_coefficient is None
    assert item.related[0].id == str(vehicle.id)


def test_fuel_storno_only_group_has_null_positive_means(database, driver):
    vehicle = existing._make_vehicle(database)
    base = datetime(2026, 3, 15, 8)
    existing._make_fuel_log(database, vehicle, driver.id, base, -10, -20)
    usage = existing._make_session(database, vehicle, driver.id, base, 0, 100)
    usage.end_odometer_km = None
    database.flush()

    result = _fuel(database)

    assert result.total_liters == -10
    assert result.avg_liters_per_refuel == 0
    item = result.top_vehicles[0]
    assert item.total_km == 0
    assert item.avg_price_per_liter is None
    assert item.avg_refuel_cost is None
    assert item.avg_liters_per_refuel is None


def test_display_name_falls_back_to_ids_for_empty_labels():
    user = ApplicationUser(id=42, username="")
    assert analytics._user_display_name(user) == "42"
    operator = existing.WCOperator(id=uuid.uuid4(), username="", first_name=None, last_name=None)
    assert analytics._wc_operator_display_name(operator) == str(operator.id)


def test_fuel_weighted_target_ignores_vehicles_without_refuel_metadata(database, driver):
    fuel_vehicle = existing._make_vehicle(database, "FUEL01")
    session_only_vehicle = existing._make_vehicle(database, "SESSION01")
    base = datetime(2026, 3, 15, 8)
    operator = existing._make_wc_operator(
        database, wc_id=10005, username="linked", gaia_user_id=driver.id
    )
    existing._make_session(database, fuel_vehicle, driver.id, base, 0, 100)
    existing._make_session(database, session_only_vehicle, driver.id, base, 0, 200)
    log = existing._make_fuel_log(database, fuel_vehicle, driver.id, base, 10, 20)
    log.wc_operator_id = operator.id
    database.flush()

    item = _fuel(database).top_operators[0]

    assert item.total_km == 300
    assert item.avg_consumption_l_per_100km == 3.33
    assert item.consumption_coefficient == round(3.33 / 7.5, 3)
    assert item.consumption_judgement == "OK"


def test_km_uses_route_distance_over_odometer_and_retains_duration(database, driver):
    vehicle = existing._make_vehicle(database)
    base = datetime(2026, 3, 15, 8)
    usage = existing._make_session(database, vehicle, driver.id, base, 0, 100)
    usage.route_distance_km = 42
    database.flush()

    result = analytics.km_analytics(None, database, "2026-01-01", "2026-12-31", "day")

    assert result.total_km == 42
    assert result.longest_session.km == 42
    assert result.longest_session.duration_minutes == 120


def test_inactive_user_without_records_yields_no_anomaly(database, driver):
    driver.is_active = False
    database.flush()
    assert _anomalies(database, "inactive_operator").items == []


def test_zero_user_id_retains_existing_truthiness_attribution_policy(database):
    zero_user = ApplicationUser(
        id=0,
        username="zero-id",
        email="zero@example.local",
        password_hash="unused",
        role="viewer",
        is_active=True,
    )
    database.add(zero_user)
    database.flush()
    vehicle = existing._make_vehicle(database)
    base = datetime(2026, 3, 15, 8)
    existing._make_session(database, vehicle, zero_user.id, base, 0, 100)
    database.flush()

    assert _anomalies(database, "driver_mismatch").items == []
    assert _fuel(database).top_operators == []
    team = Team(code="zero-user-team", name="Zero user team")
    catalog = ActivityCatalog(code="zero-user-hours", name="Zero user hours")
    database.add_all([team, catalog])
    database.flush()
    existing._make_activity(database, catalog, zero_user.id, base, 60, team_id=team.id)
    database.flush()

    hours = analytics.work_hours_analytics(None, database, "2026-01-01", "2026-12-31", "day")

    assert hours.total_hours == 1
    assert hours.top_operators == []
    assert hours.avg_hours_per_operator == 0
    assert hours.by_team[0].operator_count == 0


def test_fuel_snapshot_survives_operator_and_logs_deleted_between_reads(database, driver):
    vehicle = existing._make_vehicle(database)
    base = datetime(2026, 3, 15, 8)
    operator = existing._make_wc_operator(
        database, wc_id=10006, username="deleted", gaia_user_id=driver.id
    )
    log = existing._make_fuel_log(database, vehicle, driver.id, base, 10, 20)
    log.wc_operator_id = operator.id
    database.flush()
    operator_id = operator.id
    log_id = log.id
    fired = False

    def delete_before_operator_read(
        connection, cursor, statement, parameters, context, executemany
    ):
        nonlocal fired
        if not fired and statement.startswith("SELECT wc_operator."):
            fired = True
            connection.execute(VehicleFuelLog.__table__.delete().where(VehicleFuelLog.id == log_id))
            connection.execute(WCOperator.__table__.delete().where(WCOperator.id == operator_id))

    event.listen(existing.engine, "before_cursor_execute", delete_before_operator_read)
    try:
        result = _fuel(database)
    finally:
        event.remove(existing.engine, "before_cursor_execute", delete_before_operator_read)

    assert fired
    item = result.top_operators[0]
    assert item.id == f"wc:{operator_id}"
    assert item.label == str(operator_id)
    assert item.total_liters == 10
    assert item.total_km is None
    assert item.related[0].total_liters == 10
    assert database.scalars(select(WCOperator).where(WCOperator.id == operator_id)).all() == []


def test_fuel_card_snapshot_ignores_operator_removed_with_assignment(database, driver):
    operator = existing._make_wc_operator(
        database, wc_id=10007, username="deleted-card", gaia_user_id=None
    )
    card = FuelCard(pan="removed-card")
    database.add(card)
    database.flush()
    assignment = FuelCardAssignmentHistory(
        fuel_card_id=card.id, wc_operator_id=operator.id, start_at=datetime(2026, 3, 15)
    )
    database.add(assignment)
    database.flush()
    operator_id = operator.id
    assignment_id = assignment.id
    fired = False

    def delete_before_operator_read(
        connection, cursor, statement, parameters, context, executemany
    ):
        nonlocal fired
        if not fired and statement.startswith("SELECT wc_operator."):
            fired = True
            connection.execute(
                FuelCardAssignmentHistory.__table__.delete().where(
                    FuelCardAssignmentHistory.id == assignment_id
                )
            )
            connection.execute(WCOperator.__table__.delete().where(WCOperator.id == operator_id))

    event.listen(existing.engine, "before_cursor_execute", delete_before_operator_read)
    try:
        result = _anomalies(database, "orphan_fuel_card")
    finally:
        event.remove(existing.engine, "before_cursor_execute", delete_before_operator_read)

    assert fired
    assert result.items == []
