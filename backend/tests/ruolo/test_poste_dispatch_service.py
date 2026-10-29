from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.posta_online import PostaOnlineRegisteredMailSyncJob
from app.modules.ruolo.poste_dispatch_models import PosteDispatchEvent, PosteDispatchItem
from app.modules.ruolo.services import poste_dispatch as service
from app.modules.ruolo.services.poste_dispatch_state import (
    DispatchConflict,
    DispatchNotFound,
    attach_artifact,
    verified_artifact,
)

from .poste_dispatch_fixtures import PDF, dispatch_engine, payload, seed_batch_item, seed_user


@pytest.fixture
def db():
    engine = dispatch_engine()
    with Session(engine) as session:
        seed_user(session)
        yield session
    engine.dispose()


def _lot(db, tmp_path, **payload_overrides):
    number = f"0202178010625{len(_jobs(db)):02d}"
    items = [seed_batch_item(db, tmp_path, payload_json=payload(number, **payload_overrides))]
    lot = service.create_lot(
        db, title=" Solleciti 2021 ", batch_item_ids=[item.id for item in items], actor_id=1
    )
    return lot, list(
        db.scalars(select(PosteDispatchItem).where(PosteDispatchItem.lot_id == lot.id))
    )


def _jobs(db):
    return list(db.scalars(select(PostaOnlineRegisteredMailSyncJob)))


def test_lot_snapshots_pdf_and_recipient_and_queues_the_address_check(db, tmp_path):
    lot, [item] = _lot(db, tmp_path)
    assert lot.title == "Solleciti 2021" and lot.postal_options["tax_code"] is False
    assert item.shipment_name == item.active_key == "GAIA 020217801062500"
    assert item.status == "address_pending" and item.artifact == PDF
    assert item.recipient["city"] == "ORISTANO" and len(item.artifact_sha256) == 64
    [job] = _jobs(db)
    assert job.mode == "poste_dispatch_addresses" and job.payload_json == {"lot_id": str(lot.id)}
    kinds = [event.kind for event in db.scalars(select(PosteDispatchEvent))]
    assert kinds == ["lot_created", "job_addresses_queued"]


def test_incomplete_recipients_wait_for_the_operator_without_a_job(db, tmp_path):
    _, [item] = _lot(db, tmp_path, display_name="", avvisi=[])
    assert item.status == "address_review"
    assert item.address_review["problems"] == ["name: mancante", "address: mancante"]
    assert _jobs(db) == []


@pytest.mark.parametrize("ids", ["empty", "duplicate", "too_many"])
def test_lot_size_and_uniqueness_are_enforced(db, tmp_path, ids):
    item = seed_batch_item(db, tmp_path)
    selected = {
        "empty": [],
        "duplicate": [item.id, item.id],
        "too_many": [uuid4() for _ in range(51)],
    }[ids]
    with pytest.raises(DispatchConflict, match="da 1 a 50"):
        service.create_lot(db, title="x", batch_item_ids=selected, actor_id=1)


def test_unknown_items_are_rejected(db):
    with pytest.raises(DispatchNotFound):
        service.create_lot(db, title="x", batch_item_ids=[uuid4()], actor_id=1)


@pytest.mark.parametrize(
    "overrides,message",
    [
        ({"status": "draft"}, "non generato"),
        ({"content": b"PK docx"}, "PDF non valido"),
    ],
)
def test_only_final_pdf_reminders_can_be_prepared(db, tmp_path, overrides, message):
    item = seed_batch_item(db, tmp_path, **overrides)
    with pytest.raises(DispatchConflict, match=message):
        service.create_lot(db, title="x", batch_item_ids=[item.id], actor_id=1)


def test_a_notice_cannot_be_in_two_active_lots(db, tmp_path):
    _, [item] = _lot(db, tmp_path)
    with pytest.raises(DispatchConflict, match="già in un altro lotto"):
        service.create_lot(db, title="y", batch_item_ids=[item.batch_item_id], actor_id=1)


def test_remote_nas_documents_are_downloaded(db, tmp_path, monkeypatch):
    item = seed_batch_item(db, tmp_path)
    monkeypatch.setattr(
        service.repo, "reminder_batch_item_document_path", lambda _: Path("/volume1/x.pdf")
    )
    monkeypatch.setattr(
        service.repo, "read_remote_reminder_document", lambda path: PDF + str(path).encode()
    )
    assert service.read_batch_document(db, item, 1) == PDF + b"/volume1/x.pdf"


