"""Vehicle domain routes."""

from __future__ import annotations

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser

from app.modules.operazioni.schemas.vehicles import (
    VehicleAssignmentClose,
    VehicleAssignmentCreate,
    VehicleAssignmentResponse,
    VehicleCreate,
    VehicleDocumentResponse,
    VehicleFuelLogCreate,
    VehicleFuelLogResponse,
    VehicleListResponse,
    VehicleMaintenanceComplete,
    VehicleMaintenanceCreate,
    VehicleMaintenanceResponse,
    VehicleMaintenanceUpdate,
    VehicleOdometerReadingCreate,
    VehicleOdometerReadingResponse,
    VehicleResponse,
    VehicleUpdate,
    VehicleUsageSessionResponse,
    VehicleUsageSessionStart,
    VehicleUsageSessionStop,
    VehicleUsageSessionValidate,
)
from app.modules.operazioni.services.vehicle_service import (
    close_assignment,
    complete_maintenance,
    create_assignment,
    create_fuel_log,
    create_maintenance,
    create_odometer_reading,
    create_vehicle,
    deactivate_vehicle,
    get_vehicle,
    get_vehicle_assignments,
    list_fuel_logs,
    list_maintenances,
    list_odometer_readings,
    list_usage_sessions,
    list_vehicles,
    start_usage_session,
    stop_usage_session,
    update_maintenance,
    update_vehicle,
    validate_usage_session,
)

router = APIRouter(prefix="/vehicles", tags=["operazioni/vehicles"])


def _get_current_user_id(current_user: ApplicationUser) -> int:
    return current_user.id


# --- Vehicle CRUD ---


