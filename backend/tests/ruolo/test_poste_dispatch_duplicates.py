import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError

from app.models.posta_online import PostaOnlineRegisteredMailSyncJob
from app.modules.ruolo.poste_dispatch_models import PosteDispatchEvent, PosteDispatchItem
from app.modules.ruolo.services import poste_dispatch as service
from app.modules.ruolo.services import poste_dispatch_duplicates as duplicates
from app.modules.ruolo.services import poste_dispatch_work as work
from app.modules.ruolo.services.poste_dispatch_state import release

from .poste_dispatch_fixtures import payload, seed_account, seed_batch_item
from .test_poste_dispatch_accounts import complete_jobs, new_lot
from .test_poste_dispatch_service import db as db


def snapshot(lot, rows=(), *, at=None, legacy=False):
    lot.portal_snapshot = {
        "checked_at": (at or datetime.now(UTC)).isoformat(),
        "foreign_drafts" if legacy else "drafts": [
            {"name": name, "draft_id": draft_id} for name, draft_id in rows
        ],
    }


def job_for(db, lot, item):
    complete_jobs(db)
    item.status = "address_ok"
    return service.request_job(db, lot.id, "drafts", actor_id=1)


def test_report_is_empty_and_unverified_without_accounts_or_observations(db):
    report = duplicates.duplicate_report(db)
    assert report["total"] == 0 and report["coverage_complete"] is False
    assert report["accounts"][0]["verified"] is False
    db.query(PostaOnlineRegisteredMailSyncJob).delete()
    from app.models.posta_online import PostaOnlineCredential

    db.query(PostaOnlineCredential).delete()
    assert duplicates.duplicate_report(db)["accounts"] == []


@pytest.mark.parametrize("newest_first", [False, True])
def test_latest_account_snapshot_is_used_once_across_lots_and_credentials(
    db, tmp_path, newest_first
):
    now = datetime.now(UTC)
    a, item = new_lot(db, tmp_path)
    b, _ = new_lot(db, tmp_path)
    seed_account(db, 2, "  ACCOUNT-1  ")
    older, newer = (b, a) if newest_first else (a, b)
    snapshot(
        older,
        [(item.shipment_name, "old"), (item.shipment_name, "duplicate")],
        at=now - timedelta(minutes=2),
    )
    snapshot(newer, [(item.shipment_name, "current"), ("manual letter", "unrelated")], at=now)
    report = duplicates.duplicate_report(db, now=now)
    assert report["findings"] == [] and report["coverage_complete"] is True
    assert len(report["accounts"]) == 1
    assert report["accounts"][0]["checked_at"] == now.isoformat()


@pytest.mark.parametrize("age", [timedelta(minutes=31), -timedelta(minutes=1)])
def test_old_or_future_snapshots_cannot_certify_coverage(db, tmp_path, age):
    now = datetime.now(UTC)
    lot, _ = new_lot(db, tmp_path)
    snapshot(lot, at=now - age)
    report = duplicates.duplicate_report(db, now=now)
    assert not report["coverage_complete"] and not report["accounts"][0]["fresh"]


@pytest.mark.parametrize(
    "value",
    [None, {}, {"checked_at": None}, {"checked_at": "bad"}, {"checked_at": "2026-01-01T00:00:00"}],
)
def test_invalid_snapshot_or_unbound_account_stays_unverified(db, tmp_path, value):
    lot, _ = new_lot(db, tmp_path)
    lot.portal_snapshot = value
    assert not duplicates.duplicate_report(db)["coverage_complete"]
    lot.poste_username = None
    snapshot(lot)
    report = duplicates.duplicate_report(db)
    assert any(row["poste_username"] is None for row in report["accounts"])
    assert not report["coverage_complete"]


