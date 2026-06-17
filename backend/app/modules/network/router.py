from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import ipaddress
import zlib
import re
import socket
from typing import Annotated, Any
import urllib.error
import urllib.request
import json
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_role
from app.core.database import get_db
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.network.models import (
    DevicePosition,
    FloorPlan,
    NetworkAlert,
    NetworkDevice,
    NetworkDetectionWatchlist,
    NetworkFirewall,
    NetworkFirewallEvent,
    NetworkSophosConfig,
    NetworkScan,
    NetworkScanDevice,
    NetworkTrackedSubject,
)
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
    NetworkDetectionWatchlistRuleCreateRequest,
    NetworkDetectionWatchlistRuleRead,
    NetworkDetectionWatchlistRuleUpdateRequest,
    NetworkDeviceListResponse,
    NetworkDeviceBulkUpdateRequest,
    NetworkDeviceBulkUpdateResponse,
    NetworkAssignedUserSummary,
    NetworkDeviceTrafficEventSummary,
    NetworkDeviceTrafficPeerSummary,
    NetworkDeviceTrafficSummary,
    NetworkDeviceResponse,
    NetworkDeviceUpdateRequest,
    NetworkFirewallEventResponse,
    NetworkFirewallLogCoverageSummary,
    NetworkFirewallLogFamilyStatus,
    NetworkFirewallMetricResponse,
    NetworkSophosConfigRead,
    NetworkSophosConfigUpdateRequest,
    NetworkIpWhoisResponse,
    NetworkFirewallResponse,
    NetworkStatisticsCountItem,
    NetworkStatisticsSummary,
    NetworkStatisticsTimelinePoint,
    NetworkStatisticsTrafficItem,
    NetworkTrackedSubjectActivityEvent,
    NetworkTrackedSubjectActivitySummary,
    NetworkTrackedSubjectCreateRequest,
    NetworkTrackedSubjectResponse,
    NetworkTrackedSubjectUpdateRequest,
    NetworkArpTimelineItem,
    NetworkArpTimelineObservation,
    NetworkVpnBypassSummary,
    NetworkScanDetailResponse,
    NetworkScanDeviceResponse,
    NetworkScanDiffEntry,
    NetworkScanDiffResponse,
    NetworkScanResponse,
    NetworkScanTriggerRequest,
    NetworkScanTriggerResponse,
    SophosSyslogIngestRequest,
)
from app.modules.network.detection import default_watchlist_items, event_detection_tags
from app.modules.network.sophos import ingest_sophos_syslog, list_network_firewall_events, list_network_firewalls
from app.modules.network.sophos_snmp import list_network_firewall_metrics, poll_sophos_firewall_metrics
from app.modules.network.sophos_runtime import build_sophos_runtime_policy, clear_sophos_runtime_policy_cache, get_or_create_sophos_config
from app.modules.network.telemetry_rollups import build_network_statistics_summary_from_rollups
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
                "mac_address": item.mac_address,
                "open_ports": item.open_ports,
            }
            for item in scan_history or []
        ],
        "traffic_summary": traffic_summary,
    }
    return NetworkDeviceResponse.model_validate(payload)


def _build_arp_timeline(
    db: Session,
    *,
    window_hours: int,
    limit: int,
) -> list[NetworkArpTimelineItem]:
    observed_since = datetime.now(UTC) - timedelta(hours=window_hours)
    arp_scan_ids = select(NetworkScan.id).where(
        NetworkScan.scan_type == "arp",
        NetworkScan.completed_at >= observed_since,
    )
    rows = db.scalars(
        select(NetworkScanDevice)
        .where(NetworkScanDevice.scan_id.in_(arp_scan_ids))
        .order_by(NetworkScanDevice.observed_at.desc(), NetworkScanDevice.id.desc())
    ).all()
    if not rows:
        return []

    devices_by_id = {
        item.id: item
        for item in db.scalars(
            select(NetworkDevice).where(NetworkDevice.id.in_({row.device_id for row in rows if row.device_id is not None}))
        ).all()
    }
    grouped: dict[str, list[NetworkScanDevice]] = defaultdict(list)
    for row in rows:
        scope_key = f"device:{row.device_id}" if row.device_id is not None else f"ip:{row.ip_address}"
        grouped[scope_key].append(row)

    timeline: list[NetworkArpTimelineItem] = []
    for scope_key, items in grouped.items():
        items_desc = sorted(items, key=lambda item: (item.observed_at, item.id), reverse=True)
        items_asc = list(reversed(items_desc))
        distinct_ips = list(dict.fromkeys(item.ip_address for item in items_desc if item.ip_address))
        distinct_macs = list(dict.fromkeys(item.mac_address for item in items_desc if item.mac_address))
        rapid_reappearances = 0
        previous_online_at: datetime | None = None
        for item in items_asc:
            observed_at = item.observed_at if item.observed_at.tzinfo is not None else item.observed_at.replace(tzinfo=UTC)
            if item.status == "online":
                if previous_online_at and observed_at - previous_online_at <= timedelta(hours=2):
                    rapid_reappearances += 1
                previous_online_at = observed_at
        suspicious_reasons: list[str] = []
        if len(distinct_macs) > 1:
            suspicious_reasons.append("same_ip_multiple_macs")
        if len(distinct_ips) > 1 and items_desc[0].mac_address:
            suspicious_reasons.append("same_mac_multiple_ips")
        if rapid_reappearances > 1:
            suspicious_reasons.append("rapid_reappearances")

        device = devices_by_id.get(items_desc[0].device_id) if items_desc[0].device_id is not None else None
        resolved_label = _resolve_device_label(device)[0] if device is not None else items_desc[0].display_name or items_desc[0].hostname or items_desc[0].ip_address
        ip_counts = Counter(item.ip_address for item in items_desc if item.ip_address)
        mac_counts = Counter(item.mac_address for item in items_desc if item.mac_address)
        timeline.append(
            NetworkArpTimelineItem(
                scope_key=scope_key,
                scope_type="device" if items_desc[0].device_id is not None else "ip",
                device_id=items_desc[0].device_id,
                resolved_label=resolved_label,
                primary_ip_address=ip_counts.most_common(1)[0][0] if ip_counts else None,
                primary_mac_address=mac_counts.most_common(1)[0][0] if mac_counts else None,
                first_observed_at=items_asc[0].observed_at,
                last_observed_at=items_desc[0].observed_at,
                observations_count=len(items_desc),
                online_appearances=sum(1 for item in items_desc if item.status == "online"),
                offline_appearances=sum(1 for item in items_desc if item.status != "online"),
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
        )

    timeline.sort(
        key=lambda item: (
            len(item.suspicious_reasons),
            item.rapid_reappearances,
            len(item.distinct_mac_addresses),
            len(item.distinct_ip_addresses),
            item.last_observed_at,
        ),
        reverse=True,
    )
    return timeline[:limit]


def _extract_rdap_entity_names(payload: dict[str, Any]) -> list[str]:
    names: list[str] = []
    entities = payload.get("entities")
    if not isinstance(entities, list):
        return names

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
                and item[0] in {"fn", "org"}
                and isinstance(item[3], str)
                and item[3].strip()
            ):
                names.append(item[3].strip())
                break
    return list(dict.fromkeys(names))


