from __future__ import annotations

import json
import runpy
import signal
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.core.database as core_database
import app.modules.presenze.services.sync_runtime as sync_runtime_module
from app.modules.presenze.services import sync_worker


class _FakeDb:
    def __init__(
        self,
        *,
        job: object | None = None,
        import_job: object | None = None,
        user: object | None = None,
    ) -> None:
        self.job = job
        self.import_job = import_job
        self.user = user
        self.added: list[object] = []
        self.commits = 0
        self.closed = False

    def get(self, model, key):
        if model is sync_worker.PresenzeSyncJob:
            return self.job
        if model is sync_worker.PresenzeImportJob:
            return self.import_job
        if model is sync_worker.ApplicationUser:
            return self.user
        return None

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        self.closed = True


def _make_job(**overrides):
    payload = {
        "id": "job-1",
        "status": "pending",
        "requested_by_user_id": 55,
        "credential_id": 9,
        "import_job_id": None,
        "period_start": date(2026, 6, 1),
        "period_end": date(2026, 6, 30),
        "collaborator_limit": 25,
        "records_imported": 0,
        "records_skipped": 0,
        "records_errors": 0,
        "error_detail": None,
        "worker_pid": None,
        "worker_log_path": None,
        "json_artifact_path": None,
        "attempt_count": 0,
        "params_json": None,
        "started_at": None,
        "finished_at": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def _make_import_job(**overrides):
    payload = {
        "id": "import-1",
        "status": "pending",
        "error_detail": None,
        "finished_at": None,
        "records_imported": 0,
        "records_skipped": 0,
        "records_errors": 0,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_append_jsonl_and_write_progress(tmp_path: Path) -> None:
    events_path = tmp_path / "events.ndjson"
    progress_path = tmp_path / "progress.json"

    sync_worker._append_jsonl(events_path, {"type": "started"})
    sync_worker._append_jsonl(events_path, {"type": "completed"})
    sync_worker._write_progress(progress_path, {"state": "running"})

    assert events_path.read_text(encoding="utf-8").splitlines() == [
        json.dumps({"type": "started"}, ensure_ascii=False),
        json.dumps({"type": "completed"}, ensure_ascii=False),
    ]
    assert json.loads(progress_path.read_text(encoding="utf-8")) == {"state": "running"}


def test_checkpoint_helpers_normalize_and_update_completed_codes() -> None:
    job = _make_job(
        params_json={
            "checkpoint": {
                "completed_employee_codes": [" A1 ", "", None, "B2"],
                "last_completed_employee_code": "B2",
            }
        }
    )

    assert sync_worker._load_completed_employee_codes(job) == ["A1", "None", "B2"]

    sync_worker._update_checkpoint(job, employee_code="C3")
    checkpoint = job.params_json["checkpoint"]

    assert checkpoint["completed_employee_codes"] == ["A1", "None", "B2", "C3"]
    assert checkpoint["completed_count"] == 4
    assert checkpoint["last_completed_employee_code"] == "C3"
    assert checkpoint["updated_at"]

    sync_worker._update_checkpoint(job, employee_code="C3")
    assert job.params_json["checkpoint"]["completed_employee_codes"] == ["A1", "None", "B2", "C3"]

    other_job = _make_job(params_json={"checkpoint": {"completed_employee_codes": "bad"}})
    assert sync_worker._load_completed_employee_codes(other_job) == []


def test_mark_job_cancelled_and_handle_termination(monkeypatch: pytest.MonkeyPatch) -> None:
    cancelled_job = _make_job(status="running")
    cancelled_db = _FakeDb(job=cancelled_job)
    missing_db = _FakeDb(job=None)
    already_cancelled_db = _FakeDb(job=_make_job(status="cancelled"))
    dbs = iter([missing_db, already_cancelled_db, cancelled_db])

    monkeypatch.setattr(sync_worker, "SessionLocal", lambda: next(dbs))

    sync_worker._mark_job_cancelled("missing")
    sync_worker._mark_job_cancelled("already")
    sync_worker._mark_job_cancelled("running")

    assert missing_db.closed is True
    assert already_cancelled_db.commits == 0
    assert cancelled_job.status == "cancelled"
    assert cancelled_job.error_detail == "Sync job cancelled by user"
    assert cancelled_job.finished_at is not None
    assert cancelled_db.commits == 1

    called: list[str] = []
    monkeypatch.setattr(sync_worker, "_mark_job_cancelled", lambda job_id: called.append(job_id))

    sync_worker.CURRENT_JOB_ID = None
    with pytest.raises(SystemExit, match="143"):
        sync_worker._handle_termination(signal.SIGTERM, None)
    assert called == []

    sync_worker.CURRENT_JOB_ID = "job-77"
    with pytest.raises(SystemExit, match="130"):
        sync_worker._handle_termination(signal.SIGINT, None)
    assert called == ["job-77"]


def test_parse_args_reads_required_job_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync_worker.sys, "argv", ["sync-worker", "--job-id", "job-42"])

    args = sync_worker.parse_args()

    assert args.job_id == "job-42"


def test_main_returns_2_when_job_is_missing(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    db = _FakeDb(job=None)
    signal_calls: list[tuple[int, object]] = []

    monkeypatch.setattr(sync_worker, "parse_args", lambda: SimpleNamespace(job_id="job-404"))
    monkeypatch.setattr(sync_worker, "SessionLocal", lambda: db)
    monkeypatch.setattr(sync_worker.signal, "signal", lambda signum, handler: signal_calls.append((signum, handler)))

    exit_code = sync_worker.main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "job-404 not found" in captured.err
    assert db.closed is True
    assert signal_calls[0][0] == signal.SIGTERM
    assert signal_calls[1][0] == signal.SIGINT


def test_main_completes_job_and_writes_artifacts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    job = _make_job(
        params_json={"checkpoint": {"completed_employee_codes": ["AA1"]}, "employee_codes": ["BB2", "CC3", "BB2"]},
    )
    import_job = _make_import_job()
    db = _FakeDb(job=job, user=SimpleNamespace(id=55))
    credential = SimpleNamespace(id=9, username="inaz-user")
    used_credentials: list[tuple[int, str | None]] = []

    def fake_create_import_job(current_db, *, parsed, requested_by_user_id, filename, params_json):
        assert current_db is db
        assert parsed.period_start == job.period_start
        assert parsed.period_end == job.period_end
        assert requested_by_user_id == 55
        assert filename == "presenze_collaboratori.json"
        assert params_json["sync_job_id"] == "job-1"
        return import_job

    def fake_parsed_collaborator_from_jsonable(item, *, default_period_start, default_period_end):
        assert default_period_start == job.period_start
        assert default_period_end == job.period_end
        return SimpleNamespace(collaborator={"employee_code": item["employee_code"]})

    def fake_import_collaborator_payload(current_db, *, payload, job):
        assert current_db is db
        job.records_imported += 1
        job.records_skipped += 2
        job.records_errors += 3

    def fake_run_scrape_with_credentials(**kwargs):
        assert kwargs["username"] == "inaz-user"
        assert kwargs["password"] == "pw"
        assert kwargs["employee_codes"] == ["BB2", "CC3"]
        assert kwargs["completed_employee_codes"] == ["AA1"]
        kwargs["progress_callback"](
            {
                "type": "collaborator_completed",
                "index": 1,
                "total": 2,
                "employee_code": "BB2",
                "completed_collaborators": 1,
                "error_count": 4,
                "resumed": True,
                "pending_collaborators": 1,
            }
        )
        kwargs["completed_timesheet_callback"]({"employee_code": "BB2"})
        kwargs["json_output"].write_text("[]", encoding="utf-8")
        return {
            "authenticated_url": "https://presenze/auth",
            "completed_collaborators": 2,
            "failed_collaborators": 1,
            "total_collaborators": 3,
            "resumed_from_checkpoint": True,
            "errors": [{"employee_code": "CC3"}],
        }

    monkeypatch.setattr(sync_worker, "parse_args", lambda: SimpleNamespace(job_id="job-1"))
    monkeypatch.setattr(sync_worker, "SessionLocal", lambda: db)
    monkeypatch.setattr(sync_worker.signal, "signal", lambda *_args: None)
    monkeypatch.setattr(sync_worker, "get_sync_artifact_dir", lambda job_id: tmp_path / job_id)
    monkeypatch.setattr(sync_worker.os, "getpid", lambda: 4321)
    monkeypatch.setattr(sync_worker, "create_import_job", fake_create_import_job)
    monkeypatch.setattr(sync_worker, "parsed_collaborator_from_jsonable", fake_parsed_collaborator_from_jsonable)
    monkeypatch.setattr(sync_worker, "import_collaborator_payload", fake_import_collaborator_payload)
    monkeypatch.setattr(sync_worker, "pick_credential", lambda current_db, current_user, credential_id: (credential, "pw"))
    monkeypatch.setattr(sync_worker, "run_scrape_with_credentials", fake_run_scrape_with_credentials)
    monkeypatch.setattr(sync_worker, "mark_credential_used", lambda current_db, credential_id, url: used_credentials.append((credential_id, url)))
    monkeypatch.setattr(sync_worker, "finalize_import_job", lambda current_db, *, job, status: setattr(job, "status", status))

    exit_code = sync_worker.main()

    progress = json.loads((tmp_path / "job-1" / "progress.json").read_text(encoding="utf-8"))
    summary = json.loads((tmp_path / "job-1" / "summary.json").read_text(encoding="utf-8"))
    events = (tmp_path / "job-1" / "events.ndjson").read_text(encoding="utf-8").splitlines()

    assert exit_code == 0
    assert job.status == "completed"
    assert job.worker_pid == 4321
    assert job.import_job_id == "import-1"
    assert job.records_imported == 1
    assert job.records_skipped == 2
    assert job.records_errors == 3
    assert import_job.status == "completed"
    assert used_credentials == [(9, "https://presenze/auth")]
    assert progress["state"] == "completed"
    assert progress["completed_collaborators"] == 2
    assert progress["failed_collaborators"] == 1
    assert summary["status"] == "completed"
    assert summary["resumed_from_checkpoint"] is True
    assert len(events) == 3
    assert json.loads(events[0])["type"] == "worker_started"
    assert json.loads(events[1])["type"] == "collaborator_completed"
    assert json.loads(events[2])["type"] == "job_completed"
    assert job.params_json["checkpoint"]["completed_employee_codes"] == ["AA1", "BB2"]
    assert db.closed is True


def test_main_marks_job_and_import_failed_when_scrape_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    job = _make_job(import_job_id="import-9", params_json={"progress": {"state": "running"}})
    import_job = _make_import_job(id="import-9", status="running")
    main_db = _FakeDb(job=job, import_job=import_job, user=SimpleNamespace(id=55))
    rollback_db = _FakeDb(job=job, import_job=import_job, user=SimpleNamespace(id=55))
    dbs = iter([main_db, rollback_db])
    errors: list[tuple[int, str]] = []

    monkeypatch.setattr(sync_worker, "parse_args", lambda: SimpleNamespace(job_id="job-1"))
    monkeypatch.setattr(sync_worker, "SessionLocal", lambda: next(dbs))
    monkeypatch.setattr(sync_worker.signal, "signal", lambda *_args: None)
    monkeypatch.setattr(sync_worker, "get_sync_artifact_dir", lambda job_id: tmp_path / job_id)
    monkeypatch.setattr(sync_worker, "pick_credential", lambda current_db, current_user, credential_id: (SimpleNamespace(id=9, username="inaz-user"), "pw"))
    monkeypatch.setattr(sync_worker, "run_scrape_with_credentials", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("scrape boom")))
    monkeypatch.setattr(sync_worker, "mark_credential_error", lambda current_db, credential_id, error: errors.append((credential_id, error)))

    exit_code = sync_worker.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert errors == [(9, "scrape boom")]
    assert job.status == "failed"
    assert job.error_detail == "scrape boom"
    assert job.finished_at is not None
    assert job.params_json["progress"]["state"] == "failed"
    assert import_job.status == "failed"
    assert import_job.error_detail == "scrape boom"
    assert rollback_db.commits == 1
    assert "RuntimeError: scrape boom" in captured.err
    assert main_db.closed is True
    assert rollback_db.closed is True


def test_main_fails_when_requested_user_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    job = _make_job(import_job_id="import-9")
    import_job = _make_import_job(id="import-9", status="running")
    main_db = _FakeDb(job=job, import_job=import_job, user=None)
    rollback_db = _FakeDb(job=job, import_job=import_job, user=None)
    dbs = iter([main_db, rollback_db])

    monkeypatch.setattr(sync_worker, "parse_args", lambda: SimpleNamespace(job_id="job-1"))
    monkeypatch.setattr(sync_worker, "SessionLocal", lambda: next(dbs))
    monkeypatch.setattr(sync_worker.signal, "signal", lambda *_args: None)
    monkeypatch.setattr(sync_worker, "get_sync_artifact_dir", lambda job_id: tmp_path / job_id)

    exit_code = sync_worker.main()

    assert exit_code == 1
    assert job.status == "failed"
    assert job.error_detail == "Requested by user not found for Presenze sync job"
    assert import_job.status == "failed"


def test_main_fails_when_credential_mode_is_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    job = _make_job(credential_id=None, import_job_id="import-9")
    import_job = _make_import_job(id="import-9", status="running")
    main_db = _FakeDb(job=job, import_job=import_job, user=SimpleNamespace(id=55))
    rollback_db = _FakeDb(job=job, import_job=import_job, user=SimpleNamespace(id=55))
    dbs = iter([main_db, rollback_db])

    monkeypatch.setattr(sync_worker, "parse_args", lambda: SimpleNamespace(job_id="job-1"))
    monkeypatch.setattr(sync_worker, "SessionLocal", lambda: next(dbs))
    monkeypatch.setattr(sync_worker.signal, "signal", lambda *_args: None)
    monkeypatch.setattr(sync_worker, "get_sync_artifact_dir", lambda job_id: tmp_path / job_id)

    exit_code = sync_worker.main()

    assert exit_code == 1
    assert job.status == "failed"
    assert "Legacy Presenze sync mode is disabled" in (job.error_detail or "")
    assert import_job.status == "failed"


def test_module_main_guard_raises_system_exit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db = _FakeDb(job=None)

    monkeypatch.setattr(core_database, "SessionLocal", lambda: db)
    monkeypatch.setattr(sync_runtime_module, "get_sync_artifact_dir", lambda job_id: tmp_path / job_id)
    monkeypatch.setattr(signal, "signal", lambda *_args: None)
    monkeypatch.setattr(sys, "argv", ["sync_worker.py", "--job-id", "job-404"])
    sys.modules.pop("app.modules.presenze.services.sync_worker", None)

    with pytest.raises(SystemExit, match="2"):
        runpy.run_module("app.modules.presenze.services.sync_worker", run_name="__main__")

    assert db.closed is True