def test_a_docx_reminder_is_not_a_final_pdf(db, tmp_path):
    document = tmp_path / "sollecito.docx"
    document.write_bytes(b"PK docx")
    item = seed_batch_item(db, tmp_path, generated_document_path=str(document))
    with pytest.raises(DispatchConflict, match="senza PDF"):
        service.create_lot(db, title="x", batch_item_ids=[item.id], actor_id=1)


def test_candidates_exclude_active_notices_and_filter_by_text(db, tmp_path):
    first = seed_batch_item(db, tmp_path, display_name="BIANCHI ANNA")
    second = seed_batch_item(db, tmp_path, title="Lotto Cabras")
    seed_batch_item(db, tmp_path, status="failed")
    rows, total = service.list_candidates(db, q=None, page=1, page_size=10)
    assert total == 2 and {row[0].id for row in rows} == {first.id, second.id}
    service.create_lot(db, title="x", batch_item_ids=[first.id], actor_id=1)
    rows, total = service.list_candidates(db, q="cabras", page=1, page_size=10)
    assert total == 1 and rows[0][0].id == second.id and rows[0][1] == "Lotto Cabras"


def test_jobs_need_an_open_lot_ready_items_and_no_other_job(db, tmp_path):
    lot, _ = _lot(db, tmp_path)
    with pytest.raises(DispatchConflict, match="già un'operazione"):
        service.request_job(db, lot.id, "reconcile", actor_id=1)
    _jobs(db)[0].status = "succeeded"
    with pytest.raises(DispatchConflict, match="Nessun avviso"):
        service.request_job(db, lot.id, "drafts", actor_id=1)
    assert (
        service.request_job(db, lot.id, "reconcile", actor_id=1).mode == "poste_dispatch_reconcile"
    )
    with pytest.raises(DispatchNotFound):
        service.request_job(db, lot.id, "send", actor_id=1)


def test_jobs_of_other_lots_do_not_block(db, tmp_path):
    lot, _ = _lot(db, tmp_path)
    _jobs(db)[0].payload_json = {"lot_id": str(uuid4())}
    assert service.active_job(db, lot.id) is None


def test_recipient_correction_restarts_the_address_check(db, tmp_path):
    lot, [item] = _lot(db, tmp_path)
    fields = dict(item.recipient, address="via roma 1")
    service.update_recipient(db, lot.id, item.id, fields, actor_id=1)
    assert item.status == "address_pending" and item.recipient["address"] == "VIA ROMA 1"
    with pytest.raises(DispatchConflict, match="cap"):
        service.update_recipient(db, lot.id, item.id, fields | {"cap": "1"}, actor_id=1)
    item.status = "draft_priced"
    with pytest.raises(DispatchConflict, match="eliminare prima"):
        service.update_recipient(db, lot.id, item.id, fields, actor_id=1)


def test_manual_address_is_accepted_only_from_review_with_complete_data(db, tmp_path):
    lot, [item] = _lot(db, tmp_path)
    with pytest.raises(DispatchConflict, match="solo per avvisi da rivedere"):
        service.accept_manual_address(db, lot.id, item.id, actor_id=1)
    item.status = "address_review"
    item.recipient = dict(item.recipient, cap="")
    with pytest.raises(DispatchConflict, match="cap"):
        service.accept_manual_address(db, lot.id, item.id, actor_id=1)
    item.recipient = dict(item.recipient, cap="09170")
    service.accept_manual_address(db, lot.id, item.id, actor_id=1)
    assert item.status == "address_ok" and item.poste_address == {"mode": "manual"}


def test_cancel_frees_the_notice_or_asks_the_worker_to_delete_the_draft(db, tmp_path):
    lot, [item] = _lot(db, tmp_path)
    service.cancel_item(db, lot.id, item.id, actor_id=1)
    assert item.status == "cancelled" and item.active_key is item.artifact is None
    lot, [item] = _lot(db, tmp_path)
    item.status = "draft_priced"
    service.cancel_item(db, lot.id, item.id, actor_id=1)
    assert item.status == "cancel_requested" and item.active_key is not None
    with pytest.raises(DispatchConflict, match="già spedito"):
        service.cancel_item(db, lot.id, item.id, actor_id=1)
    with pytest.raises(DispatchNotFound):
        service.cancel_item(db, uuid4(), item.id, actor_id=1)


def test_upload_refuses_a_missing_or_altered_pdf(db, tmp_path):
    _, [item] = _lot(db, tmp_path)
    assert verified_artifact(item) == PDF
    item.artifact = PDF + b"tampered"
    with pytest.raises(DispatchConflict, match="alterato"):
        verified_artifact(item)
    attach_artifact(item, b"%PDF new")
    assert verified_artifact(item) == b"%PDF new"
