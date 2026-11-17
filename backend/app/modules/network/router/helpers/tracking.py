import ipaddress
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.network.detection import default_watchlist_items, event_detection_tags
from app.modules.network.models import (
    NetworkDetectionWatchlist,
    NetworkDevice,
    NetworkFirewallEvent,
    NetworkScan,
    NetworkScanDevice,
    NetworkTrackedSubject,
)
from app.modules.network.router.helpers.arp_timeline import (
    _arp_rapid_reappearances as _arp_rapid_reappearances,
)
from app.modules.network.router.helpers.arp_timeline import (
    _arp_suspicious_reasons as _arp_suspicious_reasons,
)
from app.modules.network.router.helpers.arp_timeline import (
    _build_arp_timeline_item,
)
from app.modules.network.router.helpers.devices import _resolve_device_label
from app.modules.network.router.helpers.endpoints import (
    _extract_event_traffic,
    _resolve_firewall_event_endpoint_labels,
)
from app.modules.network.schemas import (
    NetworkArpTimelineItem,
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
        timeline.append(_build_arp_timeline_item(scope_key, items, devices_by_id, _resolve_device_label))

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
        return _normalize_tracked_domain(normalized)
    if entity_type == "url":
        if not normalized:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid URL value")
        return normalized
    return normalized


def _normalize_tracked_domain(normalized: str) -> str:
    parsed_hostname = urlparse(normalized).hostname if "://" in normalized else normalized
    hostname = (parsed_hostname or normalized).strip().rstrip(".").lower()
    if not hostname:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid domain value")
    return hostname


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
        _merge_legacy_tracked_subject_metadata(canonical, subject)
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


def _merge_legacy_tracked_subject_metadata(
    canonical: NetworkTrackedSubject, subject: NetworkTrackedSubject,
) -> None:
    if not canonical.label and subject.label:
        canonical.label = subject.label
    if not canonical.notes and subject.notes:
        canonical.notes = subject.notes
    canonical.is_active = canonical.is_active or subject.is_active


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
        return _match_tracked_device_event(subject, event)
    if subject.entity_type == "ip":
        return _match_tracked_ip_event(subject, event)
    if subject.entity_type == "domain":
        candidate = _tracked_event_domain(parsed)
        if candidate and candidate == subject.normalized_value:
            return "domain", candidate
        return None
    if subject.entity_type == "url":
        return _match_tracked_url_event(subject, parsed)
    return None


def _match_tracked_device_event(
    subject: NetworkTrackedSubject, event: NetworkFirewallEvent,
) -> tuple[str, str] | None:
    if subject.device_id and (event.device_id == subject.device_id or event.src_ip == subject.value or event.dst_ip == subject.value):
        return "device", subject.value
    return None


def _match_tracked_ip_event(
    subject: NetworkTrackedSubject, event: NetworkFirewallEvent,
) -> tuple[str, str] | None:
    if event.src_ip == subject.normalized_value:
        return "src_ip", subject.normalized_value
    if event.dst_ip == subject.normalized_value:
        return "dst_ip", subject.normalized_value
    return None


def _match_tracked_url_event(
    subject: NetworkTrackedSubject, parsed: dict[str, Any],
) -> tuple[str, str] | None:
    raw_url = parsed.get("url")
    if isinstance(raw_url, str) and raw_url.strip() == subject.normalized_value:
        return "url", raw_url.strip()
    return None


def _tracked_event_domain(parsed: dict[str, Any]) -> str | None:
    domain = parsed.get("domain")
    if isinstance(domain, str) and domain.strip():
        return domain.strip().lower()
    raw_url = parsed.get("url")
    if isinstance(raw_url, str) and raw_url.strip():
        return (urlparse(raw_url.strip()).hostname or "").lower()
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
    window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)  # noqa: UP017 - preserve legacy AST
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


# fmt: on
