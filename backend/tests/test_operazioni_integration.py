"""Integration tests for GAIA Operazioni module — requires PostgreSQL."""

import os
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Import ApplicationUser so its table is registered in Base metadata
from app.models.application_user import ApplicationUser  # noqa: F401
from app.core.database import Base
from app.modules.operazioni.models.organizational import Team, OperatorProfile
from app.modules.operazioni.models.vehicles import (
    Vehicle,
    VehicleAssignment,
    VehicleUsageSession,
)
from app.modules.operazioni.models.activities import ActivityCatalog, OperatorActivity
from app.modules.operazioni.models.reports import (
    FieldReportCategory,
    FieldReportSeverity,
    FieldReport,
    InternalCase,
)
from app.modules.operazioni.models.attachments import Attachment
from app.modules.operazioni.models.gps import GpsTrackSummary
from app.modules.operazioni.services.vehicle_service import (
    create_vehicle,
    get_vehicle,
    list_vehicles,
    start_usage_session,
    stop_usage_session,
    create_fuel_log,
    create_maintenance,
)
from app.modules.operazioni.services.attachment_service import (
    get_attachment_type,
    check_quota,
    create_quota_metric,
    get_latest_metric,
)
from app.modules.operazioni.models.activities import ActivityCatalog, OperatorActivity
from app.modules.operazioni.models.reports import (
    FieldReportCategory,
    FieldReportSeverity,
    FieldReport,
    InternalCase,
)
from app.modules.operazioni.models.attachments import Attachment
from app.modules.operazioni.models.gps import GpsTrackSummary
from app.modules.operazioni.services.vehicle_service import (
    create_vehicle,
    get_vehicle,
    list_vehicles,
    start_usage_session,
    stop_usage_session,
    create_fuel_log,
    create_maintenance,
)
from app.modules.operazioni.services.attachment_service import (
    get_attachment_type,
    check_quota,
    create_quota_metric,
    get_latest_metric,
)


@pytest.fixture(scope="module")
def db_url():
    return os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://naap_app:change_me@localhost:5434/naap",
    )


@pytest.fixture
def db_session(db_url):
    engine = create_engine(db_url)
    session = Session(engine)
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def cleanup_vehicles(db_session):
    """Clean up vehicles created during tests."""
    created_ids = []
    yield created_ids
    for vid in created_ids:
        db_session.execute(text("DELETE FROM vehicle WHERE id = :id"), {"id": vid})
    db_session.commit()


class TestVehicleIntegration:
    def test_create_and_retrieve_vehicle(self, db_session, cleanup_vehicles):
        vehicle = create_vehicle(
            db_session,
            {
                "code": "INT-TEST-001",
                "name": "Integration Test Vehicle",
                "vehicle_type": "auto",
                "brand": "Test",
                "model": "Model T",
            },
        )
        db_session.commit()
        cleanup_vehicles.append(vehicle.id)

        found = get_vehicle(db_session, vehicle.id)
        assert found is not None
        assert found.code == "INT-TEST-001"
        assert found.name == "Integration Test Vehicle"
        assert found.current_status == "available"

    def test_list_vehicles_with_filter(self, db_session, cleanup_vehicles):
        v1 = create_vehicle(
            db_session,
            {
                "code": "INT-TEST-002",
                "name": "Filter Test Auto",
                "vehicle_type": "auto",
            },
        )
        v2 = create_vehicle(
            db_session,
            {
                "code": "INT-TEST-003",
                "name": "Filter Test Truck",
                "vehicle_type": "truck",
            },
        )
        db_session.commit()
        cleanup_vehicles.extend([v1.id, v2.id])

        autos, total = list_vehicles(db_session, vehicle_type="auto")
        assert total >= 1
        assert all(v.vehicle_type == "auto" for v in autos)

    def test_start_and_stop_usage_session(self, db_session, cleanup_vehicles):
        vehicle = create_vehicle(
            db_session,
            {
                "code": "INT-TEST-004",
                "name": "Session Test Vehicle",
                "vehicle_type": "auto",
            },
        )
        db_session.commit()
        cleanup_vehicles.append(vehicle.id)

        session = start_usage_session(
            db_session,
            {
                "vehicle_id": vehicle.id,
                "started_by_user_id": 1,
                "started_at": datetime.now(),
                "start_odometer_km": Decimal("10000.0"),
                "start_latitude": Decimal("39.9031234"),
                "start_longitude": Decimal("8.5923456"),
            },
        )
        db_session.commit()

        assert session.status == "open"
        assert session.start_odometer_km == Decimal("10000.0")

        stopped = stop_usage_session(
            db_session,
            session,
            {
                "ended_at": datetime.now(),
                "end_odometer_km": Decimal("10050.5"),
                "end_latitude": Decimal("39.9111111"),
                "end_longitude": Decimal("8.6011111"),
            },
        )
        db_session.commit()

        assert stopped.status == "closed"
        assert stopped.end_odometer_km == Decimal("10050.5")

    def test_create_fuel_log(self, db_session, cleanup_vehicles):
        vehicle = create_vehicle(
            db_session,
            {
                "code": "INT-TEST-005",
                "name": "Fuel Test Vehicle",
                "vehicle_type": "auto",
            },
        )
        db_session.commit()
        cleanup_vehicles.append(vehicle.id)

        fuel_log = create_fuel_log(
            db_session,
            vehicle.id,
            {
                "fueled_at": datetime.now(),
                "liters": Decimal("35.5"),
                "total_cost": Decimal("62.80"),
                "station_name": "Test Station",
            },
            recorded_by_user_id=1,
        )
        db_session.commit()

        assert fuel_log.liters == Decimal("35.5")
        assert fuel_log.station_name == "Test Station"

    def test_create_maintenance(self, db_session, cleanup_vehicles):
        vehicle = create_vehicle(
            db_session,
            {
                "code": "INT-TEST-006",
                "name": "Maintenance Test Vehicle",
                "vehicle_type": "auto",
            },
        )
        db_session.commit()
        cleanup_vehicles.append(vehicle.id)

        maintenance = create_maintenance(
            db_session,
            vehicle.id,
            {
                "title": "Integration Test Maintenance",
                "description": "Test maintenance record",
                "opened_at": datetime.now(),
                "status": "planned",
            },
            created_by_user_id=1,
        )
        db_session.commit()

        assert maintenance.status == "planned"
        assert maintenance.title == "Integration Test Maintenance"


