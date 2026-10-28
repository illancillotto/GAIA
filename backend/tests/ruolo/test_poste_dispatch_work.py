from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloTributiRegisteredMail
from app.modules.ruolo.notice_register_models import NoticeAttempt, NoticeDocument, NoticePosition
from app.modules.ruolo.poste_dispatch_models import PosteDispatchEvent, PosteDispatchItem
from app.modules.ruolo.services import poste_dispatch as service
from app.modules.ruolo.services import poste_dispatch_reconcile as reconcile
from app.modules.ruolo.services import poste_dispatch_views as views
from app.modules.ruolo.services import poste_dispatch_work as work
from app.modules.ruolo.services.poste_dispatch_state import DispatchConflict, DispatchNotFound

from .poste_dispatch_fixtures import (
    DETAIL_PAGE,
    PDF,
    dispatch_engine,
    payload,
    seed_batch_item,
    seed_user,
)
from .test_notice_register import _avviso, _metadata

ORISTANO = {
    "street": "VIA CAGLIARI",
    "number": "170",
    "city": "ORISTANO",
    "province": "OR",
    "zipcode": "09170",
}


@pytest.fixture
def db():
    engine = dispatch_engine()
    with Session(engine) as session:
        seed_user(session)
        yield session
    engine.dispose()


def _item(db, tmp_path, status="address_ok", number="020217801062586"):
    batch_item = seed_batch_item(db, tmp_path, payload_json=payload(number))
    lot = service.create_lot(db, title="Lotto", batch_item_ids=[batch_item.id], actor_id=1)
    item = db.scalar(select(PosteDispatchItem).where(PosteDispatchItem.lot_id == lot.id))
    item.status = status
    db.flush()
    return lot, item


def _row(name="GAIA 020217801062586", status="PREZZATO", draft_id="12269236"):
    return work.DraftRow(draft_id=draft_id, name=name, status=status, price=Decimal("5.43"))


def _events(db, item):
    return [
        event.kind
        for event in db.scalars(
            select(PosteDispatchEvent).where(PosteDispatchEvent.item_id == item.id)
        )
    ]


def test_lot_items_lists_only_requested_statuses(db, tmp_path):
    lot, item = _item(db, tmp_path)
    [listed] = work.lot_items(db, lot.id, ("address_ok",))
    assert listed.id == item.id and listed.recipient["city"] == "ORISTANO"
    assert work.lot_items(db, lot.id, ("sent",)) == []
    with pytest.raises(DispatchNotFound):
        work.lot_items(db, uuid4(), ("sent",))
    assert work.artifact_for_upload(db, item.id) == PDF


def test_address_result_accepts_a_directory_match_or_asks_for_review(db, tmp_path):
    _, found = _item(db, tmp_path, "address_pending", "020217801000001")
    work.record_address(db, found.id, job_id=7, suggestion=ORISTANO, reason="ok", labels=[])
    assert (
        found.status == "address_ok"
        and found.poste_address["label"] == "VIA CAGLIARI 170, ORISTANO (OR), 09170"
    )
    _, missing = _item(db, tmp_path, "address_pending", "020217801000002")
    work.record_address(
        db, missing.id, job_id=7, suggestion=None, reason="Nessun indirizzo", labels=list("abcdef")
    )
    assert missing.status == "address_review" and missing.address_review["suggestions"] == list(
        "abcde"
    )
    work.record_address(db, missing.id, job_id=7, suggestion=ORISTANO, reason="late", labels=[])
    assert missing.status == "address_review"


def test_submission_is_persisted_before_continua_and_only_from_ready_states(db, tmp_path):
    _, item = _item(db, tmp_path)
    item.error_detail = "old"
    assert work.mark_draft_creating(db, item.id, job_id=1) is True
    assert item.status == "draft_creating" and item.error_detail is None
    assert work.mark_draft_creating(db, item.id, job_id=1) is False


