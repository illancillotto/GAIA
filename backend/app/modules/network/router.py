from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta, timezone
from functools import lru_cache
import ipaddress
import socket
from typing import Annotated, Any
import urllib.error
import urllib.request
import json
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.network.models import DevicePosition, FloorPlan, NetworkDevice, NetworkFirewallEvent, NetworkScan, NetworkScanDevice
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
    NetworkAssignedUserSummary,
    NetworkDeviceTrafficEventSummary,
    NetworkDeviceTrafficPeerSummary,
    NetworkDeviceTrafficSummary,
    NetworkDeviceResponse,
    NetworkDeviceUpdateRequest,
    NetworkFirewallEventResponse,
    NetworkFirewallMetricResponse,
    NetworkFirewallResponse,
    NetworkStatisticsCountItem,
    NetworkStatisticsSummary,
    NetworkStatisticsTimelinePoint,
    NetworkStatisticsTrafficItem,
    NetworkScanDetailResponse,
    NetworkScanDeviceResponse,
    NetworkScanDiffEntry,
    NetworkScanDiffResponse,
    NetworkScanResponse,
    NetworkScanTriggerResponse,
    SophosSyslogIngestRequest,
)
from app.modules.network.sophos import ingest_sophos_syslog, list_network_firewall_events, list_network_firewalls
from app.modules.network.sophos_snmp import list_network_firewall_metrics, poll_sophos_firewall_metrics
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
    sync_network_device_alert_state,
    update_network_alert,
    upsert_device_position,
    metadata_sources_to_dict,
)

router = APIRouter(prefix="/network", tags=["network"])


def _resolve_device_label(device: NetworkDevice) -> tuple[str, str]:
    if device.assigned_user:
        if device.assigned_user.full_name:
            return device.assigned_user.full_name, "application_user"
        return device.assigned_user.username, "application_user"
    if device.display_name:
        return device.display_name, "device"
    if device.hostname:
        return device.hostname, "hostname"
    return device.ip_address, "ip_address"


def _serialize_device(
    device: NetworkDevice,
    *,
    positions: list[DevicePosition] | None = None,
    scan_history: list[NetworkScanDevice] | None = None,
    traffic_summary: NetworkDeviceTrafficSummary | None = None,
) -> NetworkDeviceResponse:
    resolved_label, label_source = _resolve_device_label(device)
    payload = {
        "id": device.id,
        "last_scan_id": device.last_scan_id,
        "assigned_user_id": device.assigned_user_id,
        "ip_address": device.ip_address,
        "mac_address": device.mac_address,
        "hostname": device.hostname,
        "hostname_source": device.hostname_source,
        "display_name": device.display_name,
        "resolved_label": resolved_label,
        "label_source": label_source,
        "lifecycle_state": device.lifecycle_state,
        "asset_label": device.asset_label,
        "vendor": device.vendor,
        "model_name": device.model_name,
        "device_type": device.device_type,
        "operating_system": device.operating_system,
        "dns_name": device.dns_name,
        "location_hint": device.location_hint,
        "notes": device.notes,
        "is_known_device": device.is_known_device,
        "metadata_sources": metadata_sources_to_dict(device.metadata_sources),
        "status": device.status,
        "is_monitored": device.is_monitored,
        "open_ports": device.open_ports,
        "first_seen_at": device.first_seen_at,
        "last_seen_at": device.last_seen_at,
        "created_at": device.created_at,
        "updated_at": device.updated_at,
        "assigned_user": _serialize_assigned_user(device.assigned_user) if device.assigned_user else None,
        "retired_at": device.retired_at,
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
        "traffic_summary": traffic_summary,
    }
    return NetworkDeviceResponse.model_validate(payload)


def _serialize_assigned_user(user: ApplicationUser) -> NetworkAssignedUserSummary:
    return NetworkAssignedUserSummary(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        full_name=user.full_name,
        office_location=user.office_location,
        phone_extension=user.phone_extension,
        is_placeholder_profile=((not user.is_active) and user.email.endswith("@users.local")),
    )


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