def test_foreign_legacy_draft_blocks_other_account_and_preserves_audit(db, tmp_path):
    seed_account(db, 2, "other-account", active=False)
    first, item = new_lot(db, tmp_path)
    # A disabled account is still included in historical portal evidence.
    from app.models.posta_online import PostaOnlineCredential

    db.get(PostaOnlineCredential, 2).active = True
    other, _ = new_lot(db, tmp_path, 2)
    db.get(PostaOnlineCredential, 2).active = False
    snapshot(other, [("  gaia   " + item.notice_number, None)], legacy=True)
    job = job_for(db, first, item)
    report = duplicates.duplicate_report(db)
    [finding] = report["findings"]
    assert finding["reasons"] == ["cross_account_conflict"]
    assert finding["portal_drafts"][0]["draft_id"] is None
    assert report["coverage_complete"] is False
    assert work.mark_draft_creating(db, item.id, job_id=job.id) is False
    assert item.status == "address_review" and item.upload_job_id is None
    assert item.address_review["no_automatic_retry"] is True
    work.record_draft_failure(db, item.id, job_id=job.id, submitted=False, error="Stato cambiato")
    assert item.status == "address_review" and item.address_review["duplicate_check"] is True
    recorded = db.scalar(
        select(PosteDispatchEvent).where(PosteDispatchEvent.kind == "duplicate_upload_blocked")
    )
    assert recorded.actor_id == 1 and recorded.actor_username == "poste-1"
    assert recorded.detail["conflicts"][0]["portal_drafts"][0]["poste_username"] == "other-account"
    assert not db.scalar(
        select(PosteDispatchEvent).where(PosteDispatchEvent.kind == "draft_submitting")
    )
    assert duplicates.duplicate_report(db)["total"] == 1  # the hold does not hide the conflict


@pytest.mark.parametrize("ids", [("12", "13"), (None, None)])
def test_duplicate_portal_rows_even_without_ids_are_detected_without_outbox_item(db, tmp_path, ids):
    lot, _ = new_lot(db, tmp_path)
    snapshot(lot, [("GAIA 999", identity) for identity in ids])
    [finding] = duplicates.duplicate_report(db)["findings"]
    assert finding["reasons"] == ["multiple_portal_drafts"]
    assert finding["items"] == [] and len(finding["portal_drafts"]) == 2


def test_single_local_observation_is_not_counted_twice_and_no_pdf_is_read(db, tmp_path):
    lot, item = new_lot(db, tmp_path)
    job = job_for(db, lot, item)
    assert work.mark_draft_creating(db, item.id, job_id=job.id)
    work.record_draft_row(
        db, item.id, job_id=job.id, row=work.DraftRow("12", item.shipment_name, "PREZZATO", None)
    )
    work.apply_drafts_snapshot(
        db, lot.id, job_id=job.id, rows=[work.DraftRow("12", item.shipment_name, "PREZZATO", None)]
    )
    assert lot.portal_snapshot["drafts"][0]["name"] == item.shipment_name
    db.flush()
    db.expire_all()
    statements = []

    def capture(_conn, _cursor, sql, *_args):
        statements.append(sql)

    event.listen(db.get_bind(), "before_cursor_execute", capture)
    try:
        report = duplicates.duplicate_report(db)
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", capture)
    assert report["findings"] == [] and report["coverage_complete"]
    assert all(re.search(r"\bartifact\b", sql) is None for sql in statements)
    assert all("password_encrypted" not in sql for sql in statements)
    assert all(sql.lstrip().upper().startswith("SELECT") for sql in statements)


@pytest.mark.parametrize("status", ["draft_creating", "draft_uncertain", "draft_priced", "sent"])
def test_legacy_duplicate_assignments_are_detected_including_uncertain_and_sent(
    db, tmp_path, status
):
    seed_account(db, 2, "other")
    _, original = new_lot(db, tmp_path)
    # Legacy or externally repaired data may be missing reservation keys.
    original.status = status
    original.active_key = original.active_source_key = None
    second = service.create_lot(
        db,
        title="legacy copy",
        batch_item_ids=[original.batch_item_id],
        credential_id=2,
        actor_id=1,
    )
    copy = db.scalar(select(PosteDispatchItem).where(PosteDispatchItem.lot_id == second.id))
    report = duplicates.duplicate_report(db)
    assert {row["match_by"] for row in report["findings"]} == {"notice", "source"}
    assert all("multiple_active_items" in row["reasons"] for row in report["findings"])
    job = job_for(db, second, copy)
    assert not work.mark_draft_creating(db, copy.id, job_id=job.id)
    assert original.status == status  # no deletion, sending, or rewriting historical evidence


