"""Real-database characterization prerequisites for the analytics hotspot."""

from collections.abc import Generator
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
import test_operazioni_analytics as existing
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.vehicles import VehicleFuelLog, VehicleUsageSession
from app.modules.operazioni.routes import analytics


@pytest.fixture
def database() -> Generator[Session, None, None]:
    Base.metadata.drop_all(bind=existing.engine)
    Base.metadata.create_all(bind=existing.engine)
    with existing.TestingSessionLocal() as session:
        yield session
    Base.metadata.drop_all(bind=existing.engine)


@pytest.fixture
def driver(database: Session) -> ApplicationUser:
    user = ApplicationUser(
        username="characterization-driver",
        email="characterization@example.local",
        password_hash="not-used-by-direct-route-tests",
        role="viewer",
        is_active=True,
        module_operazioni=True,
    )
    database.add(user)
    database.flush()
    return user


def _fuel_result(database: Session):
    return analytics.fuel_analytics(
        current_user=None,
        db=database,
        from_date="2026-01-01",
        to_date="2026-12-31",
        granularity="month",
    )


@pytest.mark.parametrize(
    ("vehicle_type", "wc_type", "target"),
    [
        ("autocarro", None, 7.5),
        ("truck", None, 26.0),
        ("furgone", None, 11.5),
        ("trattore", None, 15.0),
        ("speciale", None, None),
        ("", "van", 11.5),
        ("", "", None),
    ],
)
def test_fuel_vehicle_targets_preserve_existing_substring_precedence(
    database: Session,
    driver: ApplicationUser,
    vehicle_type: str,
    wc_type: str | None,
    target: float | None,
) -> None:
    vehicle = existing._make_vehicle(database)
    vehicle.vehicle_type = vehicle_type
    vehicle.vehicle_type_wc = wc_type
    started = datetime(2026, 3, 15, 8)
    usage = existing._make_session(database, vehicle, driver.id, started, 0, 100)
    usage.route_distance_km = Decimal("100")
    existing._make_fuel_log(database, vehicle, driver.id, started, 15, 30)
    database.flush()

    result = _fuel_result(database)

    item = result.top_vehicles[0]
    assert item.total_km == 100
    assert item.avg_consumption_l_per_100km == 15
    if target is None:
        assert item.consumption_coefficient is None
        assert item.consumption_judgement is None
    else:
        coefficient = 15 / target
        assert item.consumption_coefficient == round(coefficient, 3)
        expected = "OK" if coefficient <= 1.1 else "Alto" if coefficient <= 1.3 else "Molto alto"
        assert item.consumption_judgement == expected


@pytest.mark.parametrize(
    ("liters", "judgement"), [(8.25, "OK"), (9.75, "Alto"), (10, "Molto alto")]
)
def test_fuel_judgement_uses_unrounded_coefficient(
    database: Session, driver: ApplicationUser, liters: float, judgement: str
) -> None:
    vehicle = existing._make_vehicle(database)
    started = datetime(2026, 3, 15, 8)
    existing._make_session(database, vehicle, driver.id, started, 0, 100)
    existing._make_fuel_log(database, vehicle, driver.id, started, liters, liters * 2)
    database.flush()

    assert _fuel_result(database).top_vehicles[0].consumption_judgement == judgement


def test_fuel_consolidates_operator_variants_but_not_vehicle_related_keys(
    database: Session, driver: ApplicationUser
) -> None:
    vehicle = existing._make_vehicle(database)
    vehicle.vehicle_type = "van"
    started = datetime(2026, 3, 15, 8)
    operator = existing._make_wc_operator(
        database,
        wc_id=9001,
        username="mrossi",
        gaia_user_id=driver.id,
        first_name="Mario",
        last_name="Rossi",
    )
    existing._make_session(database, vehicle, driver.id, started, 0, 100)
    legacy_session = existing._make_session(database, vehicle, driver.id, started, 0, 200)
    legacy_session.actual_driver_user_id = None
    legacy_session.operator_name = "Mario Rossi"
    for index, name in enumerate([None, "Mario Rossi", "Rossi Mario", "mrossi"]):
        log = existing._make_fuel_log(database, vehicle, driver.id, started, 10, 20)
        log.operator_name = name
        log.station_name = " Station "
        if index == 0:
            log.wc_operator_id = operator.id
    database.flush()

    result = _fuel_result(database)

    assert len(result.top_operators) == 1
    item = result.top_operators[0]
    assert item.id == f"wc:{operator.id}"
    assert item.label == "Mario Rossi"
    assert item.refuel_count == 4
    assert item.total_liters == 40
    assert item.total_km == 100
    assert item.avg_consumption_l_per_100km == 40
    assert item.consumption_coefficient == round(40 / 11.5, 3)
    assert item.consumption_judgement == "Molto alto"
    assert item.avg_price_per_liter == 2
    assert item.avg_refuel_cost == 20
    assert item.avg_liters_per_refuel == 10
    assert item.top_stations[0].station_name == "Station"
    assert item.top_stations[0].refuel_count == 4
    assert item.related[0].id == str(vehicle.id)
    assert item.related[0].total_liters == 40
    assert {related.id for related in result.top_vehicles[0].related} == {
        f"wc:{operator.id}",
        "name:Mario Rossi",
        "name:Rossi Mario",
        "name:mrossi",
    }


