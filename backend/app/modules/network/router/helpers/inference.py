import ipaddress
import zlib
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.network.detection import event_detection_tags
from app.modules.network.models import (
    NetworkDevice,
    NetworkFirewallEvent,
    NetworkTrackedSubject,
)
from app.modules.network.router.helpers.devices import _resolve_device_label
from app.modules.network.router.helpers.endpoints import (
    _extract_event_traffic,
    _resolve_firewall_event_endpoint_labels,
)
from app.modules.network.router.helpers.tracking import (
    _active_detection_watchlist_entries,
    _build_tracked_subject_activity_summary,
    _extract_firewall_event_parsed,
    _get_active_tracked_subject_map,
    _normalize_tracked_value,
    _tracked_subject_key,
)
from app.modules.network.schemas import (
    NetworkTrackedSubjectActivityEvent,
    NetworkTrackedSubjectActivitySummary,
    NetworkTrackedSubjectResponse,
)
from app.modules.network.services import (
    get_device_scan_history,
    metadata_sources_to_dict,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

def _synthetic_subject_id(entity_type: str, normalized_value: str) -> int:
    return -(zlib.crc32(f"{entity_type}:{normalized_value}".encode()) or 1)


def _find_internal_device_by_ip(db: Session, ip_address: str | None) -> NetworkDevice | None:
    if not ip_address:
        return None
    return db.scalar(select(NetworkDevice).where(NetworkDevice.ip_address == ip_address))


def _build_inferred_tracked_subjects(
    db: Session,
    *,
    window_hours: int,
    entity_type: str | None = None,
    search: str | None = None,
) -> list[NetworkTrackedSubjectResponse]:
    window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)  # noqa: UP017 - preserve legacy AST
    watchlist_entries = _active_detection_watchlist_entries(db)
    active_subjects = _get_active_tracked_subject_map(db)
    events = db.scalars(
        select(NetworkFirewallEvent)
        .where(NetworkFirewallEvent.observed_at >= window_start)
        .order_by(NetworkFirewallEvent.observed_at.desc(), NetworkFirewallEvent.id.desc())
    ).all()

    inferred: dict[tuple[str, str], dict[str, Any]] = {}
    device_cache: dict[int, NetworkDevice | None] = {}
    ip_device_cache: dict[str, NetworkDevice | None] = {}

    def resolve_device(device_id: int | None) -> NetworkDevice | None:
        if device_id is None:
            return None
        if device_id not in device_cache:
            device_cache[device_id] = db.get(NetworkDevice, device_id)
        return device_cache[device_id]

    def resolve_ip_device(ip_address: str | None) -> NetworkDevice | None:
        if not ip_address:
            return None
        if ip_address not in ip_device_cache:
            ip_device_cache[ip_address] = _find_internal_device_by_ip(db, ip_address)
        return ip_device_cache[ip_address]

    def ensure_candidate(
        *,
        candidate_type: str,
        candidate_value: str,
        device: NetworkDevice | None,
        event: NetworkFirewallEvent,
        parsed: dict[str, Any],
        detection_tags: list[str],
    ) -> None:
        normalized_value = _normalize_tracked_value(candidate_type, candidate_value)
        key = _tracked_subject_key(candidate_type, normalized_value)
        if key in active_subjects:
            return
        bucket = inferred.get(key)
        if bucket is None:
            resolved_label = candidate_value
            scan_history: list[dict[str, Any]] = []
            device_id: int | None = None
            device_label: str | None = None
            if device is not None:
                device_id = device.id
                device_label = _resolve_device_label(device)[0]
                resolved_label = device_label
                scan_history = [
                    {
                        "scan_id": item.scan_id,
                        "observed_at": item.observed_at,
                        "status": item.status,
                        "hostname": item.hostname,
                        "ip_address": item.ip_address,
                        "mac_address": item.mac_address,
                        "open_ports": item.open_ports,
                    }
                    for item in get_device_scan_history(db, device.id, limit=8)
                ]
            bucket = {
                "id": _synthetic_subject_id(candidate_type, normalized_value),
                "entity_type": candidate_type,
                "normalized_value": normalized_value,
                "value": device.ip_address if candidate_type == "device" and device is not None else candidate_value,
                "label": None,
                "resolved_label": resolved_label,
                "notes": "Soggetto inferred da eventi firewall sospetti",
                "is_active": True,
                "device_id": device_id,
                "device_label": device_label,
                "created_by_user_id": None,
                "created_by_username": None,
                "created_at": event.observed_at,
                "updated_at": event.observed_at,
                "scan_history": scan_history,
                "events": [],
                "detection_counter": Counter(),
                "total_events": 0,
                "allowed_events": 0,
                "blocked_events": 0,
                "suspicious_events": 0,
                "vpn_suspected_events": 0,
                "proxy_suspected_events": 0,
                "tor_suspected_events": 0,
                "encrypted_dns_events": 0,
                "bytes_in": 0,
                "bytes_out": 0,
                "last_observed_at": event.observed_at,
            }
            inferred[key] = bucket

        bucket["updated_at"] = max(bucket["updated_at"], event.observed_at)
        bucket["created_at"] = min(bucket["created_at"], event.observed_at)
        bucket["total_events"] += 1
        lowered_type = event.event_type.lower()
        if "allow" in lowered_type:
            bucket["allowed_events"] += 1
        if "deny" in lowered_type or "denied" in lowered_type or "block" in lowered_type or "drop" in lowered_type:
            bucket["blocked_events"] += 1
        if detection_tags:
            bucket["suspicious_events"] += 1
            bucket["detection_counter"].update(detection_tags)
            if "vpn_suspected" in detection_tags:
                bucket["vpn_suspected_events"] += 1
            if "proxy_suspected" in detection_tags:
                bucket["proxy_suspected_events"] += 1
            if "tor_suspected" in detection_tags:
                bucket["tor_suspected_events"] += 1
            if "encrypted_dns" in detection_tags:
                bucket["encrypted_dns_events"] += 1
        if len(bucket["events"]) < 10:
            src_label, dst_label = _resolve_firewall_event_endpoint_labels(
                db,
                device_id=event.device_id,
                src_ip=event.src_ip,
                dst_ip=event.dst_ip,
            )
            bytes_in = 0
            bytes_out = 0
            if device is not None:
                bytes_in, bytes_out, _ = _extract_event_traffic(event, device_ip=device.ip_address)
            bucket["bytes_in"] += bytes_in
            bucket["bytes_out"] += bytes_out
            matched_on = "device" if candidate_type == "device" else candidate_type
            bucket["events"].append(
                NetworkTrackedSubjectActivityEvent(
                    id=event.id,
                    firewall_id=event.firewall_id,
                    device_id=event.device_id,
                    event_type=event.event_type,
                    severity=event.severity,
                    protocol=event.protocol,
                    src_ip=event.src_ip,
                    src_device_label=src_label,
                    dst_ip=event.dst_ip,
                    dst_device_label=dst_label,
                    domain=parsed.get("domain") if isinstance(parsed.get("domain"), str) else None,
                    url=parsed.get("url") if isinstance(parsed.get("url"), str) else None,
                    bytes_in=bytes_in,
                    bytes_out=bytes_out,
                    matched_on=matched_on,
                    matched_value=candidate_value,
                    detection_tags=detection_tags,
                    observed_at=event.observed_at,
                )
            )

    for event in events:
        parsed = _extract_firewall_event_parsed(event)
        detection_tags = event_detection_tags(
            event.event_type,
            event.message,
            event.protocol,
            parsed,
            watchlist_entries=watchlist_entries,
        )
        if not detection_tags:
            continue

        linked_device = resolve_device(event.device_id)
        src_device = resolve_ip_device(event.src_ip)
        dst_device = resolve_ip_device(event.dst_ip)
        internal_device = linked_device or src_device or dst_device

        if internal_device is not None:
            ensure_candidate(
                candidate_type="device",
                candidate_value=internal_device.ip_address,
                device=internal_device,
                event=event,
                parsed=parsed,
                detection_tags=detection_tags,
            )

        domain = parsed.get("domain")
        if isinstance(domain, str) and domain.strip():
            ensure_candidate(
                candidate_type="domain",
                candidate_value=domain.strip().lower(),
                device=None,
                event=event,
                parsed=parsed,
                detection_tags=detection_tags,
            )

        raw_url = parsed.get("url")
        if isinstance(raw_url, str) and raw_url.strip():
            ensure_candidate(
                candidate_type="url",
                candidate_value=raw_url.strip(),
                device=None,
                event=event,
                parsed=parsed,
                detection_tags=detection_tags,
            )

        peer_ip: str | None = None
        if internal_device is not None:
            if event.src_ip == internal_device.ip_address:
                peer_ip = event.dst_ip
            elif event.dst_ip == internal_device.ip_address:
                peer_ip = event.src_ip
        peer_ip = peer_ip or event.dst_ip or event.src_ip
        if peer_ip and _find_internal_device_by_ip(db, peer_ip) is None:
            try:
                ipaddress.ip_address(peer_ip)
            except ValueError:
                peer_ip = None
        if peer_ip:
            ensure_candidate(
                candidate_type="ip",
                candidate_value=peer_ip,
                device=None,
                event=event,
                parsed=parsed,
                detection_tags=detection_tags,
            )

    items: list[NetworkTrackedSubjectResponse] = []
    for item in inferred.values():
        if entity_type and item["entity_type"] != entity_type:
            continue
        if search:
            needle = search.strip().lower()
            haystack = " ".join(
                [
                    str(item["value"]),
                    str(item["resolved_label"]),
                    str(item["notes"]),
                ]
            ).lower()
            if needle not in haystack:
                continue
        items.append(
            NetworkTrackedSubjectResponse(
                id=item["id"],
                entity_type=item["entity_type"],
                normalized_value=item["normalized_value"],
                value=item["value"],
                label=item["label"],
                resolved_label=item["resolved_label"],
                notes=item["notes"],
                is_active=item["is_active"],
                device_id=item["device_id"],
                device_label=item["device_label"],
                created_by_user_id=item["created_by_user_id"],
                created_by_username=item["created_by_username"],
                created_at=item["created_at"],
                updated_at=item["updated_at"],
                activity_summary=NetworkTrackedSubjectActivitySummary(
                    window_hours=window_hours,
                    total_events=item["total_events"],
                    allowed_events=item["allowed_events"],
                    blocked_events=item["blocked_events"],
                    suspicious_events=item["suspicious_events"],
                    vpn_suspected_events=item["vpn_suspected_events"],
                    proxy_suspected_events=item["proxy_suspected_events"],
                    tor_suspected_events=item["tor_suspected_events"],
                    encrypted_dns_events=item["encrypted_dns_events"],
                    bytes_in=item["bytes_in"],
                    bytes_out=item["bytes_out"],
                    last_observed_at=item["last_observed_at"],
                    top_detection_tags=[tag for tag, _ in item["detection_counter"].most_common(4)],
                    recent_events=item["events"],
                ),
                scan_history=item["scan_history"],
            )
        )

    items.sort(
        key=lambda subject: (
            subject.activity_summary.suspicious_events if subject.activity_summary else 0,
            1 if subject.device_id is not None else 0,
            subject.updated_at,
        ),
        reverse=True,
    )
    return items


