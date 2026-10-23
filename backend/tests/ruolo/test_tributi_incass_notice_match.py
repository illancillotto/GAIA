from uuid import UUID

from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.services.incass_notice_match import cnc_notice_prefix, select_incass_notice
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


def _notice(code: str) -> dict:
    return {"source_notice_id": code}


def test_select_incass_notice_prefers_operator_code_then_cnc() -> None:
    own, other = _notice("020217801067337"), _notice("020217800079755")
    assert cnc_notice_prefix(" 01.02021780106733 ") == "02021780106733"
    assert cnc_notice_prefix(None) == ""
    assert select_incass_notice("01.02021780106733", None, [other, own]) is own
    assert select_incass_notice("01.02021780106733", "020217800079755", [own, other]) is other
    assert select_incass_notice("01.02021780106733", "missing", [other, own]) is own
    # A lone candidate is kept; several foreign ones are never attached.
    assert select_incass_notice("CNC-TEST", None, [other]) is other
    assert select_incass_notice("CNC-TEST", None, [other, _notice(None)]) is None
    assert select_incass_notice("", None, []) is None


def _seed_avviso_with_cnc(subject_id: UUID, amount: float, cnc: str) -> str:
    avviso_id = seed_avviso(amount=amount, anno=2021, subject_id=subject_id, tax_code=TAX_CODE)
    with TestingSessionLocal() as db:
        db.get(RuoloAvviso, UUID(avviso_id)).codice_cnc = cnc
        db.commit()
    return avviso_id


def test_same_year_avvisi_of_one_contribuente_keep_their_own_incass_notice(tmp_path) -> None:
    subject_id = seed_subject_with_nas(tmp_path)
    discharged = _seed_avviso_with_cnc(subject_id, 21972.78, "01.02021780106733")
    unpaid = _seed_avviso_with_cnc(subject_id, 3124.85, "01.02021001010315")
    with TestingSessionLocal() as db:
        for code, label, carico, residuo in (
            ("020217801067337", "Totalmente sgravato", "21972,78", "0"),
            ("020210010103150", "Non pagato", "3124,85", "3124,85"),
        ):
            db.add(
                AnagraficaPaymentNotice(
                    subject_id=subject_id,
                    source_system="incass",
                    source_notice_id=code,
                    codice_fiscale=TAX_CODE,
                    anno="2021",
                    stato_label=label,
                    detail_url=f"https://incass.test/{code}",
                    importo_carico=carico,
                    importo_riscosso="0",
                    importo_residuo=residuo,
                    raw_detail_json={"partitario": {"avviso": code, "info_text": label}},
                )
            )
        db.commit()
    headers = auth_headers()

    listed = client.get("/ruolo/tributi/avvisi?anno=2021", headers=headers)
    assert listed.status_code == 200
    codes = {item["id"]: item["capacitas_avviso_code"] for item in listed.json()["items"]}
    assert codes == {discharged: "020217801067337", unpaid: "020210010103150"}
    for avviso_id, code in codes.items():
        detail = client.get(f"/ruolo/tributi/avvisi/{avviso_id}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["capacitas_avviso_code"] == code
