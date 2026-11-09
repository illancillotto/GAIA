"""One financial avviso may be notified separately to its explicitly approved heirs."""

import hashlib
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem
from app.modules.ruolo.services import poste_dispatch as dispatch
from app.modules.ruolo.services import poste_dispatch_duplicates as duplicates
from app.modules.ruolo.services import poste_dispatch_final_check as final_check
from app.modules.ruolo.services import poste_dispatch_recipient as recipients
from app.modules.ruolo.services import poste_dispatch_work as work
from app.modules.ruolo.services import poste_preparation, solleciti_workspace
from app.modules.ruolo.services.poste_dispatch_state import DispatchConflict

from .poste_dispatch_fixtures import PDF, payload, seed_account, seed_batch_item
from .test_poste_dispatch_accounts import complete_jobs
from .test_poste_dispatch_duplicates import job_for, snapshot
from .test_poste_dispatch_service import db as db

NUMBER = "020210003162580"


def heir_payload(name="Bianchi Anna", **overrides):
    recipient = {
        "name": name,
        "name_extra": "in qualità di erede di Rossi Mario",
        "address": "VIA ROMA 1",
        "cap": "09170",
        "city": "ORISTANO",
        "province": "OR",
    }
    delivery = {
        "kind": "heir",
        "source_item_id": str(uuid4()),
        "pdf_sha256": hashlib.sha256(PDF).hexdigest(),
        "recipient": recipient,
        "reference": recipients.heir_shipment_name(NUMBER, recipient),
    } | overrides
    return payload(NUMBER, heir_delivery=delivery)


def make_heir(db, tmp_path, name="Bianchi Anna", **overrides):
    item = seed_batch_item(db, tmp_path, payload_json=heir_payload(name, **overrides))
    lot = poste_preparation.prepare(db, item_ids=[item.id], credential_id=1, actor_id=1)
    attempt = db.scalar(select(PosteDispatchItem).where(PosteDispatchItem.batch_item_id == item.id))
    return item, lot, attempt


def test_approved_recipient_and_pdf_have_a_stable_distinct_poste_reference():
    source = heir_payload()
    result = recipients.recipient_from_payload(source)
    name = recipients.shipment_name(NUMBER, result)
    assert name.startswith(f"GAIA {NUMBER} E") and len(name) <= 40
    assert result["name"] == "BIANCHI ANNA"
    assert result["name_extra"] == "IN QUALITÀ DI EREDE DI ROSSI MARIO"
    assert result["heir_pdf_sha256"] == hashlib.sha256(PDF).hexdigest()
    assert result["heir_source_item_id"] == source["heir_delivery"]["source_item_id"]
    assert recipients.recipient_problems(result) == []
    assert recipients.heir_shipment_name(NUMBER, {**result, "name": " bianchi   anna "}) == name
    assert source["notice_number"] == NUMBER


@pytest.mark.parametrize(
    "overrides",
    [
        {"kind": "ordinary"},
        {"source_item_id": "not-a-uuid"},
        {"pdf_sha256": "wrong"},
        {"reference": "GAIA fake"},
    ],
)
def test_invalid_or_forged_approval_is_rejected(overrides):
    with pytest.raises(ValueError):
        recipients.recipient_from_payload(heir_payload(**overrides))


def test_distinct_heirs_survive_workspace_deduplication_and_have_independent_ownership(
    db, tmp_path
):
    ordinary = seed_batch_item(db, tmp_path, payload_json=payload(NUMBER))
    original_lot = dispatch.create_lot(
        db, title="Originale", batch_item_ids=[ordinary.id], credential_id=1, actor_id=1
    )
    original = db.scalar(
        select(PosteDispatchItem).where(PosteDispatchItem.lot_id == original_lot.id)
    )
    original.status = "sent"
    original.artifact = None
    first, a, attempt_a = make_heir(db, tmp_path)
    second, b, attempt_b = make_heir(db, tmp_path, "Bianchi Bruno")
    assert attempt_a.notice_number == attempt_b.notice_number == original.notice_number == NUMBER
    assert len({attempt_a.active_key, attempt_b.active_key, original.active_key}) == 3
    assert duplicates.duplicate_report(db)["findings"] == []
    complete_jobs(db)
    first.created_at = second.created_at
    db.flush()
    filters = {"q": "", "year": 2021, "account": "all", "stage": "all", "page": 1, "page_size": 100}
    view = solleciti_workspace.workspace(db, filters)
    assert view["total"] == 3
    by_id = {row["item_id"]: row for row in view["items"]}
    assert by_id[first.id]["lot_id"] == a.id and by_id[second.id]["lot_id"] == b.id
    assert by_id[ordinary.id]["stage"] == "sent"
    assert [r["id"] for r in by_id[first.id]["poste_dispatches"]] == [attempt_a.id]
    expected = final_check._expected_items(db, [original_lot, a, b])
    assert expected[0]["notice_name"] == f"GAIA {NUMBER}"
    with pytest.raises(DispatchConflict, match="già assegnato"):
        poste_preparation.prepare(db, item_ids=[first.id], credential_id=1, actor_id=1)


