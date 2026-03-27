import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.network.models import DevicePosition, FloorPlan, NetworkAlert, NetworkDevice, NetworkScan
from app.modules.network.schemas import (
    DevicePositionResponse,
    FloorPlanDetailResponse,
    FloorPlanResponse,
    NetworkAlertResponse,
    NetworkDashboardSummary,
    NetworkDeviceListResponse,
    NetworkDeviceResponse,
    NetworkDeviceUpdateRequest,
    NetworkScanResponse,
    NetworkScanTriggerResponse,
)
from app.modules.network.services import get_network_dashboard_summary, list_network_devices, run_network_scan

router = APIRouter(prefix="/network", tags=["network"])


def _serialize_device(device: NetworkDevice) -> NetworkDeviceResponse:
    payload = {
        "id": device.id,
        "last_scan_id": device.last_scan_id,
        "ip_address": device.ip_address,
        "mac_address": device.mac_address,
        "hostname": device.hostname,
        "hostname_source": device.hostname_source,
        "display_name": device.display_name,
        "asset_label": device.asset_label,
        "vendor": device.vendor,
        "model_name": device.model_name,
        "device_type": device.device_type,
        "operating_system": device.operating_system,
        "dns_name": device.dns_name,
        "location_hint": device.location_hint,
        "notes": device.notes,
        "metadata_sources": json.loads(device.metadata_sources) if device.metadata_sources else None,
        "status": device.status,
        "is_monitored": device.is_monitored,
        "open_ports": device.open_ports,
        "first_seen_at": device.first_seen_at,
        "last_seen_at": device.last_seen_at,
        "created_at": device.created_at,
        "updated_at": device.updated_at,
    }
    return NetworkDeviceResponse.model_validate(payload)


def _require_network_module(current_user: ApplicationUser) -> None:
    if not current_user.module_rete and not current_user.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Network module not enabled")


@router.get("/dashboard", response_model=NetworkDashboardSummary)
def get_dashboard(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkDashboardSummary:
    _require_network_module(current_user)
    return NetworkDashboardSummary(**get_network_dashboard_summary(db))


@router.get("/devices", response_model=NetworkDeviceListResponse)
def get_devices(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
) -> NetworkDeviceListResponse:
    _require_network_module(current_user)
    items, total = list_network_devices(db, page=page, page_size=page_size, search=search, status=status_filter)
    return NetworkDeviceListResponse(
        items=[_serialize_device(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


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
    return _serialize_device(device)


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
    for field_name, field_value in updates.items():
        setattr(device, field_name, field_value)

    db.add(device)
    db.commit()
    db.refresh(device)
    return _serialize_device(device)


@router.get("/alerts", response_model=list[NetworkAlertResponse])
def get_alerts(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[NetworkAlertResponse]:
    _require_network_module(current_user)
    query = select(NetworkAlert).order_by(NetworkAlert.created_at.desc())
    if status_filter:
        query = query.where(NetworkAlert.status == status_filter)
    return [NetworkAlertResponse.model_validate(item) for item in db.scalars(query).all()]


@router.get("/scans", response_model=list[NetworkScanResponse])
def get_scans(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NetworkScanResponse]:
    _require_network_module(current_user)
    return [
        NetworkScanResponse.model_validate(item)
        for item in db.scalars(select(NetworkScan).order_by(NetworkScan.started_at.desc())).all()
    ]


@router.get("/scans/{scan_id}", response_model=NetworkScanResponse)
def get_scan(
    scan_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkScanResponse:
    _require_network_module(current_user)
    scan = db.get(NetworkScan, scan_id)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return NetworkScanResponse.model_validate(scan)


@router.post("/scans", response_model=NetworkScanTriggerResponse, status_code=status.HTTP_201_CREATED)
def create_scan(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkScanTriggerResponse:
    _require_network_module(current_user)
    result = run_network_scan(db, initiated_by=current_user.username)
    return NetworkScanTriggerResponse(
        scan=NetworkScanResponse.model_validate(result.scan),
        devices_upserted=result.devices_upserted,
        alerts_created=result.alerts_created,
    )


@router.get("/floor-plans", response_model=list[FloorPlanResponse])
def get_floor_plans(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[FloorPlanResponse]:
    _require_network_module(current_user)
    return [FloorPlanResponse.model_validate(item) for item in db.scalars(select(FloorPlan).order_by(FloorPlan.name.asc())).all()]


@router.get("/floor-plans/{floor_plan_id}", response_model=FloorPlanDetailResponse)
def get_floor_plan(
    floor_plan_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FloorPlanDetailResponse:
    _require_network_module(current_user)
    floor_plan = db.get(FloorPlan, floor_plan_id)
    if floor_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    payload = FloorPlanResponse.model_validate(floor_plan).model_dump()
    payload["positions"] = [
        DevicePositionResponse.model_validate(position)
        for position in db.scalars(
            select(DevicePosition).where(DevicePosition.floor_plan_id == floor_plan_id).order_by(DevicePosition.id.asc())
        ).all()
    ]
    return FloorPlanDetailResponse(**payload)
