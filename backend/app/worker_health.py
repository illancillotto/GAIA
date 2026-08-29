from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from collections.abc import Awaitable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar

HEARTBEAT_SCHEMA_VERSION = 1
DEFAULT_HEALTH_DIR = Path("/runtime-data/worker-health")
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 15.0
MAX_CLOCK_SKEW_SECONDS = 5.0
_SERVICE_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,127}")
_ResultT = TypeVar("_ResultT")


class HeartbeatError(RuntimeError):
    pass


def _validate_service_name(service: str) -> str:
    normalized = service.strip().lower()
    if _SERVICE_NAME_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"Invalid worker heartbeat service name: {service!r}")
    return normalized


def _health_directory() -> Path:
    configured = os.getenv("GAIA_WORKER_HEALTH_DIR", "").strip()
    return Path(configured) if configured else DEFAULT_HEALTH_DIR


@dataclass(frozen=True)
class WorkerHeartbeat:
    service: str
    details: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "service", _validate_service_name(self.service))

    @property
    def path(self) -> Path:
        return _health_directory() / f"{self.service}.json"

    def touch(
        self,
        *,
        status: str = "running",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        now = time.time()
        payload = {
            "schema_version": HEARTBEAT_SCHEMA_VERSION,
            "service": self.service,
            "status": status,
            "updated_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
            "updated_at_epoch": now,
            "pid": os.getpid(),
            "details": dict(self.details or {}) | dict(details or {}),
        }
        path = self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )
        temporary_path.replace(path)


def _load_heartbeat_payload(heartbeat: WorkerHeartbeat) -> dict[str, Any]:
    try:
        payload = json.loads(heartbeat.path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HeartbeatError(f"Heartbeat unavailable for {heartbeat.service}: {exc}") from exc
    if not isinstance(payload, dict):
        raise HeartbeatError(f"Heartbeat payload for {heartbeat.service} is not an object")
    return payload


def _heartbeat_timestamp(payload: dict[str, Any], heartbeat: WorkerHeartbeat) -> float:
    if payload.get("schema_version") != HEARTBEAT_SCHEMA_VERSION:
        raise HeartbeatError(f"Heartbeat schema mismatch for {heartbeat.service}")
    if payload.get("service") != heartbeat.service:
        raise HeartbeatError(f"Heartbeat service mismatch for {heartbeat.service}")
    if not isinstance(payload.get("status"), str) or not payload["status"]:
        raise HeartbeatError(f"Heartbeat status missing for {heartbeat.service}")
    updated_at_epoch = payload.get("updated_at_epoch")
    if not isinstance(updated_at_epoch, (int, float)) or isinstance(updated_at_epoch, bool):
        raise HeartbeatError(f"Heartbeat timestamp invalid for {heartbeat.service}")
    return float(updated_at_epoch)


def check_heartbeat(
    service: str,
    *,
    max_age_seconds: float,
    now: float | None = None,
) -> dict[str, Any]:
    if max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive")
    heartbeat = WorkerHeartbeat(service)
    payload = _load_heartbeat_payload(heartbeat)
    updated_at_epoch = _heartbeat_timestamp(payload, heartbeat)
    age_seconds = (time.time() if now is None else now) - float(updated_at_epoch)
    if age_seconds < -MAX_CLOCK_SKEW_SECONDS:
        raise HeartbeatError(f"Heartbeat timestamp is in the future for {heartbeat.service}")
    if age_seconds > max_age_seconds:
        raise HeartbeatError(
            f"Heartbeat stale for {heartbeat.service}: age={age_seconds:.1f}s "
            f"max={max_age_seconds:.1f}s"
        )
    return payload


async def _heartbeat_loop(
    heartbeat: WorkerHeartbeat,
    interval_seconds: float,
) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        heartbeat.touch()


async def run_with_heartbeat(
    operation: Awaitable[_ResultT],
    heartbeat: WorkerHeartbeat,
    *,
    interval_seconds: float = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
) -> _ResultT:
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")
    heartbeat.touch()
    heartbeat_task = asyncio.create_task(_heartbeat_loop(heartbeat, interval_seconds))
    try:
        return await operation
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a GAIA worker heartbeat")
    parser.add_argument("command", choices=("check",))
    parser.add_argument("--service", required=True)
    parser.add_argument("--max-age-seconds", required=True, type=float)
    args = parser.parse_args(argv)
    try:
        payload = check_heartbeat(
            args.service,
            max_age_seconds=args.max_age_seconds,
        )
    except (HeartbeatError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        f"heartbeat ok service={payload['service']} status={payload['status']} "
        f"updated_at={payload['updated_at']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