def test_a_second_batch_copy_of_the_same_heir_is_reserved_globally(db, tmp_path):
    _first, lot, attempt = make_heir(db, tmp_path)
    second = seed_batch_item(db, tmp_path, payload_json=heir_payload())
    seed_account(db, 2, "other-account")
    with pytest.raises(DispatchConflict, match="già assegnato"):
        poste_preparation.prepare(db, item_ids=[second.id], credential_id=2, actor_id=1)
    job = job_for(db, lot, attempt)
    snapshot(lot, [(attempt.shipment_name, "123")])
    assert work.mark_draft_creating(db, attempt.id, job_id=job.id) is True
    assert attempt.upload_requested_by_user_id == 1


def test_final_check_tracks_each_heir_and_preserves_cross_account_duplicate_guard(db, tmp_path):
    _, a, attempt_a = make_heir(db, tmp_path)
    _, b, attempt_b = make_heir(db, tmp_path, "Bianchi Bruno")
    attempt_a.status = attempt_b.status = "draft_priced"
    expected = final_check._expected_items(db, [a, b])
    assert {r["notice_name"] for r in expected} == {
        attempt_a.shipment_name,
        attempt_b.shipment_name,
    }
    seed_account(db, 2, "other-account")
    ordinary = seed_batch_item(db, tmp_path, payload_json=payload("OTHER"))
    other_lot = dispatch.create_lot(
        db, title="Other", batch_item_ids=[ordinary.id], credential_id=2, actor_id=1
    )
    snapshot(other_lot, [(attempt_a.shipment_name, "wrong-account")])
    job = job_for(db, a, attempt_a)
    assert work.mark_draft_creating(db, attempt_a.id, job_id=job.id) is False
    assert attempt_a.status == "address_review" and attempt_a.address_review["duplicate_check"]
    assert attempt_b.status == "draft_priced"


def test_heir_recipient_cannot_be_edited_without_a_new_approved_pdf(db, tmp_path):
    _, lot, attempt = make_heir(db, tmp_path)
    with pytest.raises(DispatchConflict, match="aggiornare prima il PDF"):
        dispatch.update_recipient(db, lot.id, attempt.id, {"name": "Different heir"}, actor_id=1)
    assert attempt.recipient["name"] == "BIANCHI ANNA"


def test_changed_pdf_is_rejected_both_when_preparing_and_before_upload(db, tmp_path):
    item = seed_batch_item(db, tmp_path, payload_json=heir_payload(pdf_sha256="0" * 64))
    with pytest.raises(DispatchConflict, match="PDF non valido"):
        dispatch.create_lot(
            db, title="Wrong PDF", batch_item_ids=[item.id], credential_id=1, actor_id=1
        )
    _, lot, attempt = make_heir(db, tmp_path)
    job = job_for(db, lot, attempt)
    attempt.artifact_sha256 = "1" * 64
    assert work.mark_draft_creating(db, attempt.id, job_id=job.id) is False
    assert attempt.status == "address_review"


def test_generation_reuses_the_ordinary_notice_instead_of_a_newer_heir_copy(
    db, tmp_path, monkeypatch
):
    from datetime import UTC, datetime, timedelta

    from app.modules.ruolo.services import solleciti_generation

    financial_id = str(uuid4())
    ordinary = seed_batch_item(db, tmp_path, payload_json=payload(NUMBER))
    heir, _, _ = make_heir(db, tmp_path)
    ordinary.avviso_ids_json = heir.avviso_ids_json = [financial_id]
    ordinary.created_at = datetime.now(UTC) - timedelta(days=1)
    heir.created_at = datetime.now(UTC)
    db.flush()
    monkeypatch.setattr(
        solleciti_generation.generation,
        "_candidates",
        lambda *_: [{"avvisi": [{"id": financial_id}]}],
    )
    result = solleciti_generation.generate(
        db, year=2021, tax_code=ordinary.codice_fiscale, actor_id=1
    )
    assert result["reused"] == [ordinary.id]
    assert result["created"] == []


def test_batch_overview_shows_each_recipients_own_shipment(db, tmp_path, monkeypatch):
    from app.modules.ruolo.services import reminder_batch_overview

    ordinary = seed_batch_item(db, tmp_path, payload_json=payload(NUMBER))
    lot = dispatch.create_lot(
        db, title="Originale", batch_item_ids=[ordinary.id], credential_id=1, actor_id=1
    )
    original = db.scalar(select(PosteDispatchItem).where(PosteDispatchItem.lot_id == lot.id))
    original.status = "sent"
    original.artifact = None
    heir, _, attempt = make_heir(db, tmp_path)
    db.flush()
    monkeypatch.setattr(reminder_batch_overview, "pec_sent_avvisi", lambda *_: set())
    result = reminder_batch_overview.batch_overview(db, [ordinary.batch_id, heir.batch_id])
    rows = {row["item_id"]: row for items in result.values() for row in items}
    assert [row["id"] for row in rows[ordinary.id]["poste_dispatches"]] == [original.id]
    assert [row["id"] for row in rows[heir.id]["poste_dispatches"]] == [attempt.id]
