from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.network.models import (
    FloorPlan,
    NetworkDevice,
)
from app.modules.network.router.common import _require_network_module
from app.modules.network.router.helpers.devices import (
    _serialize_assigned_user,
    _serialize_device,
    _summarize_ip_whois,
)
from app.modules.network.router.helpers.traffic import _build_device_traffic_summary
from app.modules.network.schemas import (
    DevicePositionResponse,
    DevicePositionUpdateRequest,
    NetworkAssignedUserSummary,
    NetworkDeviceBulkUpdateRequest,
    NetworkDeviceBulkUpdateResponse,
    NetworkDeviceListResponse,
    NetworkDeviceResponse,
    NetworkDeviceUpdateRequest,
    NetworkIpWhoisResponse,
)
from app.modules.network.services import (
    get_device_positions,
    get_device_scan_history,
    list_network_devices,
    sync_network_device_alert_state,
    upsert_device_position,
)

router = APIRouter()


# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

@router.get("/devices", response_model=NetworkDeviceListResponse)
def get_devices(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    lifecycle_state: str | None = Query(default=None, alias="lifecycle"),
    assignment: str | None = Query(default=None),
    known: str | None = Query(default=None),
    vendor: str | None = Query(default=None),
    device_type: str | None = Query(default=None),
    floor_plan_id: int | None = Query(default=None),
) -> NetworkDeviceListResponse:
    _require_network_module(current_user)
    items, total = list_network_devices(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status=status_filter,
        lifecycle_state=lifecycle_state,
        assignment=assignment,
        known=known,
        vendor=vendor,
        device_type=device_type,
        floor_plan_id=floor_plan_id,
    )
    return NetworkDeviceListResponse(
        items=[_serialize_device(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/device-assignees", response_model=list[NetworkAssignedUserSummary])
def get_device_assignees(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NetworkAssignedUserSummary]:
    _require_network_module(current_user)
    users = db.scalars(select(ApplicationUser).order_by(ApplicationUser.full_name.asc(), ApplicationUser.username.asc())).all()
    return [_serialize_assigned_user(user) for user in users]


@router.get("/devices/{device_id}", response_model=NetworkDeviceResponse)
def get_device(
    device_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkDeviceResponse:
    _require_network_module(current_user)
    device = db.get(NetworkDevice, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return _serialize_device(
        device,
        positions=get_device_positions(db, device_id),
        scan_history=get_device_scan_history(db, device_id),
        traffic_summary=_build_device_traffic_summary(db, device),
    )


@router.get("/ip-whois/{ip_address}", response_model=NetworkIpWhoisResponse)
def get_ip_whois(
    ip_address: str,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
) -> NetworkIpWhoisResponse:
    _require_network_module(current_user)
    return _summarize_ip_whois(ip_address)


@router.patch("/devices/{device_id}", response_model=NetworkDeviceResponse)
def patch_device(
    device_id: int,
    payload: NetworkDeviceUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkDeviceResponse:
    _require_network_module(current_user)
    device = db.get(NetworkDevice, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    updates = payload.model_dump(exclude_unset=True)
    if "assigned_user_id" in updates and updates["assigned_user_id"] is not None:
        assigned_user = db.get(ApplicationUser, updates["assigned_user_id"])
        if assigned_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found")
    if updates.get("lifecycle_state") == "retired":
        updates["assigned_user_id"] = None
        updates["is_monitored"] = False
        updates["retired_at"] = device.retired_at or datetime.now(UTC)
    elif updates.get("lifecycle_state") == "active":
        updates["retired_at"] = None
    for field_name, field_value in updates.items():
        setattr(device, field_name, field_value)

    sync_network_device_alert_state(db, device)
    db.add(device)
    db.commit()
    db.refresh(device)
    return _serialize_device(
        device,
        positions=get_device_positions(db, device_id),
        scan_history=get_device_scan_history(db, device_id),
        traffic_summary=_build_device_traffic_summary(db, device),
    )


@router.post("/devices/bulk-update", response_model=NetworkDeviceBulkUpdateResponse)
def bulk_update_devices(
    payload: NetworkDeviceBulkUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkDeviceBulkUpdateResponse:
    _require_network_module(current_user)
    devices = db.scalars(
        select(NetworkDevice).where(NetworkDevice.id.in_(payload.device_ids)).order_by(NetworkDevice.ip_address.asc())
    ).all()
    if not devices:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No devices found for bulk update")

    notes_append = payload.notes_append.strip() if payload.notes_append else None
    for device in devices:
        if payload.is_known_device is not None:
            device.is_known_device = payload.is_known_device
        if payload.location_hint is not None:
            device.location_hint = payload.location_hint or None
        if notes_append:
            device.notes = f"{device.notes}\n{notes_append}".strip() if device.notes else notes_append
        sync_network_device_alert_state(db, device)
        db.add(device)

    db.commit()
    for device in devices:
        db.refresh(device)

    return NetworkDeviceBulkUpdateResponse(
        updated_count=len(devices),
        items=[_serialize_device(device) for device in devices],
    )


@router.put("/devices/{device_id}/position", response_model=DevicePositionResponse)
def put_device_position(
    device_id: int,
    payload: DevicePositionUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DevicePositionResponse:
    _require_network_module(current_user)
    device = db.get(NetworkDevice, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    floor_plan = db.get(FloorPlan, payload.floor_plan_id)
    if floor_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    position = upsert_device_position(
        db,
        device_id=device_id,
        floor_plan_id=payload.floor_plan_id,
        x=payload.x,
        y=payload.y,
        label=payload.label,
    )
    return DevicePositionResponse.model_validate(position)


# fmt: on
