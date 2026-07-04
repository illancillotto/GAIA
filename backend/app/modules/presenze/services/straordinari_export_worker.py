from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.core.database import SessionLocal
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser  # noqa: F401
from app.modules.presenze.models import PresenzeSyncJob
from app.modules.presenze.services.straordinari_export_job import (
    StraordinariExportItem,
    generate_straordinari_export,
)
from app.modules.presenze.services.sync_runtime import get_sync_artifact_dir

CURRENT_JOB_ID: str | None = None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _mark_job_cancelled(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(PresenzeSyncJob, job_id)
        if job is None or job.status == "cancelled":
            return
        job.status = "cancelled"
        job.error_detail = "Export straordinari cancellato dall'utente"
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
    parser = argparse.ArgumentParser(description="Run a GAIA Presenze straordinari export job in a separate process.")
    parser.add_argument("--job-id", required=True)
    return parser.parse_args()


def _parse_period_start(raw_value: str | None) -> date:
    if not raw_value:
        raise RuntimeError("Missing period_start in export straordinari job params")
    return date.fromisoformat(raw_value)


def _parse_items(raw_items: list[dict[str, Any]] | None) -> list[StraordinariExportItem]:
    items: list[StraordinariExportItem] = []
    for raw_item in raw_items or []:
        items.append(
            StraordinariExportItem(
                work_date=date.fromisoformat(str(raw_item["work_date"])),
                motivation=str(raw_item.get("motivation") or ""),
                start_time=str(raw_item["start_time"]) if raw_item.get("start_time") else None,
                end_time=str(raw_item["end_time"]) if raw_item.get("end_time") else None,
                duration_minutes=int(raw_item["duration_minutes"]),
            )
        )
    return items


def main() -> int:
    args = parse_args()
    global CURRENT_JOB_ID
    CURRENT_JOB_ID = args.job_id
    signal.signal(signal.SIGTERM, _handle_termination)
    signal.signal(signal.SIGINT, _handle_termination)
    db = SessionLocal()
    try:
        job = db.get(PresenzeSyncJob, args.job_id)
        if job is None:
            print(f"Presenze straordinari export job {args.job_id} not found", file=sys.stderr)
            return 2

        params = dict(job.params_json or {})
        if params.get("mode") != "export_straordinari_xlsx":
            raise RuntimeError("Unsupported job mode for straordinari export worker")

        artifact_dir = get_sync_artifact_dir(str(job.id))
        artifact_dir.mkdir(parents=True, exist_ok=True)
        progress_path = artifact_dir / "progress.json"
        summary_path = artifact_dir / "summary.json"
        output_path = artifact_dir / "straordinari.xlsx"

        job.status = "running"
        job.started_at = datetime.now(UTC)
        job.finished_at = None
        job.error_detail = None
        job.worker_pid = os.getpid()
        job.worker_log_path = str(artifact_dir / "worker.log")
        job.json_artifact_path = str(output_path)
        job.attempt_count += 1
        params["progress"] = {
            "state": "running",
            "job_id": str(job.id),
            "attempt_count": job.attempt_count,
            "started_at": job.started_at.isoformat(),
            "last_event": "worker_started",
            "last_event_at": datetime.now(UTC).isoformat(),
        }
        job.params_json = params
        db.add(job)
        db.commit()
        _write_json(progress_path, params["progress"])

        filename = generate_straordinari_export(
            collaborator_name=str(params.get("collaborator_name") or ""),
            period_start=_parse_period_start(params.get("period_start")),
            items=_parse_items(params.get("items")),
            template_path=params.get("template_path"),
            output_path=output_path,
        )

        finished_at = datetime.now(UTC)
        final_params = dict(job.params_json or {})
        final_params["output_filename"] = filename
        final_params["progress"] = {
            **dict(final_params.get("progress") or {}),
            "state": "completed",
            "finished_at": finished_at.isoformat(),
            "last_event": "job_completed",
            "last_event_at": finished_at.isoformat(),
        }
        job.status = "completed"
        job.finished_at = finished_at
        job.error_detail = None
        job.params_json = final_params
        db.add(job)
        db.commit()

        _write_json(progress_path, final_params["progress"])
        _write_json(
            summary_path,
            {
                "job_id": str(job.id),
                "status": job.status,
                "period_start": params.get("period_start"),
                "output_filename": filename,
                "collaborator_id": params.get("collaborator_id"),
                "collaborator_name": params.get("collaborator_name"),
                "items": len(params.get("items") or []),
            },
        )
        return 0
    except Exception as exc:
        rollback_db = SessionLocal()
        try:
            failed_job = rollback_db.get(PresenzeSyncJob, args.job_id)
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

                artifact_dir = get_sync_artifact_dir(str(failed_job.id))
                artifact_dir.mkdir(parents=True, exist_ok=True)
                _write_json(artifact_dir / "progress.json", failed_params["progress"])
                _write_json(
                    artifact_dir / "summary.json",
                    {
                        "job_id": str(failed_job.id),
                        "status": failed_job.status,
                        "error": str(exc),
                    },
                )
        finally:
            rollback_db.close()
        print(traceback.format_exc(), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
