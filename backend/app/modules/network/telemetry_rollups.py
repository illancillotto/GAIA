from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import ipaddress
import logging
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.datetime_compat import UTC
from app.modules.network.models import NetworkDevice, NetworkFirewallEvent, NetworkFirewallHourlyRollup, NetworkTrackedSubject
from app.modules.network.schemas import (
    NetworkStatisticsCountItem,
    NetworkStatisticsSummary,
    NetworkStatisticsTimelinePoint,
    NetworkStatisticsTrafficItem,
)
from app.modules.network.sophos import list_network_firewalls
from app.modules.network.services import list_network_alerts, metadata_sources_to_dict

logger = logging.getLogger(__name__)


def _truncate_hour(value: datetime) -> datetime:
    return _ensure_utc(value).replace(minute=0, second=0, microsecond=0)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _resolve_device_label(device: NetworkDevice) -> str:
    if device.assigned_user:
        return device.assigned_user.full_name or device.assigned_user.username
    if device.display_name:
        return device.display_name
    if device.hostname:
        return device.hostname
    return device.ip_address


def _normalize_tracked_value(entity_type: str, value: str) -> str:
    normalized = value.strip()
    if entity_type == "ip":
        return str(ipaddress.ip_address(normalized))
    if entity_type == "domain":
        parsed_hostname = urlparse(normalized).hostname if "://" in normalized else normalized
        return (parsed_hostname or normalized).strip().rstrip(".").lower()
    if entity_type == "url":
        return normalized
    return normalized


def _tracked_subject_key(entity_type: str, normalized_value: str) -> tuple[str, str]:
    return entity_type, normalized_value


def _get_active_tracked_subject_map(db: Session) -> dict[tuple[str, str], NetworkTrackedSubject]:
    subjects = db.scalars(
        select(NetworkTrackedSubject)
        .where(NetworkTrackedSubject.is_active.is_(True))
        .order_by(NetworkTrackedSubject.id.asc())
    ).all()
    return {_tracked_subject_key(item.entity_type, item.normalized_value): item for item in subjects}


def _find_tracked_subject(
    tracked_subjects: dict[tuple[str, str], NetworkTrackedSubject],
    *,
    entity_type: str,
    value: str | None,
) -> NetworkTrackedSubject | None:
    if not value:
        return None
    try:
        normalized_value = _normalize_tracked_value(entity_type, value)
    except ValueError:
        return None
    return tracked_subjects.get(_tracked_subject_key(entity_type, normalized_value))


def _counter_to_items(counter: Counter[str], *, labels: dict[str, str] | None = None, limit: int = 6) -> list[NetworkStatisticsCountItem]:
    items: list[NetworkStatisticsCountItem] = []
    for key, count in counter.most_common(limit):
        if not key:
            continue
        items.append(NetworkStatisticsCountItem(key=key, label=(labels or {}).get(key, key), count=count))
    return items


def _traffic_map_to_items(values: dict[str, dict[str, Any]], *, limit: int = 8) -> list[NetworkStatisticsTrafficItem]:
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


def _build_rollup_entry_map() -> dict[tuple[datetime, str, str], dict[str, Any]]:
    return {}


