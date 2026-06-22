from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.security import hash_password
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.operazioni.models.attachments import Attachment
from app.modules.operazioni.models.organizational import Team
from app.modules.operazioni.models.vehicles import (
    Vehicle,
    VehicleAssignment,
    VehicleFuelLog,
    VehicleMaintenance,
    VehicleMaintenanceType,
    VehicleOdometerReading,
    VehicleUsageSession,
)
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.services import vehicle_service


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
TEST_TABLES = [
    ApplicationUser.__table__,
    Team.__table__,
    Attachment.__table__,
    WCOperator.__table__,
    Vehicle.__table__,
    VehicleAssignment.__table__,
    VehicleUsageSession.__table__,
    VehicleFuelLog.__table__,
    VehicleMaintenanceType.__table__,
    VehicleMaintenance.__table__,
    VehicleOdometerReading.__table__,
]


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine, tables=TEST_TABLES)
    Base.metadata.create_all(bind=engine, tables=TEST_TABLES)


def _create_user(db: Session, *, username: str = "vehicle-admin") -> ApplicationUser:
    user = ApplicationUser(
        username=username,
        email=f"{username}@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_operazioni=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_team(db: Session, *, code: str = "T-1") -> Team:
    team = Team(code=code, name=f"Team {code}")
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def _create_vehicle(db: Session, *, code: str = "V-1", name: str = "Vehicle One", status: str = "available", is_active: bool = True) -> Vehicle:
    vehicle = Vehicle(
        code=code,
        name=name,
        vehicle_type="pickup",
        plate_number=f"{code}PLATE",
        brand="Iveco",
        model="Daily",
        notes=f"note-{code}",
        current_status=status,
        is_active=is_active,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def test_vehicle_crud_and_listing_filters() -> None:
    with TestingSessionLocal() as db:
        created = vehicle_service.create_vehicle(
            db,
            {
                "code": "VH-001",
                "name": "Alpha Truck",
                "vehicle_type": "truck",
                "plate_number": "AA001AA",
                "brand": "Iveco",
                "model": "X1",
                "notes": "First note",
            },
            created_by_user_id=7,
        )
        second = _create_vehicle(db, code="VH-002", name="Beta Van", status="maintenance")
        inactive = _create_vehicle(db, code="VH-003", name="Gamma Hidden", is_active=False)

        db.add(
            VehicleUsageSession(
                vehicle_id=second.id,
                started_by_user_id=1,
                started_at=datetime(2026, 6, 10, 10, 0),
                start_odometer_km=Decimal("100.000"),
                status="closed",
            )
        )
        db.add(
            VehicleUsageSession(
                vehicle_id=created.id,
                started_by_user_id=1,
                started_at=datetime(2026, 6, 11, 10, 0),
                start_odometer_km=Decimal("200.000"),
                status="closed",
            )
        )
        db.add(
            VehicleUsageSession(
                vehicle_id=created.id,
                started_by_user_id=1,
                started_at=datetime(2026, 6, 12, 10, 0),
                start_odometer_km=Decimal("210.000"),
                status="closed",
            )
        )
        db.commit()

        updated = vehicle_service.update_vehicle(
            db,
            created,
            {"name": "Alpha Truck Updated", "notes": None, "brand": "MAN"},
            updated_by_user_id=9,
        )

        assert vehicle_service.get_vehicle(db, created.id).id == created.id
        assert updated.name == "Alpha Truck Updated"
        assert updated.notes == "First note"
        assert updated.brand == "MAN"
        assert updated.updated_by_user_id == 9
        assert vehicle_service.get_vehicle(db, uuid4()) is None

        vehicles, total = vehicle_service.list_vehicles(db, search="Truck", page=1, page_size=10)
        assert total == 1
        assert [item.id for item in vehicles] == [created.id]

        filtered, filtered_total = vehicle_service.list_vehicles(db, status="maintenance", vehicle_type="pickup")
        assert filtered_total == 1
        assert filtered[0].id == second.id

        ordered, ordered_total = vehicle_service.list_vehicles(db)
        assert ordered_total == 2
        assert [item.id for item in ordered] == [created.id, second.id]
        assert inactive.id not in [item.id for item in ordered]


def test_deactivate_vehicle_checks_open_sessions_and_updates_status() -> None:
    with TestingSessionLocal() as db:
        vehicle = _create_vehicle(db, code="VH-010")
        open_session = VehicleUsageSession(
            vehicle_id=vehicle.id,
            started_by_user_id=1,
            started_at=datetime(2026, 6, 1, 9, 0),
            start_odometer_km=Decimal("10.000"),
            status="open",
        )
        db.add(open_session)
        db.commit()

        with pytest.raises(ValueError, match="open usage session"):
            vehicle_service.deactivate_vehicle(db, vehicle)

        open_session.status = "closed"
        db.commit()

        result = vehicle_service.deactivate_vehicle(db, vehicle, updated_by_user_id=5)

        assert result.is_active is False
        assert result.current_status == "out_of_service"
        assert result.updated_by_user_id == 5


def test_assignment_creation_validation_listing_and_close() -> None:
    with TestingSessionLocal() as db:
        vehicle = _create_vehicle(db, code="VH-020")
        team = _create_team(db, code="OPS")
        now = datetime(2026, 6, 20, 8, 0)

        with pytest.raises(ValueError, match="operator_user_id required"):
            vehicle_service.create_assignment(
                db,
                vehicle.id,
                {"assignment_target_type": "operator", "operator_user_id": None, "start_at": now},
                assigned_by_user_id=1,
            )

        with pytest.raises(ValueError, match="team_id required"):
            vehicle_service.create_assignment(
                db,
                vehicle.id,
                {"assignment_target_type": "team", "team_id": None, "start_at": now},
                assigned_by_user_id=1,
            )

        operator_assignment = vehicle_service.create_assignment(
            db,
            vehicle.id,
            {
                "assignment_target_type": "operator",
                "operator_user_id": 77,
                "team_id": team.id,
                "start_at": now,
                "notes": "first",
            },
            assigned_by_user_id=1,
        )
        db.commit()

        assert operator_assignment.team_id is None
        assert operator_assignment.operator_user_id == 77

        with pytest.raises(ValueError, match="open assignment"):
            vehicle_service.create_assignment(
                db,
                vehicle.id,
                {"assignment_target_type": "team", "team_id": team.id, "start_at": now + timedelta(hours=1)},
                assigned_by_user_id=1,
            )

        closed = vehicle_service.close_assignment(db, operator_assignment, now + timedelta(days=1), notes="done")
        db.commit()
        assert closed.end_at == now + timedelta(days=1)
        assert closed.notes == "done"

        team_assignment = vehicle_service.create_assignment(
            db,
            vehicle.id,
            {"assignment_target_type": "team", "team_id": team.id, "operator_user_id": 99, "start_at": now + timedelta(days=2)},
            assigned_by_user_id=2,
        )
        db.commit()

        assert team_assignment.operator_user_id is None
        assignments = vehicle_service.get_vehicle_assignments(db, vehicle.id)
        assert [item.id for item in assignments] == [team_assignment.id, operator_assignment.id]


def test_usage_sessions_start_stop_validate_and_list() -> None:
    with TestingSessionLocal() as db:
        vehicle = _create_vehicle(db, code="VH-030")
        other_vehicle = _create_vehicle(db, code="VH-031")
        team = _create_team(db, code="FIELD")

        session = vehicle_service.start_usage_session(
            db,
            {
                "vehicle_id": vehicle.id,
                "started_by_user_id": 10,
                "actual_driver_user_id": 11,
                "team_id": team.id,
                "started_at": datetime(2026, 6, 21, 8, 0),
                "start_odometer_km": Decimal("1000.000"),
            },
        )
        db.commit()

        assert session.status == "open"
        assert db.get(Vehicle, vehicle.id).current_status == "in_use"

        with pytest.raises(ValueError, match="open usage session"):
            vehicle_service.start_usage_session(
                db,
                {
                    "vehicle_id": vehicle.id,
                    "started_by_user_id": 10,
                    "started_at": datetime(2026, 6, 21, 9, 0),
                    "start_odometer_km": Decimal("1001.000"),
                },
            )

        with pytest.raises(ValueError, match="Session is not open"):
            vehicle_service.stop_usage_session(
                db,
                VehicleUsageSession(
                    vehicle_id=other_vehicle.id,
                    started_by_user_id=1,
                    started_at=datetime(2026, 6, 1, 8, 0),
                    start_odometer_km=Decimal("1.000"),
                    status="closed",
                ),
                {"end_odometer_km": Decimal("2.000")},
            )

        with pytest.raises(ValueError, match="End odometer cannot be less"):
            vehicle_service.stop_usage_session(
                db,
                session,
                {"end_odometer_km": Decimal("999.000"), "ended_at": datetime(2026, 6, 21, 12, 0)},
            )

        stopped = vehicle_service.stop_usage_session(
            db,
            session,
            {
                "ended_at": datetime(2026, 6, 21, 12, 0),
                "end_odometer_km": Decimal("1050.000"),
                "gps_source": "gps",
                "notes": "completed",
            },
        )
        db.commit()

        odometer_rows = db.query(VehicleOdometerReading).filter(VehicleOdometerReading.vehicle_id == vehicle.id).all()
        assert stopped.status == "closed"
        assert db.get(Vehicle, vehicle.id).current_status == "available"
        assert len(odometer_rows) == 1
        assert odometer_rows[0].source_type == "gps"
        assert odometer_rows[0].recorded_by_user_id == 11

        validated = vehicle_service.validate_usage_session(db, stopped, validated_by_user_id=99, note="ok")
        db.commit()
        assert validated.status == "validated"
        assert validated.validated_by_user_id == 99
        assert validated.validated_at is not None

        later_session = VehicleUsageSession(
            vehicle_id=other_vehicle.id,
            started_by_user_id=20,
            actual_driver_user_id=21,
            team_id=team.id,
            started_at=datetime(2026, 6, 22, 9, 0),
            start_odometer_km=Decimal("1.000"),
            status="validated",
        )
        db.add(later_session)
        db.commit()

        sessions, total = vehicle_service.list_usage_sessions(
            db,
            team_id=team.id,
            date_from=datetime(2026, 6, 21, 0, 0),
            date_to=datetime(2026, 6, 22, 23, 59),
            page=1,
            page_size=10,
        )
        assert total == 2
        assert [item.id for item in sessions] == [later_session.id, session.id]

        filtered, filtered_total = vehicle_service.list_usage_sessions(
            db,
            vehicle_id=vehicle.id,
            driver_user_id=11,
            status="validated",
        )
        assert filtered_total == 1
        assert filtered[0].id == session.id


def test_fuel_logs_maintenances_and_odometer_readings_crud() -> None:
    with TestingSessionLocal() as db:
        vehicle = _create_vehicle(db, code="VH-040")

        log1 = vehicle_service.create_fuel_log(
            db,
            vehicle.id,
            {
                "fueled_at": datetime(2026, 6, 10, 8, 0),
                "liters": Decimal("20.500"),
                "total_cost": Decimal("40.00"),
                "station_name": "Station A",
            },
            recorded_by_user_id=5,
        )
        log2 = vehicle_service.create_fuel_log(
            db,
            vehicle.id,
            {
                "fueled_at": datetime(2026, 6, 11, 8, 0),
                "liters": Decimal("10.000"),
                "odometer_km": Decimal("1234.000"),
            },
            recorded_by_user_id=6,
        )
        db.commit()

        logs, log_total = vehicle_service.list_fuel_logs(db, vehicle.id, page=1, page_size=10)
        assert log_total == 2
        assert [item.id for item in logs] == [log2.id, log1.id]

        maintenance = vehicle_service.create_maintenance(
            db,
            vehicle.id,
            {
                "title": "Tagliando",
                "opened_at": datetime(2026, 6, 1, 9, 0),
                "notes": "initial",
            },
            created_by_user_id=5,
        )
        updated_maintenance = vehicle_service.update_maintenance(
            db,
            maintenance,
            {"notes": None, "supplier_name": "Officina Rossi", "status": "in_progress"},
        )
        completed = vehicle_service.complete_maintenance(
            db,
            updated_maintenance,
            {
                "completed_at": datetime(2026, 6, 5, 18, 0),
                "cost_amount": Decimal("199.99"),
                "notes": "done",
            },
        )
        db.commit()

        maintenances, maint_total = vehicle_service.list_maintenances(db, vehicle.id)
        assert maint_total == 1
        assert maintenances[0].id == maintenance.id
        assert completed.status == "completed"
        assert completed.cost_amount == Decimal("199.99")
        assert completed.notes == "done"

        reading1 = vehicle_service.create_odometer_reading(
            db,
            vehicle.id,
            {"reading_at": datetime(2026, 6, 1, 8, 0), "odometer_km": Decimal("1200.000"), "source_type": "manual"},
            recorded_by_user_id=5,
        )
        reading2 = vehicle_service.create_odometer_reading(
            db,
            vehicle.id,
            {"reading_at": datetime(2026, 6, 2, 8, 0), "odometer_km": Decimal("1250.000"), "source_type": "gps"},
        )
        db.commit()

        readings, reading_total = vehicle_service.list_odometer_readings(db, vehicle.id)
        assert reading_total == 2
        assert [item.id for item in readings] == [reading2.id, reading1.id]
