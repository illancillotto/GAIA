from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.application_user import ApplicationUser
from app.modules.inaz.models import InazSyncJob
from app.modules.inaz.services.credentials import mark_credential_error, mark_credential_used, pick_credential
from app.modules.inaz.services.import_jobs import run_import_job
from app.modules.inaz.services.live_login import run_scrape_with_credentials
from app.modules.inaz.services.parser import load_json_payload, parse_import_payload
from app.modules.inaz.services.sync_runtime import get_sync_artifact_dir

CURRENT_JOB_ID: str | None = None


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

        job.status = "running"
        job.started_at = datetime.now(UTC)
        job.worker_pid = os.getpid()
        job.worker_log_path = str(artifact_dir / "worker.log")
        job.json_artifact_path = str(json_output)
        job.attempt_count += 1
        db.add(job)
        db.commit()

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
                )
                mark_credential_used(db, credential.id, scrape_result.get("authenticated_url"))
            except Exception as exc:
                mark_credential_error(db, credential.id, str(exc))
                raise
        else:
            command = [
                settings.inaz_scraper_python_path,
                "-m",
                "inaz_scraper.collaborators",
                "--cdp-endpoint",
                str(params.get("cdp_endpoint") or settings.inaz_scraper_cdp_endpoint),
                "--year",
                str(job.period_start.year),
                "--month",
                str(job.period_start.month),
                "--json-output",
                str(json_output),
                "--start-date",
                job.period_start.isoformat(),
                "--end-date",
                job.period_end.isoformat(),
            ]
            if job.collaborator_limit is not None:
                command.extend(["--limit", str(job.collaborator_limit)])

            scraper_env = os.environ.copy()
            scraper_pythonpath = scraper_env.get("PYTHONPATH", "")
            scraper_src = str(Path(settings.inaz_scraper_project_path).expanduser() / "src")
            scraper_env["PYTHONPATH"] = scraper_src if not scraper_pythonpath else f"{scraper_src}:{scraper_pythonpath}"

            completed = subprocess.run(
                command,
                cwd=settings.inaz_scraper_project_path,
                env=scraper_env,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.stdout:
                print(completed.stdout, end="")
            if completed.stderr:
                print(completed.stderr, end="", file=sys.stderr)
            if completed.returncode != 0:
                raise RuntimeError(f"Scraper exited with code {completed.returncode}")
            if not json_output.exists():
                raise RuntimeError(f"JSON artifact not produced: {json_output}")

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
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return 0
    except Exception as exc:
        rollback_db = SessionLocal()
        try:
            failed_job = rollback_db.get(InazSyncJob, args.job_id)
            if failed_job is not None and failed_job.status != "cancelled":
                failed_job.status = "failed"
                failed_job.error_detail = str(exc)
                failed_job.finished_at = datetime.now(UTC)
                rollback_db.add(failed_job)
                rollback_db.commit()
        finally:
            rollback_db.close()
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
