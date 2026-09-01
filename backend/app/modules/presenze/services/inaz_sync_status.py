from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.presenze.models import PresenzeSyncJob

INAZ_SYNC_STATUSES = {"success", "running", "degraded", "error", "never"}


def build_presenze_snapshot_metadata(
    db: Session,
    *,
    rules_version: str,
    now: datetime | None,
    month: str | None = None,
    export_rules_version: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "source": "gaia",
        "rules_version": rules_version,
        "synced_from_gaia_at": _json_datetime(
            _as_utc(now) or datetime.now(timezone.utc)
        ),
        "inaz_sync": build_inaz_sync_status(db, month=month),
    }
    if month is not None:
        payload["month"] = month
    if export_rules_version is not None:
        payload["export_rules_version"] = export_rules_version
    return payload


def build_auto_retry_history_entry(job: Any, *, queued_at: datetime) -> dict[str, Any]:
    return {
        "queued_at": _json_datetime(_as_utc(queued_at)),
        "attempt_count": getattr(job, "attempt_count", None),
        "previous_status": getattr(job, "status", None),
        "previous_started_at": _json_datetime(
            _as_utc(getattr(job, "started_at", None))
        ),
        "previous_finished_at": _json_datetime(
            _as_utc(getattr(job, "finished_at", None))
        ),
        "previous_error": getattr(job, "error_detail", None),
    }


def build_inaz_sync_status(db: Session, *, month: str | None = None) -> dict[str, Any]:
    jobs = db.scalars(
        select(PresenzeSyncJob)
        .where(PresenzeSyncJob.credential_id.is_not(None))
        .order_by(PresenzeSyncJob.created_at.asc(), PresenzeSyncJob.id.asc())
    ).all()
    return resolve_inaz_sync_status(jobs, month=month)


def resolve_inaz_sync_status(
    jobs: Iterable[Any], *, month: str | None = None
) -> dict[str, Any]:
    period = _month_period(month) if month is not None else None
    relevant = [
        job for job in jobs if _is_live_sync(job) and _covers_period(job, period)
    ]
    attempted = [
        (attempt_at, job)
        for job in relevant
        if (attempt_at := _job_attempt_at(job)) is not None
    ]
    if not attempted:
        return _payload(status="never")

    last_attempt_at, latest_job = max(attempted, key=lambda item: item[0])
    cohorts = _cohorts(relevant)
    latest_cohort = cohorts[_cohort_key(latest_job)]
    last_success_at = _last_success_at(cohorts.values())
    status, error_code, error_message = _latest_cohort_state(
        latest_cohort, last_success_at=last_success_at
    )
    return _payload(
        status=status,
        last_attempt_at=last_attempt_at,
        last_success_at=last_success_at,
        data_updated_at=last_success_at,
        error_code=error_code,
        error_message=error_message,
    )


def _is_live_sync(job: Any) -> bool:
    if getattr(job, "credential_id", None) is None:
        return False
    params = getattr(job, "params_json", None) or {}
    return params.get("mode") in (None, "sync")


def _month_period(month: str) -> tuple[date, date]:
    year, month_number = (int(part) for part in month.split("-", maxsplit=1))
    start = date(year, month_number, 1)
    next_year = year + 1 if month_number == 12 else year
    next_month = 1 if month_number == 12 else month_number + 1
    end = date(next_year, next_month, 1)
    return start, date.fromordinal(end.toordinal() - 1)


def _covers_period(job: Any, period: tuple[date, date] | None) -> bool:
    if period is None:
        return True
    period_start, period_end = period
    job_start = getattr(job, "period_start", None)
    job_end = getattr(job, "period_end", None)
    return (
        isinstance(job_start, date)
        and isinstance(job_end, date)
        and job_start <= period_end
        and job_end >= period_start
    )


def _job_attempt_at(job: Any) -> datetime | None:
    started_at = _as_utc(getattr(job, "started_at", None))
    if started_at is not None:
        return started_at
    history = (getattr(job, "params_json", None) or {}).get("auto_retry_history")
    if not isinstance(history, list):
        return None
    for entry in reversed(history):
        if isinstance(entry, dict):
            previous_started_at = _parse_datetime(entry.get("previous_started_at"))
            if previous_started_at is not None:
                return previous_started_at
    return None


def _cohort_key(job: Any) -> str:
    params = getattr(job, "params_json", None) or {}
    group_id = params.get("sync_group_id") or params.get("source_sync_group_id")
    if group_id:
        return f"group:{group_id}"
    parent_id = params.get("parent_sync_job_id")
    if parent_id:
        return f"job:{parent_id}"
    return f"job:{getattr(job, 'id', id(job))}"


def _cohorts(jobs: Iterable[Any]) -> dict[str, list[Any]]:
    result: dict[str, list[Any]] = defaultdict(list)
    for job in jobs:
        result[_cohort_key(job)].append(job)
    return result


def _last_success_at(cohorts: Iterable[list[Any]]) -> datetime | None:
    successful_at: list[datetime] = []
    for cohort in cohorts:
        if not cohort or not all(_job_succeeded(job) for job in cohort):
            continue
        finished_at = [_as_utc(getattr(job, "finished_at", None)) for job in cohort]
        successful_at.append(max(value for value in finished_at if value is not None))
    return max(successful_at, default=None)


def _job_succeeded(job: Any) -> bool:
    if (
        getattr(job, "status", None) != "completed"
        or _as_utc(getattr(job, "finished_at", None)) is None
    ):
        return False
    if _non_negative_int(getattr(job, "records_errors", 0)) != 0:
        return False
    progress = (getattr(job, "params_json", None) or {}).get("progress") or {}
    return _non_negative_int(progress.get("failed_collaborators", 0)) == 0


def _latest_cohort_state(
    cohort: list[Any],
    *,
    last_success_at: datetime | None,
) -> tuple[str, str | None, str | None]:
    statuses = {str(getattr(job, "status", "")) for job in cohort}
    if "running" in statuses:
        return "running", None, None
    if statuses & {"failed", "cancelled"}:
        status = "degraded" if last_success_at is not None else "error"
        return (
            status,
            "inaz_sync_failed",
            "The latest INAZ synchronization attempt did not complete successfully.",
        )
    if all(_job_succeeded(job) for job in cohort):
        return "success", None, None
    if "completed" in statuses:
        return (
            "degraded",
            "inaz_sync_partial",
            "The latest INAZ synchronization completed with incomplete data.",
        )
    status = "degraded" if last_success_at is not None else "error"
    return (
        status,
        "inaz_sync_metadata_invalid",
        "The latest INAZ synchronization has incomplete status metadata.",
    )


def _non_negative_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return _as_utc(value)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return _as_utc(datetime.fromisoformat(value.strip().replace("Z", "+00:00")))
    except ValueError:
        return None


def _as_utc(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _json_datetime(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value is not None else None


def _payload(
    *,
    status: str,
    last_attempt_at: datetime | None = None,
    last_success_at: datetime | None = None,
    data_updated_at: datetime | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    if status not in INAZ_SYNC_STATUSES:
        raise ValueError(f"Unsupported INAZ sync status: {status}")
    return {
        "status": status,
        "last_attempt_at": _json_datetime(last_attempt_at),
        "last_success_at": _json_datetime(last_success_at),
        "data_updated_at": _json_datetime(data_updated_at),
        "error_code": error_code,
        "error_message": error_message,
    }