def _summarize_ip_whois(ip_address: str) -> NetworkIpWhoisResponse:
    try:
        parsed_ip = ipaddress.ip_address(ip_address)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid IP address: {ip_address}") from exc

    if parsed_ip.is_private:
        return NetworkIpWhoisResponse(
            ip_address=str(parsed_ip),
            scope="IP privato",
            is_private=True,
            rdap_status="not_applicable",
            label="Rete interna GAIA/LAN privata",
        )
    if parsed_ip.is_loopback:
        return NetworkIpWhoisResponse(
            ip_address=str(parsed_ip),
            scope="Loopback locale",
            is_loopback=True,
            rdap_status="not_applicable",
            label="Indirizzo locale della macchina stessa",
        )
    if parsed_ip.is_link_local:
        return NetworkIpWhoisResponse(
            ip_address=str(parsed_ip),
            scope="Link-local",
            is_link_local=True,
            rdap_status="not_applicable",
            label="Indirizzo autoconfigurato non instradato su Internet",
        )

    external_url = f"https://rdap.org/ip/{parsed_ip}"
    try:
        with urllib.request.urlopen(external_url, timeout=4) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return NetworkIpWhoisResponse(
            ip_address=str(parsed_ip),
            scope="IP pubblico",
            rdap_status="unavailable",
            external_url=external_url,
        )

    start_address = payload.get("startAddress")
    end_address = payload.get("endAddress")
    cidr: list[str] = []
    if isinstance(start_address, str) and isinstance(end_address, str):
        try:
            cidr = [str(item) for item in ipaddress.summarize_address_range(ipaddress.ip_address(start_address), ipaddress.ip_address(end_address))]
        except ValueError:
            cidr = []

    entity_names = _extract_rdap_entity_names(payload)
    label = entity_names[0] if entity_names else None
    network_name = payload.get("name") if isinstance(payload.get("name"), str) else None
    handle = payload.get("handle") if isinstance(payload.get("handle"), str) else None
    country = payload.get("country") if isinstance(payload.get("country"), str) else None

    return NetworkIpWhoisResponse(
        ip_address=str(parsed_ip),
        scope="IP pubblico",
        rdap_status="ok",
        label=label,
        network_name=network_name,
        handle=handle,
        country=country,
        start_address=start_address if isinstance(start_address, str) else None,
        end_address=end_address if isinstance(end_address, str) else None,
        cidr=cidr,
        entities=entity_names,
        external_url=external_url,
        raw=payload,
    )


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


def _serialize_alert(alert: NetworkAlert) -> NetworkAlertResponse:
    return NetworkAlertResponse.model_validate(
        {
            "id": alert.id,
            "device_id": alert.device_id,
            "scan_id": alert.scan_id,
            "assigned_to_user_id": alert.assigned_to_user_id,
            "assigned_to_username": alert.assigned_to_user.username if alert.assigned_to_user else None,
            "assigned_to_full_name": alert.assigned_to_user.full_name if alert.assigned_to_user else None,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "status": alert.status,
            "verification_status": alert.verification_status,
            "title": alert.title,
            "message": alert.message,
            "verification_notes": alert.verification_notes,
            "created_at": alert.created_at,
            "reviewed_at": alert.reviewed_at,
            "acknowledged_at": alert.acknowledged_at,
        }
    )


def _extract_firewall_event_parsed(event: NetworkFirewallEvent) -> dict[str, Any]:
    raw_payload = metadata_sources_to_dict(event.raw_payload) or {}
    parsed = raw_payload.get("parsed") if isinstance(raw_payload, dict) else None
    return parsed if isinstance(parsed, dict) else {}


def _normalize_tracked_value(entity_type: str, value: str) -> str:
    normalized = value.strip()
    if entity_type == "ip":
        try:
            return str(ipaddress.ip_address(normalized))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid IP address: {value}") from exc
    if entity_type == "domain":
        parsed_hostname = urlparse(normalized).hostname if "://" in normalized else normalized
        hostname = (parsed_hostname or normalized).strip().rstrip(".").lower()
        if not hostname:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid domain value")
        return hostname
    if entity_type == "url":
        if not normalized:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid URL value")
        return normalized
    return normalized


