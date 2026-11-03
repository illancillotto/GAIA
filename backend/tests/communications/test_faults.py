"""Negative paths: current-data checks and artifact failures stay fail-closed."""

from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import literal, select

from app.modules.communications import models, outbox, policy, ruolo_source, store, transports
from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.notice_register_models import NoticeDocument
from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem, PosteDispatchLot
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaSubject

from .conftest import approved, create, pdf
from .test_worker_receipts import queued


def test_source_identity_files_history_and_contacts(api, monkeypatch):
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        with pytest.raises(policy.Missing):
            ruolo_source.source_item(db, uuid4())
        original = item.generated_document_path
        item.generated_document_path = None
        with pytest.raises(policy.Conflict):
            ruolo_source.read_pdf(item)
        item.generated_document_path = original
        monkeypatch.setattr(
            ruolo_source.repo, "is_remote_reminder_document_path", lambda path: True
        )
        monkeypatch.setattr(ruolo_source.repo, "read_remote_reminder_document", lambda path: pdf())
        assert ruolo_source.read_pdf(item) == pdf()
        monkeypatch.setattr(
            ruolo_source.repo, "is_remote_reminder_document_path", lambda path: False
        )
        monkeypatch.setattr(
            Path, "stat", lambda path: SimpleNamespace(st_size=policy.MAX_BYTES + 1)
        )
        with pytest.raises(policy.Conflict):
            ruolo_source.read_pdf(item)
    monkeypatch.undo()


def test_linked_contacts_are_not_inferred_from_names(api):
    with api.session() as db:
        subject = AnagraficaSubject(source_name_raw="Synthetic")
        db.add(subject)
        db.flush()
        person = AnagraficaPerson(
            subject_id=subject.id,
            cognome="Test",
            nome="Synthetic",
            codice_fiscale="SYNTHETIC",
            email="person@example.org",
        )
        company = AnagraficaCompany(
            subject_id=subject.id,
            ragione_sociale="Synthetic",
            partita_iva="00000000000",
            email_pec="pec@example.org",
        )
        db.add_all([person, company])
        db.flush()
        item = ruolo_source.source_item(db, api.source_id)
        item.subject_id = subject.id
        assert ruolo_source.contacts(db, item) == {
            "email": "person@example.org",
            "pec": "pec@example.org",
        }


@pytest.mark.parametrize("change", ["empty", "unknown", "no_canonical", "poste"])
def test_invalid_canonical_source_or_poste_reservation_blocks(api, change):
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        if change == "empty":
            item.avviso_ids_json = []
        elif change == "unknown":
            item.avviso_ids_json = [str(uuid4())]
        elif change == "no_canonical":
            document = db.scalar(
                select(NoticeDocument).where(NoticeDocument.source_system == "gaia_batch_item")
            )
            document.document_number = "different"
        else:
            lot = PosteDispatchLot(title="Synthetic", created_by=1, postal_options={})
            db.add(lot)
            db.flush()
            db.add(
                PosteDispatchItem(
                    lot_id=lot.id,
                    batch_item_id=item.id,
                    notice_number=item.payload_json["notice_number"],
                    shipment_name="Synthetic",
                    active_key="Synthetic",
                    active_source_key=str(item.id),
                    status="address_pending",
                    recipient={},
                    artifact_sha256="a" * 64,
                    artifact_size=0,
                )
            )
        db.commit()
    response = api.client.get(f"/communications/ruolo/candidates/{api.source_id}/eligibility")
    assert response.status_code == 409


def test_filters_current_states_pagination_and_empty_results(api, monkeypatch):
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        batch = item.batch_id
    base = "/communications/ruolo/candidates?channel=pec"
    assert api.client.get(base).json()["items"][0]["payment_state"] == "unpaid"
    assert api.client.get(base + "&q=ROSSI").json()["total"] == 1
    assert api.client.get(base + "&q=unknown").json()["total"] == 0
    assert (
        api.client.get(
            base + f"&batch_id={batch}&has_contact=false&has_pec=false&has_email=false"
        ).json()["total"]
        == 1
    )
    assert api.client.get(base + "&has_contact=true").json()["total"] == 0
    assert (
        api.client.get(
            base + "&document_state=generated&notification_state=nessuna_evidenza"
        ).json()["total"]
        == 1
    )
    assert (
        api.client.get(base + "&date_from=2000-01-01&date_to=2100-01-01&page=2&page_size=1").json()[
            "items"
        ]
        == []
    )
    # Exercise the SQL payment filter against a controlled accounting subquery.
    monkeypatch.setattr(
        ruolo_source.repo,
        "_base_tributi_query",
        lambda: (select(RuoloAvviso), None, literal("unpaid")),
    )
    assert api.client.get(base + "&payment_state=unpaid").json()["total"] == 1
    assert api.client.get(base + "&payment_state=paid").json()["total"] == 0
    value = approved(api)
    assert (
        api.client.get(base + f"&account_id={value['account_id']}&state=approved").json()["total"]
        == 1
    )
    assert (
        api.client.get(f"/communications/ruolo/candidates/{api.source_id}/eligibility").status_code
        == 409
    )


