from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import re
import shlex
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.network.models import NetworkAlert, NetworkDevice, NetworkFirewall, NetworkFirewallEvent

UTC = timezone.utc
_KV_PATTERN = re.compile(r"([A-Za-z0-9_]+)=(\".*?\"|'.*?'|\S+)")
_SEVERITY_WEIGHTS = {"info": 0, "warning": 1, "danger": 2, "critical": 3}
_SYSLOG_PREFIX_PATTERN = re.compile(
    r"^(?:<\d+>)?(?:\d{4}-\d{2}-\d{2}T[^\s]+\s+|\w{3}\s+\d{1,2}\s+\d\d:\d\d:\d\d\s+)?(?P<host>\S+)\s+(?P<body>.*)$"
)

logger = logging.getLogger(__name__)


def _safe_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _json_dumps(value: dict[str, Any] | None) -> str | None:
    if not value:
        return None
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def parse_sophos_syslog_message(message: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for key, raw_value in _KV_PATTERN.findall(message):
        value = raw_value
        if value[:1] in {'"', "'"} and value[-1:] == value[:1]:
            try:
                value = shlex.split(value)[0]
            except ValueError:
                value = value[1:-1]
        parsed[key] = value
    return parsed


def strip_syslog_prefix(message: str) -> tuple[str, str | None]:
    raw_message = message.strip()
    if not raw_message:
        return "", None

    if "log_type=" in raw_message:
        marker_index = raw_message.find("log_type=")
        prefix = raw_message[:marker_index].strip()
        body = raw_message[marker_index:].strip()
        host = prefix.split()[-1] if prefix else None
        return body, host

    match = _SYSLOG_PREFIX_PATTERN.match(raw_message)
    if match:
        return match.group("body").strip(), match.group("host")

    return raw_message, None


def _normalize_severity(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"critical", "alert", "emergency"}:
        return "critical"
    if normalized in {"error", "danger"}:
        return "danger"
    if normalized in {"warning", "warn"}:
        return "warning"
    return "info"


def _infer_event_type(payload: dict[str, str]) -> str:
    parts = [
        _safe_text(payload.get("log_type")),
        _safe_text(payload.get("log_component")),
        _safe_text(payload.get("log_subtype")),
    ]
    event_type = ".".join(part.lower().replace(" ", "_") for part in parts if part)
    return event_type or "sophos.syslog"


def _find_network_device(db: Session, *, src_ip: str | None, dst_ip: str | None) -> NetworkDevice | None:
    candidates = [ip for ip in (src_ip, dst_ip) if ip]
    if not candidates:
        return None
    return db.scalar(
        select(NetworkDevice).where(or_(NetworkDevice.ip_address.in_(candidates), NetworkDevice.dns_name.in_(candidates))).limit(1)
    )


def upsert_network_firewall(
    db: Session,
    *,
    vendor: str,
    name: str,
    management_ip: str | None = None,
    model_name: str | None = None,
    serial_number: str | None = None,
    metadata_sources: dict[str, Any] | None = None,
    seen_at: datetime | None = None,
) -> NetworkFirewall:
    match_conditions = [NetworkFirewall.name == name]
    if management_ip:
        match_conditions.append(NetworkFirewall.management_ip == management_ip)
    if serial_number:
        match_conditions.append(NetworkFirewall.serial_number == serial_number)

    firewall = db.scalar(
        select(NetworkFirewall).where(
            NetworkFirewall.vendor == vendor,
            or_(*match_conditions),
        )
    )
    observed_at = _coerce_utc(seen_at) or datetime.now(UTC)
    if firewall is None:
        firewall = NetworkFirewall(
            vendor=vendor,
            name=name,
            management_ip=management_ip,
            model_name=model_name,
            serial_number=serial_number,
            metadata_sources=_json_dumps(metadata_sources),
            status="online",
            last_seen_at=observed_at,
        )
        db.add(firewall)
        db.flush()
        return firewall

    firewall.name = name or firewall.name
    firewall.management_ip = management_ip or firewall.management_ip
    firewall.model_name = model_name or firewall.model_name
    firewall.serial_number = serial_number or firewall.serial_number
    merged_metadata = _json_loads(firewall.metadata_sources)
    if metadata_sources:
        merged_metadata.update(metadata_sources)
    firewall.metadata_sources = _json_dumps(merged_metadata) or firewall.metadata_sources
    firewall.status = "online"
    firewall.last_seen_at = observed_at
    db.add(firewall)
    db.flush()
    return firewall


def ingest_sophos_syslog(
    db: Session,
    *,
    message: str,
    firewall_id: int | None = None,
    firewall_name: str | None = None,
    management_ip: str | None = None,
    observed_at: datetime | None = None,
) -> NetworkFirewallEvent:
    normalized_message, syslog_host = strip_syslog_prefix(message)
    parsed = parse_sophos_syslog_message(normalized_message)
    firewall = db.get(NetworkFirewall, firewall_id) if firewall_id is not None else None
    if firewall is None:
        inferred_name = firewall_name or parsed.get("device_name") or parsed.get("device_id") or "Sophos Firewall"
        firewall = upsert_network_firewall(
            db,
            vendor="Sophos",
            name=inferred_name,
            management_ip=management_ip or syslog_host or parsed.get("host") or parsed.get("device_id"),
            model_name=parsed.get("device_model"),
            serial_number=parsed.get("device_serial_id"),
            metadata_sources={"ingest": "syslog", "parser": "sophos"},
            seen_at=observed_at,
        )

    src_ip = parsed.get("src_ip")
    dst_ip = parsed.get("dst_ip")
    severity = _normalize_severity(parsed.get("priority"))
    event_type = _infer_event_type(parsed)
    device = _find_network_device(db, src_ip=src_ip, dst_ip=dst_ip)
    event = NetworkFirewallEvent(
        firewall_id=firewall.id,
        device_id=device.id if device else None,
        source="sophos_syslog",
        event_type=event_type,
        severity=severity,
        log_id=parsed.get("log_id"),
        message=_safe_text(parsed.get("message")) or _safe_text(normalized_message),
        src_ip=src_ip,
        dst_ip=dst_ip,
        protocol=parsed.get("protocol"),
        raw_payload=_json_dumps({"raw": message, "normalized": normalized_message, "parsed": parsed}),
        observed_at=_coerce_utc(observed_at) or datetime.now(UTC),
    )
    db.add(event)
    db.flush()

    if severity in {"danger", "critical"}:
        existing_alert = db.scalar(
            select(NetworkAlert).where(
                NetworkAlert.scan_id.is_(None),
                NetworkAlert.device_id == (device.id if device else None),
                NetworkAlert.alert_type == "FIREWALL_EVENT",
                NetworkAlert.status == "open",
                NetworkAlert.title == f"Evento firewall {severity}: {event_type}",
            )
        )
        if existing_alert is None:
            db.add(
                NetworkAlert(
                    device_id=device.id if device else None,
                    scan_id=None,
                    alert_type="FIREWALL_EVENT",
                    severity="danger" if severity == "danger" else "critical",
                    status="open",
                    title=f"Evento firewall {severity}: {event_type}",
                    message=event.message,
                )
            )

    firewall.last_seen_at = event.observed_at
    firewall.status = "online"
    db.add(firewall)
    db.commit()
    db.refresh(event)
    return event


def list_network_firewalls(db: Session) -> list[NetworkFirewall]:
    return db.scalars(select(NetworkFirewall).order_by(NetworkFirewall.vendor.asc(), NetworkFirewall.name.asc())).all()


def list_network_firewall_events(
    db: Session,
    *,
    firewall_id: int,
    severity: str | None = None,
    limit: int = 100,
) -> list[NetworkFirewallEvent]:
    query = select(NetworkFirewallEvent).where(NetworkFirewallEvent.firewall_id == firewall_id)
    if severity:
        query = query.where(NetworkFirewallEvent.severity == severity)
    return db.scalars(query.order_by(NetworkFirewallEvent.observed_at.desc(), NetworkFirewallEvent.id.desc()).limit(limit)).all()
