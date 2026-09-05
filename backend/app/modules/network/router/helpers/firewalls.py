from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.datetime_compat import UTC
from app.modules.network.models import (
    NetworkAlert,
    NetworkFirewall,
    NetworkFirewallEvent,
)
from app.modules.network.router.helpers.endpoints import _resolve_firewall_event_endpoint_labels
from app.modules.network.router.helpers.tracking import (
    _extract_firewall_event_parsed,
    _find_tracked_subject,
    _get_active_tracked_subject_map,
)
from app.modules.network.schemas import (
    NetworkAlertResponse,
    NetworkFirewallEventResponse,
    NetworkFirewallLogCoverageSummary,
    NetworkFirewallLogFamilyStatus,
    NetworkFirewallMetricResponse,
    NetworkFirewallResponse,
    NetworkStatisticsCountItem,
)
from app.modules.network.services import (
    metadata_sources_to_dict,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

_EXPECTED_SOPHOS_LOG_FAMILIES: list[tuple[str, str]] = [
    ("firewall", "Firewall"),
    ("vpn", "VPN"),
    ("ips", "IPS"),
    ("authentication", "Authentication"),
    ("system", "System"),
]


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
    if event_type.startswith(("system_health.", "event.gui.")) or "system" in log_type or "system" in log_component:
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


# fmt: on
