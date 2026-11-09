from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, select

from app.models.posta_online import PostaOnlineCredential
from app.models.posta_online import PostaOnlineRegisteredMailSyncJob as Job
from app.modules.ruolo.poste_dispatch_models import PosteDispatchEvent as Event
from app.modules.ruolo.services import poste_dispatch_final_check as checks
from app.modules.ruolo.services import poste_dispatch_final_report as reports
from app.modules.ruolo.services.poste_dispatch_state import DispatchConflict, DispatchNotFound

from .poste_dispatch_fixtures import seed_account
from .test_notice_register_api import _headers
from .test_poste_dispatch_accounts import complete_jobs, new_lot
from .test_poste_dispatch_api import URL, _create
from .test_poste_dispatch_api import api as api
from .test_poste_dispatch_service import db as db


def campaign(db, tmp_path, accounts=2):
    lots = []
    for identity in range(1, accounts + 1):
        if identity != 1:
            seed_account(db, identity, f"account-{identity}")
        lot, item = new_lot(db, tmp_path, identity)
        item.status = "draft_priced"
        lots.append((lot, item))
    complete_jobs(db)
    check = checks.start_check(db, actor_id=1)
    return check, lots


def snapshot(db, check, plan, *, drafts=(), archive=None):
    job = db.get(Job, plan["job_id"])
    job.status = "processing"
    started = datetime.now(UTC)
    job.started_at = started
    data = {
        "started_at": started.isoformat(),
        "checked_at": datetime.now(UTC).isoformat(),
        "drafts": [
            {"name": name, "draft_id": identity, "status": "PREZZATO"} for name, identity in drafts
        ],
        "archive": archive or {},
    }
    checks.record_account_snapshot(
        db,
        UUID(plan["lot_id"]),
        job_id=job.id,
        snapshot=data,
    )
    job.status = "succeeded"
    job.completed_at = datetime.now(UTC)
    db.flush()
    return db.scalars(
        select(Event)
        .where(Event.job_id == job.id, Event.kind == checks.SNAPSHOT_KIND)
        .order_by(Event.created_at.desc())
    ).first()


def finish(db, check, lots):
    for plan in check.detail["accounts"]:
        name = next(item.shipment_name for lot, item in lots if str(lot.id) == plan["lot_id"])
        snapshot(db, check, plan, drafts=[(name, str(plan["credential_id"]))])


def test_final_check_needs_existing_lots_and_a_drained_queue(db, tmp_path):
    with pytest.raises(DispatchConflict, match="Nessun lotto"):
        checks.start_check(db, actor_id=1)
    new_lot(db, tmp_path)
    with pytest.raises(DispatchConflict, match="conclusione"):
        checks.start_check(db, actor_id=1)


def test_each_account_gets_one_read_job_and_clean_report_after_all_finish(db, tmp_path):
    check, lots = campaign(db, tmp_path)
    pending = reports.check_report(db, check.id)
    assert pending["status"] == "incomplete" and not pending["complete"]
    assert len(check.detail["accounts"]) == 2
    assert check.actor_username == "poste-1"
    assert all(db.get(Job, p["job_id"]).mode == checks.MODE for p in check.detail["accounts"])
    with pytest.raises(DispatchConflict):
        checks.start_check(db, actor_id=1)
    finish(db, check, lots)
    report = reports.check_report(db, check.id)
    assert report["status"] == "verified_no_duplicates" and report["complete"]
    assert report["duplicates"] == report["missing"] == report["misplaced"] == []
    assert all(item.status == "draft_priced" for _, item in lots)
    assert all(row["snapshot"]["final_check_id"] == str(check.id) for row in report["accounts"])


@pytest.mark.parametrize(
    "reason",
    [
        "credential_inactive",
        "no_bound_lot",
        "account_changed",
        "invalid_username",
        "credential_missing",
    ],
)
def test_unavailable_and_historical_accounts_never_disappear_from_coverage(db, tmp_path, reason):
    lot, _ = new_lot(db, tmp_path)
    complete_jobs(db)
    credential = db.get(PostaOnlineCredential, 1)
    if reason == "credential_inactive":
        credential.active = False
    elif reason == "no_bound_lot":
        seed_account(db, 2, "extra")
    elif reason == "account_changed":
        credential.username = "changed"
    elif reason == "invalid_username":
        credential.username = lot.poste_username = "  "
    else:
        lot.credential_id = None
        lot.poste_username = "historical"
    check = checks.start_check(db, actor_id=1)
    report = reports.check_report(db, check.id)
    assert not report["complete"]
    assert reason in {p["unavailable_reason"] for p in report["accounts"]}


def test_duplicate_credential_records_represent_one_portal_account(db, tmp_path):
    seed_account(db, 2, "account-1", active=False)
    new_lot(db, tmp_path)
    complete_jobs(db)
    check = checks.start_check(db, actor_id=1)
    assert len(check.detail["accounts"]) == 1
    assert check.detail["accounts"][0]["credential_id"] == 1