def refresh_network_firewall_hourly_rollups_for_range(
    db: Session,
    *,
    start: datetime,
    end: datetime,
) -> int:
    start = _truncate_hour(start)
    end = _truncate_hour(end)
    if end < start:
        raise ValueError("end must be greater than or equal to start")
    tracked_subjects = _get_active_tracked_subject_map(db)
    devices = db.scalars(select(NetworkDevice)).all()
    device_by_ip = {device.ip_address: device for device in devices}

    rows: dict[tuple[datetime, str, str], dict[str, Any]] = _build_rollup_entry_map()

    def upsert_row(
        *,
        bucket_start: datetime,
        category: str,
        dimension_key: str,
        label: str | None = None,
        ip_address: str | None = None,
        device_id: int | None = None,
        tracked_subject_id: int | None = None,
        events_count: int = 0,
        allowed_events: int = 0,
        blocked_events: int = 0,
        bytes_in: int = 0,
        bytes_out: int = 0,
    ) -> None:
        key = (bucket_start, category, dimension_key)
        entry = rows.setdefault(
            key,
            {
                "bucket_start": bucket_start,
                "category": category,
                "dimension_key": dimension_key,
                "label": label,
                "ip_address": ip_address,
                "device_id": device_id,
                "tracked_subject_id": tracked_subject_id,
                "events_count": 0,
                "allowed_events": 0,
                "blocked_events": 0,
                "bytes_in": 0,
                "bytes_out": 0,
            },
        )
        if label and not entry["label"]:
            entry["label"] = label
        if ip_address and not entry["ip_address"]:
            entry["ip_address"] = ip_address
        if device_id and not entry["device_id"]:
            entry["device_id"] = device_id
        if tracked_subject_id and not entry["tracked_subject_id"]:
            entry["tracked_subject_id"] = tracked_subject_id
        entry["events_count"] += events_count
        entry["allowed_events"] += allowed_events
        entry["blocked_events"] += blocked_events
        entry["bytes_in"] += bytes_in
        entry["bytes_out"] += bytes_out

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
        .where(NetworkFirewallEvent.observed_at >= start)
        .execution_options(stream_results=True, yield_per=1000)
    )

    processed = 0
    for row in event_rows.mappings():
        processed += 1
        observed_at = row["observed_at"]
        bucket_start = _truncate_hour(observed_at)
        event_type = row["event_type"]
        severity = row["severity"] or "info"
        protocol = (row["protocol"] or "n/d").upper()
        src_ip = row["src_ip"]
        dst_ip = row["dst_ip"]
        source_device = device_by_ip.get(src_ip or "")

        raw_payload = metadata_sources_to_dict(row["raw_payload"]) or {}
        parsed = raw_payload.get("parsed") if isinstance(raw_payload, dict) else None
        parsed = parsed if isinstance(parsed, dict) else {}

        try:
            bytes_sent = max(int(str(parsed.get("bytes_sent", 0)).strip()), 0)
        except (TypeError, ValueError):
            bytes_sent = 0
        try:
            bytes_received = max(int(str(parsed.get("bytes_received", 0)).strip()), 0)
        except (TypeError, ValueError):
            bytes_received = 0

        bytes_in = bytes_received
        bytes_out = bytes_sent
        if source_device and source_device.lifecycle_state == "active":
            if src_ip == source_device.ip_address:
                bytes_in, bytes_out = bytes_received, bytes_sent
            elif dst_ip == source_device.ip_address:
                bytes_in, bytes_out = bytes_sent, bytes_received

        lowered_type = event_type.lower()
        allowed_count = 1 if "allow" in lowered_type else 0
        blocked_count = 1 if ("deny" in lowered_type or "denied" in lowered_type or "block" in lowered_type or "drop" in lowered_type) else 0

        upsert_row(
            bucket_start=bucket_start,
            category="summary",
            dimension_key="all",
            events_count=1,
            allowed_events=allowed_count,
            blocked_events=blocked_count,
            bytes_in=bytes_in,
            bytes_out=bytes_out,
        )
        upsert_row(bucket_start=bucket_start, category="severity", dimension_key=severity, label=severity, events_count=1)
        upsert_row(bucket_start=bucket_start, category="protocol", dimension_key=protocol, label=protocol, events_count=1)
        upsert_row(bucket_start=bucket_start, category="event_type", dimension_key=event_type, label=event_type, events_count=1)

        firewall_rule_name = parsed.get("fw_rule_name")
        if isinstance(firewall_rule_name, str) and firewall_rule_name.strip():
            normalized_rule = firewall_rule_name.strip()
            upsert_row(bucket_start=bucket_start, category="firewall_rule", dimension_key=normalized_rule, label=normalized_rule, events_count=1)

        domain_value = parsed.get("domain")
        if not isinstance(domain_value, str) or not domain_value.strip():
            raw_url = parsed.get("url")
            if isinstance(raw_url, str) and raw_url.strip():
                domain_value = urlparse(raw_url.strip()).hostname
        if isinstance(domain_value, str) and domain_value.strip():
            normalized_domain = domain_value.strip().lower()
            tracked_domain_subject = _find_tracked_subject(tracked_subjects, entity_type="domain", value=normalized_domain)
            upsert_row(
                bucket_start=bucket_start,
                category="domain",
                dimension_key=normalized_domain,
                label=normalized_domain,
                tracked_subject_id=tracked_domain_subject.id if tracked_domain_subject else None,
                events_count=1,
                bytes_in=bytes_in,
                bytes_out=bytes_out,
            )

        peer_ip = dst_ip or src_ip
        if peer_ip:
            peer_label = None
            if isinstance(domain_value, str) and domain_value.strip():
                peer_label = domain_value.strip().lower()
            else:
                parsed_url = parsed.get("url")
                if isinstance(parsed_url, str) and parsed_url.strip():
                    peer_label = urlparse(parsed_url.strip()).hostname or peer_ip
            tracked_destination_subject = _find_tracked_subject(tracked_subjects, entity_type="ip", value=peer_ip)
            upsert_row(
                bucket_start=bucket_start,
                category="destination",
                dimension_key=peer_ip,
                label=peer_label or peer_ip,
                ip_address=peer_ip,
                tracked_subject_id=tracked_destination_subject.id if tracked_destination_subject else None,
                events_count=1,
                bytes_in=bytes_in,
                bytes_out=bytes_out,
            )

        if source_device and source_device.lifecycle_state == "active":
            tracked_device_subject = _find_tracked_subject(tracked_subjects, entity_type="device", value=str(source_device.id))
            upsert_row(
                bucket_start=bucket_start,
                category="source_device",
                dimension_key=str(source_device.id),
                label=_resolve_device_label(source_device),
                ip_address=source_device.ip_address,
                device_id=source_device.id,
                tracked_subject_id=tracked_device_subject.id if tracked_device_subject else None,
                events_count=1,
                bytes_in=bytes_in,
                bytes_out=bytes_out,
            )

    bucket_cursor = start
    while bucket_cursor <= end:
        upsert_row(bucket_start=bucket_cursor, category="summary", dimension_key="all")
        bucket_cursor += timedelta(hours=1)

    db.execute(delete(NetworkFirewallHourlyRollup).where(NetworkFirewallHourlyRollup.bucket_start >= start))
    if rows:
        db.add_all(
            [
                NetworkFirewallHourlyRollup(
                    bucket_start=entry["bucket_start"],
                    category=entry["category"],
                    dimension_key=entry["dimension_key"],
                    label=entry["label"],
                    ip_address=entry["ip_address"],
                    device_id=entry["device_id"],
                    tracked_subject_id=entry["tracked_subject_id"],
                    events_count=entry["events_count"],
                    allowed_events=entry["allowed_events"],
                    blocked_events=entry["blocked_events"],
                    bytes_in=entry["bytes_in"],
                    bytes_out=entry["bytes_out"],
                )
                for entry in rows.values()
            ]
        )
    db.commit()
    logger.info(
        "Network firewall hourly rollups refreshed; start=%s end=%s processed_events=%s rows=%s",
        start.isoformat(),
        end.isoformat(),
        processed,
        len(rows),
    )
    return len(rows)


