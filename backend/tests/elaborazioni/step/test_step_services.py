from __future__ import annotations

import pytest

from app.modules.elaborazioni.step import credentials, jobs
from app.modules.elaborazioni.step.models import StepCredential, StepSyncJob
from app.modules.elaborazioni.step.schemas import (
    StepCredentialCreate,
    StepCredentialUpdate,
    StepSyncJobCreate,
)


def _credential(db, **overrides) -> int:
    return credentials.create_credential(
        db, StepCredentialCreate(label="STEP", username="u", password="p", **overrides)
    ).id


def test_pick_and_mark_credentials(db) -> None:
    with pytest.raises(RuntimeError, match="Nessuna credenziale"):
        credentials.pick_credential(db)
    assert not credentials.has_available_credential(db)
    first = _credential(db)
    second = _credential(db)
    credentials.mark_credential_used(db, first)

    picked, password = credentials.pick_credential(db)
    assert picked.id == second and password == "p"
    assert credentials.pick_credential(db, first)[0].id == first
    with pytest.raises(RuntimeError, match="non trovata"):
        credentials.pick_credential(db, 999)

    credentials.mark_credential_used(db, 999)
    credentials.mark_credential_error(db, None, "x")
    credentials.mark_credential_error(db, 999, "x")
    for _ in range(credentials.MAX_CONSECUTIVE_FAILURES):
        credentials.mark_credential_error(db, first, "Accesso rifiutato")
    disabled = db.get(StepCredential, first)
    assert not disabled.active and disabled.last_error == "Accesso rifiutato"
    assert not credentials.has_available_credential(db, first)

    unchanged = credentials.update_credential(db, second, StepCredentialUpdate(active=False))
    assert unchanged.active is False and unchanged.consecutive_failures == 0
    assert credentials.update_credential(db, 999, StepCredentialUpdate()) is None
    assert [item.id for item in credentials.list_credentials(db)] == [first, second]


def test_job_queue_claim_recover_and_finish(db) -> None:
    assert jobs.claim_next_job(db) is None
    job = jobs.create_job(
        db, StepSyncJobCreate(mode="list_only", credential_id=7), requested_by_user_id=None
    )
    assert job.credential_id == 7
    with pytest.raises(jobs.StepJobConflict):
        jobs.create_job(db, StepSyncJobCreate(mode="relink"), requested_by_user_id=None)
    with pytest.raises(jobs.StepJobConflict):
        jobs.create_credential_test_job(db, _credential(db), requested_by_user_id=None)
    assert jobs.create_credential_test_job(db, 999, requested_by_user_id=None) is None

    claimed = jobs.claim_next_job(db)
    assert claimed.id == job.id and claimed.status == "processing"
    with pytest.raises(jobs.StepJobConflict):
        jobs.cancel_job(db, claimed)
    with pytest.raises(jobs.StepJobConflict):
        jobs.delete_job(db, claimed)
    assert jobs.recover_interrupted_jobs(db) == [job.id]
    assert db.get(StepSyncJob, job.id).status == "pending"

    jobs.update_progress(db, job.id, {"phase": "elenco"})
    jobs.finish_job(db, job.id, status="succeeded", result={"list_rows": 3})
    finished = db.get(StepSyncJob, job.id)
    assert (
        finished.result_json["progress"] == {"phase": "elenco"}
        and finished.result_json["list_rows"] == 3
    )
    assert finished.completed_at is not None and finished.error_detail is None
    jobs.finish_job(db, job.id, status="failed", result=None, error="boom")
    assert db.get(StepSyncJob, job.id).error_detail == "boom"

    jobs.update_progress(db, 999, {})
    jobs.finish_job(db, 999, status="failed", result=None)
    jobs.delete_job(db, finished)
    assert jobs.list_jobs(db) == []


def test_job_payload_validation() -> None:
    assert (
        StepSyncJobCreate(mode="archive_import", archive_name="raccolta.zip").archive_name
        == "raccolta.zip"
    )
    with pytest.raises(ValueError, match="archive_name"):
        StepSyncJobCreate(mode="archive_import", archive_name="dir/raccolta.zip")
    with pytest.raises(ValueError, match="archive_name"):
        StepSyncJobCreate(mode="archive_import", archive_name="raccolta.txt")
    assert StepCredentialUpdate(portal_url=None).portal_url is None
