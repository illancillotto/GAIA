"""Persisted public-route contracts for ordered fuel operator name variants."""

from datetime import datetime

import pytest
import test_operazioni_analytics as existing
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_operazioni_analytics_characterization import database as database
from test_operazioni_analytics_characterization import driver as driver

from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.wc_operator import WCOperator

STARTED = datetime(2026, 3, 15, 8)


def _public_fuel(database: Session) -> dict:
    database.commit()
    previous = existing.app.dependency_overrides.get(get_db)
    existing.app.dependency_overrides[get_db] = lambda: database
    try:
        response = existing.client.get(
            "/operazioni/analytics/fuel",
            params={"from_date": "2026-03-15", "to_date": "2026-03-15"},
            headers=existing._auth_headers(),
        )
    finally:
        if previous is None:
            existing.app.dependency_overrides.pop(get_db, None)
        else:
            existing.app.dependency_overrides[get_db] = previous
    assert response.status_code == 200
    assert not database.new and not database.dirty and not database.deleted
    return response.json()


@pytest.mark.parametrize(
    ("first", "last", "username", "orphan", "session_name", "expected_count", "expected_km"),
    [
        ("Mario", "Rossi", "mrossi", "Mario Rossi", "Mario Rossi", 2, 40),
        ("Mario", "Rossi", "mrossi", "Rossi Mario", "Rossi Mario", 2, 40),
        ("Mario", "Rossi", " mrossi ", " mrossi ", " mrossi ", 2, 40),
        ("Mario", "Rossi", " mrossi ", "mrossi", "mrossi", 1, None),
        ("Mario ", " Rossi", "mrossi", "Mario   Rossi", "Mario   Rossi", 2, 40),
        (" Mario", "Rossi ", "mrossi", "Mario Rossi", "Mario Rossi", 2, 40),
        (None, "Rossi", "Rossi", "Rossi", "Rossi", 2, 40),
        ("Mario", None, "Mario", "Mario", "Mario", 2, 40),
        (None, None, "", "", "", 1, None),
        (None, None, " ", " ", " ", 2, 40),
        ("Mario", "Rossi", "mrossi", "mario rossi", "mario rossi", 1, None),
    ],
)
def test_public_route_exact_variants_consolidate_without_normalizing_raw_related_groups(
    database: Session,
    driver: ApplicationUser,
    first: str | None,
    last: str | None,
    username: str,
    orphan: str,
    session_name: str,
    expected_count: int,
    expected_km: int | None,
) -> None:
    vehicle = existing._make_vehicle(database, "R10001AA")
    operator = existing._make_wc_operator(
        database,
        wc_id=10001,
        username=username,
        gaia_user_id=None,
        first_name=first,
        last_name=last,
    )
    identified = existing._make_fuel_log(database, vehicle, driver.id, STARTED, 10, 20)
    identified.wc_operator_id = operator.id
    legacy = existing._make_fuel_log(database, vehicle, driver.id, STARTED, 10, 20)
    legacy.operator_name = orphan
    usage = existing._make_session(database, vehicle, driver.id, STARTED, 0, 40)
    usage.actual_driver_user_id = None
    usage.operator_name = session_name
    identifier = f"wc:{operator.id}"

    result = _public_fuel(database)

    matched = next(item for item in result["top_operators"] if item["id"] == identifier)
    assert matched["refuel_count"] == expected_count
    assert matched["total_liters"] == expected_count * 10
    assert matched["total_km"] == expected_km
    assert matched["avg_consumption_l_per_100km"] == (expected_count * 25 if expected_km else None)
    assert result["total_liters"] == 20
    assert result["total_cost"] == 40
    assert [item["id"] for item in result["top_vehicles"][0]["related"]] == [
        identifier,
        f"name:{orphan}" if orphan else "unknown",
    ]


def test_public_route_shared_name_collision_keeps_last_query_owner_and_original_group_order(
    database: Session, driver: ApplicationUser
) -> None:
    vehicle = existing._make_vehicle(database, "R10002AA")
    operators = [
        existing._make_wc_operator(
            database,
            wc_id=10010 + index,
            username=f"r100-{index}",
            gaia_user_id=None,
            first_name="Shared",
            last_name="Name",
        )
        for index in range(2)
    ]
    for operator in operators:
        log = existing._make_fuel_log(database, vehicle, driver.id, STARTED, 10, 20)
        log.wc_operator_id = operator.id
    legacy = existing._make_fuel_log(database, vehicle, driver.id, STARTED, 10, 20)
    legacy.operator_name = "Shared Name"
    ordered = database.scalars(
        select(WCOperator).where(WCOperator.id.in_({operator.id for operator in operators}))
    ).all()
    winner = f"wc:{ordered[-1].id}"
    loser = f"wc:{ordered[0].id}"

    result = _public_fuel(database)

    assert [(item["id"], item["refuel_count"]) for item in result["top_operators"]] == [
        (winner, 2),
        (loser, 1),
    ]
    assert [item["id"] for item in result["top_vehicles"][0]["related"]] == [
        *(f"wc:{operator.id}" for operator in operators),
        "name:Shared Name",
    ]