def _build_inferred_assigned_arp_subjects(
    db: Session,
    *,
    active_subjects: dict[tuple[str, str], NetworkTrackedSubject],
    window_hours: int,
    entity_type: str | None = None,
    search: str | None = None,
) -> list[NetworkTrackedSubjectResponse]:
    if entity_type and entity_type != "device":
        return []
    devices = db.scalars(
        select(NetworkDevice)
        .where(
            NetworkDevice.assigned_user_id.is_not(None),
            NetworkDevice.status == "online",
        )
        .order_by(NetworkDevice.last_seen_at.desc(), NetworkDevice.id.desc())
    ).all()

    items: list[NetworkTrackedSubjectResponse] = []
    for device in devices:
        metadata_sources = metadata_sources_to_dict(device.metadata_sources) or {}
        if metadata_sources.get("discovery") != "arp":
            continue
        key = _tracked_subject_key("device", str(device.id))
        if key in active_subjects:
            continue
        resolved_label = _resolve_device_label(device)[0]
        notes = (
            f"Device rilevato via ARP e associato a {resolved_label}"
            if device.assigned_user_id is not None
            else "Device rilevato via ARP"
        )
        if search:
            needle = search.strip().lower()
            haystack = " ".join(
                filter(
                    None,
                    [
                        device.ip_address,
                        device.hostname,
                        device.display_name,
                        resolved_label,
                        device.assigned_user.full_name if device.assigned_user else None,
                        device.assigned_user.username if device.assigned_user else None,
                        notes,
                    ],
                )
            ).lower()
            if needle not in haystack:
                continue
        items.append(
            NetworkTrackedSubjectResponse(
                id=_synthetic_subject_id("device", str(device.id)),
                entity_type="device",
                normalized_value=str(device.id),
                value=device.ip_address,
                label=None,
                resolved_label=resolved_label,
                notes=notes,
                is_active=True,
                device_id=device.id,
                device_label=resolved_label,
                created_by_user_id=None,
                created_by_username=None,
                created_at=device.first_seen_at,
                updated_at=device.last_seen_at,
                activity_summary=_build_tracked_subject_activity_summary(
                    db,
                    NetworkTrackedSubject(
                        id=0,
                        entity_type="device",
                        normalized_value=str(device.id),
                        value=device.ip_address,
                        label=None,
                        notes=notes,
                        is_active=True,
                        device_id=device.id,
                        created_by_user_id=None,
                        created_at=device.first_seen_at,
                        updated_at=device.last_seen_at,
                    ),
                    window_hours=window_hours,
                ),
                scan_history=[
                    {
                        "scan_id": item.scan_id,
                        "observed_at": item.observed_at,
                        "status": item.status,
                        "hostname": item.hostname,
                        "ip_address": item.ip_address,
                        "mac_address": item.mac_address,
                        "open_ports": item.open_ports,
                    }
                    for item in get_device_scan_history(db, device.id, limit=8)
                ],
            )
        )
    return items


# fmt: on