def refresh_network_firewall_hourly_rollups(db: Session, *, lookback_hours: int = 48) -> int:
    now = datetime.now(UTC)
    start = now - timedelta(hours=max(lookback_hours, 1))
    end = now
    return refresh_network_firewall_hourly_rollups_for_range(db, start=start, end=end)


def prune_network_firewall_events(db: Session, *, retention_days: int = 14) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=max(retention_days, 1))
    deleted = db.query(NetworkFirewallEvent).filter(NetworkFirewallEvent.observed_at < cutoff).delete(synchronize_session=False)
    db.commit()
    logger.info("Network firewall raw events pruned; retention_days=%s deleted=%s", retention_days, deleted)
    return deleted


def build_network_statistics_summary_from_rollups(db: Session, *, window_hours: int = 24) -> NetworkStatisticsSummary | None:
    now = datetime.now(UTC)
    window_start = _truncate_hour(now - timedelta(hours=max(window_hours, 1)))
    window_end = _truncate_hour(now)
    rollups = db.scalars(
        select(NetworkFirewallHourlyRollup).where(NetworkFirewallHourlyRollup.bucket_start >= window_start)
    ).all()
    summary_rows = [item for item in rollups if item.category == "summary"]
    if not summary_rows:
        return None
    covered_buckets = {_ensure_utc(item.bucket_start) for item in summary_rows}
    bucket_cursor = window_start
    while bucket_cursor <= window_end:
        if bucket_cursor not in covered_buckets:
            return None
        bucket_cursor += timedelta(hours=1)

    devices = db.scalars(select(NetworkDevice)).all()
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
    domains_map: dict[str, dict[str, Any]] = defaultdict(lambda: {"label": None, "ip_address": None, "events_count": 0, "bytes_in": 0, "bytes_out": 0, "bytes_total": 0, "tracked_subject_id": None})
    destinations_map: dict[str, dict[str, Any]] = defaultdict(lambda: {"label": None, "ip_address": None, "events_count": 0, "bytes_in": 0, "bytes_out": 0, "bytes_total": 0, "tracked_subject_id": None})
    sources_map: dict[str, dict[str, Any]] = defaultdict(lambda: {"label": None, "ip_address": None, "device_id": None, "events_count": 0, "bytes_in": 0, "bytes_out": 0, "bytes_total": 0, "tracked_subject_id": None})
    timeline_map: dict[str, dict[str, int]] = defaultdict(lambda: {"events_count": 0, "bytes_in": 0, "bytes_out": 0})
    seen_domains: set[str] = set()
    external_peers: set[str] = set()
    source_devices_with_traffic: set[int] = set()
    total_events = 0
    allowed_events = 0
    blocked_events = 0
    total_bytes_in = 0
    total_bytes_out = 0

    for row in rollups:
        if row.category == "summary":
            total_events += row.events_count
            allowed_events += row.allowed_events
            blocked_events += row.blocked_events
            total_bytes_in += row.bytes_in
            total_bytes_out += row.bytes_out
            bucket = _ensure_utc(row.bucket_start).astimezone(timezone.utc).strftime("%d/%m %H:00")
            timeline_map[bucket]["events_count"] += row.events_count
            timeline_map[bucket]["bytes_in"] += row.bytes_in
            timeline_map[bucket]["bytes_out"] += row.bytes_out
            continue
        if row.category == "severity":
            severity_counter[row.dimension_key] += row.events_count
            continue
        if row.category == "protocol":
            protocol_counter[row.dimension_key] += row.events_count
            continue
        if row.category == "event_type":
            event_type_counter[row.dimension_key] += row.events_count
            continue
        if row.category == "firewall_rule":
            firewall_rule_counter[row.dimension_key] += row.events_count
            continue
        if row.category == "domain":
            seen_domains.add(row.dimension_key)
            entry = domains_map[row.dimension_key]
            entry["label"] = row.label or row.dimension_key
            entry["events_count"] += row.events_count
            entry["bytes_in"] += row.bytes_in
            entry["bytes_out"] += row.bytes_out
            entry["bytes_total"] += row.bytes_in + row.bytes_out
            entry["tracked_subject_id"] = entry["tracked_subject_id"] or row.tracked_subject_id
            continue
        if row.category == "destination":
            if row.ip_address:
                try:
                    peer_parsed = ipaddress.ip_address(row.ip_address)
                except ValueError:
                    peer_parsed = None
                if peer_parsed and not (peer_parsed.is_private or peer_parsed.is_loopback or peer_parsed.is_link_local or peer_parsed.is_multicast):
                    external_peers.add(row.ip_address)
            entry = destinations_map[row.dimension_key]
            entry["label"] = row.label or row.dimension_key
            entry["ip_address"] = row.ip_address
            entry["events_count"] += row.events_count
            entry["bytes_in"] += row.bytes_in
            entry["bytes_out"] += row.bytes_out
            entry["bytes_total"] += row.bytes_in + row.bytes_out
            entry["tracked_subject_id"] = entry["tracked_subject_id"] or row.tracked_subject_id
            continue
        if row.category == "source_device":
            if row.device_id:
                source_devices_with_traffic.add(row.device_id)
            entry = sources_map[row.dimension_key]
            entry["label"] = row.label or row.dimension_key
            entry["ip_address"] = row.ip_address
            entry["device_id"] = row.device_id
            entry["events_count"] += row.events_count
            entry["bytes_in"] += row.bytes_in
            entry["bytes_out"] += row.bytes_out
            entry["bytes_total"] += row.bytes_in + row.bytes_out
            entry["tracked_subject_id"] = entry["tracked_subject_id"] or row.tracked_subject_id

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
