"""Persisted work-hours discrepancy contracts for the guarded emission slice."""

from datetime import date, datetime, timedelta
from uuid import UUID

import pytest
import test_operazioni_analytics as existing
from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session
from test_operazioni_analytics_characterization import database as database
from test_operazioni_analytics_characterization import driver as driver

from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.activities import ActivityCatalog, OperatorActivity
from app.modules.operazioni.routes import analytics

STARTED = datetime(2026, 3, 15, 8)
PARAMS = {"from_date": "2026-03-15", "to_date": "2026-03-15", "type": "hours_discrepancy"}
EMPTY_RESPONSE = {"items": [], "total": 0, "by_type": {}, "by_severity": {}}


@pytest.fixture
def catalog(database: Session) -> ActivityCatalog:
    value = ActivityCatalog(code="r52-hours", name="R52 work hours")
    database.add(value)
    database.flush()
    return value


def _activity(database, catalog, driver, durations, started=STARTED):
    value = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=driver.id,
        started_at=started,
        duration_minutes_declared=durations[0],
        duration_minutes_calculated=durations[1],
        status="submitted",
    )
    database.add(value)
    database.flush()
    return value


def _result(database, kind="hours_discrepancy", dates=("2026-03-15", "2026-03-15")):
    return analytics.anomalies_analytics(
        current_user=None,
        db=database,
        from_date=dates[0],
        to_date=dates[1],
        anomaly_type=kind,
    ).model_dump(mode="json")


def _item(activity, label):
    declared = int(activity.duration_minutes_declared)
    calculated = int(activity.duration_minutes_calculated)
    difference = abs(declared - calculated)
    return {
        "id": f"hours_{activity.id}",
        "type": "hours_discrepancy",
        "severity": "low" if difference < 120 else "medium",
        "description": f"Discrepanza ore: dichiarate vs calcolate ({difference} min di scarto)",
        "entity_id": str(activity.id),
        "entity_label": label,
        "detected_at": activity.started_at.isoformat(),
        "details": {"declared_min": declared, "calculated_min": calculated, "diff_min": difference},
    }


@pytest.mark.parametrize("difference", [0, 59, 60, 61, 119, 120, 121])
@pytest.mark.parametrize("direction", [-1, 1])
def test_persisted_integer_thresholds_keep_exact_response(
    database, driver, catalog, difference, direction
):
    activity = _activity(database, catalog, driver, (180 + direction * difference, 180))
    result = _result(database)

    if difference <= 60:
        assert result == EMPTY_RESPONSE
        return
    severity = "low" if difference < 120 else "medium"
    expected = _item(activity, driver.username)
    assert expected["details"]["diff_min"] == difference
    assert expected["severity"] == severity
    assert result == {
        "items": [expected],
        "total": 1,
        "by_type": {"hours_discrepancy": 1},
        "by_severity": {severity: 1},
    }


@pytest.mark.parametrize("durations", [(None, 120), (120, None), (None, None)])
def test_query_excludes_nullable_duration_before_integer_conversion(
    database, driver, catalog, durations
):
    _activity(database, catalog, driver, durations)
    assert _result(database) == EMPTY_RESPONSE


@pytest.mark.parametrize("durations", [(0, 61), (61, 0), (-61, 0), (0, -61), (-180, -60)])
def test_zero_and_negative_persisted_minutes_keep_absolute_difference(
    database, driver, catalog, durations
):
    activity = _activity(database, catalog, driver, durations)
    result = _result(database)
    assert result["items"] == [_item(activity, driver.username)]
    assert result["total"] == 1


def test_real_query_predicates_parameters_order_and_orm_state_are_unchanged(
    database, driver, catalog
):
    activity = _activity(database, catalog, driver, (61, 0))
    before = {
        column.key: getattr(activity, column.key) for column in inspect(activity).mapper.columns
    }
    records = []

    def record_query(execution):
        statement = execution.statement
        records.append(
            (
                statement.column_descriptions[0]["entity"],
                statement.compile().params,
                str(statement.whereclause),
            )
        )

    event.listen(database, "do_orm_execute", record_query)
    try:
        result = _result(database)
    finally:
        event.remove(database, "do_orm_execute", record_query)

    assert result["items"] == [_item(activity, driver.username)]
    assert [record[0] for record in records] == [OperatorActivity, ApplicationUser]
    assert records[0][1] == {
        "started_at_1": datetime(2026, 3, 15),
        "started_at_2": datetime(2026, 3, 15, 23, 59, 59, 999999),
    }
    assert records[0][2] == (
        "operator_activity.started_at >= :started_at_1 AND "
        "operator_activity.started_at <= :started_at_2 AND "
        "operator_activity.duration_minutes_declared IS NOT NULL AND "
        "operator_activity.duration_minutes_calculated IS NOT NULL"
    )
    assert records[1][1] == {"id_1": [driver.id]}
    assert records[1][2] == "application_users.id IN (__[POSTCOMPILE_id_1])"
    assert before == {
        column.key: getattr(activity, column.key) for column in inspect(activity).mapper.columns
    }
    assert not database.new
    assert not database.dirty
    assert not database.deleted
    assert database.in_transaction()