def _find_matching_device_for_legacy_ip_subject(db: Session, subject: NetworkTrackedSubject) -> NetworkDevice | None:
    if subject.entity_type != "ip" or subject.device_id is not None or not subject.value:
        return None
    try:
        parsed_ip = ipaddress.ip_address(subject.value)
    except ValueError:
        return None
    if not parsed_ip.is_private:
        return None
    return db.scalar(select(NetworkDevice).where(NetworkDevice.ip_address == subject.value))


def _reconcile_legacy_ip_tracked_subject(db: Session, subject: NetworkTrackedSubject) -> tuple[NetworkTrackedSubject, bool]:
    device = _find_matching_device_for_legacy_ip_subject(db, subject)
    if device is None:
        return subject, False

    canonical = db.scalar(
        select(NetworkTrackedSubject).where(
            NetworkTrackedSubject.entity_type == "device",
            NetworkTrackedSubject.normalized_value == str(device.id),
            NetworkTrackedSubject.id != subject.id,
        )
    )
    if canonical is not None:
        if not canonical.label and subject.label:
            canonical.label = subject.label
        if not canonical.notes and subject.notes:
            canonical.notes = subject.notes
        canonical.is_active = canonical.is_active or subject.is_active
        canonical.device_id = device.id
        canonical.value = device.ip_address
        db.add(canonical)
        db.delete(subject)
        return canonical, True

    subject.entity_type = "device"
    subject.device_id = device.id
    subject.normalized_value = str(device.id)
    subject.value = device.ip_address
    db.add(subject)
    return subject, True


def _reconcile_legacy_ip_tracked_subjects(db: Session) -> None:
    legacy_subjects = db.scalars(
        select(NetworkTrackedSubject).where(
            NetworkTrackedSubject.entity_type == "ip",
            NetworkTrackedSubject.device_id.is_(None),
        )
    ).all()
    changed = False
    for subject in legacy_subjects:
        _, subject_changed = _reconcile_legacy_ip_tracked_subject(db, subject)
        changed = changed or subject_changed
    if changed:
        db.commit()


def _tracked_subject_key(entity_type: str, normalized_value: str) -> tuple[str, str]:
    return entity_type, normalized_value


def _get_active_tracked_subject_map(db: Session) -> dict[tuple[str, str], NetworkTrackedSubject]:
    subjects = db.scalars(
        select(NetworkTrackedSubject)
        .where(NetworkTrackedSubject.is_active.is_(True))
        .order_by(NetworkTrackedSubject.id.asc())
    ).all()
    return {_tracked_subject_key(item.entity_type, item.normalized_value): item for item in subjects}


def _resolve_tracked_subject_label(subject: NetworkTrackedSubject, db: Session) -> str:
    if subject.label:
        return subject.label
    if subject.device_id:
        device = db.get(NetworkDevice, subject.device_id)
        if device is not None:
            return _resolve_device_label(device)[0]
    return subject.value


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
    except HTTPException:
        return None
    return tracked_subjects.get(_tracked_subject_key(entity_type, normalized_value))


def _match_tracked_subject_against_event(
    subject: NetworkTrackedSubject,
    event: NetworkFirewallEvent,
    *,
    parsed: dict[str, Any],
) -> tuple[str, str] | None:
    if subject.entity_type == "device":
        if subject.device_id and (event.device_id == subject.device_id or event.src_ip == subject.value or event.dst_ip == subject.value):
            return "device", subject.value
        return None
    if subject.entity_type == "ip":
        if event.src_ip == subject.normalized_value:
            return "src_ip", subject.normalized_value
        if event.dst_ip == subject.normalized_value:
            return "dst_ip", subject.normalized_value
        return None
    if subject.entity_type == "domain":
        domain = parsed.get("domain")
        candidate = None
        if isinstance(domain, str) and domain.strip():
            candidate = domain.strip().lower()
        else:
            raw_url = parsed.get("url")
            if isinstance(raw_url, str) and raw_url.strip():
                candidate = (urlparse(raw_url.strip()).hostname or "").lower()
        if candidate and candidate == subject.normalized_value:
            return "domain", candidate
        return None
    if subject.entity_type == "url":
        raw_url = parsed.get("url")
        if isinstance(raw_url, str) and raw_url.strip() == subject.normalized_value:
            return "url", raw_url.strip()
    return None


def _ensure_detection_watchlist_seeded(db: Session) -> None:
    for item in default_watchlist_items():
        exists = db.scalar(
            select(NetworkDetectionWatchlist.id).where(
                NetworkDetectionWatchlist.category == item["category"],
                NetworkDetectionWatchlist.rule_mode == item.get("rule_mode", "detect"),
                NetworkDetectionWatchlist.match_type == item["match_type"],
                NetworkDetectionWatchlist.pattern == item["pattern"],
            )
        )
        if exists is not None:
            continue
        db.add(
            NetworkDetectionWatchlist(
                category=item["category"],
                rule_mode=item.get("rule_mode", "detect"),
                match_type=item["match_type"],
                pattern=item["pattern"],
                label=item["label"],
                is_active=True,
            )
        )
    db.flush()


def _active_detection_watchlist_entries(db: Session) -> list[tuple[str, str, str, str]]:
    _ensure_detection_watchlist_seeded(db)
    items = db.scalars(
        select(NetworkDetectionWatchlist)
        .where(NetworkDetectionWatchlist.is_active.is_(True))
        .order_by(NetworkDetectionWatchlist.category.asc(), NetworkDetectionWatchlist.pattern.asc())
    ).all()
    return [(item.category, item.rule_mode, item.match_type, item.pattern) for item in items]


