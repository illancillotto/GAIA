from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.network.models import DevicePosition, FloorPlan, NetworkDevice, NetworkScan, NetworkScanDevice
from app.modules.network.schemas import (
    DevicePositionResponse,
    DevicePositionUpdateRequest,
    FloorPlanCreateRequest,
    FloorPlanDetailResponse,
    FloorPlanDeviceResponse,
    FloorPlanResponse,
    NetworkAlertResponse,
    NetworkAlertUpdateRequest,
    NetworkDashboardSummary,
    NetworkDeviceListResponse,
    NetworkDeviceResponse,
    NetworkDeviceUpdateRequest,
    NetworkScanDetailResponse,
    NetworkScanDeviceResponse,
    NetworkScanDiffEntry,
    NetworkScanDiffResponse,
    NetworkScanResponse,
    NetworkScanTriggerResponse,
)
from app.modules.network.services import (
    create_floor_plan,
    get_device_positions,
    get_device_scan_history,
    get_floor_plan_devices,
    get_network_dashboard_summary,
    get_network_scan_detail,
    get_scan_delta,
    get_scan_diff,
    list_network_alerts,
    list_network_devices,
    list_network_scans,
    run_network_scan,
    update_network_alert,
    upsert_device_position,
    metadata_sources_to_dict,
)

router = APIRouter(prefix="/network", tags=["network"])


def _serialize_device(
    device: NetworkDevice,
    *,
    positions: list[DevicePosition] | None = None,
    scan_history: list[NetworkScanDevice] | None = None,
) -> NetworkDeviceResponse:
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
        "metadata_sources": metadata_sources_to_dict(device.metadata_sources),
        "status": device.status,
        "is_monitored": device.is_monitored,
        "open_ports": device.open_ports,
        "first_seen_at": device.first_seen_at,
        "last_seen_at": device.last_seen_at,
        "created_at": device.created_at,
        "updated_at": device.updated_at,
        "positions": [DevicePositionResponse.model_validate(position) for position in positions or []],
        "scan_history": [
            {
                "scan_id": item.scan_id,
                "observed_at": item.observed_at,
                "status": item.status,
                "hostname": item.hostname,
                "ip_address": item.ip_address,
                "open_ports": item.open_ports,
            }
            for item in scan_history or []
        ],
    }
    return NetworkDeviceResponse.model_validate(payload)


def _serialize_scan(scan_id: int, scan: object, db: Session) -> NetworkScanResponse:
    payload = NetworkScanResponse.model_validate(scan).model_dump()
    payload["delta"] = get_scan_delta(db, scan_id)
    return NetworkScanResponse(**payload)


def _serialize_scan_device(device: NetworkScanDevice) -> NetworkScanDeviceResponse:
    payload = {
        "id": device.id,
        "scan_id": device.scan_id,
        "device_id": device.device_id,
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
        "metadata_sources": metadata_sources_to_dict(device.metadata_sources),
        "status": device.status,
        "open_ports": device.open_ports,
        "observed_at": device.observed_at,
    }
    return NetworkScanDeviceResponse.model_validate(payload)


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
    )


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
    return _serialize_device(
        device,
        positions=get_device_positions(db, device_id),
        scan_history=get_device_scan_history(db, device_id),
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


@router.get("/alerts", response_model=list[NetworkAlertResponse])
def get_alerts(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
) -> list[NetworkAlertResponse]:
    _require_network_module(current_user)
    return [NetworkAlertResponse.model_validate(item) for item in list_network_alerts(db, status_filter, severity)]


@router.patch("/alerts/{alert_id}", response_model=NetworkAlertResponse)
def patch_alert(
    alert_id: int,
    payload: NetworkAlertUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkAlertResponse:
    _require_network_module(current_user)
    alert = update_network_alert(db, alert_id, payload.status)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return NetworkAlertResponse.model_validate(alert)


@router.get("/scans", response_model=list[NetworkScanResponse])
def get_scans(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NetworkScanResponse]:
    _require_network_module(current_user)
    return [_serialize_scan(item.id, item, db) for item in list_network_scans(db)]


@router.get("/scans/{scan_id}", response_model=NetworkScanDetailResponse)
def get_scan(
    scan_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkScanDetailResponse:
    _require_network_module(current_user)
    scan, devices, delta = get_network_scan_detail(db, scan_id)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    payload = NetworkScanResponse.model_validate(scan).model_dump()
    payload["delta"] = delta
    payload["devices"] = [_serialize_scan_device(item) for item in devices]
    return NetworkScanDetailResponse(**payload)


@router.get("/scans/{scan_id}/diff/{other_scan_id}", response_model=NetworkScanDiffResponse)
def get_scan_diff_endpoint(
    scan_id: int,
    other_scan_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkScanDiffResponse:
    _require_network_module(current_user)
    if db.get(NetworkScan, scan_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source scan not found")
    if db.get(NetworkScan, other_scan_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target scan not found")
    summary, changes = get_scan_diff(db, scan_id, other_scan_id)
    return NetworkScanDiffResponse(
        from_scan_id=scan_id,
        to_scan_id=other_scan_id,
        summary=summary,
        changes=[
            NetworkScanDiffEntry(
                key=item["key"],
                before=_serialize_scan_device(item["before"]) if item["before"] else None,
                after=_serialize_scan_device(item["after"]) if item["after"] else None,
                change_type=item["change_type"],
            )
            for item in changes
        ],
    )


@router.post("/scans", response_model=NetworkScanTriggerResponse, status_code=status.HTTP_201_CREATED)
def create_scan(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkScanTriggerResponse:
    _require_network_module(current_user)
    result = run_network_scan(db, initiated_by=current_user.username)
    scan_payload = NetworkScanResponse.model_validate(result.scan).model_dump()
    scan_payload["delta"] = getattr(
        result,
        "delta",
        {"new_devices_count": 0, "missing_devices_count": 0, "changed_devices_count": 0},
    )
    return NetworkScanTriggerResponse(
        scan=NetworkScanResponse(**scan_payload),
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


@router.post("/floor-plans", response_model=FloorPlanResponse, status_code=status.HTTP_201_CREATED)
def post_floor_plan(
    payload: FloorPlanCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FloorPlanResponse:
    _require_network_module(current_user)
    floor_plan = create_floor_plan(
        db,
        name=payload.name,
        floor_label=payload.floor_label,
        building=payload.building,
        svg_content=payload.svg_content,
        image_url=payload.image_url,
        width=payload.width,
        height=payload.height,
    )
    return FloorPlanResponse.model_validate(floor_plan)


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


@router.get("/floor-plans/{floor_plan_id}/devices", response_model=list[FloorPlanDeviceResponse])
def get_floor_plan_devices_endpoint(
    floor_plan_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[FloorPlanDeviceResponse]:
    _require_network_module(current_user)
    floor_plan = db.get(FloorPlan, floor_plan_id)
    if floor_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    return [
        FloorPlanDeviceResponse(
            position=DevicePositionResponse.model_validate(position),
            device=_serialize_device(device),
        )
        for position, device in get_floor_plan_devices(db, floor_plan_id)
    ]
