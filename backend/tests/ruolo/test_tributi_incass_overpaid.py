from decimal import Decimal
from uuid import UUID

from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.services.incass_residual import settled_status
from app.modules.utenze.models import AnagraficaPaymentNotice

from .test_tributi_api import (
    TestingSessionLocal,
    auth_headers,
    client,
    seed_avviso,
    seed_subject_with_nas,
)
from .test_tributi_api import setup_database as setup_database

TAX_CODE = "RSSMRA80A01H501Z"


def test_settled_residual_status() -> None:
    assert settled_status(Decimal("-0.01")) == "overpaid"
    assert settled_status(Decimal("0.00")) == "paid"


def _seed(
    subject_id, cnc: str, code: str, stato: str, carico: str, riscosso: str, residuo: str
) -> str:
    avviso_id = seed_avviso(amount=1291.04, anno=2021, subject_id=subject_id, tax_code=TAX_CODE)
    with TestingSessionLocal() as db:
        db.get(RuoloAvviso, UUID(avviso_id)).codice_cnc = cnc
        db.add(
            AnagraficaPaymentNotice(
                subject_id=subject_id,
                source_system="incass",
                source_notice_id=code,
                codice_fiscale=TAX_CODE,
                anno="2021",
                stato_label=stato,
                detail_url=f"https://incass.test/{code}",
                importo_carico=carico,
                importo_riscosso=riscosso,
                importo_residuo=residuo,
                importo_rateizzato="0",
            )
        )
        db.commit()
    return avviso_id


def test_overpaid_incass_notice_is_a_credit_not_a_debt(tmp_path) -> None:
    subject_id = seed_subject_with_nas(tmp_path)
    overpaid = _seed(
        subject_id,
        "01.02021780103813",
        "020217801038136",
        "Con esubero",
        "1291,04",
        "-2582,08",
        "-1291,04",
    )
    unpaid = _seed(
        subject_id, "01.02021780103814", "020217801038147", "Non pagato", "1291,04", "0", "1291,04"
    )
    headers = auth_headers()

    listed = client.get("/ruolo/tributi/avvisi?anno=2021&open_only=false", headers=headers)
    items = {item["id"]: item for item in listed.json()["items"]}
    assert items[overpaid]["payment_status"] == "overpaid"
    assert items[overpaid]["saldo_amount"] == -1291.04
    assert items[overpaid]["reminder_enabled"] is False
    assert items[unpaid]["payment_status"] == "unpaid"
    assert items[unpaid]["saldo_amount"] == 1291.04

    open_items = client.get(
        "/ruolo/tributi/avvisi?anno=2021&open_only=true", headers=headers
    ).json()["items"]
    assert [item["id"] for item in open_items] == [unpaid]