def _build_tracked_subject_activity_summary(
    db: Session,
    subject: NetworkTrackedSubject,
    *,
    window_hours: int = 168,
    limit: int = 25,
) -> NetworkTrackedSubjectActivitySummary:
    window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    event_query = select(NetworkFirewallEvent).where(NetworkFirewallEvent.observed_at >= window_start)
    if subject.entity_type == "device" and subject.device_id and subject.value:
        event_query = event_query.where(
            or_(
                NetworkFirewallEvent.device_id == subject.device_id,
                NetworkFirewallEvent.src_ip == subject.value,
                NetworkFirewallEvent.dst_ip == subject.value,
            )
        )
    elif subject.entity_type == "ip":
        event_query = event_query.where(
            or_(
                NetworkFirewallEvent.src_ip == subject.normalized_value,
                NetworkFirewallEvent.dst_ip == subject.normalized_value,
            )
        )
    elif subject.entity_type in {"domain", "url"}:
        event_query = event_query.where(NetworkFirewallEvent.raw_payload.ilike(f"%{subject.normalized_value}%"))

    events = db.scalars(event_query.order_by(NetworkFirewallEvent.observed_at.desc())).all()

    matched_events: list[NetworkTrackedSubjectActivityEvent] = []
    total_events = 0
    allowed_events = 0
    blocked_events = 0
    suspicious_events = 0
    vpn_suspected_events = 0
    proxy_suspected_events = 0
    tor_suspected_events = 0
    encrypted_dns_events = 0
    total_bytes_in = 0
    total_bytes_out = 0
    last_observed_at: datetime | None = None
    detection_counter: Counter[str] = Counter()
    watchlist_entries = _active_detection_watchlist_entries(db)

    for event in events:
        parsed = _extract_firewall_event_parsed(event)
        match = _match_tracked_subject_against_event(subject, event, parsed=parsed)
        if not match:
            continue
        detection_tags = event_detection_tags(
            event.event_type,
            event.message,
            event.protocol,
            parsed,
            watchlist_entries=watchlist_entries,
        )
        total_events += 1
        matched_on, matched_value = match
        bytes_in = 0
        bytes_out = 0
        if subject.entity_type == "device" and subject.value:
            bytes_in, bytes_out, _ = _extract_event_traffic(event, device_ip=subject.value)
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
        if last_observed_at is None:
            last_observed_at = event.observed_at

        lowered_type = event.event_type.lower()
        if "allow" in lowered_type:
            allowed_events += 1
        if "deny" in lowered_type or "denied" in lowered_type or "block" in lowered_type or "drop" in lowered_type:
            blocked_events += 1
        if detection_tags:
            suspicious_events += 1
            detection_counter.update(detection_tags)
            if "vpn_suspected" in detection_tags:
                vpn_suspected_events += 1
            if "proxy_suspected" in detection_tags:
                proxy_suspected_events += 1
            if "tor_suspected" in detection_tags:
                tor_suspected_events += 1
            if "encrypted_dns" in detection_tags:
                encrypted_dns_events += 1

        if len(matched_events) < limit:
            src_label, dst_label = _resolve_firewall_event_endpoint_labels(
                db,
                device_id=event.device_id,
                src_ip=event.src_ip,
                dst_ip=event.dst_ip,
            )
            matched_events.append(
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
                    matched_value=matched_value,
                    detection_tags=detection_tags,
                    observed_at=event.observed_at,
                )
            )

    return NetworkTrackedSubjectActivitySummary(
        window_hours=window_hours,
        total_events=total_events,
        allowed_events=allowed_events,
        blocked_events=blocked_events,
        suspicious_events=suspicious_events,
        vpn_suspected_events=vpn_suspected_events,
        proxy_suspected_events=proxy_suspected_events,
        tor_suspected_events=tor_suspected_events,
        encrypted_dns_events=encrypted_dns_events,
        bytes_in=total_bytes_in,
        bytes_out=total_bytes_out,
        last_observed_at=last_observed_at,
        top_detection_tags=[tag for tag, _ in detection_counter.most_common(4)],
        recent_events=matched_events,
    )


def _serialize_tracked_subject(
    db: Session,
    subject: NetworkTrackedSubject,
    *,
    include_activity_summary: bool = True,
    window_hours: int = 168,
) -> NetworkTrackedSubjectResponse:
    device = db.get(NetworkDevice, subject.device_id) if subject.device_id else None
    created_by = db.get(ApplicationUser, subject.created_by_user_id) if subject.created_by_user_id else None
    scan_history = get_device_scan_history(db, subject.device_id, limit=8) if subject.device_id else []
    return NetworkTrackedSubjectResponse(
        id=subject.id,
        entity_type=subject.entity_type,
        normalized_value=subject.normalized_value,
        value=subject.value,
        label=subject.label,
        resolved_label=_resolve_tracked_subject_label(subject, db),
        notes=subject.notes,
        is_active=subject.is_active,
        device_id=subject.device_id,
        device_label=_resolve_device_label(device)[0] if device is not None else None,
        created_by_user_id=subject.created_by_user_id,
        created_by_username=created_by.username if created_by is not None else None,
        created_at=subject.created_at,
        updated_at=subject.updated_at,
        activity_summary=_build_tracked_subject_activity_summary(db, subject, window_hours=window_hours) if include_activity_summary else None,
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
            for item in scan_history
        ],
    )


