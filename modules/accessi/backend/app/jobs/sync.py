from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import random
import time

from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.sync import SyncApplyResponse
from app.services.nas_connector import NasConnectorError, NasSSHClient
from app.services.sync import apply_live_sync
from app.services.sync_runs import create_sync_run


@dataclass
class LiveSyncJobResult:
    attempts_used: int
    sync_result: SyncApplyResponse


def compute_retry_delay(attempt: int) -> float:
    base_delay = float(settings.sync_live_retry_delay_seconds)
    if settings.sync_live_backoff_mode == "exponential":
        delay = base_delay * (settings.sync_live_backoff_multiplier ** max(attempt - 1, 0))
    else:
        delay = base_delay
    capped_delay = min(delay, float(settings.sync_live_backoff_max_delay_seconds))
    if not settings.sync_live_backoff_jitter_enabled:
        return capped_delay

    jitter_span = capped_delay * float(settings.sync_live_backoff_jitter_ratio)
    lower_bound = max(0.0, capped_delay - jitter_span)
    upper_bound = capped_delay + jitter_span
    return random.uniform(lower_bound, upper_bound)


def run_scheduled_live_sync_cycle(
    db: Session,
    client: NasSSHClient | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> LiveSyncJobResult:
    return run_live_sync_job(
        db,
        client=client,
        trigger_type="scheduled",
        initiated_by="system",
        source_label="scheduler:ssh",
        sleep_fn=sleep_fn,
    )


def run_live_sync_job(
    db: Session,
    client: NasSSHClient | None = None,
    trigger_type: str = "job",
    initiated_by: str | None = None,
    source_label: str | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> LiveSyncJobResult:
    last_error: NasConnectorError | None = None
    started_at = time.monotonic()
    started_wall_clock = datetime.now(timezone.utc)

    for attempt in range(1, settings.sync_live_max_attempts + 1):
        try:
            sync_result = apply_live_sync(db, client)
            create_sync_run(
                db,
                mode="live",
                trigger_type=trigger_type,
                status="succeeded",
                attempts_used=attempt,
                snapshot_id=sync_result.snapshot_id,
                duration_ms=int((time.monotonic() - started_at) * 1000),
                initiated_by=initiated_by,
                source_label=source_label or "ssh",
                started_at=started_wall_clock,
                completed_at=datetime.now(timezone.utc),
            )
            return LiveSyncJobResult(attempts_used=attempt, sync_result=sync_result)
        except NasConnectorError as exc:
            last_error = exc
            if attempt >= settings.sync_live_max_attempts:
                break
            sleep_fn(compute_retry_delay(attempt))

    assert last_error is not None
    create_sync_run(
        db,
        mode="live",
        trigger_type=trigger_type,
        status="failed",
        attempts_used=settings.sync_live_max_attempts,
        duration_ms=int((time.monotonic() - started_at) * 1000),
        initiated_by=initiated_by,
        source_label=source_label or "ssh",
        error_detail=str(last_error),
        started_at=started_wall_clock,
        completed_at=datetime.now(timezone.utc),
    )
    raise last_error
