import ipaddress
import json
import socket
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.datetime_compat import UTC
from app.modules.network.models import (
    NetworkDevice,
    NetworkFirewallEvent,
)
from app.modules.network.router.helpers.devices import _resolve_device_label
from app.modules.network.router.helpers.endpoints import _extract_event_traffic
from app.modules.network.router.helpers.tracking import (
    _extract_firewall_event_parsed,
    _find_tracked_subject,
    _get_active_tracked_subject_map,
)
from app.modules.network.schemas import (
    NetworkDeviceTrafficEventSummary,
    NetworkDeviceTrafficPeerSummary,
    NetworkDeviceTrafficSummary,
    NetworkStatisticsCountItem,
    NetworkStatisticsSummary,
    NetworkStatisticsTimelinePoint,
    NetworkStatisticsTrafficItem,
)
from app.modules.network.services import (
    list_network_alerts,
    metadata_sources_to_dict,
)
from app.modules.network.sophos import (
    list_network_firewalls,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

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
    window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)  # noqa: UP017 - preserve legacy AST
    tracked_subjects = _get_active_tracked_subject_map(db)
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
        parsed = _extract_firewall_event_parsed(event)
        tracked_peer_ip_subject = _find_tracked_subject(tracked_subjects, entity_type="ip", value=peer_ip)
        peer_label_hint = _extract_peer_hint(event, peer_ip=peer_ip)
        tracked_domain_subject = _find_tracked_subject(tracked_subjects, entity_type="domain", value=peer_label_hint)
        tracked_url_subject = _find_tracked_subject(
            tracked_subjects,
            entity_type="url",
            value=parsed.get("url") if isinstance(parsed.get("url"), str) else None,
        )
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
            if peer_label_hint:
                peer_entry["labels"][peer_label_hint] += 1

        if len(recent_events) < 8:
            recent_events.append(
                NetworkDeviceTrafficEventSummary(
                    id=event.id,
                    event_type=event.event_type,
                    severity=event.severity,
                    protocol=event.protocol,
                    src_ip=event.src_ip,
                    dst_ip=event.dst_ip,
                    peer_ip=peer_ip,
                    peer_label=peer_label_hint,
                    bytes_in=bytes_in,
                    bytes_out=bytes_out,
                    observed_at=event.observed_at,
                    tracked_peer_ip_subject_id=tracked_peer_ip_subject.id if tracked_peer_ip_subject else None,
                    tracked_peer_label_subject_id=tracked_domain_subject.id if tracked_domain_subject else None,
                    tracked_url_subject_id=tracked_url_subject.id if tracked_url_subject else None,
                )
            )

    top_peers = [
        NetworkDeviceTrafficPeerSummary(
            ip_address=ip_address,
            label=max(values["labels"].items(), key=lambda item: item[1])[0] if values["labels"] else _resolve_peer_label(ip_address),
            events_count=values["events_count"],
            bytes_in=values["bytes_in"],
            bytes_out=values["bytes_out"],
            tracked_subject_id=(
                tracked_subject.id
                if (tracked_subject := _find_tracked_subject(tracked_subjects, entity_type="ip", value=ip_address))
                else None
            ),
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
                device_id=payload.get("device_id"),
                events_count=payload["events_count"],
                bytes_in=payload["bytes_in"],
                bytes_out=payload["bytes_out"],
                bytes_total=payload["bytes_total"],
                tracked_subject_id=payload.get("tracked_subject_id"),
            )
        )
    return items


