"""Vehicle domain services."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.operazioni.models.vehicles import (
    Vehicle,
    VehicleAssignment,
    VehicleDocument,
    VehicleFuelLog,
    VehicleMaintenance,
    VehicleOdometerReading,
    VehicleUsageSession,
)

logger = logging.getLogger(__name__)


def list_vehicles(
    db: Session,
    status: str | None = None,
    vehicle_type: str | None = None,
    team_id: UUID | None = None,
    assigned_user_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[Vehicle], int]:
    query = select(Vehicle).where(Vehicle.is_active == True)

    if status:
        query = query.where(Vehicle.current_status == status)
    if vehicle_type:
        query = query.where(Vehicle.vehicle_type == vehicle_type)
    if search:
        like = f"%{search}%"
        query = query.where(
            (Vehicle.name.ilike(like))
            | (Vehicle.code.ilike(like))
            | (Vehicle.plate_number.ilike(like))
            | (Vehicle.brand.ilike(like))
            | (Vehicle.model.ilike(like))
            | (Vehicle.notes.ilike(like))
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    vehicles = db.scalars(
        query.order_by(Vehicle.name).offset((page - 1) * page_size).limit(page_size)
    ).all()

    return list(vehicles), total


def get_vehicle(db: Session, vehicle_id: UUID) -> Vehicle | None:
    return db.get(Vehicle, vehicle_id)


def create_vehicle(
    db: Session, data: dict, created_by_user_id: int | None = None
) -> Vehicle:
    vehicle = Vehicle(**data, created_by_user_id=created_by_user_id)
    db.add(vehicle)
    db.flush()
    logger.info("Vehicle created: %s (%s)", vehicle.code, vehicle.id)
    return vehicle


def update_vehicle(
    db: Session, vehicle: Vehicle, data: dict, updated_by_user_id: int | None = None
) -> Vehicle:
    for key, value in data.items():
        if value is not None:
            setattr(vehicle, key, value)
    if updated_by_user_id is not None:
        vehicle.updated_by_user_id = updated_by_user_id
    db.flush()
    logger.info("Vehicle updated: %s", vehicle.id)
    return vehicle


def deactivate_vehicle(
    db: Session, vehicle: Vehicle, updated_by_user_id: int | None = None
) -> Vehicle:
    open_session = db.scalar(
        select(VehicleUsageSession).where(
            VehicleUsageSession.vehicle_id == vehicle.id,
            VehicleUsageSession.status == "open",
        )
    )
    if open_session:
        raise ValueError("Cannot deactivate vehicle with open usage session")

    vehicle.is_active = False
    vehicle.current_status = "out_of_service"
    if updated_by_user_id is not None:
        vehicle.updated_by_user_id = updated_by_user_id
    db.flush()
    logger.info("Vehicle deactivated: %s", vehicle.id)
    return vehicle


def get_vehicle_assignments(db: Session, vehicle_id: UUID) -> list[VehicleAssignment]:
    return db.scalars(
        select(VehicleAssignment)
        .where(VehicleAssignment.vehicle_id == vehicle_id)
        .order_by(VehicleAssignment.start_at.desc())
    ).all()


def create_assignment(
    db: Session, vehicle_id: UUID, data: dict, assigned_by_user_id: int
) -> VehicleAssignment:
    existing = db.scalar(
        select(VehicleAssignment).where(
            VehicleAssignment.vehicle_id == vehicle_id,
            VehicleAssignment.end_at.is_(None),
        )
    )
    if existing:
        raise ValueError("Vehicle already has an open assignment")

    if data["assignment_target_type"] == "operator":
        if not data.get("operator_user_id"):
            raise ValueError("operator_user_id required for operator assignment")
        data["team_id"] = None
    elif data["assignment_target_type"] == "team":
        if not data.get("team_id"):
            raise ValueError("team_id required for team assignment")
        data["operator_user_id"] = None

    assignment = VehicleAssignment(
        vehicle_id=vehicle_id, assigned_by_user_id=assigned_by_user_id, **data
    )
    db.add(assignment)
    db.flush()
    logger.info("Vehicle assignment created: %s", assignment.id)
    return assignment


def close_assignment(
    db: Session,
    assignment: VehicleAssignment,
    end_at: datetime,
    notes: str | None = None,
) -> VehicleAssignment:
    assignment.end_at = end_at
    if notes:
        assignment.notes = notes
    db.flush()
    logger.info("Vehicle assignment closed: %s", assignment.id)
    return assignment


def start_usage_session(db: Session, data: dict) -> VehicleUsageSession:
    open_session = db.scalar(
        select(VehicleUsageSession).where(
            VehicleUsageSession.vehicle_id == data["vehicle_id"],
            VehicleUsageSession.status == "open",
        )
    )
    if open_session:
        raise ValueError("Vehicle already has an open usage session")

    session = VehicleUsageSession(**data)
    db.add(session)
    db.flush()

    vehicle = db.get(Vehicle, data["vehicle_id"])
    if vehicle:
        vehicle.current_status = "in_use"

    logger.info("Vehicle usage session started: %s", session.id)
    return session


def stop_usage_session(
    db: Session, session: VehicleUsageSession, data: dict
) -> VehicleUsageSession:
    if session.status != "open":
        raise ValueError("Session is not open")

    start_km = session.start_odometer_km
    end_km = data["end_odometer_km"]
    if end_km < start_km:
        raise ValueError("End odometer cannot be less than start odometer")

    for key, value in data.items():
        setattr(session, key, value)
    session.status = "closed"
    db.flush()

    vehicle = db.get(Vehicle, session.vehicle_id)
    if vehicle:
        vehicle.current_status = "available"

    odometer = VehicleOdometerReading(
        vehicle_id=session.vehicle_id,
        reading_at=session.ended_at or datetime.now(),
        odometer_km=end_km,
        source_type=data.get("gps_source", "manual"),
        usage_session_id=session.id,
        recorded_by_user_id=session.actual_driver_user_id or session.started_by_user_id,
    )
    db.add(odometer)

    logger.info("Vehicle usage session stopped: %s", session.id)
    return session


def validate_usage_session(
    db: Session,
    session: VehicleUsageSession,
    validated_by_user_id: int,
    note: str | None = None,
) -> VehicleUsageSession:
    session.status = "validated"
    session.validated_by_user_id = validated_by_user_id
    session.validated_at = datetime.now()
    db.flush()
    logger.info("Vehicle usage session validated: %s", session.id)
    return session


def list_usage_sessions(
    db: Session,
    vehicle_id: UUID | None = None,
    driver_user_id: int | None = None,
    team_id: UUID | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[VehicleUsageSession], int]:
    query = select(VehicleUsageSession)

    if vehicle_id:
        query = query.where(VehicleUsageSession.vehicle_id == vehicle_id)
    if driver_user_id:
        query = query.where(VehicleUsageSession.actual_driver_user_id == driver_user_id)
    if team_id:
        query = query.where(VehicleUsageSession.team_id == team_id)
    if status:
        query = query.where(VehicleUsageSession.status == status)
    if date_from:
        query = query.where(VehicleUsageSession.started_at >= date_from)
    if date_to:
        query = query.where(VehicleUsageSession.started_at <= date_to)

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    sessions = db.scalars(
        query.order_by(VehicleUsageSession.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return list(sessions), total


def create_fuel_log(
    db: Session, vehicle_id: UUID, data: dict, recorded_by_user_id: int
) -> VehicleFuelLog:
    fuel_log = VehicleFuelLog(
        vehicle_id=vehicle_id, recorded_by_user_id=recorded_by_user_id, **data
    )
    db.add(fuel_log)
    db.flush()
    logger.info("Fuel log created: %s", fuel_log.id)
    return fuel_log


def list_fuel_logs(
    db: Session, vehicle_id: UUID, page: int = 1, page_size: int = 25
) -> tuple[list[VehicleFuelLog], int]:
    query = select(VehicleFuelLog).where(VehicleFuelLog.vehicle_id == vehicle_id)
    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0
    logs = db.scalars(
        query.order_by(VehicleFuelLog.fueled_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(logs), total


def create_maintenance(
    db: Session, vehicle_id: UUID, data: dict, created_by_user_id: int | None = None
) -> VehicleMaintenance:
    maintenance = VehicleMaintenance(
        vehicle_id=vehicle_id, created_by_user_id=created_by_user_id, **data
    )
    db.add(maintenance)
    db.flush()
    logger.info("Maintenance created: %s", maintenance.id)
    return maintenance


def update_maintenance(
    db: Session, maintenance: VehicleMaintenance, data: dict
) -> VehicleMaintenance:
    for key, value in data.items():
        if value is not None:
            setattr(maintenance, key, value)
    db.flush()
    return maintenance


def complete_maintenance(
    db: Session, maintenance: VehicleMaintenance, data: dict
) -> VehicleMaintenance:
    maintenance.status = "completed"
    maintenance.completed_at = data["completed_at"]
    if data.get("cost_amount") is not None:
        maintenance.cost_amount = data["cost_amount"]
    if data.get("notes"):
        maintenance.notes = data["notes"]
    db.flush()
    logger.info("Maintenance completed: %s", maintenance.id)
    return maintenance


def list_maintenances(
    db: Session, vehicle_id: UUID, page: int = 1, page_size: int = 25
) -> tuple[list[VehicleMaintenance], int]:
    query = select(VehicleMaintenance).where(
        VehicleMaintenance.vehicle_id == vehicle_id
    )
    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.order_by(VehicleMaintenance.opened_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total


def create_odometer_reading(
    db: Session, vehicle_id: UUID, data: dict, recorded_by_user_id: int | None = None
) -> VehicleOdometerReading:
    reading = VehicleOdometerReading(
        vehicle_id=vehicle_id, recorded_by_user_id=recorded_by_user_id, **data
    )
    db.add(reading)
    db.flush()
    return reading


def list_odometer_readings(
    db: Session, vehicle_id: UUID, page: int = 1, page_size: int = 25
) -> tuple[list[VehicleOdometerReading], int]:
    query = select(VehicleOdometerReading).where(
        VehicleOdometerReading.vehicle_id == vehicle_id
    )
    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.order_by(VehicleOdometerReading.reading_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total