def test_inclusive_day_boundaries_exclude_adjacent_microseconds(database, driver, catalog):
    midnight = STARTED.replace(hour=0)
    final = midnight + timedelta(days=1, microseconds=-1)
    included = [
        _activity(database, catalog, driver, (61, 0), moment) for moment in (midnight, final)
    ]
    for moment in (midnight - timedelta(microseconds=1), final + timedelta(microseconds=1)):
        _activity(database, catalog, driver, (61, 0), moment)
    assert _result(database)["items"] == [_item(activity, driver.username) for activity in included]


@pytest.mark.parametrize("dates", [("invalid", "invalid"), (None, None), ("", "")])
def test_invalid_and_absent_dates_keep_real_default_window(
    database, driver, catalog, dates, monkeypatch
):
    today = date.today()

    class FixtureDate(date):
        @classmethod
        def today(cls):
            return today

    monkeypatch.setattr(analytics, "date", FixtureDate)
    start = datetime.combine(today - timedelta(days=30), datetime.min.time())
    end = datetime.combine(today, datetime.max.time())
    included = [_activity(database, catalog, driver, (61, 0), moment) for moment in (start, end)]
    for moment in (start - timedelta(microseconds=1), end + timedelta(microseconds=1)):
        _activity(database, catalog, driver, (61, 0), moment)
    assert _result(database, dates=dates)["items"] == [
        _item(activity, driver.username) for activity in included
    ]


def test_reversed_valid_dates_return_empty_without_reordering_bounds(database, driver, catalog):
    _activity(database, catalog, driver, (61, 0))
    assert _result(database, dates=("2026-03-16", "2026-03-14")) == EMPTY_RESPONSE


@pytest.mark.parametrize("kind", [None, "", "hours_discrepancy", "unsupported", "excessive_fuel"])
def test_type_filter_keeps_hours_inclusion_and_other_families_separate(
    database, driver, catalog, kind
):
    activity = _activity(database, catalog, driver, (61, 0))
    result = _result(database, kind)
    assert result["items"] == (
        [_item(activity, driver.username)] if kind in (None, "", "hours_discrepancy") else []
    )


def test_severity_stable_sort_preserves_database_order_for_ties(database, driver, catalog):
    rows = [
        _activity(database, catalog, driver, (difference, 0)) for difference in (61, 120, 119, 121)
    ]
    for identifier, activity in enumerate(rows, start=1):
        activity.id = UUID(int=identifier)
    database.flush()
    result = _result(database)
    assert result == {
        "items": [_item(rows[index], driver.username) for index in (1, 3, 0, 2)],
        "total": 4,
        "by_type": {"hours_discrepancy": 4},
        "by_severity": {"low": 2, "medium": 2},
    }
    assert list(result["by_severity"]) == ["low", "medium"]


@pytest.mark.parametrize("allowed", [False, True])
def test_public_route_keeps_real_login_module_permission_and_type_alias(database, catalog, allowed):
    def real_database():
        yield database

    with pytest.MonkeyPatch.context() as overrides:
        overrides.setitem(existing.app.dependency_overrides, get_db, real_database)
        headers = existing._auth_headers(module_operazioni=allowed)
        authenticated = database.scalar(
            select(ApplicationUser).where(
                ApplicationUser.username == ("analytics-admin" if allowed else "analytics-noaccess")
            )
        )
        activity = _activity(database, catalog, authenticated, (120, 0))
        database.commit()
        anonymous = existing.client.get("/operazioni/analytics/anomalies", params=PARAMS)
        response = existing.client.get(
            "/operazioni/analytics/anomalies", params=PARAMS, headers=headers
        )

    assert anonymous.status_code == 401
    assert response.status_code == (200 if allowed else 403)
    if allowed:
        assert response.json()["items"] == [_item(activity, authenticated.username)]