@router.get("", response_model=VehicleListResponse)
def list_vehicles_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status"),
    vehicle_type: str | None = None,
    team_id: UUID | None = None,
    assigned_user_id: int | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    vehicles, total = list_vehicles(
        db,
        status=status_filter,
        vehicle_type=vehicle_type,
        team_id=team_id,
        assigned_user_id=assigned_user_id,
        search=search,
        page=page,
        page_size=page_size,
    )
    return VehicleListResponse(
        items=[VehicleResponse.model_validate(v) for v in vehicles],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if page_size else 0,
    )


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle_endpoint(
    data: VehicleCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    vehicle = create_vehicle(
        db, data.model_dump(), created_by_user_id=_get_current_user_id(current_user)
    )
    db.commit()
    return vehicle


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle_endpoint(
    vehicle_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    vehicle = get_vehicle(db, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )
    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle_endpoint(
    vehicle_id: UUID,
    data: VehicleUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    vehicle = get_vehicle(db, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )
    vehicle = update_vehicle(
        db,
        vehicle,
        data.model_dump(exclude_unset=True),
        updated_by_user_id=_get_current_user_id(current_user),
    )
    db.commit()
    return vehicle


@router.post("/{vehicle_id}/deactivate", response_model=VehicleResponse)
def deactivate_vehicle_endpoint(
    vehicle_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    vehicle = get_vehicle(db, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )
    try:
        vehicle = deactivate_vehicle(
            db, vehicle, updated_by_user_id=_get_current_user_id(current_user)
        )
        db.commit()
        return vehicle
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# --- Assignments ---


@router.get("/{vehicle_id}/assignments", response_model=list[VehicleAssignmentResponse])
def list_assignments_endpoint(
    vehicle_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return get_vehicle_assignments(db, vehicle_id)


@router.post(
    "/{vehicle_id}/assignments",
    response_model=VehicleAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment_endpoint(
    vehicle_id: UUID,
    data: VehicleAssignmentCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        assignment = create_assignment(
            db,
            vehicle_id,
            data.model_dump(),
            assigned_by_user_id=_get_current_user_id(current_user),
        )
        db.commit()
        return assignment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post(
    "/{vehicle_id}/assignments/{assignment_id}/close",
    response_model=VehicleAssignmentResponse,
)
def close_assignment_endpoint(
    vehicle_id: UUID,
    assignment_id: UUID,
    data: VehicleAssignmentClose,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assignments = get_vehicle_assignments(db, vehicle_id)
    assignment = next((a for a in assignments if a.id == assignment_id), None)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
        )
    assignment = close_assignment(db, assignment, data.end_at, data.notes)
    db.commit()
    return assignment


# --- Usage Sessions ---


@router.get("/usage-sessions", response_model=dict)
def list_usage_sessions_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    vehicle_id: UUID | None = None,
    driver_user_id: int | None = None,
    team_id: UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    from datetime import datetime

    sessions, total = list_usage_sessions(
        db,
        vehicle_id=vehicle_id,
        driver_user_id=driver_user_id,
        team_id=team_id,
        status=status_filter,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [VehicleUsageSessionResponse.model_validate(s) for s in sessions],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if page_size else 0,
    }


@router.post(
    "/usage-sessions/start",
    response_model=VehicleUsageSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_usage_session_endpoint(
    data: VehicleUsageSessionStart,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        session_data = data.model_dump()
        session_data["started_by_user_id"] = _get_current_user_id(current_user)
        session = start_usage_session(db, session_data)
        db.commit()
        return session
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post(
    "/usage-sessions/{session_id}/stop", response_model=VehicleUsageSessionResponse
)
def stop_usage_session_endpoint(
    session_id: UUID,
    data: VehicleUsageSessionStop,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    from app.modules.operazioni.models.vehicles import VehicleUsageSession as VUS
    from sqlalchemy import select

    session_obj = db.get(VUS, session_id)
    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    try:
        session_obj = stop_usage_session(db, session_obj, data.model_dump())
        db.commit()
        return session_obj
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post(
    "/usage-sessions/{session_id}/validate", response_model=VehicleUsageSessionResponse
)
def validate_usage_session_endpoint(
    session_id: UUID,
    data: VehicleUsageSessionValidate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    from app.modules.operazioni.models.vehicles import VehicleUsageSession as VUS

    session_obj = db.get(VUS, session_id)
    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    session_obj = validate_usage_session(
        db, session_obj, _get_current_user_id(current_user), data.note
    )
    db.commit()
    return session_obj


@router.get("/usage-sessions/{session_id}", response_model=VehicleUsageSessionResponse)
def get_usage_session_endpoint(
    session_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    from app.modules.operazioni.models.vehicles import VehicleUsageSession as VUS

    session_obj = db.get(VUS, session_id)
    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return session_obj


# --- Odometer ---


@router.post(
    "/{vehicle_id}/odometer-readings",
    response_model=VehicleOdometerReadingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_odometer_reading_endpoint(
    vehicle_id: UUID,
    data: VehicleOdometerReadingCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    reading = create_odometer_reading(
        db,
        vehicle_id,
        data.model_dump(),
        recorded_by_user_id=_get_current_user_id(current_user),
    )
    db.commit()
    return reading


@router.get("/{vehicle_id}/odometer-readings", response_model=dict)
def list_odometer_readings_endpoint(
    vehicle_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    readings, total = list_odometer_readings(
        db, vehicle_id, page=page, page_size=page_size
    )
    return {
        "items": [VehicleOdometerReadingResponse.model_validate(r) for r in readings],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if page_size else 0,
    }


# --- Fuel Logs ---


@router.post(
    "/{vehicle_id}/fuel-logs",
    response_model=VehicleFuelLogResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_fuel_log_endpoint(
    vehicle_id: UUID,
    data: VehicleFuelLogCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    fuel_log = create_fuel_log(
        db,
        vehicle_id,
        data.model_dump(),
        recorded_by_user_id=_get_current_user_id(current_user),
    )
    db.commit()
    return fuel_log


@router.get("/{vehicle_id}/fuel-logs", response_model=dict)
def list_fuel_logs_endpoint(
    vehicle_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    logs, total = list_fuel_logs(db, vehicle_id, page=page, page_size=page_size)
    return {
        "items": [VehicleFuelLogResponse.model_validate(l) for l in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if page_size else 0,
    }


# --- Maintenances ---


@router.post(
    "/{vehicle_id}/maintenances",
    response_model=VehicleMaintenanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_maintenance_endpoint(
    vehicle_id: UUID,
    data: VehicleMaintenanceCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    maintenance = create_maintenance(
        db,
        vehicle_id,
        data.model_dump(),
        created_by_user_id=_get_current_user_id(current_user),
    )
    db.commit()
    return maintenance


@router.get("/{vehicle_id}/maintenances", response_model=dict)
def list_maintenances_endpoint(
    vehicle_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    items, total = list_maintenances(db, vehicle_id, page=page, page_size=page_size)
    return {
        "items": [VehicleMaintenanceResponse.model_validate(m) for m in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if page_size else 0,
    }


@router.patch(
    "/maintenances/{maintenance_id}", response_model=VehicleMaintenanceResponse
)
def update_maintenance_endpoint(
    maintenance_id: UUID,
    data: VehicleMaintenanceUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    from app.modules.operazioni.models.vehicles import VehicleMaintenance as VM

    maintenance = db.get(VM, maintenance_id)
    if not maintenance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance not found"
        )
    maintenance = update_maintenance(
        db, maintenance, data.model_dump(exclude_unset=True)
    )
    db.commit()
    return maintenance


@router.post(
    "/maintenances/{maintenance_id}/complete", response_model=VehicleMaintenanceResponse
)
def complete_maintenance_endpoint(
    maintenance_id: UUID,
    data: VehicleMaintenanceComplete,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    from app.modules.operazioni.models.vehicles import VehicleMaintenance as VM

    maintenance = db.get(VM, maintenance_id)
    if not maintenance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance not found"
        )
    maintenance = complete_maintenance(db, maintenance, data.model_dump())
    db.commit()
    return maintenance