def _extract_peer_hint(event: NetworkFirewallEvent, *, peer_ip: str | None) -> str | None:
    raw_payload = metadata_sources_to_dict(event.raw_payload) or {}
    parsed = raw_payload.get("parsed") if isinstance(raw_payload, dict) else None
    parsed = parsed if isinstance(parsed, dict) else {}

    domain = parsed.get("domain")
    if isinstance(domain, str) and domain.strip():
        return domain.strip()

    url = parsed.get("url")
    if isinstance(url, str) and url.strip():
        hostname = urlparse(url.strip()).hostname
        if hostname:
            return hostname

    if peer_ip:
        return _resolve_peer_label(peer_ip)
    return None


@lru_cache(maxsize=512)
def _resolve_peer_label(ip_address: str | None) -> str | None:
    if not ip_address:
        return None

    try:
        parsed_ip = ipaddress.ip_address(ip_address)
    except ValueError:
        return None

    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        hostname = hostname.strip().rstrip(".")
        if hostname:
            return hostname
    except OSError:
        pass

    if parsed_ip.is_private or parsed_ip.is_loopback or parsed_ip.is_link_local or parsed_ip.is_multicast:
        return None

    try:
        with urllib.request.urlopen(f"https://rdap.org/ip/{ip_address}", timeout=4) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None

    entities = payload.get("entities")
    if isinstance(entities, list):
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            vcard = entity.get("vcardArray")
            if not (isinstance(vcard, list) and len(vcard) == 2 and isinstance(vcard[1], list)):
                continue
            for item in vcard[1]:
                if (
                    isinstance(item, list)
                    and len(item) >= 4
                    and item[0] == "fn"
                    and isinstance(item[3], str)
                    and item[3].strip()
                ):
                    return item[3].strip()

    for key in ("name", "handle"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _build_device_traffic_summary(db: Session, device: NetworkDevice, *, window_hours: int = 24) -> NetworkDeviceTrafficSummary:
    window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    events = db.scalars(
        select(NetworkFirewallEvent)
        .where(
            NetworkFirewallEvent.observed_at >= window_start,
            or_(
                NetworkFirewallEvent.device_id == device.id,
                NetworkFirewallEvent.src_ip == device.ip_address,
                NetworkFirewallEvent.dst_ip == device.ip_address,
            ),
        )
        .order_by(NetworkFirewallEvent.observed_at.desc())
    ).all()

    if not events:
        return NetworkDeviceTrafficSummary(window_hours=window_hours)

    peer_totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"events_count": 0, "bytes_in": 0, "bytes_out": 0, "labels": defaultdict(int)}
    )
    recent_events: list[NetworkDeviceTrafficEventSummary] = []
    total_bytes_in = 0
    total_bytes_out = 0
    allowed_events = 0
    blocked_events = 0

    for event in events:
        bytes_in, bytes_out, peer_ip = _extract_event_traffic(event, device_ip=device.ip_address)
        total_bytes_in += bytes_in
        total_bytes_out += bytes_out

        lowered_type = event.event_type.lower()
        if "allow" in lowered_type:
            allowed_events += 1
        if "deny" in lowered_type or "block" in lowered_type or "drop" in lowered_type:
            blocked_events += 1

        if peer_ip:
            peer_entry = peer_totals[peer_ip]
            peer_entry["events_count"] += 1
            peer_entry["bytes_in"] += bytes_in
            peer_entry["bytes_out"] += bytes_out
            peer_label_hint = _extract_peer_hint(event, peer_ip=peer_ip)
            if peer_label_hint:
                peer_entry["labels"][peer_label_hint] += 1

        if len(recent_events) < 8:
            peer_label = _extract_peer_hint(event, peer_ip=peer_ip)
            recent_events.append(
                NetworkDeviceTrafficEventSummary(
                    id=event.id,
                    event_type=event.event_type,
                    severity=event.severity,
                    protocol=event.protocol,
                    src_ip=event.src_ip,
                    dst_ip=event.dst_ip,
                    peer_ip=peer_ip,
                    peer_label=peer_label,
                    bytes_in=bytes_in,
                    bytes_out=bytes_out,
                    observed_at=event.observed_at,
                )
            )

    top_peers = [
        NetworkDeviceTrafficPeerSummary(
            ip_address=ip_address,
            label=max(values["labels"].items(), key=lambda item: item[1])[0] if values["labels"] else _resolve_peer_label(ip_address),
            events_count=values["events_count"],
            bytes_in=values["bytes_in"],
            bytes_out=values["bytes_out"],
        )
        for ip_address, values in sorted(
            peer_totals.items(),
            key=lambda item: (item[1]["bytes_in"] + item[1]["bytes_out"], item[1]["events_count"]),
            reverse=True,
        )[:5]
    ]

    return NetworkDeviceTrafficSummary(
        window_hours=window_hours,
        total_events=len(events),
        allowed_events=allowed_events,
        blocked_events=blocked_events,
        bytes_in=total_bytes_in,
        bytes_out=total_bytes_out,
        last_observed_at=events[0].observed_at,
        top_peers=top_peers,
        recent_events=recent_events,
    )


