import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.application_user import ApplicationUser
from app.models.posta_online import PostaOnlineRegisteredMailSyncJob
from app.modules.ruolo.poste_dispatch_models import (
    PosteDispatchEvent,
    PosteDispatchItem,
    PosteDispatchLot,
)
from app.modules.ruolo.services import poste_dispatch as service
from app.modules.ruolo.services import poste_dispatch_accounts as accounts
from app.modules.ruolo.services import poste_dispatch_reconcile as reconcile
from app.modules.ruolo.services import poste_dispatch_views as views
from app.modules.ruolo.services import poste_dispatch_work as work
from app.modules.ruolo.services.poste_dispatch_state import DispatchConflict

from .poste_dispatch_fixtures import DETAIL_PAGE, payload, seed_account, seed_batch_item, seed_user
from .test_poste_dispatch_service import db as db


def new_lot(db, tmp_path, credential_id=1):
    index = db.scalar(select(func.count()).select_from(PosteDispatchLot)) + 1
    item = seed_batch_item(db, tmp_path, payload_json=payload(f"0202178{index:08d}"))
    lot = service.create_lot(
        db,
        title=f"Lotto {index}",
        batch_item_ids=[item.id],
        credential_id=credential_id,
        actor_id=1,
    )
    dispatch = db.scalar(select(PosteDispatchItem).where(PosteDispatchItem.lot_id == lot.id))
    return lot, dispatch


def complete_jobs(db):
    for job in db.scalars(select(PostaOnlineRegisteredMailSyncJob)):
        job.status = "succeeded"
    db.flush()


def test_each_lot_and_operation_retains_its_own_poste_account(db, tmp_path):
    seed_account(db, 2, "other-poste")
    first, a = new_lot(db, tmp_path)
    second, b = new_lot(db, tmp_path, 2)
    complete_jobs(db)
    for lot, item, credential in ((first, a, 1), (second, b, 2)):
        item.status = "address_ok"
        for kind in ("drafts", "reconcile"):
            job = service.request_job(db, lot.id, kind, actor_id=1)
            assert job.credential_id == credential
            assert accounts.job_account(db, job).id == lot.id
            job.status = "succeeded"
    rows, total = views.list_lots(db, page=1, page_size=20, credential_id=2)
    assert total == 1 and rows[0].id == second.id
    assert rows[0].poste_username == "other-poste" and rows[0].credential_label == "Account 2"
    assert views.list_lots(db, page=1, page_size=20, credential_id=999) == ([], 0)
    assert first.created_by_username == "poste-1"
    assert set(accounts.list_accounts(db)[0]) == {"id", "label", "username", "active"}


def test_upload_operator_is_the_requester_not_the_lot_creator(db, tmp_path):
    seed_user(db, 2)
    lot, item = new_lot(db, tmp_path)
    complete_jobs(db)
    item.status = "address_ok"
    job = service.request_job(db, lot.id, "drafts", actor_id=2)
    assert work.mark_draft_creating(db, item.id, job_id=job.id)
    work.record_draft_row(
        db, item.id, job_id=job.id, row=work.DraftRow("456", item.shipment_name, "PREZZATO", None)
    )
    assert item.upload_requested_by_user_id == 2 and item.upload_requested_by_username == "poste-2"
    assert item.upload_job_id == job.id and lot.created_by == 1
    event = db.scalar(
        select(PosteDispatchEvent).where(PosteDispatchEvent.kind == "draft_submitting")
    )
    assert event.actor_id == 2 and event.actor_username == "poste-2"
    db.get(ApplicationUser, 2).username = "renamed"
    detail = views.lot_detail(db, lot.id)
    assert detail.items[0].upload_requested_by_username == "poste-2"
    assert detail.events[0].actor_username == "poste-2"


@pytest.mark.parametrize(
    "change", ["missing", "inactive", "username", "job_credential", "job_username", "unbound"]
)
def test_account_changes_never_fall_back_to_another_available_account(db, tmp_path, change):
    lot, item = new_lot(db, tmp_path)
    seed_account(db, 2, "other")
    job = db.scalars(select(PostaOnlineRegisteredMailSyncJob)).first()
    credential = accounts.selected_account(db, 1)
    if change == "missing":
        lot.credential_id = 999
    elif change == "inactive":
        credential.active = False
    elif change == "username":
        credential.username = "replaced-account"
    elif change == "job_credential":
        job.credential_id = 2
    elif change == "job_username":
        job.payload_json = {"lot_id": str(lot.id), "poste_username": "other"}
    else:
        lot.credential_id = None
    with db.no_autoflush, pytest.raises(DispatchConflict):
        accounts.job_account(db, job)
    assert item.poste_draft_id is None


