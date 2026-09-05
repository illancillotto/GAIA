from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.network.models import (
    NetworkScan,
)
from app.modules.network.router.common import _require_network_module
from app.modules.network.router.helpers.scans import _serialize_scan, _serialize_scan_device
from app.modules.network.schemas import (
    NetworkScanDetailResponse,
    NetworkScanDiffEntry,
    NetworkScanDiffResponse,
    NetworkScanResponse,
    NetworkScanTriggerRequest,
    NetworkScanTriggerResponse,
)
from app.modules.network.services import (
    get_network_scan_detail,
    get_scan_diff,
    list_network_scans,
)

router = APIRouter()


# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

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
    payload["devices"] = [_serialize_scan_device(item, db) for item in devices]
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
                before=_serialize_scan_device(item["before"], db) if item["before"] else None,
                after=_serialize_scan_device(item["after"], db) if item["after"] else None,
                change_type=item["change_type"],
            )
            for item in changes
        ],
    )


@router.post("/scans", response_model=NetworkScanTriggerResponse, status_code=status.HTTP_201_CREATED)
def create_scan(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    payload: NetworkScanTriggerRequest | None = None,
) -> NetworkScanTriggerResponse:
    import app.modules.network.router as network_router
    _require_network_module(current_user)
    request_payload = payload or NetworkScanTriggerRequest()
    result = network_router.run_network_scan(
        db,
        initiated_by=current_user.username,
        network_range=request_payload.network_range,
        scan_type=request_payload.scan_type,
    )
    scan_payload = NetworkScanResponse.model_validate(result.scan).model_dump()
    scan_payload["delta"] = getattr(
        result,
        "delta",
        {"new_devices_count": 0, "missing_devices_count": 0, "changed_devices_count": 0},
    )
    return NetworkScanTriggerResponse(
        scan=NetworkScanResponse(**scan_payload),
        devices_upserted=result.devices_upserted, alerts_created=result.alerts_created,
    )


# fmt: on