def test_draft_rows_set_id_price_and_priced_state(db, tmp_path):
    _, item = _item(db, tmp_path, "draft_creating")
    work.record_draft_row(db, item.id, job_id=1, row=_row(status="IN ATTESA DI LAVORAZIONE"))
    assert item.status == "draft_created" and item.poste_draft_id == "12269236"
    created_at = item.draft_created_at
    work.record_draft_row(db, item.id, job_id=1, row=_row())
    assert item.status == "draft_priced" and item.price_amount == Decimal("5.43")
    assert item.draft_created_at == created_at
    work.record_draft_row(db, item.id, job_id=1, row=_row())
    assert _events(db, item).count("draft_observed") == 2


def test_a_cancellation_request_survives_draft_observations(db, tmp_path):
    _, item = _item(db, tmp_path, "cancel_requested")
    work.record_draft_row(db, item.id, job_id=1, row=_row())
    assert item.status == "cancel_requested" and item.poste_draft_id == "12269236"


def test_failures_before_and_after_continua_are_distinguished(db, tmp_path):
    _, item = _item(db, tmp_path, "draft_creating")
    work.record_draft_failure(db, item.id, job_id=1, submitted=True, error="x" * 2000)
    assert item.status == "draft_uncertain" and len(item.error_detail) == 1000
    work.record_draft_failure(db, item.id, job_id=1, submitted=False, error="late")
    assert item.status == "draft_uncertain"
    _, other = _item(db, tmp_path, "address_ok", "020217801000003")
    work.record_draft_failure(db, other.id, job_id=1, submitted=False, error="modulo")
    assert other.status == "draft_error"


def test_snapshot_matches_drafts_by_name_and_reports_foreign_and_duplicate_ones(db, tmp_path):
    lot, item = _item(db, tmp_path, "draft_created")
    rows = [_row(), _row(name="ROSSI MARIO", draft_id="1")]
    assert work.apply_drafts_snapshot(db, lot.id, job_id=3, rows=rows) == []
    assert item.status == "draft_priced"
    assert lot.portal_snapshot["foreign_drafts"] == [
        {"draft_id": "1", "name": "ROSSI MARIO", "status": "PREZZATO"}
    ]
    rows = [_row(), _row(draft_id="2")]
    assert work.apply_drafts_snapshot(db, lot.id, job_id=3, rows=rows) == []
    assert (
        lot.portal_snapshot["duplicate_names"] == [item.shipment_name]
        and "Più bozze" in item.error_detail
    )
    assert work.apply_drafts_snapshot(db, lot.id, job_id=3, rows=[]) == [item.id]


def test_missing_drafts_become_recreatable_or_complete_a_cancellation(db, tmp_path):
    _, item = _item(db, tmp_path, "draft_priced")
    item.poste_draft_id = "1"
    work.record_missing(db, item.id, job_id=1)
    assert item.status == "draft_missing" and item.poste_draft_id is None
    item.status = "cancel_requested"
    work.record_missing(db, item.id, job_id=1)
    assert item.status == "cancelled" and item.active_key is None


def test_deleted_drafts_release_the_notice(db, tmp_path):
    _, item = _item(db, tmp_path, "cancel_requested")
    work.record_deleted(db, item.id, job_id=1)
    assert item.status == "cancelled" and item.artifact is None and item.active_source_key is None


def test_anomalies_keep_the_status_and_are_audited(db, tmp_path):
    _, item = _item(db, tmp_path, "draft_priced")
    work.record_anomaly(db, item.id, job_id=1, message="Archivio non letto")
    assert item.status == "draft_priced" and item.error_detail == "Archivio non letto"
    assert "portal_anomaly" in _events(db, item)


def _document(db, item):
    document = NoticeDocument(
        source_system="gaia_batch_item",
        source_key=str(item.batch_item_id),
        document_number=item.notice_number,
        tax_code="RSSMRA70A01G113X",
        original_json={},
    )
    db.add(document)
    db.flush()
    return document