class TestActivityIntegration:
    def test_create_activity_with_catalog(self, db_session):
        catalog = ActivityCatalog(
            code="INT-TEST-ACT",
            name="Integration Test Activity",
            category="test",
        )
        db_session.add(catalog)
        db_session.flush()

        activity = OperatorActivity(
            activity_catalog_id=catalog.id,
            operator_user_id=1,
            started_at=datetime.now(),
            status="in_progress",
        )
        db_session.add(activity)
        db_session.flush()

        assert activity.id is not None
        assert activity.status == "in_progress"


class TestReportCaseIntegration:
    def test_report_and_case_linkage(self, db_session):
        cat = FieldReportCategory(code="INT-TEST-CAT", name="Integration Test Category")
        sev = FieldReportSeverity(
            code="INT-TEST-SEV", name="Integration Test Severity", rank_order=5
        )
        db_session.add_all([cat, sev])
        db_session.flush()

        report = FieldReport(
            report_number="INT-TEST-REP-001",
            reporter_user_id=1,
            category_id=cat.id,
            severity_id=sev.id,
            title="Integration Test Report",
            description="Test report description",
        )
        db_session.add(report)
        db_session.flush()

        case = InternalCase(
            case_number="INT-TEST-CAS-001",
            source_report_id=report.id,
            title="Integration Test Case",
            description="Test case description",
            category_id=cat.id,
            severity_id=sev.id,
        )
        db_session.add(case)
        db_session.flush()

        report.internal_case_id = case.id
        report.status = "linked"
        db_session.flush()

        assert report.internal_case_id == case.id
        assert case.source_report_id == report.id
        assert report.status == "linked"


class TestAttachmentIntegration:
    def test_quota_calculation(self, db_session):
        quota = check_quota(db_session)
        assert "total_bytes_used" in quota
        assert "quota_bytes" in quota
        assert "percentage_used" in quota

    def test_create_quota_metric(self, db_session):
        metric = create_quota_metric(db_session)
        db_session.flush()

        assert metric.id is not None
        assert metric.total_bytes_used >= 0

    def test_get_latest_metric(self, db_session):
        create_quota_metric(db_session)
        db_session.commit()
        metric = get_latest_metric(db_session)
        assert metric is not None
        assert metric.percentage_used >= 0


class TestGpsIntegration:
    def test_create_gps_track(self, db_session):
        track = GpsTrackSummary(
            source_type="device_app",
            provider_name="test_provider",
            started_at=datetime.now(),
            start_latitude=Decimal("39.9031234"),
            start_longitude=Decimal("8.5923456"),
            end_latitude=Decimal("39.9111111"),
            end_longitude=Decimal("8.6011111"),
            total_distance_km=Decimal("5.5"),
            total_duration_seconds=3600,
        )
        db_session.add(track)
        db_session.flush()

        assert track.id is not None
        assert track.source_type == "device_app"
        assert track.total_distance_km == Decimal("5.5")


class TestTeamIntegration:
    def test_create_team(self, db_session):
        team = Team(
            code="INT-TEST-TEAM",
            name="Integration Test Team",
            description="Test team for integration",
        )
        db_session.add(team)
        db_session.flush()

        assert team.id is not None
        assert team.code == "INT-TEST-TEAM"

    def test_create_operator_profile(self, db_session):
        profile = OperatorProfile(
            user_id=1,
            employee_code="INT-TEST-EMP",
            phone="+39 123 456 7890",
            can_drive_vehicles=True,
        )
        db_session.add(profile)
        db_session.flush()

        assert profile.id is not None
        assert profile.employee_code == "INT-TEST-EMP"
        assert profile.can_drive_vehicles is True
