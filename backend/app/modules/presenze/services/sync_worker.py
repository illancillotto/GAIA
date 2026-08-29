from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import PresenzeImportJob, PresenzeSyncJob
from app.modules.presenze.services.credentials import (
    mark_credential_error,
    mark_credential_used,
    pick_credential,
)
from app.modules.presenze.services.import_jobs import (
    create_import_job,
    finalize_import_job,
    import_collaborator_payload,
    parsed_collaborator_from_jsonable,
)
from app.modules.presenze.services.live_login import run_scrape_with_credentials
from app.modules.presenze.services.sync_runtime import (
    clear_sync_job_lease,
    get_sync_artifact_dir,
    prepare_sync_job_artifacts,
    touch_sync_job_lease,
)

CURRENT_JOB_ID: str | None = None
FAILED_EMPLOYEE_RETRY_TRIGGER = "auto_failed_employee_retry"


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _write_progress(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_completed_employee_codes(job: PresenzeSyncJob) -> list[str]:
    checkpoint = dict((job.params_json or {}).get("checkpoint") or {})
    completed = checkpoint.get("completed_employee_codes")
    if not isinstance(completed, list):
        return []
    return [str(item).strip() for item in completed if str(item).strip()]


def _load_target_employee_codes(job: PresenzeSyncJob) -> list[str]:
    values = (job.params_json or {}).get("employee_codes")
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        code = str(value).strip()
        if not code or code in seen:
            continue
        seen.add(code)
        normalized.append(code)
    return normalized


def _update_checkpoint(job: PresenzeSyncJob, *, employee_code: str | None = None) -> None:
    params = dict(job.params_json or {})
    checkpoint = dict(params.get("checkpoint") or {})
    completed = [str(item).strip() for item in checkpoint.get("completed_employee_codes", []) if str(item).strip()]
    if employee_code and employee_code not in completed:
        completed.append(employee_code)
    checkpoint["completed_employee_codes"] = completed
    checkpoint["completed_count"] = len(completed)
    checkpoint["last_completed_employee_code"] = employee_code or checkpoint.get("last_completed_employee_code")
    checkpoint["updated_at"] = datetime.now(UTC).isoformat()
    params["checkpoint"] = checkpoint
    job.params_json = params


def _failed_employee_codes(error_items: object) -> list[str]:
    if not isinstance(error_items, list):
        return []
    codes: list[str] = []
    seen: set[str] = set()
    for item in error_items:
        if not isinstance(item, dict):
            continue
        code = str(item.get("employee_code") or "").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        codes.append(code)
    return codes


def _failed_employee_retry_attempt(job: PresenzeSyncJob) -> int:
    params = job.params_json or {}
    value = params.get("failed_employee_retry_attempt")
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _should_enqueue_failed_employee_retry(job: PresenzeSyncJob, failed_codes: list[str]) -> bool:
    if not settings.presenze_auto_sync_failed_employee_retry_enabled:
        return False
    if not failed_codes:
        return False
    params = job.params_json or {}
    trigger = params.get("trigger")
    if trigger not in ("auto", FAILED_EMPLOYEE_RETRY_TRIGGER):
        return False
    return _failed_employee_retry_attempt(job) < settings.presenze_auto_sync_failed_employee_retry_max_attempts


def _enqueue_failed_employee_retry_jobs(
    db,
    *,
    source_job: PresenzeSyncJob,
    failed_codes: list[str],
) -> list[PresenzeSyncJob]:
    if not _should_enqueue_failed_employee_retry(source_job, failed_codes):
        return []
    if source_job.credential_id is None:
        return []

    source_params = dict(source_job.params_json or {})
    next_attempt = _failed_employee_retry_attempt(source_job) + 1
    batch_size = settings.presenze_auto_sync_failed_employee_retry_batch_size
    jobs: list[PresenzeSyncJob] = []
    for index in range(0, len(failed_codes), batch_size):
        batch = failed_codes[index : index + batch_size]
        params_json = {
            "auth_mode": "credential",
            "year": source_params.get("year") or source_job.period_end.year,
            "month": source_params.get("month") or source_job.period_end.month,
            "trigger": FAILED_EMPLOYEE_RETRY_TRIGGER,
            "retry_source": "failed_employee_codes",
            "parent_sync_job_id": str(source_job.id),
            "failed_employee_retry_attempt": next_attempt,
            "source_sync_group_id": source_params.get("sync_group_id"),
            "source_shard_index": source_params.get("shard_index"),
            "target_scope": source_params.get("target_scope"),
            "target_months": source_params.get("target_months"),
            "employee_codes": batch,
        }
        retry_job = PresenzeSyncJob(
            status="pending",
            requested_by_user_id=source_job.requested_by_user_id,
            credential_id=source_job.credential_id,
            period_start=source_job.period_start,
            period_end=source_job.period_end,
            collaborator_limit=len(batch),
            max_attempts=source_job.max_attempts,
            params_json=params_json,
        )
        db.add(retry_job)
        db.flush()
        prepare_sync_job_artifacts(retry_job)
        db.add(retry_job)
        jobs.append(retry_job)
    return jobs


def _handle_termination(signum: int, _frame) -> None:
    raise SystemExit(128 + signum)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a GAIA Presenze live sync job in a separate process.")
    parser.add_argument("--job-id", required=True)
    return parser.parse_args()


def _lease_token_matches(job: PresenzeSyncJob | None, claimed_lease_token: str | None) -> bool:
    return job is not None and (
        (job.lease_token is None and claimed_lease_token is None)
        or str(job.lease_token) == claimed_lease_token
    )


def _mark_failed_import_job(
    db: Session,
    failed_job: PresenzeSyncJob,
    error_detail: str,
) -> None:
    if failed_job.import_job_id is None:
        return
    import_job = db.get(PresenzeImportJob, failed_job.import_job_id)
    if import_job is None or import_job.status == "completed":
        return
    import_job.status = "failed"
    import_job.error_detail = error_detail
    import_job.finished_at = failed_job.finished_at
    db.add(import_job)


def _persist_sync_job_failure(
    job_id: str,
    claimed_lease_token: str | None,
    exc: Exception,
) -> None:
    rollback_db = SessionLocal()
    try:
        failed_job = rollback_db.get(PresenzeSyncJob, job_id)
        if not _lease_token_matches(failed_job, claimed_lease_token) or failed_job.status == "cancelled":
            return
        failed_job.status = "failed"
        failed_job.error_detail = str(exc)
        failed_job.finished_at = datetime.now(UTC)
        failed_params = dict(failed_job.params_json or {})
        failed_params["progress"] = {
            **dict(failed_params.get("progress") or {}),
            "state": "failed",
            "finished_at": failed_job.finished_at.isoformat(),
            "last_event": "job_failed",
            "last_event_at": datetime.now(UTC).isoformat(),
            "error": str(exc),
        }
        failed_job.params_json = failed_params
        clear_sync_job_lease(failed_job)
        rollback_db.add(failed_job)
        _mark_failed_import_job(rollback_db, failed_job, str(exc))
        rollback_db.commit()
    finally:
        rollback_db.close()


def _report_stale_sync_job_lease(db: Session, job_id: str) -> int:
    db.rollback()
    print(f"Presenze sync job {job_id} lost its lease fencing generation", file=sys.stderr)
    return 75


def _report_sync_job_failure(
    db: Session,
    job_id: str,
    claimed_lease_token: str | None,
    exc: Exception,
) -> int:
    db.rollback()
    _persist_sync_job_failure(job_id, claimed_lease_token, exc)
    print(traceback.format_exc(), file=sys.stderr)
    return 1


def run_job_by_id(job_id: str) -> int:
    db = SessionLocal()
    claimed_lease_token: str | None = None
    try:
        job = db.get(PresenzeSyncJob, job_id)
        if job is None:
            print(f"Presenze sync job {job_id} not found", file=sys.stderr)
            return 2
        claimed_lease_token = str(job.lease_token) if job.lease_token is not None else None

        artifact_dir = get_sync_artifact_dir(str(job.id))
        artifact_dir.mkdir(parents=True, exist_ok=True)
        json_output = artifact_dir / "presenze_collaboratori.json"
        progress_path = artifact_dir / "progress.json"
        events_path = artifact_dir / "events.ndjson"

        completed_employee_codes = _load_completed_employee_codes(job)
        target_employee_codes = _load_target_employee_codes(job)

        job.status = "running"
        job.started_at = datetime.now(UTC)
        job.finished_at = None
        job.error_detail = None
        job.worker_pid = os.getpid()
        job.worker_log_path = str(artifact_dir / "worker.log")
        job.json_artifact_path = str(json_output)
        if job.lease_token is None:
            job.attempt_count += 1
        base_params = dict(job.params_json or {})
        base_params["progress"] = {
            "state": "running",
            "job_id": str(job.id),
            "attempt_count": job.attempt_count,
            "started_at": job.started_at.isoformat(),
            "completed_collaborators": len(completed_employee_codes),
            "failed_collaborators": 0,
            "total_collaborators": None,
            "last_event": "worker_started",
            "last_event_at": datetime.now(UTC).isoformat(),
            "resumed": bool(completed_employee_codes),
            "pending_collaborators": None,
            "selected_employee_codes": target_employee_codes,
        }
        job.params_json = base_params
        touch_sync_job_lease(job)
        db.add(job)
        db.commit()

        import_job = db.get(PresenzeImportJob, job.import_job_id) if job.import_job_id is not None else None
        if import_job is None:
            placeholder_parsed = type(
                "SyncPlaceholderParsedPayload",
                (),
                {
                    "period_start": job.period_start,
                    "period_end": job.period_end,
                    "collaborators": [],
                    "errors": [],
                },
            )()
            import_job = create_import_job(
                db,
                parsed=placeholder_parsed,
                requested_by_user_id=job.requested_by_user_id,
                filename=json_output.name,
                params_json={"format": "collaboratori-json", "source": "live-sync", "sync_job_id": str(job.id)},
            )
            job.import_job_id = import_job.id
            touch_sync_job_lease(job)
            db.add(job)
            db.commit()
        else:
            import_job.status = "running"
            import_job.error_detail = None
            import_job.finished_at = None
            db.add(import_job)
            db.commit()

        _append_jsonl(
            events_path,
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "type": "worker_started",
                "job_id": str(job.id),
                "attempt_count": job.attempt_count,
            },
        )
        _write_progress(progress_path, job.params_json["progress"])

        def persist_timesheet(item: dict[str, Any]) -> None:
            payload = parsed_collaborator_from_jsonable(
                item,
                default_period_start=job.period_start,
                default_period_end=job.period_end,
            )
            import_collaborator_payload(db, payload=payload, job=import_job)
            employee_code = str(payload.collaborator.get("employee_code") or "").strip()
            _update_checkpoint(job, employee_code=employee_code or None)
            job.records_imported = import_job.records_imported
            job.records_skipped = import_job.records_skipped
            job.records_errors = import_job.records_errors
            touch_sync_job_lease(job)
            db.add(job)
            db.commit()

        def on_progress(event: dict[str, Any]) -> None:
            event_time = datetime.now(UTC).isoformat()
            event_payload = {"timestamp": event_time, **event}
            _append_jsonl(events_path, event_payload)

            progress = dict((job.params_json or {}).get("progress") or {})
            progress["state"] = "running"
            progress["job_id"] = str(job.id)
            progress["attempt_count"] = job.attempt_count
            progress["last_event"] = event.get("type")
            progress["last_event_at"] = event_time
            for key in (
                "index",
                "total",
                "employee_code",
                "name",
                "elapsed_seconds",
                "completed_collaborators",
                "error_count",
                "daily_rows",
                "summary_rows",
                "error",
                "resumed",
                "pending_collaborators",
            ):
                if key in event:
                    progress[key] = event[key]
            if "total" in event:
                progress["total_collaborators"] = event["total"]
            if "completed_collaborators" in event:
                progress["completed_collaborators"] = event["completed_collaborators"]
            if "error_count" in event:
                progress["failed_collaborators"] = event["error_count"]
                job.records_errors = int(event["error_count"])

            updated_params = dict(job.params_json or {})
            updated_params["progress"] = progress
            job.params_json = updated_params
            touch_sync_job_lease(job)
            db.add(job)
            db.commit()
            _write_progress(progress_path, progress)

        if job.credential_id is not None:
            current_user = db.get(ApplicationUser, job.requested_by_user_id)
            if current_user is None:
                raise RuntimeError("Requested by user not found for Presenze sync job")
            credential, password = pick_credential(db, current_user, job.credential_id)
            try:
                scrape_result = run_scrape_with_credentials(
                    username=credential.username,
                    password=password,
                    period_start=job.period_start,
                    period_end=job.period_end,
                    json_output=json_output,
                    limit=job.collaborator_limit,
                    employee_codes=target_employee_codes,
                    completed_employee_codes=completed_employee_codes,
                    progress_callback=on_progress,
                    completed_timesheet_callback=persist_timesheet,
                )
                mark_credential_used(db, credential.id, scrape_result.get("authenticated_url"))
            except Exception as exc:
                mark_credential_error(db, credential.id, str(exc))
                raise
        else:
            raise RuntimeError("Legacy Presenze sync mode is disabled. Create a new sync job with a saved credential.")

        finalize_import_job(db, job=import_job, status="completed")
        job.import_job_id = import_job.id
        job.records_imported = import_job.records_imported
        job.records_skipped = import_job.records_skipped
        job.records_errors = import_job.records_errors
        job.status = "completed"
        job.error_detail = None
        job.finished_at = datetime.now(UTC)
        final_params = dict(job.params_json or {})
        final_params["progress"] = {
            **dict(final_params.get("progress") or {}),
            "state": "completed",
            "finished_at": job.finished_at.isoformat(),
            "completed_collaborators": scrape_result.get("completed_collaborators"),
                    "failed_collaborators": scrape_result.get("failed_collaborators"),
                    "total_collaborators": scrape_result.get("total_collaborators"),
                    "last_event": "job_completed",
                    "last_event_at": datetime.now(UTC).isoformat(),
                    "selected_employee_codes": target_employee_codes,
                }
        job.params_json = final_params
        clear_sync_job_lease(job)
        db.add(job)
        db.commit()
        failed_employee_codes = _failed_employee_codes(scrape_result.get("errors"))
        retry_jobs = _enqueue_failed_employee_retry_jobs(
            db,
            source_job=job,
            failed_codes=failed_employee_codes,
        )
        if retry_jobs:
            retry_params = dict(job.params_json or {})
            retry_params["failed_employee_retry"] = {
                "queued_job_ids": [str(retry_job.id) for retry_job in retry_jobs],
                "employee_codes": failed_employee_codes,
                "queued_at": datetime.now(UTC).isoformat(),
            }
            job.params_json = retry_params
            db.add(job)
            db.commit()

        summary_path = artifact_dir / "summary.json"
        summary_path.write_text(
            json.dumps(
                {
                    "sync_job_id": str(job.id),
                    "import_job_id": str(import_job.id),
                    "status": job.status,
                    "records_imported": job.records_imported,
                    "records_skipped": job.records_skipped,
                    "records_errors": job.records_errors,
                    "completed_collaborators": scrape_result.get("completed_collaborators"),
                    "failed_collaborators": scrape_result.get("failed_collaborators"),
                    "total_collaborators": scrape_result.get("total_collaborators"),
                    "resumed_from_checkpoint": scrape_result.get("resumed_from_checkpoint"),
                    "error_items": scrape_result.get("errors"),
                    "failed_employee_retry_job_ids": [str(retry_job.id) for retry_job in retry_jobs],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        _append_jsonl(
            events_path,
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "type": "job_completed",
                "job_id": str(job.id),
                "records_imported": job.records_imported,
                "records_errors": job.records_errors,
                "failed_employee_retry_jobs": [str(retry_job.id) for retry_job in retry_jobs],
            },
        )
        _write_progress(progress_path, job.params_json["progress"])
        return 0
    except StaleDataError:
        return _report_stale_sync_job_lease(db, job_id)
    except Exception as exc:  # noqa: BLE001 - process boundary must persist every failure
        return _report_sync_job_failure(db, job_id, claimed_lease_token, exc)
    finally:
        db.close()


def main() -> int:
    args = parse_args()
    global CURRENT_JOB_ID
    CURRENT_JOB_ID = args.job_id
    signal.signal(signal.SIGTERM, _handle_termination)
    signal.signal(signal.SIGINT, _handle_termination)
    try:
        return run_job_by_id(args.job_id)
    finally:
        CURRENT_JOB_ID = None


if __name__ == "__main__":
    raise SystemExit(main())