def test_later_valid_credential_can_replace_unavailable_duplicate(db, tmp_path):
    db.get(PostaOnlineCredential, 1).active = False
    seed_account(db, 2, "account-1")
    new_lot(db, tmp_path, 2)
    complete_jobs(db)
    check = checks.start_check(db, actor_id=1)
    assert len(check.detail["accounts"]) == 1 and check.detail["accounts"][0]["credential_id"] == 2


@pytest.mark.parametrize("source", ["draft", "archive"])
def test_cross_account_duplicates_include_same_poste_id_on_different_accounts(db, tmp_path, source):
    check, lots = campaign(db, tmp_path)
    name = lots[0][1].shipment_name
    for plan in check.detail["accounts"]:
        if source == "draft":
            snapshot(db, check, plan, drafts=[(name, "12")])
        else:
            snapshot(db, check, plan, archive={name: ["12"]})
    report = reports.check_report(db, check.id)
    assert report["status"] == "duplicates_found" and report["complete"]
    [duplicate] = report["duplicates"]
    assert duplicate["cross_account"] and len(duplicate["occurrences"]) == 2
    assert {r["poste_username"] for r in duplicate["occurrences"]} == {"account-1", "account-2"}


def test_two_pending_drafts_without_identifiers_on_same_account_are_duplicates(db, tmp_path):
    check, lots = campaign(db, tmp_path, 1)
    snapshot(db, check, check.detail["accounts"][0], drafts=[(lots[0][1].shipment_name, None)] * 2)
    report = reports.check_report(db, check.id)
    assert report["status"] == "duplicates_found" and not report["duplicates"][0]["cross_account"]


def test_same_shipment_moving_to_archive_is_not_counted_twice(db, tmp_path):
    check, lots = campaign(db, tmp_path, 1)
    name = lots[0][1].shipment_name
    snapshot(
        db,
        check,
        check.detail["accounts"][0],
        drafts=[(name, "12"), ("manual", "99")],
        archive={name: ["12", "12"]},
    )
    report = reports.check_report(db, check.id)
    assert report["status"] == "verified_no_duplicates" and report["unmatched_rows"] == 1


@pytest.mark.parametrize("problem", ["missing", "misplaced"])
def test_expected_uploaded_notice_absent_or_on_wrong_account_requires_review(db, tmp_path, problem):
    check, lots = campaign(db, tmp_path)
    for index, plan in enumerate(check.detail["accounts"]):
        names = [(lots[index][1].shipment_name, "12")]
        if index == 0:
            names = []
        elif problem == "misplaced":
            names.append((lots[0][1].shipment_name, "13"))
        snapshot(db, check, plan, drafts=names)
    report = reports.check_report(db, check.id)
    assert report["status"] == "needs_review" and report["complete"]
    assert len(report[problem]) == 1


@pytest.mark.parametrize("status", ["pending", "queued_resume", "processing", "failed"])
def test_waiting_timeout_or_failed_account_cannot_produce_clean_result(db, tmp_path, status):
    check, lots = campaign(db, tmp_path)
    first, second = check.detail["accounts"]
    snapshot(db, check, first, drafts=[(lots[0][1].shipment_name, "12")])
    job = db.get(Job, second["job_id"])
    job.status = status
    job.error_detail = "Poste timeout"
    report = reports.check_report(db, check.id)
    assert report["status"] == "incomplete" and not report["complete"]
    assert report["accounts"][1]["status"] == status


@pytest.mark.parametrize(
    "problem",
    [
        "missing_job",
        "snapshot_missing",
        "invalid_snapshot",
        "snapshot_stale",
        "invalid_read_interval",
        "account_or_run_mismatch",
    ],
)
def test_invalid_or_stale_evidence_is_never_reused_as_success(db, tmp_path, problem):
    check, lots = campaign(db, tmp_path, 1)
    plan = check.detail["accounts"][0]
    evidence = snapshot(db, check, plan, drafts=[(lots[0][1].shipment_name, "12")])
    now = datetime.now(UTC)
    if problem == "missing_job":
        db.delete(db.get(Job, plan["job_id"]))
    elif problem == "snapshot_missing":
        db.delete(evidence)
    elif problem == "invalid_snapshot":
        evidence.detail = {**evidence.detail, "drafts": "broken"}
    elif problem == "snapshot_stale":
        now += timedelta(minutes=31)
    elif problem == "invalid_read_interval":
        evidence.detail = {**evidence.detail, "started_at": (now - timedelta(days=1)).isoformat()}
    else:
        evidence.detail = {**evidence.detail, "final_check_id": str(uuid4())}
    db.flush()
    report = reports.check_report(db, check.id, now=now)
    assert report["status"] == "incomplete" and report["accounts"][0]["status"] == problem