def _synthetic_subject_id(entity_type: str, normalized_value: str) -> int:
    return -(zlib.crc32(f"{entity_type}:{normalized_value}".encode("utf-8")) or 1)


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
    window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
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

        bucket = observed_at.astimezone(timezone.utc).strftime("%d/%m %H:00")
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
    tracked_subjects = _get_active_tracked_subject_map(db)
    src_label, dst_label = _resolve_firewall_event_endpoint_labels(
        db,
        device_id=event.device_id,
        src_ip=event.src_ip,
        dst_ip=event.dst_ip,
    )
    parsed = _extract_firewall_event_parsed(event)
    tracked_src = _find_tracked_subject(tracked_subjects, entity_type="ip", value=event.src_ip)
    tracked_dst = _find_tracked_subject(tracked_subjects, entity_type="ip", value=event.dst_ip)
    tracked_domain = _find_tracked_subject(
        tracked_subjects,
        entity_type="domain",
        value=parsed.get("domain") if isinstance(parsed.get("domain"), str) else None,
    )
    tracked_url = _find_tracked_subject(
        tracked_subjects,
        entity_type="url",
        value=parsed.get("url") if isinstance(parsed.get("url"), str) else None,
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
        "tracked_src_ip_subject_id": tracked_src.id if tracked_src else None,
        "tracked_dst_ip_subject_id": tracked_dst.id if tracked_dst else None,
        "tracked_domain_subject_id": tracked_domain.id if tracked_domain else None,
        "tracked_url_subject_id": tracked_url.id if tracked_url else None,
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


_EXPECTED_SOPHOS_LOG_FAMILIES: list[tuple[str, str]] = [
    ("firewall", "Firewall"),
    ("vpn", "VPN"),
    ("ips", "IPS"),
    ("authentication", "Authentication"),
    ("system", "System"),
]


def _classify_sophos_log_family(event: NetworkFirewallEvent) -> str:
    parsed = _extract_firewall_event_parsed(event)
    return _classify_sophos_log_family_from_values(event_type=event.event_type, parsed=parsed)


def _classify_sophos_log_family_from_values(*, event_type: str, parsed: dict[str, Any] | None) -> str:
    parsed = parsed if isinstance(parsed, dict) else {}
    log_type = str(parsed.get("log_type") or "").strip().lower()
    log_component = str(parsed.get("log_component") or "").strip().lower()
    event_type = event_type.lower()

    if event_type.startswith("firewall.") or "firewall" in log_type:
        return "firewall"
    if "vpn" in event_type or "vpn" in log_type or "vpn" in log_component:
        return "vpn"
    if "ips" in event_type or "intrusion" in log_type or "ips" in log_type or "ips" in log_component:
        return "ips"
    if "auth" in event_type or "authentication" in log_type or "authentication" in log_component:
        return "authentication"
    if event_type.startswith("system_health.") or event_type.startswith("event.gui.") or "system" in log_type or "system" in log_component:
        return "system"
    if event_type.startswith("content_filtering."):
        return "content_filtering"
    if event_type.startswith("anti-virus.") or "anti-virus" in event_type:
        return "anti-virus"
    return event_type.split(".", 1)[0] if "." in event_type else event_type or "other"


def _build_firewall_log_coverage_summary(
    db: Session,
    *,
    firewall: NetworkFirewall,
    window_hours: int,
) -> NetworkFirewallLogCoverageSummary:
    observed_since = datetime.now(UTC) - timedelta(hours=window_hours)
    event_rows = db.execute(
        select(
            NetworkFirewallEvent.event_type.label("event_type"),
            func.count(NetworkFirewallEvent.id).label("events_count"),
            func.max(NetworkFirewallEvent.observed_at).label("last_observed_at"),
        )
        .where(
            NetworkFirewallEvent.firewall_id == firewall.id,
            NetworkFirewallEvent.observed_at >= observed_since,
        )
        .group_by(NetworkFirewallEvent.event_type)
        .execution_options(stream_results=True, yield_per=1000)
    )

    grouped: dict[str, dict[str, Any]] = {}
    event_type_counts: Counter[str] = Counter()
    total_events = 0
    for row in event_rows.mappings():
        event_type = row["event_type"]
        observed_at = row["last_observed_at"]
        events_count = int(row["events_count"] or 0)
        family = _classify_sophos_log_family_from_values(event_type=event_type, parsed=None)
        bucket = grouped.setdefault(
            family,
            {
                "count": 0,
                "last_observed_at": None,
                "examples": [],
                "example_seen": set(),
            },
        )
        total_events += events_count
        event_type_counts[event_type] += events_count
        bucket["count"] += events_count
        if bucket["last_observed_at"] is None or observed_at > bucket["last_observed_at"]:
            bucket["last_observed_at"] = observed_at
        if event_type not in bucket["example_seen"] and len(bucket["examples"]) < 3:
            bucket["examples"].append(event_type)
            bucket["example_seen"].add(event_type)

    expected_keys = {family_key for family_key, _ in _EXPECTED_SOPHOS_LOG_FAMILIES}
    expected_families = [
        NetworkFirewallLogFamilyStatus(
            family_key=family_key,
            label=label,
            expected=True,
            observed_count=int(grouped.get(family_key, {}).get("count", 0)),
            last_observed_at=grouped.get(family_key, {}).get("last_observed_at"),
            status="ok" if grouped.get(family_key, {}).get("count", 0) > 0 else "missing",
            examples=list(grouped.get(family_key, {}).get("examples", [])),
        )
        for family_key, label in _EXPECTED_SOPHOS_LOG_FAMILIES
    ]
    additional_families = [
        NetworkFirewallLogFamilyStatus(
            family_key=family_key,
            label=family_key.replace("_", " ").title(),
            expected=False,
            observed_count=int(data["count"]),
            last_observed_at=data["last_observed_at"],
            status="observed",
            examples=list(data["examples"]),
        )
        for family_key, data in sorted(grouped.items(), key=lambda item: item[1]["count"], reverse=True)
        if family_key not in expected_keys
    ]
    return NetworkFirewallLogCoverageSummary(
        firewall_id=firewall.id,
        window_hours=window_hours,
        generated_at=datetime.now(UTC),
        total_events=total_events,
        expected_families=expected_families,
        additional_families=additional_families,
        missing_expected_families=[item.family_key for item in expected_families if item.status == "missing"],
        top_event_types=[
            NetworkStatisticsCountItem(key=event_type, label=event_type, count=count)
            for event_type, count in event_type_counts.most_common(6)
        ],
    )


def _require_network_module(current_user: ApplicationUser) -> None:
    if not current_user.module_rete and not current_user.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Network module not enabled")


def _serialize_sophos_config(config: NetworkSophosConfig) -> NetworkSophosConfigRead:
    policy = build_sophos_runtime_policy(config)
    return NetworkSophosConfigRead(
        syslog_enabled=policy.syslog_enabled,
        snmp_enabled=policy.snmp_enabled,
        operation_window_enabled=policy.operation_window_enabled,
        operation_start_hour=policy.operation_start_hour,
        operation_end_hour=policy.operation_end_hour,
        operation_timezone=policy.operation_timezone,
        is_within_window=policy.is_within_window,
        syslog_effective_enabled=policy.syslog_should_ingest,
        snmp_effective_enabled=policy.snmp_should_poll,
        updated_at=config.updated_at,
    )


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
    rollup_summary = build_network_statistics_summary_from_rollups(db, window_hours=window_hours)
    if rollup_summary is not None:
        return rollup_summary
    return _build_network_statistics_summary(db, window_hours=window_hours)


@router.get("/devices", response_model=NetworkDeviceListResponse)
def get_devices(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    lifecycle_state: str | None = Query(default=None, alias="lifecycle"),
    assignment: str | None = Query(default=None),
    known: str | None = Query(default=None),
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
        lifecycle_state=lifecycle_state,
        assignment=assignment,
        known=known,
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


@router.get("/ip-whois/{ip_address}", response_model=NetworkIpWhoisResponse)
def get_ip_whois(
    ip_address: str,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
) -> NetworkIpWhoisResponse:
    _require_network_module(current_user)
    return _summarize_ip_whois(ip_address)


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


@router.post("/devices/bulk-update", response_model=NetworkDeviceBulkUpdateResponse)
def bulk_update_devices(
    payload: NetworkDeviceBulkUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkDeviceBulkUpdateResponse:
    _require_network_module(current_user)
    devices = db.scalars(
        select(NetworkDevice).where(NetworkDevice.id.in_(payload.device_ids)).order_by(NetworkDevice.ip_address.asc())
    ).all()
    if not devices:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No devices found for bulk update")

    notes_append = payload.notes_append.strip() if payload.notes_append else None
    for device in devices:
        if payload.is_known_device is not None:
            device.is_known_device = payload.is_known_device
        if payload.location_hint is not None:
            device.location_hint = payload.location_hint or None
        if notes_append:
            device.notes = f"{device.notes}\n{notes_append}".strip() if device.notes else notes_append
        sync_network_device_alert_state(db, device)
        db.add(device)

    db.commit()
    for device in devices:
        db.refresh(device)

    return NetworkDeviceBulkUpdateResponse(
        updated_count=len(devices),
        items=[_serialize_device(device) for device in devices],
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


@router.get("/tracking", response_model=list[NetworkTrackedSubjectResponse])
def get_tracked_subjects(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    include_inactive: bool = Query(default=False),
    include_inferred: bool = Query(default=False),
    window_hours: int = Query(default=168, ge=1, le=24 * 30),
    search: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
) -> list[NetworkTrackedSubjectResponse]:
    _require_network_module(current_user)
    _reconcile_legacy_ip_tracked_subjects(db)
    query = select(NetworkTrackedSubject).order_by(NetworkTrackedSubject.updated_at.desc(), NetworkTrackedSubject.id.desc())
    if not include_inactive:
        query = query.where(NetworkTrackedSubject.is_active.is_(True))
    if entity_type:
        query = query.where(NetworkTrackedSubject.entity_type == entity_type)
    if search:
        normalized_search = f"%{search.strip()}%"
        query = query.where(
            or_(
                NetworkTrackedSubject.value.ilike(normalized_search),
                NetworkTrackedSubject.label.ilike(normalized_search),
                NetworkTrackedSubject.notes.ilike(normalized_search),
            )
        )
    subjects = db.scalars(query).all()
    items = [_serialize_tracked_subject(db, subject, window_hours=window_hours) for subject in subjects]
    if include_inferred:
        active_subject_map = _get_active_tracked_subject_map(db)
        items.extend(
            _build_inferred_assigned_arp_subjects(
                db,
                active_subjects=active_subject_map,
                window_hours=window_hours,
                entity_type=entity_type,
                search=search,
            )
        )
        items.extend(
            _build_inferred_tracked_subjects(
                db,
                window_hours=window_hours,
                entity_type=entity_type,
                search=search,
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


@router.post("/tracking", response_model=NetworkTrackedSubjectResponse, status_code=status.HTTP_201_CREATED)
def create_tracked_subject(
    payload: NetworkTrackedSubjectCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkTrackedSubjectResponse:
    _require_network_module(current_user)

    device: NetworkDevice | None = None
    value = payload.value.strip() if payload.value else None
    normalized_value = value
    if payload.entity_type == "device":
        device = db.get(NetworkDevice, payload.device_id)
        if device is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        normalized_value = str(device.id)
        value = device.ip_address
        legacy_subject = db.scalar(
            select(NetworkTrackedSubject).where(
                NetworkTrackedSubject.entity_type == "ip",
                NetworkTrackedSubject.device_id.is_(None),
                NetworkTrackedSubject.value == device.ip_address,
            )
        )
        if legacy_subject is not None:
            reconciled_subject, _ = _reconcile_legacy_ip_tracked_subject(db, legacy_subject)
            db.commit()
            db.refresh(reconciled_subject)
            if payload.label is not None:
                reconciled_subject.label = payload.label or None
            if payload.notes is not None:
                reconciled_subject.notes = payload.notes or None
            reconciled_subject.is_active = True
            db.add(reconciled_subject)
            db.commit()
            db.refresh(reconciled_subject)
            return _serialize_tracked_subject(db, reconciled_subject, include_activity_summary=False)
    else:
        if value is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing tracking value")
        normalized_value = _normalize_tracked_value(payload.entity_type, value)

    existing = db.scalar(
        select(NetworkTrackedSubject).where(
            NetworkTrackedSubject.entity_type == payload.entity_type,
            NetworkTrackedSubject.normalized_value == normalized_value,
        )
    )
    if existing is not None:
        if payload.label is not None:
            existing.label = payload.label or None
        if payload.notes is not None:
            existing.notes = payload.notes or None
        existing.is_active = True
        if device is not None:
            existing.device_id = device.id
            existing.value = device.ip_address
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return _serialize_tracked_subject(db, existing, include_activity_summary=False)

    subject = NetworkTrackedSubject(
        entity_type=payload.entity_type,
        normalized_value=normalized_value or "",
        value=value or "",
        label=payload.label or None,
        notes=payload.notes or None,
        is_active=True,
        device_id=device.id if device is not None else None,
        created_by_user_id=current_user.id,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return _serialize_tracked_subject(db, subject, include_activity_summary=False)


@router.patch("/tracking/{subject_id}", response_model=NetworkTrackedSubjectResponse)
def patch_tracked_subject(
    subject_id: int,
    payload: NetworkTrackedSubjectUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkTrackedSubjectResponse:
    _require_network_module(current_user)
    subject = db.get(NetworkTrackedSubject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tracked subject not found")
    updates = payload.model_dump(exclude_unset=True)
    for field_name, field_value in updates.items():
        setattr(subject, field_name, field_value)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return _serialize_tracked_subject(db, subject, include_activity_summary=False)


@router.get("/tracking/{subject_id}/activities", response_model=NetworkTrackedSubjectActivitySummary)
def get_tracked_subject_activities(
    subject_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    window_hours: int = Query(default=168, ge=1, le=24 * 30),
    limit: int = Query(default=25, ge=1, le=200),
) -> NetworkTrackedSubjectActivitySummary:
    _require_network_module(current_user)
    subject = db.get(NetworkTrackedSubject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tracked subject not found")
    return _build_tracked_subject_activity_summary(db, subject, window_hours=window_hours, limit=limit)


@router.get("/detection-watchlist", response_model=list[NetworkDetectionWatchlistRuleRead])
def get_detection_watchlist(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NetworkDetectionWatchlistRuleRead]:
    _require_network_module(current_user)
    _ensure_detection_watchlist_seeded(db)
    items = db.scalars(
        select(NetworkDetectionWatchlist).order_by(
            NetworkDetectionWatchlist.category.asc(),
            NetworkDetectionWatchlist.match_type.asc(),
            NetworkDetectionWatchlist.pattern.asc(),
        )
    ).all()
    return [NetworkDetectionWatchlistRuleRead.model_validate(item) for item in items]


@router.post("/detection-watchlist", response_model=NetworkDetectionWatchlistRuleRead, status_code=status.HTTP_201_CREATED)
def create_detection_watchlist_rule(
    payload: NetworkDetectionWatchlistRuleCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkDetectionWatchlistRuleRead:
    _require_network_module(current_user)
    _ensure_detection_watchlist_seeded(db)
    normalized_pattern = payload.pattern.strip().lower()
    existing = db.scalar(
        select(NetworkDetectionWatchlist).where(
            NetworkDetectionWatchlist.category == payload.category,
            NetworkDetectionWatchlist.rule_mode == payload.rule_mode,
            NetworkDetectionWatchlist.match_type == payload.match_type,
            NetworkDetectionWatchlist.pattern == normalized_pattern,
        )
    )
    if existing is not None:
        existing.label = payload.label or existing.label
        existing.notes = payload.notes or existing.notes
        existing.is_active = payload.is_active
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return NetworkDetectionWatchlistRuleRead.model_validate(existing)

    item = NetworkDetectionWatchlist(
        category=payload.category,
        rule_mode=payload.rule_mode,
        match_type=payload.match_type,
        pattern=normalized_pattern,
        label=payload.label,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return NetworkDetectionWatchlistRuleRead.model_validate(item)


@router.patch("/detection-watchlist/{rule_id}", response_model=NetworkDetectionWatchlistRuleRead)
def patch_detection_watchlist_rule(
    rule_id: int,
    payload: NetworkDetectionWatchlistRuleUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkDetectionWatchlistRuleRead:
    _require_network_module(current_user)
    item = db.get(NetworkDetectionWatchlist, rule_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist rule not found")
    updates = payload.model_dump(exclude_unset=True)
    for field_name, field_value in updates.items():
        setattr(item, field_name, field_value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return NetworkDetectionWatchlistRuleRead.model_validate(item)


@router.get("/vpn-bypass/summary", response_model=NetworkVpnBypassSummary)
def get_vpn_bypass_summary(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    window_hours: int = Query(default=168, ge=1, le=24 * 30),
) -> NetworkVpnBypassSummary:
    _require_network_module(current_user)
    _ensure_detection_watchlist_seeded(db)
    subjects = get_tracked_subjects(
        current_user=current_user,
        db=db,
        include_inactive=False,
        include_inferred=True,
        window_hours=window_hours,
        search=None,
        entity_type=None,
    )
    suspicious_subjects = 0
    vpn_subjects = 0
    proxy_subjects = 0
    tor_subjects = 0
    encrypted_dns_subjects = 0
    total_suspicious_events = 0
    for subject in subjects:
        activity = subject.activity_summary or NetworkTrackedSubjectActivitySummary(window_hours=window_hours)
        if activity.suspicious_events > 0:
            suspicious_subjects += 1
            total_suspicious_events += activity.suspicious_events
        if activity.vpn_suspected_events > 0:
            vpn_subjects += 1
        if activity.proxy_suspected_events > 0:
            proxy_subjects += 1
        if activity.tor_suspected_events > 0:
            tor_subjects += 1
        if activity.encrypted_dns_events > 0:
            encrypted_dns_subjects += 1

    open_alerts = db.scalar(
        select(func.count()).select_from(NetworkAlert).where(
            NetworkAlert.status == "open",
            NetworkAlert.alert_type.in_([
                "VPN_BYPASS_SUSPECTED",
                "VPN_BYPASS_TRANSIENT_DEVICE",
                "ARP_EPHEMERAL_DEVICE",
                "ARP_MAC_CHANGE_SUSPECTED",
                "ARP_IP_ROTATION_SUSPECTED",
            ]),
        )
    ) or 0
    transient_device_alerts = db.scalar(
        select(func.count()).select_from(NetworkAlert).where(
            NetworkAlert.status == "open",
            NetworkAlert.alert_type == "VPN_BYPASS_TRANSIENT_DEVICE",
        )
    ) or 0
    arp_ephemeral_alerts = db.scalar(
        select(func.count()).select_from(NetworkAlert).where(
            NetworkAlert.status == "open",
            NetworkAlert.alert_type == "ARP_EPHEMERAL_DEVICE",
        )
    ) or 0
    arp_identity_alerts = db.scalar(
        select(func.count()).select_from(NetworkAlert).where(
            NetworkAlert.status == "open",
            NetworkAlert.alert_type == "ARP_MAC_CHANGE_SUSPECTED",
        )
    ) or 0
    arp_spoofing_alerts = db.scalar(
        select(func.count()).select_from(NetworkAlert).where(
            NetworkAlert.status == "open",
            NetworkAlert.alert_type == "ARP_IP_ROTATION_SUSPECTED",
        )
    ) or 0
    watchlist_rules = db.scalar(select(func.count()).select_from(NetworkDetectionWatchlist)) or 0
    return NetworkVpnBypassSummary(
        total_subjects=suspicious_subjects,
        vpn_subjects=vpn_subjects,
        proxy_subjects=proxy_subjects,
        tor_subjects=tor_subjects,
        encrypted_dns_subjects=encrypted_dns_subjects,
        total_suspicious_events=total_suspicious_events,
        open_alerts=open_alerts,
        transient_device_alerts=transient_device_alerts,
        arp_ephemeral_alerts=arp_ephemeral_alerts,
        arp_identity_alerts=arp_identity_alerts,
        arp_spoofing_alerts=arp_spoofing_alerts,
        watchlist_rules=watchlist_rules,
    )


@router.get("/vpn-bypass/arp-timeline", response_model=list[NetworkArpTimelineItem])
def get_vpn_bypass_arp_timeline(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    window_hours: int = Query(default=168, ge=1, le=24 * 30),
    limit: int = Query(default=12, ge=1, le=50),
) -> list[NetworkArpTimelineItem]:
    _require_network_module(current_user)
    return _build_arp_timeline(db, window_hours=window_hours, limit=limit)


@router.get("/alerts", response_model=list[NetworkAlertResponse])
def get_alerts(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
) -> list[NetworkAlertResponse]:
    _require_network_module(current_user)
    return [_serialize_alert(item) for item in list_network_alerts(db, status_filter, severity)]


@router.get("/firewalls", response_model=list[NetworkFirewallResponse])
def get_firewalls(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NetworkFirewallResponse]:
    _require_network_module(current_user)
    return [_serialize_firewall(item) for item in list_network_firewalls(db)]


@router.get("/sophos-config", response_model=NetworkSophosConfigRead)
def get_sophos_config(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkSophosConfigRead:
    _require_network_module(current_user)
    return _serialize_sophos_config(get_or_create_sophos_config(db))


@router.put("/sophos-config", response_model=NetworkSophosConfigRead)
def put_sophos_config(
    payload: NetworkSophosConfigUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, Depends(require_role("super_admin", "admin"))],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkSophosConfigRead:
    _require_network_module(current_user)
    config = get_or_create_sophos_config(db)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(config, field, value)
    config.updated_at = datetime.now(UTC)
    config.updated_by_user_id = current_user.id
    db.add(config)
    db.commit()
    db.refresh(config)
    clear_sophos_runtime_policy_cache()
    return _serialize_sophos_config(config)


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


@router.get("/firewalls/{firewall_id}/log-coverage", response_model=NetworkFirewallLogCoverageSummary)
def get_firewall_log_coverage(
    firewall_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    window_hours: int = Query(default=168, ge=1, le=24 * 30),
) -> NetworkFirewallLogCoverageSummary:
    _require_network_module(current_user)
    firewall = db.get(NetworkFirewall, firewall_id)
    if firewall is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firewall not found")
    return _build_firewall_log_coverage_summary(db, firewall=firewall, window_hours=window_hours)


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
    assigned_to_user_id = payload.assigned_to_user_id
    if assigned_to_user_id is not None:
        assigned_user = db.get(ApplicationUser, assigned_to_user_id)
        if assigned_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found")
    alert = update_network_alert(
        db,
        alert_id,
        status=payload.status,
        assigned_to_user_id=assigned_to_user_id,
        verification_status=payload.verification_status,
        verification_notes=payload.verification_notes,
    )
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return _serialize_alert(alert)


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
    _require_network_module(current_user)
    request_payload = payload or NetworkScanTriggerRequest()
    result = run_network_scan(
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
