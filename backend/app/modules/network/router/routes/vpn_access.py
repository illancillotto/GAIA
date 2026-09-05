from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.network.schemas import (
    NetworkVpnDeviceListResponse,
    NetworkVpnDeviceResponse,
    NetworkVpnDeviceStatusUpdateRequest,
    NetworkVpnSessionListResponse,
    NetworkVpnSessionResponse,
)
from app.modules.network.vpn_access import (
    list_vpn_devices,
    list_vpn_sessions,
    update_vpn_device_status,
)

router = APIRouter()


# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

@router.get("/vpn-access/devices", response_model=NetworkVpnDeviceListResponse)
def list_vpn_access_devices(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_role("super_admin", "admin"))],
    user_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> NetworkVpnDeviceListResponse:
    devices, total = list_vpn_devices(db, user_id=user_id, status=status_filter, skip=skip, limit=limit)
    return NetworkVpnDeviceListResponse(
        items=[NetworkVpnDeviceResponse.model_validate(device) for device in devices],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/vpn-access/sessions", response_model=NetworkVpnSessionListResponse)
def list_vpn_access_sessions(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_role("super_admin", "admin"))],
    user_id: int | None = Query(default=None),
    event_type: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> NetworkVpnSessionListResponse:
    sessions, total = list_vpn_sessions(db, user_id=user_id, event_type=event_type, skip=skip, limit=limit)
    return NetworkVpnSessionListResponse(
        items=[NetworkVpnSessionResponse.model_validate(session) for session in sessions],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.patch("/vpn-access/devices/{device_id}", response_model=NetworkVpnDeviceResponse)
def patch_vpn_access_device(
    device_id: int,
    payload: NetworkVpnDeviceStatusUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_role("super_admin", "admin"))],
) -> NetworkVpnDeviceResponse:
    device = update_vpn_device_status(db, device_id=device_id, status=payload.status)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo VPN non trovato")
    return NetworkVpnDeviceResponse.model_validate(device)


# fmt: on