@pytest.mark.parametrize("change", ["job", "old_job_restart", "item", "credential"])
def test_operations_restarted_during_verification_invalidate_result(db, tmp_path, change):
    check, lots = campaign(db, tmp_path, 1)
    finish(db, check, lots)
    if change == "job":
        db.add(Job(mode="poste_dispatch_drafts", status="pending", started_at=datetime.now(UTC)))
        expected = "operations_after_request"
    elif change == "old_job_restart":
        old = db.scalar(select(Job).where(Job.mode != checks.MODE))
        old.started_at = datetime.now(UTC)
        expected = "operations_after_request"
    elif change == "item":
        db.add(Event(lot_id=lots[0][0].id, item_id=lots[0][1].id, kind="recipient_updated"))
        expected = "items_changed_after_request"
    else:
        seed_account(db, 2, "new-account")
        expected = "account_scope_changed"
    db.flush()
    report = reports.check_report(db, check.id)
    assert report["status"] == "incomplete" and expected in report["invalidations"]


@pytest.mark.parametrize(
    "changed_field", ["account", "credential", "mode", "run", "lot", "username"]
)
def test_completed_evidence_must_still_match_the_frozen_job_and_account(
    db, tmp_path, changed_field
):
    check, lots = campaign(db, tmp_path, 1)
    plan = check.detail["accounts"][0]
    evidence = snapshot(db, check, plan, drafts=[(lots[0][1].shipment_name, "12")])
    job = db.get(Job, plan["job_id"])
    if changed_field == "account":
        evidence.detail = {**evidence.detail, "poste_username": "other-account"}
    elif changed_field == "credential":
        seed_account(db, 2, "other-account")
        job.credential_id = 2
    elif changed_field == "mode":
        job.mode = "poste_dispatch_reconcile"
    else:
        key = {"run": "final_check_id", "lot": "lot_id", "username": "poste_username"}[
            changed_field
        ]
        job.payload_json = {**job.payload_json, key: "different"}
    db.flush()
    report = reports.check_report(db, check.id)
    assert report["status"] == "incomplete" and not report["complete"]
    assert report["accounts"][0]["status"] == "account_or_run_mismatch"


def test_report_uses_only_this_run_and_does_not_read_pdfs_or_write_data(db, tmp_path):
    first, lots = campaign(db, tmp_path, 1)
    finish(db, first, lots)
    second = checks.start_check(db, actor_id=1)
    db.flush()
    db.expire_all()
    sql = []

    def capture(_connection, _cursor, statement, *_args):
        sql.append(statement)

    event.listen(db.get_bind(), "before_cursor_execute", capture)
    try:
        report = reports.check_report(db, second.id)
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", capture)
    assert not report["complete"]
    assert all(s.lstrip().upper().startswith("SELECT") for s in sql)
    assert all("artifact" not in s and "password_encrypted" not in s for s in sql)


def test_wrong_check_ids_and_non_check_events_are_not_found(db, tmp_path):
    with pytest.raises(DispatchNotFound):
        reports.check_report(db, uuid4())
    lot, _ = new_lot(db, tmp_path)
    other = db.scalar(select(Event).where(Event.lot_id == lot.id))
    with pytest.raises(DispatchNotFound):
        reports.check_report(db, other.id)


@pytest.mark.parametrize("problem", ["mode", "manifest_job", "manifest_account"])
def test_snapshot_from_unplanned_job_cannot_be_attributed_to_an_account(db, tmp_path, problem):
    check, _ = campaign(db, tmp_path, 1)
    plan = check.detail["accounts"][0]
    job = db.get(Job, plan["job_id"])
    if problem == "mode":
        job.mode = "poste_dispatch_reconcile"
    else:
        replacement = (
            {**plan, "job_id": -1} if problem == "manifest_job" else {**plan, "credential_id": -1}
        )
        check.detail = {**check.detail, "accounts": [replacement]}
    from uuid import UUID

    with pytest.raises(DispatchConflict):
        checks.record_account_snapshot(db, UUID(plan["lot_id"]), job_id=job.id, snapshot={})


def test_final_check_api_starts_once_and_viewers_can_read_result(api):
    _create(api)
    response = api.client.post(f"{URL}/final-checks")
    assert response.status_code == 409  # existing address job has not finished
    with api.session() as db:
        complete_jobs(db)
        db.commit()
    response = api.client.post(f"{URL}/final-checks")
    assert response.status_code == 200, response.text
    check = response.json()
    assert check["status"] == "incomplete" and len(check["accounts"]) == 1
    assert (
        api.client.get(f"{URL}/final-checks/{check['check_id']}", headers=_headers(2)).status_code
        == 200
    )
    assert api.client.post(f"{URL}/final-checks").status_code == 409
    assert api.client.post(f"{URL}/final-checks", headers=_headers(2)).status_code == 403
    assert api.client.get(f"{URL}/final-checks/{uuid4()}").status_code == 404
    assert (
        api.client.get(f"{URL}/final-checks/{check['check_id']}", headers=_headers(5)).status_code
        == 403
    )
