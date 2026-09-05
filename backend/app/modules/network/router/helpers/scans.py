from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.network.models import (
    NetworkDevice,
    NetworkScanDevice,
)
from app.modules.network.router.helpers.devices import _resolve_device_label
from app.modules.network.schemas import (
    NetworkScanDeviceResponse,
    NetworkScanResponse,
)
from app.modules.network.services import (
    get_scan_delta,
    metadata_sources_to_dict,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

def _serialize_scan(scan_id: int, scan: object, db: Session) -> NetworkScanResponse:
    payload = NetworkScanResponse.model_validate(scan).model_dump()
    payload["delta"] = get_scan_delta(db, scan_id)
    return NetworkScanResponse(**payload)


def _serialize_scan_device(device: NetworkScanDevice, db: Session) -> NetworkScanDeviceResponse:
    reference_device = None
    if device.device_id:
        reference_device = db.get(NetworkDevice, device.device_id)
    if reference_device is None and device.ip_address:
        reference_device = db.scalar(select(NetworkDevice).where(NetworkDevice.ip_address == device.ip_address))
    resolved_label, label_source = (
        _resolve_device_label(reference_device)
        if reference_device is not None
        else (device.display_name or device.hostname or device.ip_address, None)
    )
    payload = {
        "id": device.id,
        "scan_id": device.scan_id,
        "device_id": device.device_id,
        "ip_address": device.ip_address,
        "mac_address": device.mac_address,
        "hostname": device.hostname,
        "hostname_source": device.hostname_source,
        "display_name": device.display_name,
        "resolved_label": resolved_label,
        "label_source": label_source,
        "assigned_user_label": resolved_label if reference_device and reference_device.assigned_user_id else None,
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


# fmt: on
