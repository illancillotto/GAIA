from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.me.router.common import (
    RequireNetworkModule,
    RequireOperazioniModule,
    _serialize_assigned_device,
)
from app.modules.me.schemas import (
    MeAssignedDeviceListResponse,
    MeVehicleAssignmentItem,
    MeVehicleAssignmentListResponse,
)
from app.modules.network.models import NetworkDevice
from app.modules.operazioni.models.vehicles import Vehicle, VehicleAssignment

router = APIRouter(prefix="/me")


# Preserve legacy callable layout so the complexity ratchet remains comparable.
# fmt: off
@router.get("/assets/devices", response_model=MeAssignedDeviceListResponse)
def list_me_assigned_devices(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireNetworkModule],
) -> MeAssignedDeviceListResponse:
    devices = db.execute(
        select(NetworkDevice)
        .where(NetworkDevice.assigned_user_id == current_user.id)
        .order_by(NetworkDevice.last_seen_at.desc())
    ).scalars().all()
    return MeAssignedDeviceListResponse(items=[_serialize_assigned_device(device) for device in devices], total=len(devices))


@router.get("/assets/vehicle-assignments", response_model=MeVehicleAssignmentListResponse)
def list_me_vehicle_assignments(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireOperazioniModule],
) -> MeVehicleAssignmentListResponse:
    rows = db.execute(
        select(VehicleAssignment, Vehicle.name, Vehicle.plate_number, Vehicle.vehicle_type)
        .join(Vehicle, Vehicle.id == VehicleAssignment.vehicle_id)
        .where(VehicleAssignment.operator_user_id == current_user.id)
        .order_by(VehicleAssignment.start_at.desc())
    ).all()
    now = date.today()
    return MeVehicleAssignmentListResponse(
        items=[
            MeVehicleAssignmentItem(
                id=assignment.id,
                vehicle_id=assignment.vehicle_id,
                vehicle_name=vehicle_name,
                vehicle_plate_number=plate_number,
                vehicle_type=vehicle_type,
                assignment_target_type=assignment.assignment_target_type,
                start_at=assignment.start_at,
                end_at=assignment.end_at,
                reason=assignment.reason,
                notes=assignment.notes,
                is_active=assignment.end_at is None or assignment.end_at.date() >= now,
            )
            for assignment, vehicle_name, plate_number, vehicle_type in rows
        ],
        total=len(rows),
    )
# fmt: on
