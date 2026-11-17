from collections import Counter
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta

from app.core.datetime_compat import UTC
from app.modules.network.models import NetworkDevice, NetworkScanDevice
from app.modules.network.schemas import NetworkArpTimelineItem, NetworkArpTimelineObservation


def _build_arp_timeline_item(
    scope_key: str,
    items: list[NetworkScanDevice],
    devices_by_id: Mapping[int, NetworkDevice],
    resolve_device_label: Callable[[NetworkDevice], tuple[str, str]],
) -> NetworkArpTimelineItem:
    items_desc = sorted(items, key=lambda item: (item.observed_at, item.id), reverse=True)
    items_asc = list(reversed(items_desc))
    distinct_ips = list(dict.fromkeys(item.ip_address for item in items_desc if item.ip_address))
    distinct_macs = list(dict.fromkeys(item.mac_address for item in items_desc if item.mac_address))
    rapid_reappearances = _arp_rapid_reappearances(items_asc)
    suspicious_reasons = _arp_suspicious_reasons(
        distinct_ips, distinct_macs, items_desc, rapid_reappearances
    )

    resolved_label = _resolve_arp_group_label(items_desc, devices_by_id, resolve_device_label)
    ip_counts = Counter(item.ip_address for item in items_desc if item.ip_address)
    mac_counts = Counter(item.mac_address for item in items_desc if item.mac_address)
    return NetworkArpTimelineItem(
        scope_key=scope_key,
        scope_type="device" if items_desc[0].device_id is not None else "ip",
        device_id=items_desc[0].device_id,
        resolved_label=resolved_label,
        primary_ip_address=ip_counts.most_common(1)[0][0] if ip_counts else None,
        primary_mac_address=mac_counts.most_common(1)[0][0] if mac_counts else None,
        first_observed_at=items_asc[0].observed_at,
        last_observed_at=items_desc[0].observed_at,
        observations_count=len(items_desc),
        **_arp_presence_counts(items_desc),
        distinct_ip_addresses=distinct_ips,
        distinct_mac_addresses=distinct_macs,
        rapid_reappearances=rapid_reappearances,
        suspicious_reasons=suspicious_reasons,
        observations=[
            NetworkArpTimelineObservation(
                observed_at=item.observed_at,
                scan_id=item.scan_id,
                device_id=item.device_id,
                ip_address=item.ip_address,
                mac_address=item.mac_address,
                status=item.status,
                resolved_label=resolved_label,
                hostname=item.hostname,
            )
            for item in items_desc[:6]
        ],
    )


def _arp_rapid_reappearances(items_asc: list[NetworkScanDevice]) -> int:
    rapid_reappearances = 0
    previous_online_at: datetime | None = None
    for item in items_asc:
        observed_at = (
            item.observed_at
            if item.observed_at.tzinfo is not None
            else item.observed_at.replace(tzinfo=UTC)
        )
        if item.status == "online":
            if previous_online_at and observed_at - previous_online_at <= timedelta(hours=2):
                rapid_reappearances += 1
            previous_online_at = observed_at
    return rapid_reappearances


def _arp_suspicious_reasons(
    distinct_ips: list[str],
    distinct_macs: list[str],
    items_desc: list[NetworkScanDevice],
    rapid_reappearances: int,
) -> list[str]:
    suspicious_reasons: list[str] = []
    if len(distinct_macs) > 1:
        suspicious_reasons.append("same_ip_multiple_macs")
    if len(distinct_ips) > 1 and items_desc[0].mac_address:
        suspicious_reasons.append("same_mac_multiple_ips")
    if rapid_reappearances > 1:
        suspicious_reasons.append("rapid_reappearances")
    return suspicious_reasons


def _resolve_arp_group_label(
    items_desc: list[NetworkScanDevice],
    devices_by_id: Mapping[int, NetworkDevice],
    resolve_device_label: Callable[[NetworkDevice], tuple[str, str]],
) -> str:
    device = (
        devices_by_id.get(items_desc[0].device_id) if items_desc[0].device_id is not None else None
    )
    return (
        resolve_device_label(device)[0]
        if device is not None
        else items_desc[0].display_name or items_desc[0].hostname or items_desc[0].ip_address
    )


def _arp_presence_counts(items_desc: list[NetworkScanDevice]) -> dict[str, int]:
    return {
        "online_appearances": sum(1 for item in items_desc if item.status == "online"),
        "offline_appearances": sum(1 for item in items_desc if item.status != "online"),
    }
