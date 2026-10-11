"""Public route contracts for the shared vehicle-session distance policy."""

from collections.abc import Generator
from datetime import datetime
from decimal import Decimal

import pytest
import test_operazioni_analytics as existing
from sqlalchemy.orm import Session
from test_operazioni_analytics_characterization import database as database
from test_operazioni_analytics_characterization import driver as driver

from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.vehicles import VehicleUsageSession

STARTED = datetime(2026, 3, 15, 8)
PARAMS = {"from_date": "2026-03-15", "to_date": "2026-03-15", "granularity": "day"}


@pytest.fixture
def public_database(database: Session) -> Generator[Session, None, None]:
    previous = existing.app.dependency_overrides.get(get_db)
    existing.app.dependency_overrides[get_db] = lambda: database
    try:
        yield database
    finally:
        if previous is None:
            existing.app.dependency_overrides.pop(get_db, None)
        else:
            existing.app.dependency_overrides[get_db] = previous


def _seed(database: Session, driver: ApplicationUser) -> VehicleUsageSession:
    vehicle = existing._make_vehicle(database, "R31001AA")
    usage = existing._make_session(database, vehicle, driver.id, STARTED, 0, 100)
    operator = existing._make_wc_operator(
        database, wc_id=31001, username="r31operator", gaia_user_id=driver.id
    )
    log = existing._make_fuel_log(database, vehicle, driver.id, STARTED, 10, 20)
    log.wc_operator_id = operator.id
    return usage


@pytest.mark.parametrize("endpoint", ["fuel", "km"])
@pytest.mark.parametrize(
    ("route", "start", "end", "distance"),
    [
        (Decimal("42.125"), Decimal("100"), Decimal("110"), 42.1),
        (Decimal("-5"), Decimal("100"), Decimal("110"), -5),
        (Decimal("0"), Decimal("100"), Decimal("110"), 10),
        (None, Decimal("100"), Decimal("110"), 10),
        (None, Decimal("0"), Decimal("0"), 0),
        (None, Decimal("100"), Decimal("90"), 0),
        (None, Decimal("-10"), Decimal("0"), 10),
        (None, Decimal("0"), Decimal("10.125"), 10.1),
        (None, Decimal("100"), None, 0),
        (Decimal("12"), Decimal("100"), None, 12),
    ],
)
def test_public_distance_precedence_and_all_km_response_projections(
    public_database: Session,
    driver: ApplicationUser,
    endpoint: str,
    route: Decimal | None,
    start: Decimal,
    end: Decimal | None,
    distance: float,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    usage = _seed(public_database, driver)
    usage.route_distance_km = route
    usage.start_odometer_km = start
    usage.end_odometer_km = end
    public_database.commit()
    headers = existing._auth_headers()
    identifier = str(usage.id)
    vehicle_id = str(usage.vehicle_id)
    driver_id = str(driver.id)
    reads = []
    original_getattribute = VehicleUsageSession.__getattribute__

    def record_read(instance, name):
        if name in {"route_distance_km", "start_odometer_km", "end_odometer_km"}:
            reads.append(name)
        return original_getattribute(instance, name)

    monkeypatch.setattr(VehicleUsageSession, "__getattribute__", record_read)
    response = existing.client.get(
        f"/operazioni/analytics/{endpoint}", params=PARAMS, headers=headers
    )

    assert response.status_code == 200
    payload = response.json()
    if endpoint == "km":
        extreme = {
            "session_id": identifier,
            "vehicle_label": "R31001AA",
            "operator_label": "characterization-driver",
            "started_at": STARTED.isoformat(),
            "ended_at": "2026-03-15T10:00:00",
            "duration_minutes": 120,
            "km": distance,
        }
        assert payload == {
            "time_series": [{"period": "2026-03-15", "value": distance}],
            "top_vehicles": [
                {
                    "id": vehicle_id,
                    "label": "R31001AA",
                    "total_km": distance,
                    "session_count": 1,
                    "avg_km_per_session": distance,
                }
            ],
            "top_operators": [
                {
                    "id": driver_id,
                    "label": "characterization-driver",
                    "total_km": distance,
                    "session_count": 1,
                    "avg_km_per_session": distance,
                }
            ],
            "total_km": distance,
            "avg_km_per_session": distance,
            "longest_session": extreme,
            "shortest_session": extreme,
        }
    else:
        assert payload["top_vehicles"][0]["total_km"] == distance
        assert payload["top_operators"][0]["total_km"] == (distance if distance > 0 else None)
        assert payload["total_liters"] == 10
        assert payload["total_cost"] == 20
        assert payload["top_vehicles"][0]["refuel_count"] == 1
        assert payload["storno_count"] == 0
    if route:
        per_call = ["route_distance_km", "route_distance_km"]
    elif end is None:
        per_call = ["route_distance_km", "end_odometer_km"]
    else:
        per_call = [
            "route_distance_km",
            "end_odometer_km",
            "start_odometer_km",
            "end_odometer_km",
            "start_odometer_km",
        ]
    assert reads == per_call * (2 if endpoint == "fuel" else 6)
    assert not public_database.new and not public_database.dirty and not public_database.deleted


@pytest.mark.parametrize("endpoint", ["fuel", "km"])
@pytest.mark.parametrize("allowed", [False, True])
def test_public_distance_routes_require_real_login_and_module_permission(
    public_database: Session, endpoint: str, allowed: bool
) -> None:
    headers = existing._auth_headers(module_operazioni=allowed)
    anonymous = existing.client.get(f"/operazioni/analytics/{endpoint}", params=PARAMS)
    response = existing.client.get(
        f"/operazioni/analytics/{endpoint}", params=PARAMS, headers=headers
    )
    assert anonymous.status_code == 401
    assert response.status_code == (200 if allowed else 403)


@pytest.mark.parametrize("endpoint", ["fuel", "km"])
@pytest.mark.parametrize("field", ["route_distance_km", "end_odometer_km", "start_odometer_km"])
def test_public_distance_float_errors_are_not_swallowed_for_unflushed_orm_values(
    public_database: Session, driver: ApplicationUser, endpoint: str, field: str
) -> None:
    usage = _seed(public_database, driver)
    public_database.commit()
    headers = existing._auth_headers()
    setattr(usage, field, "not-a-number")

    with pytest.raises(ValueError, match="could not convert string to float"):
        existing.client.get(f"/operazioni/analytics/{endpoint}", params=PARAMS, headers=headers)

    assert usage in public_database.dirty


@pytest.mark.parametrize("endpoint", ["fuel", "km"])
def test_public_distance_missing_unflushed_start_is_zero_not_a_coercion_error(
    public_database: Session, driver: ApplicationUser, endpoint: str
) -> None:
    usage = _seed(public_database, driver)
    public_database.commit()
    headers = existing._auth_headers()
    usage.start_odometer_km = None

    response = existing.client.get(
        f"/operazioni/analytics/{endpoint}", params=PARAMS, headers=headers
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["top_vehicles"][0]["total_km"] == 0
    if endpoint == "km":
        assert payload["total_km"] == 0
    assert usage in public_database.dirty
