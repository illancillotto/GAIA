"""The batch list shows which reminders can go to Poste and which avvisi inCASS already sent by PEC."""

from datetime import UTC
from pathlib import Path
from uuid import UUID

import pytest

from app.modules.ruolo.models import RuoloTributiReminderBatchItem
from app.modules.utenze.models import AnagraficaPaymentNotice

from .test_notice_pdf_regeneration import RENDERER, TAX_CODE, _batch, _broken
from .test_notice_pdf_regeneration import renders as renders
from .test_tributi_api import TestingSessionLocal, auth_headers, client
from .test_tributi_api import setup_database as setup_database

OVERVIEW = "/ruolo/tributi/solleciti/batch-overview"


def _pec_notice(tax_code: str, anno: str = "2024") -> None:
    db = TestingSessionLocal()
    db.add(
        AnagraficaPaymentNotice(
            source_system="incass",
            source_notice_id=f"INCASS-{tax_code}",
            codice_fiscale=tax_code,
            anno=anno,
            detail_url="https://incass.example.local/notices/1",
            raw_detail_json={
                "mailing_list": {
                    "shipments": [
                        {
                            "external_id": "S1",
                            "recipient": "rossi@pec.it",
                            "status_label": "Consegnata",
                        }
                    ],
                    "receipt_parents_by_shipment_id": {},
                }
            },
        )
    )
    db.commit()
    db.close()


def test_overview_lists_sendable_reminders_and_pec_shipments(
    tmp_path: Path, renders, monkeypatch: pytest.MonkeyPatch
):
    sent, _ = _batch(tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(RENDERER, _broken)
        failed, _ = _batch(tmp_path / "altro", tax_code="BNCLGU80A01H501Y")
    _pec_notice(TAX_CODE)
    empty = "00000000-0000-0000-0000-000000000000"
    response = client.get(
        OVERVIEW,
        params={"batch_id": [sent["batch_id"], failed["batch_id"], empty]},
        headers=auth_headers("ruolo-tributi-viewer"),
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            "batch_id": sent["batch_id"],
            "items": [
                {
                    "item_id": sent["id"],
                    "label": sent["display_name"],
                    "status": "generated",
                    "sendable": True,
                    "pec_sent": True,
                    "notice_number": sent["payload_json"]["notice_number"],
                    "years": [2024],
                    "amount": 111.55,
                    "poste_dispatches": [],
                }
            ],
        },
        {
            "batch_id": failed["batch_id"],
            "items": [
                {
                    "item_id": failed["id"],
                    "label": failed["display_name"],
                    "status": "failed",
                    "sendable": False,
                    "pec_sent": False,
                    "notice_number": failed["payload_json"]["notice_number"],
                    "years": [2024],
                    "amount": 111.55,
                    "poste_dispatches": [],
                }
            ],
        },
        {"batch_id": empty, "items": []},
    ]


def test_overview_needs_batches_and_a_known_avviso_list(tmp_path: Path, renders):
    assert client.get(OVERVIEW, headers=auth_headers()).status_code == 422
    item, _ = _batch(tmp_path)
    db = TestingSessionLocal()
    db.get(RuoloTributiReminderBatchItem, UUID(item["id"])).avviso_ids_json = None
    db.commit()
    db.close()
    body = client.get(
        OVERVIEW, params={"batch_id": item["batch_id"]}, headers=auth_headers()
    ).json()
    assert body[0]["items"][0]["pec_sent"] is False


def _poste_attempt(db, item, *, status, number, created_at):
    from datetime import datetime

    from sqlalchemy import select

    from app.models.application_user import ApplicationUser
    from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem, PosteDispatchLot

    actor = db.scalar(select(ApplicationUser.id).limit(1))
    lot = PosteDispatchLot(
        title="Synthetic Poste",
        created_by=actor,
        postal_options={},
        poste_username="synthetic-account",
    )
    db.add(lot)
    db.flush()
    attempt = PosteDispatchItem(
        lot_id=lot.id,
        batch_item_id=UUID(item["id"]),
        notice_number=number,
        shipment_name="GAIA " + number,
        status=status,
        recipient={},
        artifact=b"synthetic-private-artifact",
        artifact_sha256="a" * 64,
        artifact_size=26,
        poste_draft_id="synthetic-poste-id",
        poste_status="Accettato" if status == "sent" else "Prezzato",
        draft_created_at=created_at,
        sent_at=datetime(2026, 11, 3, 10, tzinfo=UTC) if status == "sent" else None,
        tracking_number="synthetic-tracking" if status == "sent" else None,
        upload_requested_by_username="synthetic-operator",
        created_at=created_at,
    )
    db.add(attempt)
    db.flush()
    return attempt


