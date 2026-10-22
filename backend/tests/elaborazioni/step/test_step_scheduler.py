from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.elaborazioni.step import scheduler
from app.modules.elaborazioni.step.credentials import create_credential
from app.modules.elaborazioni.step.jobs import finish_job
from app.modules.elaborazioni.step.models import StepSyncJob
from app.modules.elaborazioni.step.schemas import StepCredentialCreate

# 2026-10-21 is CEST (UTC+2): 02:15 Europe/Rome is 00:15 UTC.
BEFORE = datetime(2026, 10, 21, 0, 10, tzinfo=UTC)
AFTER = datetime(2026, 10, 21, 0, 20, tzinfo=UTC)


def test_autosync_is_disabled_by_default(db, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STEP_AUTOSYNC_ENABLED", raising=False)
    assert scheduler.queue_due_autosync(db, now=AFTER) is None


def test_autosync_queues_once_per_day_after_the_configured_time(
    db, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STEP_AUTOSYNC_ENABLED", "TRUE")
    assert scheduler.queue_due_autosync(db, now=AFTER) is None
    create_credential(db, StepCredentialCreate(label="STEP", username="u", password="p"))
    assert scheduler.queue_due_autosync(db, now=BEFORE) is None

    job_id = scheduler.queue_due_autosync(db, now=AFTER)
    job = db.get(StepSyncJob, job_id)
    assert job.mode == "sync" and job.requested_by_user_id is None
    assert scheduler.queue_due_autosync(db, now=AFTER) is None

    finish_job(db, job_id, status="succeeded", result={})
    job.created_at = datetime(2026, 10, 21, 0, 30)
    db.commit()
    assert scheduler.queue_due_autosync(db, now=AFTER) is None
    assert (
        scheduler.queue_due_autosync(db, now=datetime(2026, 10, 22, 0, 20, tzinfo=UTC)) is not None
    )


def test_autosync_uses_current_time_and_custom_schedule(
    db, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STEP_AUTOSYNC_ENABLED", "true")
    monkeypatch.setenv("STEP_AUTOSYNC_TIME", "00:00")
    monkeypatch.setenv("STEP_AUTOSYNC_TIMEZONE", "UTC")
    create_credential(db, StepCredentialCreate(label="STEP", username="u", password="p"))
    assert scheduler.queue_due_autosync(db) is not None