def _counter_to_items(counter: Counter[str], *, labels: dict[str, str] | None = None, limit: int = 6) -> list[NetworkStatisticsCountItem]:
    items: list[NetworkStatisticsCountItem] = []
    for key, count in counter.most_common(limit):
        if not key:
            continue
        items.append(NetworkStatisticsCountItem(key=key, label=(labels or {}).get(key, key), count=count))
    return items


def _traffic_map_to_items(
    values: dict[str, dict[str, Any]],
    *,
    limit: int = 8,
) -> list[NetworkStatisticsTrafficItem]:
    items: list[NetworkStatisticsTrafficItem] = []
    ranked = sorted(
        values.items(),
        key=lambda item: (item[1]["bytes_total"], item[1]["events_count"]),
        reverse=True,
    )[:limit]
    for key, payload in ranked:
        items.append(
            NetworkStatisticsTrafficItem(
                label=payload.get("label") or key,
                ip_address=payload.get("ip_address"),
                events_count=payload["events_count"],
                bytes_in=payload["bytes_in"],
                bytes_out=payload["bytes_out"],
                bytes_total=payload["bytes_total"],
            )
        )
    return items


def _build_network_statistics_summary(db: Session, *, window_hours: int = 24) -> NetworkStatisticsSummary:
    now = datetime.now(UTC)
    window_start = now - timedelta(hours=window_hours)

    devices = db.scalars(select(NetworkDevice)).all()
    device_by_ip = {device.ip_address: device for device in devices}
    firewalls = list_network_firewalls(db)
    alerts = list_network_alerts(db, status="open")
    events = db.scalars(
        select(NetworkFirewallEvent)
        .where(NetworkFirewallEvent.observed_at >= window_start)
        .order_by(NetworkFirewallEvent.observed_at.desc())
    ).all()

    total_devices = len(devices)
    active_devices = sum(1 for device in devices if device.lifecycle_state == "active")
    retired_devices = sum(1 for device in devices if device.lifecycle_state == "retired")
    online_devices = sum(1 for device in devices if device.lifecycle_state == "active" and device.status == "online")
    offline_devices = sum(1 for device in devices if device.lifecycle_state == "active" and device.status == "offline")
    known_devices = sum(1 for device in devices if device.lifecycle_state == "active" and device.is_known_device)
    unknown_devices = sum(1 for device in devices if device.lifecycle_state == "active" and not device.is_known_device)
    monitored_devices = sum(1 for device in devices if device.lifecycle_state == "active" and device.is_monitored)
    assigned_devices = sum(1 for device in devices if device.lifecycle_state == "active" and device.assigned_user_id is not None)
    unassigned_devices = sum(1 for device in devices if device.lifecycle_state == "active" and device.assigned_user_id is None)
    placeholder_profiles = sum(
        1
        for device in devices
        if device.lifecycle_state == "active"
        and device.assigned_user is not None
        and (not device.assigned_user.is_active)
        and device.assigned_user.email.endswith("@users.local")
    )

    device_type_counter: Counter[str] = Counter()
    vendor_counter: Counter[str] = Counter()
    office_counter: Counter[str] = Counter()
    assignee_counter: Counter[str] = Counter()
    for device in devices:
        if device.lifecycle_state != "active":
            continue
        if device.device_type:
            device_type_counter[device.device_type] += 1
        if device.vendor:
            vendor_counter[device.vendor] += 1
        office_value = device.assigned_user.office_location if device.assigned_user and device.assigned_user.office_location else device.location_hint
        if office_value:
            office_counter[office_value] += 1
        if device.assigned_user:
            assignee_counter[device.assigned_user.full_name or device.assigned_user.username] += 1

    severity_counter: Counter[str] = Counter()
    protocol_counter: Counter[str] = Counter()
    event_type_counter: Counter[str] = Counter()
    firewall_rule_counter: Counter[str] = Counter()
    domains_map: dict[str, dict[str, Any]] = defaultdict(lambda: {"label": None, "ip_address": None, "events_count": 0, "bytes_in": 0, "bytes_out": 0, "bytes_total": 0})
    destinations_map: dict[str, dict[str, Any]] = defaultdict(lambda: {"label": None, "ip_address": None, "events_count": 0, "bytes_in": 0, "bytes_out": 0, "bytes_total": 0})
    sources_map: dict[str, dict[str, Any]] = defaultdict(lambda: {"label": None, "ip_address": None, "events_count": 0, "bytes_in": 0, "bytes_out": 0, "bytes_total": 0})
    timeline_map: dict[str, dict[str, int]] = defaultdict(lambda: {"events_count": 0, "bytes_in": 0, "bytes_out": 0})
    seen_domains: set[str] = set()
    external_peers: set[str] = set()
    source_devices_with_traffic: set[int] = set()
    total_bytes_in = 0
    total_bytes_out = 0
    allowed_events = 0
    blocked_events = 0

    for event in events:
        severity_counter[event.severity or "info"] += 1
        protocol_counter[(event.protocol or "n/d").upper()] += 1
        event_type_counter[event.event_type] += 1

        raw_payload = metadata_sources_to_dict(event.raw_payload) or {}
        parsed = raw_payload.get("parsed") if isinstance(raw_payload, dict) else None
        parsed = parsed if isinstance(parsed, dict) else {}

        bytes_in = 0
        bytes_out = 0
        source_device = device_by_ip.get(event.src_ip or "")
        source_label = None
        if source_device and source_device.lifecycle_state == "active":
            bytes_in, bytes_out, _ = _extract_event_traffic(event, device_ip=source_device.ip_address)
            source_label = _resolve_device_label(source_device)[0]
            source_devices_with_traffic.add(source_device.id)
        else:
            try:
                bytes_out = max(int(str(parsed.get("bytes_sent", 0)).strip()), 0)
            except (TypeError, ValueError):
                bytes_out = 0
            try:
                bytes_in = max(int(str(parsed.get("bytes_received", 0)).strip()), 0)
            except (TypeError, ValueError):
                bytes_in = 0

        total_bytes_in += bytes_in
        total_bytes_out += bytes_out

        lowered_type = event.event_type.lower()
        if "allow" in lowered_type:
            allowed_events += 1
        if "deny" in lowered_type or "block" in lowered_type or "drop" in lowered_type:
            blocked_events += 1

        firewall_rule_name = parsed.get("fw_rule_name")
        if isinstance(firewall_rule_name, str) and firewall_rule_name.strip():
            firewall_rule_counter[firewall_rule_name.strip()] += 1

        domain_value = parsed.get("domain")
        if not isinstance(domain_value, str) or not domain_value.strip():
            raw_url = parsed.get("url")
            if isinstance(raw_url, str) and raw_url.strip():
                domain_value = urlparse(raw_url.strip()).hostname
        if isinstance(domain_value, str) and domain_value.strip():
            normalized_domain = domain_value.strip().lower()
            seen_domains.add(normalized_domain)
            domains_entry = domains_map[normalized_domain]
            domains_entry["label"] = normalized_domain
            domains_entry["events_count"] += 1
            domains_entry["bytes_in"] += bytes_in
            domains_entry["bytes_out"] += bytes_out
            domains_entry["bytes_total"] += bytes_in + bytes_out

        peer_ip = event.dst_ip or event.src_ip
        if peer_ip:
            try:
                peer_parsed = ipaddress.ip_address(peer_ip)
            except ValueError:
                peer_parsed = None
            if peer_parsed and not (peer_parsed.is_private or peer_parsed.is_loopback or peer_parsed.is_link_local or peer_parsed.is_multicast):
                external_peers.add(peer_ip)
            peer_label = _extract_peer_hint(event, peer_ip=peer_ip) or peer_ip
            destinations_entry = destinations_map[peer_ip]
            destinations_entry["label"] = peer_label
            destinations_entry["ip_address"] = peer_ip
            destinations_entry["events_count"] += 1
            destinations_entry["bytes_in"] += bytes_in
            destinations_entry["bytes_out"] += bytes_out
            destinations_entry["bytes_total"] += bytes_in + bytes_out

        if source_label:
            source_entry = sources_map[source_device.ip_address]
            source_entry["label"] = source_label
            source_entry["ip_address"] = source_device.ip_address
            source_entry["events_count"] += 1
            source_entry["bytes_in"] += bytes_in
            source_entry["bytes_out"] += bytes_out
            source_entry["bytes_total"] += bytes_in + bytes_out

        bucket = event.observed_at.astimezone(timezone.utc).strftime("%d/%m %H:00")
        timeline_map[bucket]["events_count"] += 1
        timeline_map[bucket]["bytes_in"] += bytes_in
        timeline_map[bucket]["bytes_out"] += bytes_out

    return NetworkStatisticsSummary(
        window_hours=window_hours,
        generated_at=now,
        total_devices=total_devices,
        active_devices=active_devices,
        retired_devices=retired_devices,
        online_devices=online_devices,
        offline_devices=offline_devices,
        known_devices=known_devices,
        unknown_devices=unknown_devices,
        monitored_devices=monitored_devices,
        assigned_devices=assigned_devices,
        unassigned_devices=unassigned_devices,
        placeholder_profiles=placeholder_profiles,
        devices_with_traffic=len(source_devices_with_traffic),
        firewall_count=len(firewalls),
        open_alerts=len(alerts),
        total_events=len(events),
        allowed_events=allowed_events,
        blocked_events=blocked_events,
        bytes_in=total_bytes_in,
        bytes_out=total_bytes_out,
        unique_external_peers=len(external_peers),
        unique_domains=len(seen_domains),
        top_device_types=_counter_to_items(device_type_counter, limit=6),
        top_vendors=_counter_to_items(vendor_counter, limit=6),
        top_offices=_counter_to_items(office_counter, limit=6),
        top_assignees=_counter_to_items(assignee_counter, limit=8),
        severity_breakdown=_counter_to_items(severity_counter, labels={"info": "Info", "warning": "Warning", "danger": "Danger", "critical": "Critical", "notice": "Notice"}, limit=6),
        protocol_breakdown=_counter_to_items(protocol_counter, limit=6),
        top_event_types=_counter_to_items(event_type_counter, limit=8),
        top_firewall_rules=_counter_to_items(firewall_rule_counter, limit=8),
        top_domains=_traffic_map_to_items(domains_map, limit=8),
        top_destinations=_traffic_map_to_items(destinations_map, limit=8),
        top_source_devices=_traffic_map_to_items(sources_map, limit=8),
        hourly_timeline=[
            NetworkStatisticsTimelinePoint(
                bucket=bucket,
                events_count=values["events_count"],
                bytes_in=values["bytes_in"],
                bytes_out=values["bytes_out"],
            )
            for bucket, values in sorted(timeline_map.items(), key=lambda item: item[0])
        ],
    )


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