def test_overview_shows_saved_poste_history_for_same_notice_across_batches(tmp_path, renders):
    from datetime import datetime

    from sqlalchemy import func, select

    from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem

    current, _ = _batch(tmp_path)
    older, _ = _batch(tmp_path / "older", tax_code="BNCLGU80A01H501Y")
    number = current["payload_json"]["notice_number"]
    with TestingSessionLocal() as db:
        source = db.get(RuoloTributiReminderBatchItem, UUID(older["id"]))
        source.payload_json = {**source.payload_json, "notice_number": number}
        sent = _poste_attempt(
            db,
            older,
            status="sent",
            number=number,
            created_at=datetime(2026, 11, 3, tzinfo=UTC),
        )
        sent_id = str(sent.id)
        cancelled = _poste_attempt(
            db,
            current,
            status="cancelled",
            number=number,
            created_at=datetime(2026, 11, 4, tzinfo=UTC),
        )
        cancelled.poste_draft_id = cancelled.poste_status = cancelled.draft_created_at = None
        cancelled.upload_requested_by_username = None
        _poste_attempt(
            db,
            current,
            status="draft_priced",
            number="UNRELATED-NUMBER",
            created_at=datetime(2026, 11, 5, tzinfo=UTC),
        )
        db.commit()
        before = db.scalar(select(func.count()).select_from(PosteDispatchItem))
    response = client.get(
        OVERVIEW,
        params={"batch_id": [current["batch_id"], older["batch_id"]]},
        headers=auth_headers("ruolo-tributi-viewer"),
    )
    assert response.status_code == 200
    histories = [entry["items"][0]["poste_dispatches"] for entry in response.json()]
    assert histories[0] == histories[1]
    cancelled, sent = histories[0]
    assert cancelled["status"] == "cancelled"
    assert cancelled["poste_draft_id"] is None
    assert cancelled["sent_at"] is None
    assert sent["id"] == sent_id
    assert sent["notice_number"] == number
    assert sent["poste_draft_id"] == "synthetic-poste-id"
    assert sent["tracking_number"] == "synthetic-tracking"
    assert sent["sent_at"].startswith("2026-11-03T10:00:00")
    assert sent["draft_created_at"].startswith("2026-11-03T00:00:00")
    assert sent["poste_username"] == "synthetic-account"
    assert sent["upload_requested_by_username"] == "synthetic-operator"
    assert sent["poste_status"] == "Accettato"
    assert "artifact" not in sent and "recipient" not in sent
    with TestingSessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(PosteDispatchItem)) == before


def test_poste_overview_without_notice_numbers_or_matching_shipments(tmp_path, renders):
    from types import SimpleNamespace

    from app.modules.ruolo.services.reminder_batch_poste import dispatches_by_notice

    with TestingSessionLocal() as db:
        assert dispatches_by_notice(db, []) == {}
        assert (
            dispatches_by_notice(
                db,
                [
                    SimpleNamespace(payload_json=None),
                    SimpleNamespace(payload_json={"notice_number": ""}),
                ],
            )
            == {}
        )
    item, _ = _batch(tmp_path)
    with TestingSessionLocal() as db:
        source = db.get(RuoloTributiReminderBatchItem, UUID(item["id"]))
        source.payload_json = None
        source.display_name = None
        source.years_json = None
        source.generated_document_path = "/synthetic/not-a-pdf.txt"
        db.commit()
    response = client.get(OVERVIEW, params={"batch_id": item["batch_id"]}, headers=auth_headers())
    assert response.status_code == 200
    assert response.json()[0]["items"][0]["poste_dispatches"] == []
    assert response.json()[0]["items"][0]["label"] == item["codice_fiscale"]
    assert response.json()[0]["items"][0]["years"] == []
    assert response.json()[0]["items"][0]["sendable"] is False
    assert client.get(OVERVIEW, params={"batch_id": item["batch_id"]}).status_code == 401
