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
    progress_callback: Callable[[str], None] | None = None,
) -> LiveSyncJobResult:
    return run_live_sync_job(
        db,
        client=client,
        trigger_type="scheduled",
        initiated_by="system",
        source_label="scheduler:ssh:quick",
        profile="quick",
        sleep_fn=sleep_fn,
        progress_callback=progress_callback,
    )


def run_live_sync_job(
    db: Session,
    client: NasSSHClient | None = None,
    trigger_type: str = "job",
    initiated_by: str | None = None,
    source_label: str | None = None,
    profile: str = "quick",
    sleep_fn: Callable[[float], None] = time.sleep,
    progress_callback: Callable[[str], None] | None = None,
) -> LiveSyncJobResult:
    last_error: NasConnectorError | None = None
    started_at = time.monotonic()
    started_wall_clock = datetime.now(timezone.utc)
    emit = progress_callback or (lambda _message: None)

    emit(
        "Starting NAS live sync "
        f"profile={profile} trigger={trigger_type} source={source_label or f'ssh:{profile}'} "
        f"max_attempts={settings.sync_live_max_attempts}"
    )

    for attempt in range(1, settings.sync_live_max_attempts + 1):
        try:
            emit(f"Attempt {attempt}/{settings.sync_live_max_attempts}: collecting NAS payload via SSH")
            sync_result = apply_live_sync(db, client, profile=profile)
            emit(
                "Attempt "
                f"{attempt}: sync payload persisted "
                f"snapshot_id={sync_result.snapshot_id} users={sync_result.persisted_users} "
                f"groups={sync_result.persisted_groups} shares={sync_result.persisted_shares} "
                f"acl_pairs={sync_result.share_acl_pairs_used}"
            )
            create_sync_run(
                db,
                mode="live",
                trigger_type=trigger_type,
                status="succeeded",
                attempts_used=attempt,
                snapshot_id=sync_result.snapshot_id,
                duration_ms=int((time.monotonic() - started_at) * 1000),
                initiated_by=initiated_by,
                source_label=source_label or f"ssh:{profile}",
                started_at=started_wall_clock,
                completed_at=datetime.now(timezone.utc),
            )
            emit(f"Sync completed successfully after {attempt} attempt(s)")
            return LiveSyncJobResult(attempts_used=attempt, sync_result=sync_result)
        except NasConnectorError as exc:
            last_error = exc
            emit(f"Attempt {attempt}/{settings.sync_live_max_attempts} failed: {exc}")
            if attempt >= settings.sync_live_max_attempts:
                break
            delay = compute_retry_delay(attempt)
            emit(f"Retry scheduled in {delay:.2f}s")
            sleep_fn(delay)

    assert last_error is not None
    create_sync_run(
        db,
        mode="live",
        trigger_type=trigger_type,
        status="failed",
        attempts_used=settings.sync_live_max_attempts,
        duration_ms=int((time.monotonic() - started_at) * 1000),
        initiated_by=initiated_by,
        source_label=source_label or f"ssh:{profile}",
        error_detail=str(last_error),
        started_at=started_wall_clock,
        completed_at=datetime.now(timezone.utc),
    )
    emit(f"Sync failed after {settings.sync_live_max_attempts} attempt(s): {last_error}")
    raise last_error