def _build_network_statistics_summary(db: Session, *, window_hours: int = 24) -> NetworkStatisticsSummary:
    now = datetime.now(UTC)
    window_start = now - timedelta(hours=window_hours)
    tracked_subjects = _get_active_tracked_subject_map(db)

    devices = db.scalars(select(NetworkDevice)).all()
    device_by_ip = {device.ip_address: device for device in devices}
    firewalls = list_network_firewalls(db)
    alerts = list_network_alerts(db, status="open")
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

    total_events = 0
    event_rows = db.execute(
        select(
            NetworkFirewallEvent.event_type,
            NetworkFirewallEvent.severity,
            NetworkFirewallEvent.protocol,
            NetworkFirewallEvent.raw_payload,
            NetworkFirewallEvent.src_ip,
            NetworkFirewallEvent.dst_ip,
            NetworkFirewallEvent.device_id,
            NetworkFirewallEvent.observed_at,
        )
        .where(NetworkFirewallEvent.observed_at >= window_start)
        .execution_options(stream_results=True, yield_per=1000)
    )

    for row in event_rows.mappings():
        total_events += 1
        event_type = row["event_type"]
        event_severity = row["severity"] or "info"
        event_protocol = row["protocol"]
        src_ip = row["src_ip"]
        dst_ip = row["dst_ip"]
        observed_at = row["observed_at"]

        severity_counter[event_severity] += 1
        protocol_counter[(event_protocol or "n/d").upper()] += 1
        event_type_counter[event_type] += 1

        raw_payload = metadata_sources_to_dict(row["raw_payload"]) or {}
        parsed = raw_payload.get("parsed") if isinstance(raw_payload, dict) else None
        parsed = parsed if isinstance(parsed, dict) else {}

        bytes_in = 0
        bytes_out = 0
        source_device = device_by_ip.get(src_ip or "")
        source_label = None
        if source_device and source_device.lifecycle_state == "active":
            try:
                bytes_sent = max(int(str(parsed.get("bytes_sent", 0)).strip()), 0)
            except (TypeError, ValueError):
                bytes_sent = 0
            try:
                bytes_received = max(int(str(parsed.get("bytes_received", 0)).strip()), 0)
            except (TypeError, ValueError):
                bytes_received = 0
            if src_ip == source_device.ip_address:
                bytes_in, bytes_out = bytes_received, bytes_sent
            elif dst_ip == source_device.ip_address:
                bytes_in, bytes_out = bytes_sent, bytes_received
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

        lowered_type = event_type.lower()
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
            tracked_domain_subject = _find_tracked_subject(tracked_subjects, entity_type="domain", value=normalized_domain)
            domains_entry["tracked_subject_id"] = tracked_domain_subject.id if tracked_domain_subject else None

        peer_ip = dst_ip or src_ip
        if peer_ip:
            try:
                peer_parsed = ipaddress.ip_address(peer_ip)
            except ValueError:
                peer_parsed = None
            if peer_parsed and not (peer_parsed.is_private or peer_parsed.is_loopback or peer_parsed.is_link_local or peer_parsed.is_multicast):
                external_peers.add(peer_ip)
            peer_label = None
            parsed_domain = parsed.get("domain")
            if isinstance(parsed_domain, str) and parsed_domain.strip():
                peer_label = parsed_domain.strip()
            else:
                parsed_url = parsed.get("url")
                if isinstance(parsed_url, str) and parsed_url.strip():
                    peer_label = urlparse(parsed_url.strip()).hostname or peer_ip
            peer_label = peer_label or peer_ip
            destinations_entry = destinations_map[peer_ip]
            destinations_entry["label"] = peer_label
            destinations_entry["ip_address"] = peer_ip
            destinations_entry["events_count"] += 1
            destinations_entry["bytes_in"] += bytes_in
            destinations_entry["bytes_out"] += bytes_out
            destinations_entry["bytes_total"] += bytes_in + bytes_out
            tracked_destination_subject = _find_tracked_subject(tracked_subjects, entity_type="ip", value=peer_ip)
            destinations_entry["tracked_subject_id"] = tracked_destination_subject.id if tracked_destination_subject else None

        if source_label:
            source_entry = sources_map[source_device.ip_address]
            source_entry["label"] = source_label
            source_entry["ip_address"] = source_device.ip_address
            source_entry["device_id"] = source_device.id
            source_entry["events_count"] += 1
            source_entry["bytes_in"] += bytes_in
            source_entry["bytes_out"] += bytes_out
            source_entry["bytes_total"] += bytes_in + bytes_out
            tracked_device_subject = _find_tracked_subject(tracked_subjects, entity_type="device", value=str(source_device.id))
            source_entry["tracked_subject_id"] = tracked_device_subject.id if tracked_device_subject else None

        bucket = observed_at.astimezone(timezone.utc).strftime("%d/%m %H:00")  # noqa: UP017 - preserve legacy AST
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
        total_events=total_events,
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


# fmt: on
