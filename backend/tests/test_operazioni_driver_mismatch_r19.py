"""Original driver-mismatch ORM contracts and separately named synthetic diagnostics."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
import test_operazioni_analytics as existing
from sqlalchemy import delete
from sqlalchemy.orm import Session
from test_operazioni_analytics_characterization import database as database

from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.vehicles import Vehicle, VehicleAssignment, VehicleUsageSession
from app.modules.operazioni.routes import analytics

SESSION_ID = UUID("00000000-0000-0000-0000-000000000001")
VEHICLE_ID = UUID("00000000-0000-0000-0000-000000000002")
STARTED = datetime(2026, 3, 15, 8)
DESCRIPTION = "Guidatore effettivo non coincide con operatore assegnato al mezzo"
EMPTY_RESPONSE = {"items": [], "total": 0, "by_type": {}, "by_severity": {}}


@dataclass
class MismatchData:
    vehicle: Vehicle
    driver: ApplicationUser
    session: VehicleUsageSession


def _user(database: Session, identifier: int, username: str) -> ApplicationUser:
    user = ApplicationUser(
        id=identifier,
        username=username,
        email=f"{identifier}@r19.example.local",
        password_hash="unused-direct-route-fixture",
        role="viewer",
        is_active=True,
        module_operazioni=True,
    )
    database.add(user)
    database.flush()
    return user


@pytest.fixture
def mismatch_data(database: Session) -> MismatchData:
    driver = _user(database, 41, "actual-driver")
    driver.first_name = "Mario"
    driver.last_name = "Rossi"
    for identifier in (52, 53, 99):
        _user(database, identifier, f"operator-{identifier}")
    vehicle = Vehicle(
        id=VEHICLE_ID,
        code="R19-VEHICLE",
        name="Driver mismatch fixture",
        plate_number="DM001AA",
        vehicle_type="autocarro",
        fuel_type="diesel",
        current_status="available",
    )
    database.add(vehicle)
    database.flush()
    session = VehicleUsageSession(
        id=SESSION_ID,
        vehicle_id=VEHICLE_ID,
        started_by_user_id=99,
        actual_driver_user_id=41,
        started_at=STARTED,
        ended_at=STARTED + timedelta(hours=1),
        start_odometer_km=Decimal("100"),
        end_odometer_km=Decimal("110"),
        status="closed",
    )
    database.add(session)
    database.flush()
    return MismatchData(vehicle, driver, session)


def _assignment(
    database: Session,
    operator_id: int | None = 52,
    start_at: datetime = STARTED - timedelta(days=1),
    end_at: datetime | None = None,
    target: str = "operator",
) -> VehicleAssignment:
    assignment = VehicleAssignment(
        vehicle_id=VEHICLE_ID,
        assignment_target_type=target,
        operator_user_id=operator_id,
        assigned_by_user_id=99,
        start_at=start_at,
        end_at=end_at,
    )
    database.add(assignment)
    database.flush()
    return assignment


def _anomalies(
    database: Session,
    kind: str | None = "driver_mismatch",
    from_date: str | None = "2026-03-15",
    to_date: str | None = "2026-03-15",
) -> dict:
    return analytics.anomalies_analytics(None, database, from_date, to_date, kind).model_dump()


def _expected_item(
    session_id: UUID = SESSION_ID,
    timestamp: str = "2026-03-15T08:00:00",
    label: str = "DM001AA",
    driver: str = "Mario Rossi",
    assigned: tuple[str, ...] = ("52",),
) -> dict:
    return {
        "id": f"mismatch_{session_id}",
        "type": "driver_mismatch",
        "severity": "high",
        "description": DESCRIPTION,
        "entity_id": str(session_id),
        "entity_label": label,
        "detected_at": timestamp,
        "details": {"actual_driver": driver, "assigned_operator_ids": list(assigned)},
    }


def _expected_response(items: list[dict]) -> dict:
    return {
        "items": items,
        "total": len(items),
        "by_type": {"driver_mismatch": len(items)},
        "by_severity": {"high": len(items)},
    }


def _record_queries(database: Session, monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    records = []
    actual_scalars = database.scalars

    def recorded_scalars(statement, *arguments, **keywords):
        records.append(
            {
                "table": statement.column_descriptions[0]["entity"].__tablename__,
                "predicate": str(statement.whereclause),
                "parameters": statement.compile().params,
                "sql": str(statement),
            }
        )
        return actual_scalars(statement, *arguments, **keywords)

    monkeypatch.setattr(database, "scalars", recorded_scalars)
    return records


def test_original_complete_literal_response(database: Session, mismatch_data: MismatchData) -> None:
    _assignment(database)

    assert _anomalies(database) == {
        "items": [
            {
                "id": "mismatch_00000000-0000-0000-0000-000000000001",
                "type": "driver_mismatch",
                "severity": "high",
                "description": "Guidatore effettivo non coincide con operatore assegnato al mezzo",
                "entity_id": "00000000-0000-0000-0000-000000000001",
                "entity_label": "DM001AA",
                "detected_at": "2026-03-15T08:00:00",
                "details": {"actual_driver": "Mario Rossi", "assigned_operator_ids": ["52"]},
            }
        ],
        "total": 1,
        "by_type": {"driver_mismatch": 1},
        "by_severity": {"high": 1},
    }
    assert not database.dirty


@pytest.mark.parametrize("operators", [(41,), (52, 41), (41, 52, 41), (52, 53, 41)])
def test_original_any_matching_assignment_suppresses_mismatch(
    database: Session, mismatch_data: MismatchData, operators: tuple[int, ...]
) -> None:
    for operator_id in operators:
        _assignment(database, operator_id)

    assert _anomalies(database) == EMPTY_RESPONSE


def test_original_assignment_order_and_duplicates(database: Session, mismatch_data: MismatchData):
    for operator_id in (52, 53, 52):
        _assignment(database, operator_id)

    assert _anomalies(database) == _expected_response([_expected_item(assigned=("52", "53", "52"))])


@pytest.mark.parametrize(
    ("start_at", "end_at", "included"),
    [
        (STARTED, None, True),
        (STARTED - timedelta(days=1), STARTED, True),
        (STARTED, STARTED, True),
        (STARTED + timedelta(microseconds=1), None, False),
        (STARTED - timedelta(days=1), STARTED - timedelta(microseconds=1), False),
    ],
)
def test_original_inclusive_assignment_bounds(
    database: Session,
    mismatch_data: MismatchData,
    start_at: datetime,
    end_at: datetime | None,
    included: bool,
) -> None:
    _assignment(database, start_at=start_at, end_at=end_at)

    expected = _expected_response([_expected_item()]) if included else EMPTY_RESPONSE
    assert _anomalies(database) == expected


def test_original_no_assignments_produce_no_anomaly(database: Session, mismatch_data: MismatchData):
    assert _anomalies(database) == EMPTY_RESPONSE


@pytest.mark.parametrize("operator_id", [None, 0])
def test_original_falsy_assignment_operator_is_ignored(
    database: Session, mismatch_data: MismatchData, operator_id: int | None
) -> None:
    if operator_id == 0:
        _user(database, 0, "zero-operator")
    _assignment(database, operator_id)

    assert _anomalies(database) == EMPTY_RESPONSE


def test_original_team_assignment_does_not_enter_operator_pipeline(
    database: Session, mismatch_data: MismatchData, monkeypatch: pytest.MonkeyPatch
) -> None:
    _assignment(database, target="team")
    records = _record_queries(database, monkeypatch)

    assert _anomalies(database) == EMPTY_RESPONSE
    assert records[3]["predicate"] == (
        "vehicle_assignment.vehicle_id IN (__[POSTCOMPILE_vehicle_id_1]) "
        "AND vehicle_assignment.assignment_target_type = :assignment_target_type_1"
    )
    assert records[3]["parameters"] == {
        "vehicle_id_1": [VEHICLE_ID],
        "assignment_target_type_1": "operator",
    }


def test_original_null_driver_is_filtered_by_sql(
    database: Session, mismatch_data: MismatchData, monkeypatch: pytest.MonkeyPatch
) -> None:
    mismatch_data.session.actual_driver_user_id = None
    database.flush()
    records = _record_queries(database, monkeypatch)

    assert _anomalies(database) == EMPTY_RESPONSE
    assert [record["table"] for record in records] == ["vehicle_usage_session"]
    assert records[0]["predicate"] == (
        "vehicle_usage_session.started_at >= :started_at_1 "
        "AND vehicle_usage_session.started_at <= :started_at_2 "
        "AND vehicle_usage_session.actual_driver_user_id IS NOT NULL"
    )


def test_original_zero_driver_preserves_all_queries_before_truthiness_guard(
    database: Session, mismatch_data: MismatchData, monkeypatch: pytest.MonkeyPatch
) -> None:
    _user(database, 0, "zero-driver")
    mismatch_data.session.actual_driver_user_id = 0
    database.flush()
    _assignment(database)
    records = _record_queries(database, monkeypatch)

    assert _anomalies(database) == EMPTY_RESPONSE
    assert [record["table"] for record in records] == [
        "vehicle_usage_session",
        "vehicle",
        "application_users",
        "vehicle_assignment",
    ]
    assert set(records[2]["parameters"]["id_1"]) == {0, 99}


@pytest.mark.parametrize(
    ("timestamp", "included"),
    [
        (datetime(2026, 3, 15), True),
        (datetime(2026, 3, 15, 23, 59, 59, 999999), True),
        (datetime(2026, 3, 14, 23, 59, 59, 999999), False),
        (datetime(2026, 3, 16), False),
    ],
)
def test_original_inclusive_request_time_bounds(
    database: Session, mismatch_data: MismatchData, timestamp: datetime, included: bool
) -> None:
    mismatch_data.session.started_at = timestamp
    database.flush()
    _assignment(database, start_at=datetime(2026, 3, 1))

    expected = (
        _expected_response([_expected_item(timestamp=timestamp.isoformat())])
        if included
        else EMPTY_RESPONSE
    )
    assert _anomalies(database) == expected


@pytest.mark.parametrize("date_value", [None, "", "not-a-date", "2026-02-30"])
def test_original_date_fallbacks_use_unchanged_window(
    database: Session,
    mismatch_data: MismatchData,
    monkeypatch: pytest.MonkeyPatch,
    date_value: str | None,
) -> None:
    class FixedDate(date):
        @classmethod
        def today(cls) -> date:
            return cls(2026, 3, 15)

    monkeypatch.setattr(analytics, "date", FixedDate)
    _assignment(database)
    records = _record_queries(database, monkeypatch)

    assert _anomalies(database, from_date=date_value, to_date=date_value) == _expected_response(
        [_expected_item()]
    )
    assert records[0]["parameters"] == {
        "started_at_1": datetime(2026, 2, 13),
        "started_at_2": datetime(2026, 3, 15, 23, 59, 59, 999999),
    }


def test_original_inverted_range_is_not_swapped_or_rejected(
    database: Session, mismatch_data: MismatchData, monkeypatch: pytest.MonkeyPatch
) -> None:
    _assignment(database)
    records = _record_queries(database, monkeypatch)

    assert _anomalies(database, from_date="2026-03-16", to_date="2026-03-14") == EMPTY_RESPONSE
    assert len(records) == 1
    assert records[0]["parameters"] == {
        "started_at_1": datetime(2026, 3, 16),
        "started_at_2": datetime(2026, 3, 14, 23, 59, 59, 999999),
    }


def test_original_aware_session_preserves_its_iso_offset(
    database: Session, mismatch_data: MismatchData
) -> None:
    mismatch_data.session.started_at = STARTED.replace(tzinfo=UTC)
    database.flush()
    assignment = _assignment(database, start_at=(STARTED - timedelta(days=1)).replace(tzinfo=UTC))

    assert _anomalies(database) == _expected_response(
        [_expected_item(timestamp="2026-03-15T08:00:00+00:00")]
    )
    assert assignment.start_at.tzinfo is UTC


def test_original_incompatible_temporal_operands_raise_without_normalization(
    database: Session, mismatch_data: MismatchData
) -> None:
    assignment = _assignment(database, end_at=STARTED.replace(tzinfo=UTC))

    with pytest.raises(TypeError, match="offset-naive and offset-aware"):
        _anomalies(database)
    assert assignment.end_at.tzinfo is UTC


@pytest.mark.parametrize("plate", [None, ""])
def test_original_empty_plate_falls_back_to_vehicle_uuid(
    database: Session, mismatch_data: MismatchData, plate: str | None
) -> None:
    mismatch_data.vehicle.plate_number = plate
    database.flush()
    _assignment(database)

    assert _anomalies(database) == _expected_response([_expected_item(label=str(VEHICLE_ID))])


def test_original_missing_vehicle_lookup_uses_uuid(
    database: Session, mismatch_data: MismatchData
) -> None:
    _assignment(database)
    database.execute(delete(Vehicle).where(Vehicle.id == VEHICLE_ID))

    assert _anomalies(database) == _expected_response([_expected_item(label=str(VEHICLE_ID))])


def test_original_missing_driver_lookup_uses_canonical_unknown(
    database: Session, mismatch_data: MismatchData
) -> None:
    _assignment(database)
    database.execute(delete(ApplicationUser).where(ApplicationUser.id == 41))

    assert _anomalies(database) == _expected_response([_expected_item(driver="Sconosciuto")])


@pytest.mark.parametrize(
    ("first_name", "last_name", "username", "expected"),
    [
        ("  Mario", "Rossi  ", "actual-driver", "Mario Rossi"),
        (None, None, "actual-driver", "actual-driver"),
        ("", "", "", "41"),
    ],
)
def test_original_driver_display_uses_canonical_fallbacks(
    database: Session,
    mismatch_data: MismatchData,
    first_name: str | None,
    last_name: str | None,
    username: str,
    expected: str,
) -> None:
    mismatch_data.driver.first_name = first_name
    mismatch_data.driver.last_name = last_name
    mismatch_data.driver.username = username
    database.flush()
    _assignment(database)

    assert _anomalies(database) == _expected_response([_expected_item(driver=expected)])


def test_original_nonempty_query_order_predicates_and_started_by_ids(
    database: Session, mismatch_data: MismatchData, monkeypatch: pytest.MonkeyPatch
) -> None:
    _assignment(database)
    records = _record_queries(database, monkeypatch)

    assert _anomalies(database) == _expected_response([_expected_item()])
    assert [record["table"] for record in records] == [
        "vehicle_usage_session",
        "vehicle",
        "application_users",
        "vehicle_assignment",
    ]
    assert [record["predicate"] for record in records] == [
        "vehicle_usage_session.started_at >= :started_at_1 "
        "AND vehicle_usage_session.started_at <= :started_at_2 "
        "AND vehicle_usage_session.actual_driver_user_id IS NOT NULL",
        "vehicle.id IN (__[POSTCOMPILE_id_1])",
        "application_users.id IN (__[POSTCOMPILE_id_1])",
        "vehicle_assignment.vehicle_id IN (__[POSTCOMPILE_vehicle_id_1]) "
        "AND vehicle_assignment.assignment_target_type = :assignment_target_type_1",
    ]
    assert records[0]["parameters"] == {
        "started_at_1": datetime(2026, 3, 15),
        "started_at_2": datetime(2026, 3, 15, 23, 59, 59, 999999),
    }
    assert records[1]["parameters"] == {"id_1": [VEHICLE_ID]}
    assert set(records[2]["parameters"]["id_1"]) == {41, 99}
    assert records[3]["parameters"] == {
        "vehicle_id_1": [VEHICLE_ID],
        "assignment_target_type_1": "operator",
    }
    assert all("ORDER BY" not in record["sql"] for record in records)
    assert not database.dirty


def test_original_empty_sessions_have_exactly_one_query(
    database: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    records = _record_queries(database, monkeypatch)

    assert _anomalies(database) == EMPTY_RESPONSE
    assert [record["table"] for record in records] == ["vehicle_usage_session"]


@pytest.mark.parametrize("kind", [None, "", "driver_mismatch", "unsupported"])
def test_original_type_guard_and_seven_other_family_isolation(
    database: Session,
    mismatch_data: MismatchData,
    monkeypatch: pytest.MonkeyPatch,
    kind: str | None,
) -> None:
    _assignment(database)
    records = _record_queries(database, monkeypatch)

    result = _anomalies(database, kind=kind)

    if kind == "unsupported":
        assert result == EMPTY_RESPONSE
        assert records == []
    elif kind == "driver_mismatch":
        assert result == _expected_response([_expected_item()])
        assert [record["table"] for record in records] == [
            "vehicle_usage_session",
            "vehicle",
            "application_users",
            "vehicle_assignment",
        ]
    else:
        assert result == _expected_response([_expected_item()])
        assert [record["table"] for record in records] == [
            "vehicle_usage_session",
            "vehicle_usage_session",
            "vehicle",
            "application_users",
            "vehicle_assignment",
            "vehicle_fuel_log",
            "wc_refuel_event",
            "operator_activity",
            "vehicle",
            "application_users",
            "fuel_card_assignment_history",
        ]


def test_original_multiple_mismatches_keep_query_iteration_order(
    database: Session, mismatch_data: MismatchData, monkeypatch: pytest.MonkeyPatch
) -> None:
    _assignment(database)
    second = existing._make_session(
        database, mismatch_data.vehicle, 41, STARTED - timedelta(hours=1), 0, 10
    )
    second.id = UUID("00000000-0000-0000-0000-000000000003")
    database.flush()
    actual_scalars = database.scalars

    class OrderedSessionRows:
        def __init__(self, rows) -> None:
            self.rows = rows

        def all(self):
            return sorted(self.rows.all(), key=lambda session: session.id)

    def controlled_scalars(statement, *arguments, **keywords):
        rows = actual_scalars(statement, *arguments, **keywords)
        if statement.column_descriptions[0]["entity"] is VehicleUsageSession:
            return OrderedSessionRows(rows)
        return rows

    monkeypatch.setattr(database, "scalars", controlled_scalars)

    assert _anomalies(database) == _expected_response(
        [
            _expected_item(),
            _expected_item(
                session_id=UUID("00000000-0000-0000-0000-000000000003"),
                timestamp="2026-03-15T07:00:00",
            ),
        ]
    )


def test_original_unfiltered_high_severity_ties_keep_family_order(
    database: Session, mismatch_data: MismatchData
) -> None:
    mismatch_data.vehicle.is_active = False
    mismatch_data.driver.is_active = False
    database.flush()
    _assignment(database)

    result = _anomalies(database, kind=None)

    assert result["items"] == [
        _expected_item(),
        {
            "id": f"inact_v_sess_{SESSION_ID}",
            "type": "inactive_vehicle",
            "severity": "high",
            "description": "Sessione d'uso registrata su mezzo dismesso",
            "entity_id": str(VEHICLE_ID),
            "entity_label": "DM001AA",
            "detected_at": "2026-03-15T08:00:00",
            "details": {"vehicle_code": "R19-VEHICLE"},
        },
        {
            "id": f"inact_op_sess_{SESSION_ID}",
            "type": "inactive_operator",
            "severity": "high",
            "description": "Sessione d'uso registrata da operatore non più attivo",
            "entity_id": "41",
            "entity_label": "Mario Rossi",
            "detected_at": "2026-03-15T08:00:00",
            "details": {"vehicle": "DM001AA"},
        },
    ]
    assert result["total"] == 3
    assert list(result["by_type"].items()) == [
        ("driver_mismatch", 1),
        ("inactive_vehicle", 1),
        ("inactive_operator", 1),
    ]
    assert result["by_severity"] == {"high": 3}


class SyntheticRows:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def all(self) -> list[object]:
        return self.rows


class SyntheticSession:
    """Supplementary boundary diagnostics; never persisted ORM/coverage proof."""

    def __init__(self, rows: dict[str, list[object]]) -> None:
        self.rows = rows
        self.tables: list[str] = []
        self.parameters: list[dict] = []

    def scalars(self, statement) -> SyntheticRows:
        table = statement.column_descriptions[0]["entity"].__tablename__
        self.tables.append(table)
        self.parameters.append(statement.compile().params)
        return SyntheticRows(self.rows.get(table, []))


def _synthetic_session(**overrides) -> SimpleNamespace:
    values = {
        "id": SESSION_ID,
        "vehicle_id": VEHICLE_ID,
        "actual_driver_user_id": 41,
        "started_by_user_id": 99,
        "started_at": STARTED,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _synthetic_assignment(**overrides) -> SimpleNamespace:
    values = {
        "vehicle_id": VEHICLE_ID,
        "operator_user_id": 52,
        "start_at": STARTED - timedelta(days=1),
        "end_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.parametrize("vehicle_id", [None, ""])
def test_synthetic_falsy_vehicle_preserves_user_query_before_skip(vehicle_id) -> None:
    database = SyntheticSession(
        {"vehicle_usage_session": [_synthetic_session(vehicle_id=vehicle_id)]}
    )

    assert _anomalies(database) == EMPTY_RESPONSE
    assert database.tables == ["vehicle_usage_session", "application_users"]


def test_synthetic_duplicate_lookup_rows_preserve_last_row_wins() -> None:
    database = SyntheticSession(
        {
            "vehicle_usage_session": [_synthetic_session()],
            "vehicle": [
                SimpleNamespace(id=VEHICLE_ID, plate_number="FIRST"),
                SimpleNamespace(id=VEHICLE_ID, plate_number="LAST"),
            ],
            "application_users": [
                SimpleNamespace(id=41, username="first"),
                SimpleNamespace(id=41, username="last"),
            ],
            "vehicle_assignment": [_synthetic_assignment()],
        }
    )

    assert _anomalies(database) == _expected_response([_expected_item(label="LAST", driver="last")])


def test_synthetic_none_started_by_id_remains_in_user_query_union() -> None:
    database = SyntheticSession(
        {
            "vehicle_usage_session": [_synthetic_session(started_by_user_id=None)],
            "vehicle_assignment": [_synthetic_assignment()],
        }
    )

    assert _anomalies(database) == _expected_response(
        [_expected_item(label=str(VEHICLE_ID), driver="Sconosciuto")]
    )
    assert set(database.parameters[2]["id_1"]) == {41, None}


@pytest.mark.parametrize("operator_id", [None, 0])
def test_synthetic_falsy_operator_short_circuits_before_timestamp_getter(operator_id) -> None:
    class Assignment:
        vehicle_id = VEHICLE_ID
        operator_user_id = operator_id

        @property
        def end_at(self):
            raise AssertionError("end_at must not be read for falsy operator")

        @property
        def start_at(self):
            raise AssertionError("start_at must not be read for falsy operator")

    class Usage:
        vehicle_id = VEHICLE_ID
        actual_driver_user_id = 41
        started_by_user_id = 99

        @property
        def started_at(self):
            raise AssertionError("session time must not be read for falsy operator")

    database = SyntheticSession(
        {"vehicle_usage_session": [Usage()], "vehicle_assignment": [Assignment()]}
    )

    assert _anomalies(database) == EMPTY_RESPONSE


def test_synthetic_expired_assignment_checks_end_before_start() -> None:
    class Assignment:
        vehicle_id = VEHICLE_ID
        operator_user_id = 52
        end_at = STARTED - timedelta(microseconds=1)

        @property
        def start_at(self):
            raise AssertionError("start_at must not be read after expired end")

    database = SyntheticSession(
        {"vehicle_usage_session": [_synthetic_session()], "vehicle_assignment": [Assignment()]}
    )

    assert _anomalies(database) == EMPTY_RESPONSE


@pytest.mark.parametrize(
    ("end_at", "expected_prefix"),
    [(None, ["start-comparison"]), (STARTED, ["end-comparison", "start-comparison"])],
)
def test_synthetic_literal_response_evaluation_order(
    monkeypatch: pytest.MonkeyPatch, end_at: datetime | None, expected_prefix: list[str]
) -> None:
    events = []

    class Timestamp:
        def __ge__(self, other):
            events.append("start-comparison")
            return True

        def __le__(self, other):
            events.append("end-comparison")
            return True

        def isoformat(self):
            events.append("timestamp-iso")
            return "2026-03-15T08:00:00"

    class OperatorID(int):
        def __str__(self):
            events.append("operator-string")
            return "52"

    class VehicleRow:
        id = VEHICLE_ID

        @property
        def plate_number(self):
            events.append("vehicle-label")
            return "DM001AA"

    actual_display: Callable = analytics._user_display_name

    def traced_display(user):
        events.append("canonical-display")
        return actual_display(user)

    monkeypatch.setattr(analytics, "_user_display_name", traced_display)
    database = SyntheticSession(
        {
            "vehicle_usage_session": [_synthetic_session(started_at=Timestamp())],
            "vehicle": [VehicleRow()],
            "application_users": [SimpleNamespace(id=41, first_name="Mario", last_name="Rossi")],
            "vehicle_assignment": [
                _synthetic_assignment(operator_user_id=OperatorID(52), end_at=end_at)
            ],
        }
    )

    assert _anomalies(database) == _expected_response([_expected_item()])
    assert events == [
        *expected_prefix,
        "vehicle-label",
        "timestamp-iso",
        "canonical-display",
        "operator-string",
    ]


def test_synthetic_timestamp_failure_precedes_display_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Timestamp:
        def __ge__(self, other):
            return True

        def isoformat(self):
            raise ValueError("original timestamp failure")

    def unexpected_display(user):
        raise AssertionError("display must not be evaluated before timestamp failure")

    monkeypatch.setattr(analytics, "_user_display_name", unexpected_display)
    database = SyntheticSession(
        {
            "vehicle_usage_session": [_synthetic_session(started_at=Timestamp())],
            "vehicle_assignment": [_synthetic_assignment()],
        }
    )

    with pytest.raises(ValueError, match="original timestamp failure"):
        _anomalies(database)
