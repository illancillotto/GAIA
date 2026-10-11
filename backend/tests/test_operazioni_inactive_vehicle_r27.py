"""Inactive-vehicle contracts through persisted ORM rows and the public route."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
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
from app.modules.operazioni.routes import analytics

VEHICLE_ID = UUID("00000000-0000-0000-0000-000000000027")
LOG_ID = UUID("00000000-0000-0000-0000-000000000028")
SESSION_ID = UUID("00000000-0000-0000-0000-000000000029")
STARTED = datetime(2026, 3, 15, 8)
EMPTY_RESPONSE = {"items": [], "total": 0, "by_type": {}, "by_severity": {}}
LOG_ITEM = {
    "id": "inact_v_log_00000000-0000-0000-0000-000000000028",
    "type": "inactive_vehicle",
    "severity": "high",
    "description": "Rifornimento registrato su mezzo dismesso",
    "entity_id": "00000000-0000-0000-0000-000000000027",
    "entity_label": "R27001AA",
    "detected_at": "2026-03-15T08:00:00",
    "details": {"liters": 10.25, "vehicle_code": "R27-VEHICLE"},
}
SESSION_ITEM = {
    "id": "inact_v_sess_00000000-0000-0000-0000-000000000029",
    "type": "inactive_vehicle",
    "severity": "high",
    "description": "Sessione d'uso registrata su mezzo dismesso",
    "entity_id": "00000000-0000-0000-0000-000000000027",
    "entity_label": "R27001AA",
    "detected_at": "2026-03-15T08:00:00",
    "details": {"vehicle_code": "R27-VEHICLE"},
}


@dataclass
class QueryRecord:
    table: str
    predicate: str
    parameters: dict
    sql: str


@pytest.fixture
def inactive_vehicle(database: Session) -> Vehicle:
    vehicle = Vehicle(
        id=VEHICLE_ID,
        code="R27-VEHICLE",
        name="R27 inactive vehicle",
        plate_number="R27001AA",
        vehicle_type="autocarro",
        fuel_type="diesel",
        current_status="available",
        is_active=False,
    )
    database.add(vehicle)
    database.flush()
    return vehicle


@pytest.fixture
def sources(
    database: Session, driver: ApplicationUser, inactive_vehicle: Vehicle
) -> tuple[VehicleFuelLog, VehicleUsageSession]:
    log = existing._make_fuel_log(database, inactive_vehicle, driver.id, STARTED, 10.25, 20)
    usage = existing._make_session(database, inactive_vehicle, driver.id, STARTED, 0, 100)
    log.id = LOG_ID
    usage.id = SESSION_ID
    database.flush()
    return log, usage


def _anomalies(database: Session, kind: str | None = "inactive_vehicle") -> dict:
    return analytics.anomalies_analytics(
        current_user=None,
        db=database,
        from_date="2026-03-15",
        to_date="2026-03-15",
        anomaly_type=kind,
    ).model_dump(mode="json")


def _response(items: list[dict]) -> dict:
    return {
        "items": items,
        "total": len(items),
        "by_type": {"inactive_vehicle": len(items)} if items else {},
        "by_severity": {"high": len(items)} if items else {},
    }


def _record_queries(database: Session, monkeypatch: pytest.MonkeyPatch) -> list[QueryRecord]:
    records: list[QueryRecord] = []
    actual_scalars = database.scalars

    def recorded_scalars(statement, *arguments, **keywords):
        records.append(
            QueryRecord(
                table=statement.column_descriptions[0]["entity"].__tablename__,
                predicate=str(statement.whereclause),
                parameters=statement.compile().params,
                sql=str(statement),
            )
        )
        return actual_scalars(statement, *arguments, **keywords)

    monkeypatch.setattr(database, "scalars", recorded_scalars)
    return records


def test_two_sources_preserve_complete_literal_payload_and_query_contract(
    database: Session,
    sources: tuple[VehicleFuelLog, VehicleUsageSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = _record_queries(database, monkeypatch)

    result = _anomalies(database)

    assert result == _response([LOG_ITEM, SESSION_ITEM])
    assert list(result["items"][0]["details"]) == ["liters", "vehicle_code"]
    assert list(result["items"][1]["details"]) == ["vehicle_code"]
    assert [record.table for record in records] == [
        "vehicle",
        "vehicle_fuel_log",
        "vehicle_usage_session",
        "vehicle",
    ]
    assert [record.predicate for record in records] == [
        "vehicle.is_active IS false",
        "vehicle_fuel_log.fueled_at >= :fueled_at_1 "
        "AND vehicle_fuel_log.fueled_at <= :fueled_at_2 "
        "AND vehicle_fuel_log.vehicle_id IN (__[POSTCOMPILE_vehicle_id_1])",
        "vehicle_usage_session.started_at >= :started_at_1 "
        "AND vehicle_usage_session.started_at <= :started_at_2 "
        "AND vehicle_usage_session.vehicle_id IN (__[POSTCOMPILE_vehicle_id_1])",
        "vehicle.id IN (__[POSTCOMPILE_id_1])",
    ]
    assert records[0].parameters == {}
    assert records[1].parameters == {
        "fueled_at_1": datetime(2026, 3, 15),
        "fueled_at_2": datetime(2026, 3, 15, 23, 59, 59, 999999),
        "vehicle_id_1": [VEHICLE_ID],
    }
    assert records[2].parameters == {
        "started_at_1": datetime(2026, 3, 15),
        "started_at_2": datetime(2026, 3, 15, 23, 59, 59, 999999),
        "vehicle_id_1": [VEHICLE_ID],
    }
    assert records[3].parameters == {"id_1": [VEHICLE_ID]}
    assert all("ORDER BY" not in record.sql and "LIMIT" not in record.sql for record in records)
    assert not database.dirty


@pytest.mark.parametrize("active_only", [False, True])
def test_no_inactive_ids_runs_only_vehicle_query(
    database: Session, monkeypatch: pytest.MonkeyPatch, active_only: bool
) -> None:
    if active_only:
        existing._make_vehicle(database)
    records = _record_queries(database, monkeypatch)

    assert _anomalies(database) == EMPTY_RESPONSE
    assert [record.table for record in records] == ["vehicle"]
    assert records[0].predicate == "vehicle.is_active IS false"


def test_inactive_ids_without_rows_still_issue_empty_second_vehicle_select(
    database: Session, inactive_vehicle: Vehicle, monkeypatch: pytest.MonkeyPatch
) -> None:
    records = _record_queries(database, monkeypatch)

    assert _anomalies(database) == EMPTY_RESPONSE
    assert [record.table for record in records] == [
        "vehicle",
        "vehicle_fuel_log",
        "vehicle_usage_session",
        "vehicle",
    ]
    assert records[-1].predicate == "vehicle.id IN (__[POSTCOMPILE_id_1])"
    assert records[-1].parameters == {"id_1": []}


@pytest.mark.parametrize(
    ("plate", "code", "label"),
    [
        ("R27001AA", "R27-VEHICLE", "R27001AA"),
        (None, "R27-VEHICLE", "R27-VEHICLE"),
        ("", "R27-VEHICLE", "R27-VEHICLE"),
        (None, "", "00000000-0000-0000-0000-000000000027"),
        ("", "", "00000000-0000-0000-0000-000000000027"),
    ],
)
def test_both_sources_keep_plate_code_and_uuid_fallbacks(
    database: Session,
    inactive_vehicle: Vehicle,
    sources: tuple[VehicleFuelLog, VehicleUsageSession],
    plate: str | None,
    code: str,
    label: str,
) -> None:
    inactive_vehicle.plate_number = plate
    inactive_vehicle.code = code
    database.flush()

    assert _anomalies(database) == _response(
        [
            {**LOG_ITEM, "entity_label": label, "details": {"liters": 10.25, "vehicle_code": code}},
            {**SESSION_ITEM, "entity_label": label, "details": {"vehicle_code": code}},
        ]
    )
    assert not database.dirty


@pytest.mark.parametrize("liters", [Decimal("0"), Decimal("-3.125"), Decimal("1.25")])
def test_liters_preserve_supported_decimal_and_zero_values_without_session_key(
    database: Session, sources: tuple[VehicleFuelLog, VehicleUsageSession], liters: Decimal
) -> None:
    log = sources[0]
    log.liters = liters
    database.flush()

    result = _anomalies(database)

    assert result == _response(
        [
            {**LOG_ITEM, "details": {"liters": float(liters), "vehicle_code": "R27-VEHICLE"}},
            SESSION_ITEM,
        ]
    )
    assert list(result["items"][0]["details"]) == ["liters", "vehicle_code"]
    assert list(result["items"][1]["details"]) == ["vehicle_code"]
    assert isinstance(result["items"][0]["details"]["liters"], float)


@pytest.mark.parametrize(
    ("timestamp", "included"),
    [
        (datetime(2026, 3, 15), True),
        (datetime(2026, 3, 15, 23, 59, 59, 999999), True),
        (datetime(2026, 3, 14, 23, 59, 59, 999999), False),
        (datetime(2026, 3, 16), False),
    ],
)
def test_each_source_uses_inclusive_day_boundaries(
    database: Session,
    sources: tuple[VehicleFuelLog, VehicleUsageSession],
    timestamp: datetime,
    included: bool,
) -> None:
    log, usage = sources
    log.fueled_at = timestamp
    usage.started_at = timestamp
    usage.ended_at = timestamp + timedelta(hours=1)
    database.flush()

    expected = (
        [
            {**LOG_ITEM, "detected_at": timestamp.isoformat()},
            {**SESSION_ITEM, "detected_at": timestamp.isoformat()},
        ]
        if included
        else []
    )
    assert _anomalies(database) == _response(expected)


@pytest.mark.parametrize("status", ["open", "closed", "cancelled"])
def test_inactive_usage_does_not_gain_a_status_filter(
    database: Session, sources: tuple[VehicleFuelLog, VehicleUsageSession], status: str
) -> None:
    usage = sources[1]
    usage.status = status
    database.flush()

    assert _anomalies(database) == _response([LOG_ITEM, SESSION_ITEM])


def test_active_vehicle_rows_are_excluded_without_affecting_inactive_sources(
    database: Session, driver: ApplicationUser, sources: tuple[VehicleFuelLog, VehicleUsageSession]
) -> None:
    active = existing._make_vehicle(database, "R27002AA")
    existing._make_fuel_log(database, active, driver.id, STARTED, 99, 198)
    existing._make_session(database, active, driver.id, STARTED, 0, 500)

    assert _anomalies(database) == _response([LOG_ITEM, SESSION_ITEM])


@pytest.mark.parametrize("kind", [None, "", "inactive_vehicle"])
def test_falsy_and_explicit_filters_include_the_same_two_inactive_sources(
    database: Session, sources: tuple[VehicleFuelLog, VehicleUsageSession], kind: str | None
) -> None:
    assert _anomalies(database, kind) == _response([LOG_ITEM, SESSION_ITEM])


@pytest.mark.parametrize(
    "kind",
    [
        "orphan_session",
        "driver_mismatch",
        "excessive_fuel",
        "unmatched_refuel",
        "hours_discrepancy",
        "inactive_operator",
        "orphan_fuel_card",
        "unsupported",
    ],
)
def test_other_family_filters_do_not_emit_inactive_vehicle_items(
    database: Session, sources: tuple[VehicleFuelLog, VehicleUsageSession], kind: str
) -> None:
    assert _anomalies(database, kind) == EMPTY_RESPONSE


def test_real_source_row_order_is_preserved_without_interleaving_by_timestamp(
    database: Session,
    driver: ApplicationUser,
    inactive_vehicle: Vehicle,
    sources: tuple[VehicleFuelLog, VehicleUsageSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    later_log = existing._make_fuel_log(
        database, inactive_vehicle, driver.id, STARTED - timedelta(hours=1), 7, 14
    )
    later_log.id = UUID("00000000-0000-0000-0000-000000000030")
    later_usage = existing._make_session(
        database, inactive_vehicle, driver.id, STARTED - timedelta(hours=2), 0, 10
    )
    later_usage.id = UUID("00000000-0000-0000-0000-000000000031")
    database.flush()
    actual_scalars = database.scalars

    class OrderedPersistedRows:
        def __init__(self, result):
            self.result = result

        def all(self):
            return sorted(self.result.all(), key=lambda record: record.id, reverse=True)

    def ordered_scalars(statement, *arguments, **keywords):
        result = actual_scalars(statement, *arguments, **keywords)
        if statement.column_descriptions[0]["entity"] in (VehicleFuelLog, VehicleUsageSession):
            return OrderedPersistedRows(result)
        return result

    monkeypatch.setattr(database, "scalars", ordered_scalars)

    assert _anomalies(database) == _response(
        [
            {
                **LOG_ITEM,
                "id": "inact_v_log_00000000-0000-0000-0000-000000000030",
                "detected_at": "2026-03-15T07:00:00",
                "details": {"liters": 7.0, "vehicle_code": "R27-VEHICLE"},
            },
            LOG_ITEM,
            {
                **SESSION_ITEM,
                "id": "inact_v_sess_00000000-0000-0000-0000-000000000031",
                "detected_at": "2026-03-15T06:00:00",
            },
            SESSION_ITEM,
        ]
    )


def test_unfiltered_high_severity_ties_keep_inactive_vehicle_before_inactive_operator(
    database: Session, driver: ApplicationUser, sources: tuple[VehicleFuelLog, VehicleUsageSession]
) -> None:
    driver.is_active = False
    database.flush()

    result = _anomalies(database, None)

    assert result == {
        "items": [
            LOG_ITEM,
            SESSION_ITEM,
            {
                "id": "inact_op_log_00000000-0000-0000-0000-000000000028",
                "type": "inactive_operator",
                "severity": "high",
                "description": "Rifornimento registrato da operatore non più attivo",
                "entity_id": str(driver.id),
                "entity_label": "characterization-driver",
                "detected_at": "2026-03-15T08:00:00",
                "details": {"vehicle": "R27001AA", "liters": 10.25},
            },
            {
                "id": "inact_op_sess_00000000-0000-0000-0000-000000000029",
                "type": "inactive_operator",
                "severity": "high",
                "description": "Sessione d'uso registrata da operatore non più attivo",
                "entity_id": str(driver.id),
                "entity_label": "characterization-driver",
                "detected_at": "2026-03-15T08:00:00",
                "details": {"vehicle": "R27001AA"},
            },
        ],
        "total": 4,
        "by_type": {"inactive_vehicle": 2, "inactive_operator": 2},
        "by_severity": {"high": 4},
    }
    assert list(result["by_type"]) == ["inactive_vehicle", "inactive_operator"]
    assert not database.dirty


def test_public_endpoint_keeps_payload_and_type_alias_with_real_auth(database: Session) -> None:
    def real_database():
        yield database

    with pytest.MonkeyPatch.context() as overrides:
        overrides.setitem(existing.app.dependency_overrides, get_db, real_database)
        headers = existing._auth_headers()
    authenticated = database.scalar(
        select(ApplicationUser).where(ApplicationUser.username == "analytics-admin")
    )
    assert authenticated is not None
    vehicle = Vehicle(
        id=VEHICLE_ID,
        code="R27-VEHICLE",
        name="R27 public vehicle",
        plate_number="R27001AA",
        vehicle_type="autocarro",
        is_active=False,
    )
    database.add(vehicle)
    database.flush()
    log = existing._make_fuel_log(database, vehicle, authenticated.id, STARTED, 10.25, 20)
    usage = existing._make_session(database, vehicle, authenticated.id, STARTED, 0, 100)
    log.id = LOG_ID
    usage.id = SESSION_ID
    database.commit()

    with pytest.MonkeyPatch.context() as overrides:
        overrides.setitem(existing.app.dependency_overrides, get_db, real_database)
        response = existing.client.get(
            "/operazioni/analytics/anomalies",
            params={"from_date": "2026-03-15", "to_date": "2026-03-15", "type": "inactive_vehicle"},
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json() == _response([LOG_ITEM, SESSION_ITEM])


def test_public_endpoint_rejects_missing_auth_without_querying_inactive_sources(
    database: Session,
    sources: tuple[VehicleFuelLog, VehicleUsageSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = _record_queries(database, monkeypatch)

    def real_database():
        yield database

    with pytest.MonkeyPatch.context() as overrides:
        overrides.setitem(existing.app.dependency_overrides, get_db, real_database)
        response = existing.client.get(
            "/operazioni/analytics/anomalies",
            params={"from_date": "2026-03-15", "to_date": "2026-03-15", "type": "inactive_vehicle"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
    assert records == []