def _serialize_firewall(firewall: object) -> NetworkFirewallResponse:
    payload = {
        "id": firewall.id,
        "vendor": firewall.vendor,
        "name": firewall.name,
        "model_name": firewall.model_name,
        "serial_number": firewall.serial_number,
        "management_ip": firewall.management_ip,
        "status": firewall.status,
        "metadata_sources": metadata_sources_to_dict(firewall.metadata_sources),
        "last_seen_at": firewall.last_seen_at,
        "created_at": firewall.created_at,
        "updated_at": firewall.updated_at,
    }
    return NetworkFirewallResponse.model_validate(payload)


def _serialize_firewall_event(event: object, db: Session) -> NetworkFirewallEventResponse:
    src_label, dst_label = _resolve_firewall_event_endpoint_labels(
        db,
        device_id=event.device_id,
        src_ip=event.src_ip,
        dst_ip=event.dst_ip,
    )
    payload = {
        "id": event.id,
        "firewall_id": event.firewall_id,
        "device_id": event.device_id,
        "source": event.source,
        "event_type": event.event_type,
        "severity": event.severity,
        "log_id": event.log_id,
        "message": event.message,
        "src_ip": event.src_ip,
        "src_device_label": src_label,
        "dst_ip": event.dst_ip,
        "dst_device_label": dst_label,
        "protocol": event.protocol,
        "raw_payload": metadata_sources_to_dict(event.raw_payload),
        "observed_at": event.observed_at,
    }
    return NetworkFirewallEventResponse.model_validate(payload)


