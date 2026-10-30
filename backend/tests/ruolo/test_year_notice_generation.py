"""«Avvisi da sollecitare»: a year's notices are ready, failed or missing, and only missing ones are made."""

from pathlib import Path

import pytest

from .test_notice_pdf_regeneration import RENDERER, _batch, _broken
from .test_notice_pdf_regeneration import renders as renders
from .test_tributi_api import auth_headers, client, seed_avviso, seed_subject_with_nas
from .test_tributi_api import setup_database as setup_database

STATUS = "/ruolo/tributi/solleciti/years/2024/status"
GENERATE = "/ruolo/tributi/solleciti/years/2024/generate"
MISSING_CF = "VRDNNA80A41H501X"


def _status(username: str = "ruolo-tributi-admin"):
    return client.get(STATUS, headers=auth_headers(username))


def _generate(avviso_ids: list[str]):
    return client.post(GENERATE, headers=auth_headers(), json={"avviso_ids": avviso_ids})


def _year(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[dict, dict, str]:
    ready, _ = _batch(tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(RENDERER, _broken)
        failed, _ = _batch(tmp_path / "fallito", tax_code="BNCLGU80A01H501Y")
    subject_id = seed_subject_with_nas(tmp_path / "mancante", tax_code=MISSING_CF)
    missing = seed_avviso(amount=80.0, anno=2024, subject_id=subject_id, tax_code=MISSING_CF)
    return ready, failed, missing


def test_the_year_splits_into_ready_failed_and_missing_notices(tmp_path, renders, monkeypatch):
    _, failed, missing = _year(tmp_path, monkeypatch)
    status = _status().json()
    assert (status["year"], status["total"], status["ready"]) == (2024, 3, 1)
    assert status["failed"] == [{"item_id": failed["id"], "label": failed["display_name"]}]
    assert [entry["avviso_ids"] for entry in status["missing"]] == [[missing]]
    assert _status("ruolo-tributi-viewer").status_code == 403


def test_only_missing_notices_are_generated_and_never_twice(tmp_path, renders, monkeypatch):
    _, _, missing = _year(tmp_path, monkeypatch)
    printed = len(renders)
    result = _generate([missing]).json()
    assert result["batch_id"] and (result["generated"], result["problems"]) == (1, [])
    assert len(renders) == printed + 1
    batch = client.get(
        f"/ruolo/tributi/solleciti/batches/{result['batch_id']}", headers=auth_headers()
    ).json()
    assert batch["title"] == "Solleciti 2024" and batch["items"][0]["codice_fiscale"] == MISSING_CF
    status = _status().json()
    assert (status["ready"], status["missing"]) == (2, [])
    assert _generate([missing]).json() == {"batch_id": None, "generated": 0, "problems": []}
    unknown = "00000000-0000-0000-0000-000000000000"
    assert _generate([unknown]).json()["batch_id"] is None
    assert len(renders) == printed + 1


def test_a_notice_that_cannot_be_printed_is_reported_with_its_reason(
    tmp_path, renders, monkeypatch
):
    _, _, missing = _year(tmp_path, monkeypatch)
    monkeypatch.setattr(RENDERER, _broken)
    result = _generate([missing]).json()
    assert result["generated"] == 0
    assert result["problems"] == [{"label": "ROSSI MARIO", "detail": "Chromium non trovato"}]
    assert _status().json()["failed"][-1]["label"] == "ROSSI MARIO"