def test_cancelled_notice_is_reusable_but_positive_portal_evidence_still_blocks(db, tmp_path):
    seed_account(db, 2, "other")
    old, original = new_lot(db, tmp_path)
    original.status = "cancelled"
    release(original)
    new = service.create_lot(
        db, title="retry", batch_item_ids=[original.batch_item_id], credential_id=2, actor_id=1
    )
    copy = db.scalar(select(PosteDispatchItem).where(PosteDispatchItem.lot_id == new.id))
    job = job_for(db, new, copy)
    assert duplicates.duplicate_report(db)["findings"] == []
    snapshot(old, [(original.shipment_name, "12")])
    assert not work.mark_draft_creating(db, copy.id, job_id=job.id)
    # A later complete empty snapshot clears that positive evidence, not the old snapshot.
    snapshot(old)
    copy.status = "address_ok"
    assert work.mark_draft_creating(db, copy.id, job_id=job.id)


@pytest.mark.parametrize("key", ["active_key", "active_source_key", "shipment_name"])
def test_invalid_global_reservation_blocks_before_continua(db, tmp_path, key):
    lot, item = new_lot(db, tmp_path)
    job = job_for(db, lot, item)
    setattr(item, key, "wrong")
    assert not work.mark_draft_creating(db, item.id, job_id=job.id)
    assert item.status == "address_review" and item.upload_job_id is None


def test_regenerated_batch_cannot_bypass_global_notice_key_on_another_account(db, tmp_path):
    seed_account(db, 2, "other")
    _, original = new_lot(db, tmp_path)
    different_source = seed_batch_item(db, tmp_path, payload_json=payload(original.notice_number))
    from app.modules.ruolo.services.poste_dispatch_state import DispatchConflict

    with pytest.raises(DispatchConflict, match="altro lotto"):
        service.create_lot(
            db,
            title="regenerated",
            batch_item_ids=[different_source.id],
            credential_id=2,
            actor_id=1,
        )
    # The database constraint itself, independent of the service, remains the race barrier.
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            PosteDispatchItem(
                id=uuid4(),
                lot_id=original.lot_id,
                batch_item_id=different_source.id,
                notice_number=original.notice_number,
                shipment_name=original.shipment_name,
                active_key=original.active_key,
                active_source_key=str(different_source.id),
                recipient=original.recipient,
                artifact_sha256="unused",
                artifact_size=0,
            )
        )
        db.flush()


@pytest.mark.parametrize("invalid", ["mode", "operator"])
def test_account_and_operator_validation_precede_duplicate_hold(db, tmp_path, invalid):
    from app.modules.ruolo.services.poste_dispatch_state import DispatchConflict

    seed_account(db, 2, "other")
    lot, item = new_lot(db, tmp_path)
    other, _ = new_lot(db, tmp_path, 2)
    snapshot(other, [(item.shipment_name, "12")])
    job = job_for(db, lot, item)
    if invalid == "mode":
        job.mode = "poste_dispatch_reconcile"
        message = "Job di caricamento"
    else:
        job.requested_by_user_id = None
        message = "Operatore GAIA del caricamento"
    with pytest.raises(DispatchConflict, match=message):
        work.mark_draft_creating(db, item.id, job_id=job.id)
    assert item.status == "address_ok" and item.address_review is None
    assert item.upload_job_id is None
    assert not db.scalar(
        select(PosteDispatchEvent).where(PosteDispatchEvent.kind == "duplicate_upload_blocked")
    )


def test_snapshot_separates_lot_membership_from_upload_state(db, tmp_path):
    first = seed_batch_item(db, tmp_path, payload_json=payload("020210000000001"))
    second = seed_batch_item(db, tmp_path, payload_json=payload("020210000000002"))
    lot = service.create_lot(
        db, title="Mixed states", batch_item_ids=[first.id, second.id], credential_id=1, actor_id=1
    )
    items = list(db.scalars(select(PosteDispatchItem).where(PosteDispatchItem.lot_id == lot.id)))
    by_source = {row.batch_item_id: row for row in items}
    by_source[first.id].status = "draft_created"
    by_source[second.id].status = "address_ok"
    rows = [work.DraftRow("12", row.shipment_name, "PREZZATO", None) for row in items]
    rows.append(work.DraftRow("99", "GAIA 999", "PREZZATO", None))
    assert work.apply_drafts_snapshot(db, lot.id, job_id=7, rows=rows) == []
    assert by_source[first.id].status == "draft_priced"
    assert by_source[second.id].status == "address_ok"
    assert len(lot.portal_snapshot["drafts"]) == 3
    assert lot.portal_snapshot["foreign_drafts"] == [
        {"draft_id": "99", "name": "GAIA 999", "status": "PREZZATO"}
    ]
