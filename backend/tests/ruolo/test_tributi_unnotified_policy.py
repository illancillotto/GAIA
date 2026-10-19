from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest

from app.modules.ruolo.models import RuoloTributiRegisteredMail
from app.modules.ruolo.tributi_notification_evidence import (
    documented_registered_mail_ids,
    has_documented_mail_receipt,
    has_documented_pec_delivery,
)
from app.modules.utenze.models import AnagraficaPaymentNotice

from .test_tributi_api import TestingSessionLocal, auth_headers, client, seed_avviso
from .test_tributi_api import setup_database as setup_database


def pec_payload(group: str, receipt_date: str) -> dict:
    return {
        "mailing_list": {
            "shipments": [{"external_id": "one", "status_label": group, "event_at": receipt_date}],
            "receipt_parents_by_shipment_id": {
                "one": [{"group": group, "date": receipt_date}],
            },
        },
    }


@pytest.mark.parametrize(
    ("channel", "documented"),
    [
        ("none", False),
        ("accepted", False),
        ("failed", False),
        ("delivered", True),
        ("received", True),
        ("sent", False),
        ("outcome", False),
    ],
)
def test_only_unnotified_policy_uses_delivery_evidence_across_read_paths(
    channel: str,
    documented: bool,
) -> None:
    avviso_id = seed_avviso()
    headers = auth_headers()
    start = (date.today() - timedelta(days=10)).isoformat()
    with TestingSessionLocal() as db:
        if channel in {"accepted", "failed", "delivered"}:
            group = {
                "accepted": "ACCETTAZIONE",
                "failed": "MANCATA CONSEGNA",
                "delivered": "CONSEGNA",
            }[channel]
            db.add(
                AnagraficaPaymentNotice(
                    source_system="incass",
                    source_notice_id="test-notification",
                    anno="2024",
                    codice_fiscale="RSSMRA80A01H501Z",
                    detail_url="https://example.test/notice",
                    raw_detail_json=pec_payload(group, start),
                )
            )
        if channel in {"received", "sent", "outcome"}:
            field = {"received": "DataRicezione", "sent": "sent_at", "outcome": "data_esito"}[
                channel
            ]
            db.add(
                RuoloTributiRegisteredMail(
                    avviso_id=UUID(avviso_id),
                    source_shipment_id=str(uuid4()),
                    raw_payload_json={"history": ["ignored", {field: start}]},
                )
            )
        db.commit()

    payload = {
        "name": "Blocco 2024",
        "year_from": 2024,
        "year_to": 2024,
        "only_unnotified": True,
        "surcharge_rate_percent": 6,
        "surcharge_from": start,
        "interest_rate_percent": 3.65,
        "interest_from": start,
        "interest_start_mode": "fixed_date",
    }
    created = client.post("/ruolo/tributi/calculation-policies", headers=headers, json=payload)
    assert created.status_code == 200
    assert created.json()["only_unnotified"] is True
    policy_id = created.json()["id"]
    assert (
        client.get("/ruolo/tributi/calculation-policies", headers=headers).json()["items"][0][
            "only_unnotified"
        ]
        is True
    )
    expected = 100 if documented else 106.10
    listed = client.get("/ruolo/tributi/avvisi?anno=2024", headers=headers)
    assert listed.status_code == 200
    item = listed.json()["items"][0]
    detail = client.get(f"/ruolo/tributi/avvisi/{avviso_id}", headers=headers)
    assert detail.status_code == 200
    for actual in [item, detail.json()]:
        assert actual["adjusted_due_amount"] == expected
        assert actual["surcharge_amount"] == (0 if documented else 6)
        assert actual["interest_amount"] == (0 if documented else 0.10)
        assert actual["calculation_policy_id"] == (None if documented else policy_id)
    summary = client.get("/ruolo/tributi/summary?anno=2024", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total_amount"] == expected
    candidates = client.get(
        "/ruolo/tributi/solleciti/candidates?anno_from=2024&anno_to=2024", headers=headers
    )
    assert candidates.status_code == 200
    if documented:
        assert candidates.json()["items"] == []
    else:
        assert candidates.json()["items"][0]["due_amount"] == expected

    updated = client.put(
        f"/ruolo/tributi/calculation-policies/{policy_id}",
        headers=headers,
        json={**payload, "only_unnotified": False},
    )
    assert updated.status_code == 200
    assert updated.json()["only_unnotified"] is False
    assert (
        client.get(f"/ruolo/tributi/avvisi/{avviso_id}", headers=headers).json()[
            "adjusted_due_amount"
        ]
        == 106.10
    )


@pytest.mark.parametrize(
    "raw",
    [None, [], {}, {"mailing_list": []}, {"mailing_list": {"receipt_parents_by_shipment_id": []}}],
)
def test_missing_or_unusable_pec_evidence_is_not_delivery(raw: object) -> None:
    assert has_documented_pec_delivery(raw) is False


def test_delivery_receipts_are_checked_across_shipments_not_just_latest_status() -> None:
    payload = pec_payload("MANCATA CONSEGNA", "2026-01-01")
    receipts = payload["mailing_list"]["receipt_parents_by_shipment_id"]
    receipts["invalid"] = "missing"
    receipts["retry"] = [None, {"group": "CONSEGNA", "date": "invalid"}]
    assert has_documented_pec_delivery(payload) is False
    receipts["original"] = [{"group": " consegna ", "date": "01/01/2026 10:30"}]
    assert has_documented_pec_delivery(payload) is True


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {"received_at": "invalid"},
        {"received_at": None},
        {"history": [{"data_esito": "2026-01-01"}]},
    ],
)
def test_mail_evidence_requires_an_explicit_valid_receipt_date(payload: object) -> None:
    assert has_documented_mail_receipt(payload) is False


def test_unrelated_registered_delivery_does_not_exempt_an_unnotified_notice() -> None:
    target = seed_avviso()
    other = seed_avviso(tax_code="OTHER")
    with TestingSessionLocal() as db:
        db.add(
            RuoloTributiRegisteredMail(
                avviso_id=UUID(other),
                source_shipment_id="other-delivered",
                raw_payload_json={"received_at": date.today().isoformat()},
            )
        )
        db.commit()
    with TestingSessionLocal() as db:
        assert documented_registered_mail_ids(db, [UUID(target)]) == set()
        assert documented_registered_mail_ids(db, [UUID(other)]) == {UUID(other)}


def test_cumulative_documented_receipt_excludes_all_associated_annualities() -> None:
    first = seed_avviso(anno=2024)
    second = seed_avviso(anno=2025)
    with TestingSessionLocal() as db:
        db.add(
            RuoloTributiRegisteredMail(
                avviso_id=UUID(first),
                source_shipment_id="cumulative-delivered",
                raw_payload_json={
                    "received_at": date.today().isoformat(),
                    "manual_association": {"active": True, "avviso_ids": [first, second]},
                },
            )
        )
        db.commit()
        assert documented_registered_mail_ids(db, [UUID(first), UUID(second)]) == {
            UUID(first),
            UUID(second),
        }