@pytest.mark.parametrize("session_name", ["Mario Rossi", "Rossi Mario", "mrossi"])
def test_fuel_operator_km_falls_back_to_wc_session_name(
    database: Session, driver: ApplicationUser, session_name: str
) -> None:
    vehicle = existing._make_vehicle(database)
    started = datetime(2026, 3, 15, 8)
    operator = existing._make_wc_operator(
        database,
        wc_id=9002,
        username="mrossi",
        gaia_user_id=None,
        first_name="Mario",
        last_name="Rossi",
    )
    usage = existing._make_session(database, vehicle, driver.id, started, 0, 100)
    usage.actual_driver_user_id = None
    usage.operator_name = session_name
    log = existing._make_fuel_log(database, vehicle, driver.id, started, 10, 20)
    log.wc_operator_id = operator.id
    database.flush()

    assert _fuel_result(database).top_operators[0].total_km == 100


def test_fuel_storni_do_not_enter_positive_refuel_averages(
    database: Session, driver: ApplicationUser
) -> None:
    vehicle = existing._make_vehicle(database)
    started = datetime(2026, 3, 15, 8)
    for liters, cost in [(10, 20), (20, 50), (-5, -10), (0, 7)]:
        existing._make_fuel_log(database, vehicle, driver.id, started, liters, cost)
    database.flush()

    result = _fuel_result(database)

    assert result.total_liters == 25
    assert result.total_cost == 67
    assert result.avg_liters_per_refuel == 15
    assert (result.storno_count, result.storno_liters, result.storno_cost) == (1, -5, -10)
    item = result.top_vehicles[0]
    assert item.refuel_count == 4
    assert item.avg_price_per_liter == round(70 / 30, 4)
    assert item.avg_refuel_cost == 35
    assert item.avg_liters_per_refuel == 15
    assert item.total_km is None
    assert item.avg_consumption_l_per_100km is None
    assert item.top_stations[0].station_name == "Non specificata"


def test_available_periods_merges_sources_deduplicates_and_handles_year_end(
    database: Session, driver: ApplicationUser
) -> None:
    assert analytics.available_periods(None, database) == {
        "years": [],
        "quarters": [],
        "months": [],
    }
    vehicle = existing._make_vehicle(database)
    for fueled in [datetime(2025, 12, 31), datetime(2026, 2, 1), datetime(2026, 2, 28)]:
        existing._make_fuel_log(database, vehicle, driver.id, fueled, 10, 20)
    existing._make_session(database, vehicle, driver.id, datetime(2026, 4, 30), 0, 100)
    database.flush()

    periods = analytics.available_periods(None, database)

    assert periods["years"] == [2026, 2025]
    assert [item["label"] for item in periods["months"]] == ["Apr 2026", "Feb 2026", "Dic 2025"]
    assert [item["to_date"] for item in periods["months"]] == [
        "2026-04-30",
        "2026-02-28",
        "2025-12-31",
    ]
    assert [item["to_date"] for item in periods["quarters"]] == [
        "2026-06-30",
        "2026-03-31",
        "2025-12-31",
    ]


def test_date_and_identity_helpers_preserve_unknown_and_ambiguous_cases() -> None:
    fallback = date(2026, 3, 15)
    assert analytics._parse_date("not-a-date", fallback) == fallback
    assert analytics._parse_date("2026-02-30", fallback) == fallback
    assert analytics._user_display_name(None) == "Sconosciuto"
    context = analytics.SessionAttributionContext({}, {})
    unattributed = VehicleUsageSession(actual_driver_user_id=None, operator_name=None)
    assert analytics._resolve_session_attribution(
        unattributed, context
    ) == analytics.SessionAttribution(None, None, None)


@pytest.mark.parametrize("duration", [None, -30])
def test_km_excludes_missing_or_negative_durations_from_extremes(
    database: Session, driver: ApplicationUser, duration: int | None
) -> None:
    vehicle = existing._make_vehicle(database)
    started = datetime(2026, 3, 15, 8)
    usage = existing._make_session(database, vehicle, driver.id, started, 100, 90)
    usage.end_odometer_km = None
    usage.ended_at = None if duration is None else started + timedelta(minutes=duration)
    usage.actual_driver_user_id = None
    database.flush()

    result = analytics.km_analytics(None, database, "2026-01-01", "2026-12-31", "day")

    assert result.total_km == 0
    assert result.top_operators == []
    assert result.longest_session is None
    assert result.shortest_session is None


def test_fuel_log_null_cost_is_excluded_from_cost_average(
    database: Session, driver: ApplicationUser
) -> None:
    vehicle = existing._make_vehicle(database)
    started = datetime(2026, 3, 15, 8)
    log: VehicleFuelLog = existing._make_fuel_log(database, vehicle, driver.id, started, 10, 0)
    log.total_cost = None
    database.flush()

    item = _fuel_result(database).top_vehicles[0]

    assert item.avg_price_per_liter == 0
    assert item.avg_refuel_cost is None
    assert item.avg_liters_per_refuel == 10
