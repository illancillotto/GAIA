from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.database import SessionLocal
from app.models.application_user import ApplicationUser
from app.modules.inaz.models import InazSyncJob
from app.modules.inaz.services.credentials import mark_credential_error, mark_credential_used, pick_credential
from app.modules.inaz.services.import_jobs import run_import_job
from app.modules.inaz.services.live_login import run_scrape_with_credentials
from app.modules.inaz.services.parser import load_json_payload, parse_import_payload
from app.modules.inaz.services.sync_runtime import get_sync_artifact_dir

CURRENT_JOB_ID: str | None = None


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _write_progress(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _mark_job_cancelled(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(InazSyncJob, job_id)
        if job is None or job.status == "cancelled":
            return
        job.status = "cancelled"
        job.error_detail = "Sync job cancelled by user"
        job.finished_at = datetime.now(UTC)
        db.add(job)
        db.commit()
    finally:
        db.close()


def _handle_termination(signum: int, _frame) -> None:
    if CURRENT_JOB_ID is not None:
        _mark_job_cancelled(CURRENT_JOB_ID)
    raise SystemExit(128 + signum)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a GAIA Inaz live sync job in a separate process.")
    parser.add_argument("--job-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    global CURRENT_JOB_ID
    CURRENT_JOB_ID = args.job_id
    signal.signal(signal.SIGTERM, _handle_termination)
    signal.signal(signal.SIGINT, _handle_termination)
    db = SessionLocal()
    try:
        job = db.get(InazSyncJob, args.job_id)
        if job is None:
            print(f"Inaz sync job {args.job_id} not found", file=sys.stderr)
            return 2

        artifact_dir = get_sync_artifact_dir(str(job.id))
        artifact_dir.mkdir(parents=True, exist_ok=True)
        json_output = artifact_dir / "inaz_collaboratori.json"
        progress_path = artifact_dir / "progress.json"
        events_path = artifact_dir / "events.ndjson"

        job.status = "running"
        job.started_at = datetime.now(UTC)
        job.finished_at = None
        job.error_detail = None
        job.worker_pid = os.getpid()
        job.worker_log_path = str(artifact_dir / "worker.log")
        job.json_artifact_path = str(json_output)
        job.attempt_count += 1
        base_params = dict(job.params_json or {})
        base_params["progress"] = {
            "state": "running",
            "job_id": str(job.id),
            "attempt_count": job.attempt_count,
            "started_at": job.started_at.isoformat(),
            "completed_collaborators": 0,
            "failed_collaborators": 0,
            "total_collaborators": None,
            "last_event": "worker_started",
            "last_event_at": datetime.now(UTC).isoformat(),
        }
        job.params_json = base_params
        db.add(job)
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
            db.add(job)
            db.commit()
            _write_progress(progress_path, progress)

        params = job.params_json or {}
        if job.credential_id is not None:
            current_user = db.get(ApplicationUser, job.requested_by_user_id)
            if current_user is None:
                raise RuntimeError("Requested by user not found for Inaz sync job")
            credential, password = pick_credential(db, current_user, job.credential_id)
            try:
                scrape_result = run_scrape_with_credentials(
                    username=credential.username,
                    password=password,
                    period_start=job.period_start,
                    period_end=job.period_end,
                    json_output=json_output,
                    limit=job.collaborator_limit,
                    progress_callback=on_progress,
                )
                mark_credential_used(db, credential.id, scrape_result.get("authenticated_url"))
            except Exception as exc:
                mark_credential_error(db, credential.id, str(exc))
                raise
        else:
            raise RuntimeError("Legacy Inaz sync mode is disabled. Create a new sync job with a saved credential.")

        parsed = parse_import_payload(load_json_payload(json_output.read_bytes()))
        import_result = run_import_job(
            db,
            parsed=parsed,
            requested_by_user_id=job.requested_by_user_id,
            filename=json_output.name,
            params_json={"format": "collaboratori-json", "source": "live-sync", "sync_job_id": str(job.id)},
        )

        job.import_job_id = import_result.job.id
        job.records_imported = import_result.job.records_imported
        job.records_skipped = import_result.job.records_skipped
        job.records_errors = import_result.job.records_errors
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
        }
        job.params_json = final_params
        db.add(job)
        db.commit()

        summary_path = artifact_dir / "summary.json"
        summary_path.write_text(
            json.dumps(
                {
                    "sync_job_id": str(job.id),
                    "import_job_id": str(import_result.job.id),
                    "status": job.status,
                    "records_imported": job.records_imported,
                    "records_skipped": job.records_skipped,
                    "records_errors": job.records_errors,
                    "completed_collaborators": scrape_result.get("completed_collaborators"),
                    "failed_collaborators": scrape_result.get("failed_collaborators"),
                    "total_collaborators": scrape_result.get("total_collaborators"),
                    "resumed_from_checkpoint": scrape_result.get("resumed_from_checkpoint"),
                    "error_items": scrape_result.get("errors"),
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
            },
        )
        _write_progress(progress_path, job.params_json["progress"])
        return 0
    except Exception as exc:
        rollback_db = SessionLocal()
        try:
            failed_job = rollback_db.get(InazSyncJob, args.job_id)
            if failed_job is not None and failed_job.status != "cancelled":
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
                rollback_db.add(failed_job)
                rollback_db.commit()
        finally:
            rollback_db.close()
        print(traceback.format_exc(), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
