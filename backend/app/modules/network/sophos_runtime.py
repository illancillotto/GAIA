from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_compat import UTC
from app.modules.network.models import NetworkSophosConfig

_CACHE_TTL_SECONDS = 30
_cache_lock = threading.Lock()
_cached_policy: "SophosRuntimePolicy | None" = None
_cached_at: datetime | None = None


@dataclass(frozen=True)
class SophosRuntimePolicy:
    syslog_enabled: bool
    snmp_enabled: bool
    operation_window_enabled: bool
    operation_start_hour: int
    operation_end_hour: int
    operation_timezone: str
    is_within_window: bool
    syslog_should_ingest: bool
    snmp_should_poll: bool
    evaluated_at: datetime


def _normalize_hour(value: int) -> int:
    return min(max(int(value), 0), 23)


def _normalize_timezone_name(value: str | None) -> str:
    candidate = (value or "").strip() or "Europe/Rome"
    try:
        ZoneInfo(candidate)
    except ZoneInfoNotFoundError:
        return "Europe/Rome"
    return candidate


def _is_within_window(*, start_hour: int, end_hour: int, current_hour: int) -> bool:
    if start_hour == end_hour:
        return True
    if start_hour < end_hour:
        return start_hour <= current_hour < end_hour
    return current_hour >= start_hour or current_hour < end_hour


def clear_sophos_runtime_policy_cache() -> None:
    global _cached_at, _cached_policy
    with _cache_lock:
        _cached_policy = None
        _cached_at = None


def get_or_create_sophos_config(db: Session) -> NetworkSophosConfig:
    config = db.get(NetworkSophosConfig, 1)
    if config is not None:
        return config

    config = NetworkSophosConfig(
        id=1,
        syslog_enabled=settings.network_sophos_syslog_enabled,
        snmp_enabled=settings.network_sophos_snmp_enabled,
        operation_window_enabled=True,
        operation_start_hour=19,
        operation_end_hour=4,
        operation_timezone="Europe/Rome",
    )
    db.add(config)
    db.flush()
    clear_sophos_runtime_policy_cache()
    return config


def build_sophos_runtime_policy(config: NetworkSophosConfig, *, now: datetime | None = None) -> SophosRuntimePolicy:
    evaluated_at = now.astimezone(UTC) if now is not None else datetime.now(UTC)
    timezone_name = _normalize_timezone_name(config.operation_timezone)
    local_now = evaluated_at.astimezone(ZoneInfo(timezone_name))
    start_hour = _normalize_hour(config.operation_start_hour)
    end_hour = _normalize_hour(config.operation_end_hour)
    is_within_window = (
        True
        if not config.operation_window_enabled
        else _is_within_window(start_hour=start_hour, end_hour=end_hour, current_hour=local_now.hour)
    )
    syslog_should_ingest = bool(config.syslog_enabled and is_within_window)
    snmp_should_poll = bool(config.snmp_enabled and is_within_window)
    return SophosRuntimePolicy(
        syslog_enabled=bool(config.syslog_enabled),
        snmp_enabled=bool(config.snmp_enabled),
        operation_window_enabled=bool(config.operation_window_enabled),
        operation_start_hour=start_hour,
        operation_end_hour=end_hour,
        operation_timezone=timezone_name,
        is_within_window=is_within_window,
        syslog_should_ingest=syslog_should_ingest,
        snmp_should_poll=snmp_should_poll,
        evaluated_at=evaluated_at,
    )


def get_sophos_runtime_policy(
    db: Session,
    *,
    now: datetime | None = None,
    force_refresh: bool = False,
) -> SophosRuntimePolicy:
    global _cached_at, _cached_policy
    current_time = now.astimezone(UTC) if now is not None else datetime.now(UTC)
    with _cache_lock:
        if (
            not force_refresh
            and _cached_policy is not None
            and _cached_at is not None
            and current_time - _cached_at < timedelta(seconds=_CACHE_TTL_SECONDS)
        ):
            return _cached_policy

    config = get_or_create_sophos_config(db)
    policy = build_sophos_runtime_policy(config, now=current_time)
    with _cache_lock:
        _cached_policy = policy
        _cached_at = current_time
    return policy