def _serialize_firewall_metric(metric: object) -> NetworkFirewallMetricResponse:
    payload = {
        "id": metric.id,
        "firewall_id": metric.firewall_id,
        "metric_key": metric.metric_key,
        "metric_value": metric.metric_value,
        "metric_text": metric.metric_text,
        "unit": metric.unit,
        "severity": metric.severity,
        "raw_payload": metadata_sources_to_dict(metric.raw_payload),
        "observed_at": metric.observed_at,
    }
    return NetworkFirewallMetricResponse.model_validate(payload)


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


@router.get("/statistics", response_model=NetworkStatisticsSummary)
def get_statistics(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    window_hours: int = Query(default=24, ge=1, le=24 * 30),
) -> NetworkStatisticsSummary:
    _require_network_module(current_user)
    return _build_network_statistics_summary(db, window_hours=window_hours)


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


@router.get("/firewalls", response_model=list[NetworkFirewallResponse])
def get_firewalls(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NetworkFirewallResponse]:
    _require_network_module(current_user)
    return [_serialize_firewall(item) for item in list_network_firewalls(db)]


@router.get("/firewalls/{firewall_id}/events", response_model=list[NetworkFirewallEventResponse])
def get_firewall_events(
    firewall_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    severity: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[NetworkFirewallEventResponse]:
    _require_network_module(current_user)
    return [_serialize_firewall_event(item, db) for item in list_network_firewall_events(db, firewall_id=firewall_id, severity=severity, limit=limit)]


@router.get("/firewalls/{firewall_id}/metrics", response_model=list[NetworkFirewallMetricResponse])
def get_firewall_metrics(
    firewall_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    metric_key: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[NetworkFirewallMetricResponse]:
    _require_network_module(current_user)
    return [_serialize_firewall_metric(item) for item in list_network_firewall_metrics(db, firewall_id=firewall_id, metric_key=metric_key, limit=limit)]


@router.post("/firewalls/{firewall_id}/metrics/poll", response_model=list[NetworkFirewallMetricResponse], status_code=status.HTTP_201_CREATED)
def poll_firewall_metrics(
    firewall_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NetworkFirewallMetricResponse]:
    _require_network_module(current_user)
    metrics = poll_sophos_firewall_metrics(db)
    filtered = [item for item in metrics if item.firewall_id == firewall_id]
    return [_serialize_firewall_metric(item) for item in filtered]


@router.post("/firewalls/sophos/syslog", response_model=NetworkFirewallEventResponse, status_code=status.HTTP_201_CREATED)
def post_sophos_syslog(
    payload: SophosSyslogIngestRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkFirewallEventResponse:
    _require_network_module(current_user)
    event = ingest_sophos_syslog(
        db,
        message=payload.message,
        firewall_id=payload.firewall_id,
        firewall_name=payload.firewall_name,
        management_ip=payload.management_ip,
        observed_at=payload.observed_at,
    )
    return _serialize_firewall_event(event, db)


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
