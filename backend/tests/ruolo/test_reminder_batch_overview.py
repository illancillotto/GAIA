"""The batch list shows which reminders can go to Poste and which avvisi inCASS already sent by PEC."""

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
