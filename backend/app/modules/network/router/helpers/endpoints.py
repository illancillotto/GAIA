from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.network.models import (
    NetworkDevice,
    NetworkFirewallEvent,
)
from app.modules.network.router.helpers.devices import _resolve_device_label
from app.modules.network.services import (
    metadata_sources_to_dict,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

def _resolve_label_for_ip(db: Session, ip_address: str | None) -> str | None:
    if not ip_address:
        return None
    device = db.scalar(select(NetworkDevice).where(NetworkDevice.ip_address == ip_address))
    if device is None:
        return None
    return _resolve_device_label(device)[0]


def _resolve_firewall_event_endpoint_labels(
    db: Session,
    *,
    device_id: int | None,
    src_ip: str | None,
    dst_ip: str | None,
) -> tuple[str | None, str | None]:
    src_label = _resolve_label_for_ip(db, src_ip)
    dst_label = _resolve_label_for_ip(db, dst_ip)
    if device_id is None or (src_label and dst_label):
        return src_label, dst_label

    linked_device = db.get(NetworkDevice, device_id)
    if linked_device is None:
        return src_label, dst_label

    linked_label = _resolve_device_label(linked_device)[0]
    if not src_label and src_ip and src_ip == linked_device.ip_address:
        src_label = linked_label
    if not dst_label and dst_ip and dst_ip == linked_device.ip_address:
        dst_label = linked_label
    return src_label, dst_label


def _extract_event_traffic(event: NetworkFirewallEvent, *, device_ip: str) -> tuple[int, int, str | None]:
    raw_payload = metadata_sources_to_dict(event.raw_payload) or {}
    parsed = raw_payload.get("parsed") if isinstance(raw_payload, dict) else None
    parsed = parsed if isinstance(parsed, dict) else {}

    def _to_int(value: Any) -> int:
        if value is None:
            return 0
        try:
            return max(int(str(value).strip()), 0)
        except (TypeError, ValueError):
            return 0

    bytes_sent = _to_int(parsed.get("bytes_sent"))
    bytes_received = _to_int(parsed.get("bytes_received"))

    if event.src_ip == device_ip:
        return bytes_received, bytes_sent, event.dst_ip
    if event.dst_ip == device_ip:
        return bytes_sent, bytes_received, event.src_ip
    return 0, 0, event.dst_ip or event.src_ip


# fmt: on
