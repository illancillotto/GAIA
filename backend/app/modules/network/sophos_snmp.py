from __future__ import annotations

from datetime import datetime, timezone
import json
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.network.models import NetworkFirewall, NetworkFirewallMetric
from app.modules.network.sophos import _coerce_utc, _json_dumps, upsert_network_firewall
from app.modules.network.sophos_runtime import get_sophos_runtime_policy
from app.modules.network.services import CommunityData, ContextData, ObjectIdentity, ObjectType, SnmpEngine, UdpTransportTarget, get_cmd

UTC = timezone.utc

STANDARD_OIDS: list[dict[str, Any]] = [
    {"key": "sys_name", "oid": "1.3.6.1.2.1.1.5.0", "mode": "text"},
    {"key": "sys_descr", "oid": "1.3.6.1.2.1.1.1.0", "mode": "text"},
    {"key": "sys_uptime_ticks", "oid": "1.3.6.1.2.1.1.3.0", "mode": "int", "unit": "ticks"},
    {"key": "if_number", "oid": "1.3.6.1.2.1.2.1.0", "mode": "int", "unit": "count"},
]


def _normalize_severity(metric_key: str, metric_value: float | None) -> str:
    if metric_value is None:
        return "info"
    key = metric_key.lower()
    if "cpu" in key or "memory" in key or "disk" in key:
        if metric_value >= 90:
            return "critical"
        if metric_value >= 80:
            return "danger"
        if metric_value >= 70:
            return "warning"
    return "info"


def _load_custom_oids() -> list[dict[str, Any]]:
    try:
        raw = json.loads(settings.network_sophos_snmp_custom_oids)
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        oid = item.get("oid")
        if isinstance(key, str) and key.strip() and isinstance(oid, str) and oid.strip():
            result.append(
                {
                    "key": key.strip(),
                    "oid": oid.strip(),
                    "mode": item.get("mode") if isinstance(item.get("mode"), str) else "text",
                    "unit": item.get("unit") if isinstance(item.get("unit"), str) else None,
                }
            )
    return result


def _coerce_metric_value(raw_value: str, mode: str) -> tuple[float | None, str | None]:
    if mode == "text":
        return None, raw_value
    try:
        numeric = float(raw_value)
    except (TypeError, ValueError):
        return None, raw_value
    return numeric, None


async def _snmp_get_values_async(host: str, port: int, community: str, oids: list[dict[str, Any]]) -> dict[str, str]:
    if get_cmd is None or UdpTransportTarget is None:
        return {}
    transport = await UdpTransportTarget.create((host, port), timeout=3.0, retries=0)
    error_indication, error_status, _, var_binds = await get_cmd(
        SnmpEngine(),
        CommunityData(community, mpModel=1),
        transport,
        ContextData(),
        *[ObjectType(ObjectIdentity(item["oid"])) for item in oids],
    )
    if error_indication or error_status:
        return {}
    oid_map = {item["oid"]: item["key"] for item in oids}
    values: dict[str, str] = {}
    for name, value in var_binds:
        key = oid_map.get(str(name))
        if key:
            values[key] = str(value)
    return values


def _snmp_get_values(host: str, port: int, community: str, oids: list[dict[str, Any]]) -> dict[str, str]:
    if get_cmd is None:
        return {}
    try:
        import asyncio

        return asyncio.run(_snmp_get_values_async(host, port, community, oids))
    except Exception:
        return {}


def record_firewall_metric(
    db: Session,
    *,
    firewall_id: int,
    metric_key: str,
    metric_value: float | None = None,
    metric_text: str | None = None,
    unit: str | None = None,
    severity: str = "info",
    raw_payload: dict[str, Any] | None = None,
    observed_at: datetime | None = None,
) -> NetworkFirewallMetric:
    metric = NetworkFirewallMetric(
        firewall_id=firewall_id,
        metric_key=metric_key,
        metric_value=metric_value,
        metric_text=metric_text,
        unit=unit,
        severity=severity,
        raw_payload=_json_dumps(raw_payload),
        observed_at=_coerce_utc(observed_at) or datetime.now(UTC),
    )
    db.add(metric)
    db.flush()
    return metric


def poll_sophos_firewall_metrics(db: Session) -> list[NetworkFirewallMetric]:
    host = settings.network_sophos_snmp_host or settings.network_sophos_firewall_management_ip
    community = settings.network_sophos_snmp_community
    if not host or not community:
        return []

    oids = [*STANDARD_OIDS, *_load_custom_oids()]
    values = _snmp_get_values(host, settings.network_sophos_snmp_port, community, oids)
    if not values:
        return []

    firewall = upsert_network_firewall(
        db,
        vendor="Sophos",
        name=values.get("sys_name") or settings.network_sophos_firewall_default_name,
        management_ip=host,
        model_name=values.get("sys_descr"),
        metadata_sources={"ingest": "snmp", "community": community},
    )

    created: list[NetworkFirewallMetric] = []
    for oid_def in oids:
        key = oid_def["key"]
        if key not in values:
            continue
        metric_value, metric_text = _coerce_metric_value(values[key], oid_def.get("mode", "text"))
        created.append(
            record_firewall_metric(
                db,
                firewall_id=firewall.id,
                metric_key=key,
                metric_value=metric_value,
                metric_text=metric_text,
                unit=oid_def.get("unit"),
                severity=_normalize_severity(key, metric_value),
                raw_payload={"source": "snmp", "host": host, "oid": oid_def["oid"], "raw_value": values[key]},
            )
        )

    firewall.last_seen_at = datetime.now(UTC)
    firewall.status = "online"
    db.add(firewall)
    db.commit()
    return created


def list_network_firewall_metrics(
    db: Session,
    *,
    firewall_id: int,
    metric_key: str | None = None,
    limit: int = 100,
) -> list[NetworkFirewallMetric]:
    query = select(NetworkFirewallMetric).where(NetworkFirewallMetric.firewall_id == firewall_id)
    if metric_key:
        query = query.where(NetworkFirewallMetric.metric_key == metric_key)
    return db.scalars(query.order_by(NetworkFirewallMetric.observed_at.desc(), NetworkFirewallMetric.id.desc()).limit(limit)).all()


def run_sophos_snmp_poller() -> None:
    from app.core.database import SessionLocal

    interval = max(settings.network_sophos_snmp_interval_seconds, 30)
    while True:
        db = SessionLocal()
        try:
            policy = get_sophos_runtime_policy(db)
            if policy.snmp_should_poll:
                poll_sophos_firewall_metrics(db)
        finally:
            db.close()
        time.sleep(interval)