def test_archive_detail_marks_the_item_sent_and_links_the_register(db, tmp_path, monkeypatch):
    _, item = _item(db, tmp_path, "draft_priced")
    document = _document(db, item)
    calls = []
    monkeypatch.setattr(reconcile, "associate_registered_mail", lambda *args: calls.append(args))
    reconcile.record_sent(
        db,
        item.id,
        job_id=5,
        id_invio="12269236",
        detail_html=DETAIL_PAGE.format(id="12269236", name=item.shipment_name),
    )
    mail = db.get(RuoloTributiRegisteredMail, item.registered_mail_id)
    assert item.status == "sent" and item.tracking_number == mail.tracking_number == "619591492509"
    assert item.artifact is None and item.active_key == item.shipment_name
    assert item.error_detail is None and calls[0][1:3] == (document.id, mail.id)
    assert calls[0][3].expected_version == document.version and "Posta Online" in calls[0][3].reason


def test_register_problems_are_reported_without_blocking_the_sent_state(db, tmp_path, monkeypatch):
    _, item = _item(db, tmp_path, "draft_priced")
    html = DETAIL_PAGE.format(id="9", name=item.shipment_name)
    reconcile.record_sent(db, item.id, job_id=5, id_invio="9", detail_html=html)
    assert item.status == "sent" and "collegare la raccomandata a mano" in item.error_detail
    _, other = _item(db, tmp_path, "draft_priced", "020217801000009")
    _document(db, other)

    def refuse(*_):
        raise ValueError("CF del documento non coerente")

    monkeypatch.setattr(reconcile, "associate_registered_mail", refuse)
    reconcile.record_sent(
        db,
        other.id,
        job_id=5,
        id_invio="10",
        detail_html=DETAIL_PAGE.format(id="10", name=other.shipment_name),
    )
    assert (
        other.status == "sent"
        and other.error_detail == "Registro non aggiornato: CF del documento non coerente"
    )


def test_a_detail_with_another_name_is_rejected(db, tmp_path):
    _, item = _item(db, tmp_path, "draft_priced")
    with pytest.raises(DispatchConflict, match="non coerente"):
        reconcile.record_sent(
            db,
            item.id,
            job_id=5,
            id_invio="11",
            detail_html=DETAIL_PAGE.format(id="11", name="ROSSI MARIO"),
        )
    assert item.status == "draft_priced"


def test_views_summarize_lots_prices_and_draft_expiry(db, tmp_path):
    lot, item = _item(db, tmp_path, "draft_priced")
    item.price_amount, item.draft_created_at = Decimal("5.43"), datetime(2026, 10, 28, tzinfo=UTC)
    db.flush()
    [summary], total = views.list_lots(db, page=1, page_size=10)
    assert total == 1 and summary.counts == {"draft_priced": 1} and summary.priced_total == 5.43
    detail = views.lot_detail(db, lot.id)
    assert detail.draft_expires_at.replace(tzinfo=UTC) == datetime(
        2026, 10, 28, tzinfo=UTC
    ) + timedelta(days=7)
    assert detail.active_job.mode == "poste_dispatch_addresses" and detail.items[0].id == item.id
    assert [event.kind for event in detail.events][-2:] == ["job_addresses_queued", "lot_created"]
    assert views.item_document(db, lot.id, item.id) == PDF
    item.status = "address_ok"
    db.flush()
    assert views.lot_detail(db, lot.id).draft_expires_at is None


def test_sent_item_becomes_an_attempt_in_the_notice_register(db, tmp_path):
    _, item = _item(db, tmp_path, "draft_priced")
    document = _document(db, item)
    subject_id = uuid4()
    db.execute(_metadata().tables["ana_subjects"].insert().values(id=subject_id))
    avviso = _avviso(db, 2021)
    avviso.codice_fiscale_raw, avviso.subject_id = document.tax_code, subject_id
    db.add(
        NoticePosition(
            document_id=document.id,
            source_namespace="incass",
            source_reference="020210000000001",
            tax_year=2021,
            avviso_id=avviso.id,
        )
    )
    db.flush()
    html = DETAIL_PAGE.format(id="12", name=item.shipment_name)
    reconcile.record_sent(db, item.id, job_id=5, id_invio="12", detail_html=html)
    attempt = db.scalar(select(NoticeAttempt).where(NoticeAttempt.document_id == document.id))
    assert item.error_detail is None and attempt.tracking_code == "619591492509"
    assert (
        attempt.registered_mail_id == item.registered_mail_id and attempt.channel == "raccomandata"
    )