def test_direct_eligibility_get_is_not_an_authorization(api):
    response = api.client.get(f"/communications/ruolo/candidates/{api.source_id}/eligibility")
    assert response.status_code == 200 and not response.json()["authorizes_dispatch"]
    response = api.client.post(
        "/communications/messages",
        json={
            "source_entity_id": str(api.source_id),
            "channel": "email",
            "recipient": "recipient@example.org",
            "subject": "S",
            "body": "B",
            "purpose": "pec_notice",
        },
    )
    assert response.status_code == 409
    response = api.client.post(
        "/communications/messages",
        json={
            "source_entity_id": str(api.source_id),
            "channel": "pec",
            "recipient": "recipient@example.org",
        },
    )
    assert response.status_code == 409


def test_additional_multipage_attachment_invalidates_review(api):
    value = approved(api)
    base = f"/communications/messages/{value['id']}"
    response = api.client.post(
        f"{base}/attachments",
        data={"expected_version": "1"},
        files={"upload": ("appendix.pdf", pdf(2), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["version"] == 2 and result["state"] == "draft" and len(result["attachments"]) == 2
    assert result["attachments"][0]["primary_document"]
    assert api.client.post(f"{base}/validate", json={"expected_version": 2}).status_code == 200
    assert (
        api.client.post(
            f"{base}/attachments",
            data={"expected_version": "2"},
            files={"upload": ("bad.pdf", b"not pdf", "application/pdf")},
        ).status_code
        == 409
    )
    assert (
        api.client.post(
            f"{base}/attachments",
            data={"expected_version": "2"},
            files={"upload": ("too-many.pdf", pdf(200), "application/pdf")},
        ).status_code
        == 409
    )


@pytest.mark.parametrize("change", ["snapshot", "hash", "missing", "size", "mime", "source_digest"])
def test_snapshot_integrity_and_size_fail_closed(api, change):
    value = create(api)
    with api.session() as db:
        message = db.get(models.CommunicationMessage, UUID(value["id"]))
        part = db.scalar(select(models.CommunicationAttachment))
        if change == "snapshot":
            part.content = pdf(4)
        elif change == "hash":
            part.sha256 = "b" * 64
        elif change == "missing":
            db.delete(part)
        elif change == "size":
            part.size = 100000000
        elif change == "mime":
            account = db.get(models.CommunicationAccount, message.account_id)
            account.max_bytes = 1024
            message.account_digest = policy.account_fingerprint(account)
        else:
            message.source_digest = "b" * 64
        db.commit()
    assert (
        api.client.post(
            f"/communications/messages/{value['id']}/validate", json={"expected_version": 1}
        ).status_code
        == 409
    )
    if change == "snapshot":
        assert (
            api.client.get(
                f"/communications/messages/{value['id']}/attachments/{part.id}/preview"
            ).status_code
            == 409
        )


def test_invalid_transitions_and_no_authorization(api):
    value, _ = queued(api)
    base = f"/communications/messages/{value['id']}"
    payload = {
        "expected_version": 1,
        "account_id": value["account_id"],
        "recipient": value["recipient"],
        "subject": value["subject"],
        "body": value["body"],
    }
    assert api.client.patch(base, json=payload).status_code == 409
    assert api.client.post(f"{base}/validate", json={"expected_version": 1}).status_code == 409
    assert (
        api.client.post(
            f"{base}/attachments",
            data={"expected_version": "1"},
            files={"upload": ("extra.pdf", pdf(), "application/pdf")},
        ).status_code
        == 409
    )
    with api.session() as db:
        message = db.get(models.CommunicationMessage, UUID(value["id"]))
        with pytest.raises(policy.Conflict):
            store.transition(db, message, "delivered")
        message.version = 2
        with pytest.raises(policy.Conflict):
            outbox.authorization(db, message, store.attachments(db, message.id))
        account = db.get(models.CommunicationAccount, message.account_id)
        account.max_bytes = 1
        with pytest.raises(policy.Conflict):
            transports.mime_message(
                message, account, store.attachments(db, message.id), "<synthetic@example.org>"
            )


@pytest.mark.parametrize(
    "field,value",
    [
        ("display_name", "Changed"),
        ("codice_fiscale", "CHANGED"),
        ("subject_id", None),
        ("saldo_amount", 123),
    ],
)
def test_source_row_metadata_changes_invalidate_approval(api, field, value):
    message = approved(api)
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        if field == "subject_id":
            subject = AnagraficaSubject(source_name_raw="Changed")
            db.add(subject)
            db.flush()
            value = subject.id
        setattr(item, field, value)
        db.commit()
    assert (
        api.client.post(
            f"/communications/messages/{message['id']}/dispatch", json={"expected_version": 1}
        ).status_code
        == 409
    )


def test_unavailable_nas_pdf_is_a_sanitized_conflict(monkeypatch):
    from app.services.nas_connector import NasConnectorError

    monkeypatch.setattr(ruolo_source.repo, "is_remote_reminder_document_path", lambda path: True)

    def unavailable(path):
        raise NasConnectorError("synthetic remote failure")

    monkeypatch.setattr(ruolo_source.repo, "read_remote_reminder_document", unavailable)
    with pytest.raises(policy.Conflict, match="PDF sorgente non disponibile"):
        ruolo_source.read_pdf(SimpleNamespace(generated_document_path="/volume1/synthetic.pdf"))
