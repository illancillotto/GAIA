"""Exact CF/P.IVA generation uses the existing domain eligibility and PDF renderer."""

from .test_notice_pdf_regeneration import RENDERER, TAX_CODE, _broken
from .test_notice_pdf_regeneration import renders as renders
from .test_tributi_api import auth_headers, client, seed_avviso, seed_subject_with_nas
from .test_tributi_api import setup_database as setup_database

URL = "/ruolo/tributi/solleciti/workspace/generate"


def test_generate_and_reuse_exact_taxpayer_without_creating_duplicate_pdfs(tmp_path, renders):
    subject = seed_subject_with_nas(tmp_path, tax_code=TAX_CODE)
    seed_avviso(amount=80, anno=2024, subject_id=subject, tax_code=TAX_CODE)
    body = {"year": 2024, "tax_code": " " + TAX_CODE.lower() + " "}
    first = client.post(URL, headers=auth_headers(), json=body)
    assert first.status_code == 200, first.text
    assert len(first.json()["created"]) == 1 and first.json()["problems"] == []
    second = client.post(URL, headers=auth_headers(), json=body).json()
    assert second["reused"] == first.json()["created"] and second["created"] == []
    assert len(renders) == 1
    assert (
        client.post(
            URL, headers=auth_headers(), json={"year": 2024, "tax_code": "12345678901"}
        ).status_code
        == 409
    )


def test_generation_failure_and_invalid_identity_never_broaden_selection(
    tmp_path, renders, monkeypatch
):
    subject = seed_subject_with_nas(tmp_path, tax_code=TAX_CODE)
    seed_avviso(amount=80, anno=2024, subject_id=subject, tax_code=TAX_CODE)
    monkeypatch.setattr(RENDERER, _broken)
    response = client.post(URL, headers=auth_headers(), json={"year": 2024, "tax_code": TAX_CODE})
    assert response.status_code == 200
    assert response.json()["problems"][0]["detail"] == "Chromium non trovato"
    for body in (
        {"year": 2020, "tax_code": TAX_CODE},
        {"year": 2099, "tax_code": TAX_CODE},
        {"year": 2024, "tax_code": ""},
        {"year": 2024, "tax_code": 123},
    ):
        assert client.post(URL, headers=auth_headers(), json=body).status_code == 422