def test_historical_lot_requires_explicit_once_only_account_binding(db, tmp_path):
    lot, _ = new_lot(db, tmp_path)
    lot.credential_id = lot.poste_username = lot.credential_label = None
    with pytest.raises(DispatchConflict, match="in corso"):
        service.bind_account(db, lot.id, 1, actor_id=1)
    complete_jobs(db)
    with pytest.raises(DispatchConflict, match="storico"):
        service.request_job(db, lot.id, "reconcile", actor_id=1)
    service.bind_account(db, lot.id, 1, actor_id=1)
    event = db.scalar(select(PosteDispatchEvent).where(PosteDispatchEvent.kind == "account_bound"))
    assert event.actor_username == "poste-1" and event.detail["poste_username"] == "account-1"
    seed_account(db, 2, "other")
    with pytest.raises(DispatchConflict, match="cambiato"):
        service.bind_account(db, lot.id, 2, actor_id=1)
    assert service.request_job(db, lot.id, "reconcile", actor_id=1).credential_id == 1


def test_cross_lot_or_missing_jobs_cannot_attribute_an_upload(db, tmp_path):
    first, a = new_lot(db, tmp_path)
    second, b = new_lot(db, tmp_path)
    complete_jobs(db)
    a.status = b.status = "address_ok"
    with pytest.raises(DispatchConflict):
        work.mark_draft_creating(db, a.id, job_id=999)
    wrong = service.request_job(db, second.id, "drafts", actor_id=1)
    with pytest.raises(DispatchConflict):
        work.mark_draft_creating(db, a.id, job_id=wrong.id)
    other_mode = service.request_job(db, first.id, "reconcile", actor_id=1)
    with pytest.raises(DispatchConflict, match="caricamento"):
        work.mark_draft_creating(db, a.id, job_id=other_mode.id)
    assert a.upload_requested_by_user_id is None and a.status == "address_ok"


def test_the_same_notice_cannot_be_uploaded_with_a_second_account(db, tmp_path):
    _, item = new_lot(db, tmp_path)
    seed_account(db, 2, "other")
    with pytest.raises(DispatchConflict, match="altro lotto"):
        service.create_lot(
            db, title="Duplicate", batch_item_ids=[item.batch_item_id], credential_id=2, actor_id=1
        )


def test_upload_without_an_identifiable_operator_is_rejected(db, tmp_path):
    lot, item = new_lot(db, tmp_path)
    complete_jobs(db)
    item.status = "address_ok"
    job = service.request_job(db, lot.id, "drafts", actor_id=1)
    job.requested_by_user_id = None
    with pytest.raises(DispatchConflict, match="Operatore GAIA del caricamento"):
        work.mark_draft_creating(db, item.id, job_id=job.id)
    assert item.status == "address_ok" and item.upload_job_id is None


def test_used_account_cannot_be_deleted(db, tmp_path):
    new_lot(db, tmp_path)
    credential = accounts.selected_account(db, 1)
    with pytest.raises(IntegrityError), db.begin_nested():
        db.delete(credential)
        db.flush()


def test_archive_observation_uses_its_operator_without_inventing_the_manual_sender(
    db, tmp_path, monkeypatch
):
    seed_user(db, 2)
    lot, item = new_lot(db, tmp_path)
    complete_jobs(db)
    job = service.request_job(db, lot.id, "reconcile", actor_id=2)
    actors = []
    original = reconcile._import_detail

    def capture(session, dispatch, invio, detail, actor):
        actors.append(actor)
        return original(session, dispatch, invio, detail, actor)

    monkeypatch.setattr(reconcile, "_import_detail", capture)
    monkeypatch.setattr(reconcile, "link_register", lambda *_args: None)
    reconcile.record_sent(
        db,
        item.id,
        job_id=job.id,
        id_invio="456",
        detail_html=DETAIL_PAGE.format(id="456", name=item.shipment_name),
    )
    assert actors == [2] and item.status == "sent"


def test_archive_observation_with_missing_operator_is_rejected(db, tmp_path):
    lot, item = new_lot(db, tmp_path)
    complete_jobs(db)
    job = service.request_job(db, lot.id, "reconcile", actor_id=1)
    job.requested_by_user_id = None
    with pytest.raises(DispatchConflict, match="Operatore"):
        reconcile.record_sent(db, item.id, job_id=job.id, id_invio="456", detail_html="unused")
