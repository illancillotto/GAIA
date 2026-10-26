"""User-facing print contracts: saved rules, real Chromium pages and optical codes."""

from pathlib import Path
from uuid import UUID

import pytest
from pypdf import PdfReader

from app.modules.ruolo.models import RuoloTributiReminderBatchItem
from app.modules.ruolo.services import tributi_reminder_service as service

from .test_bollettino_v2 import payload as payload
from .test_tributi_api import (
    TestingSessionLocal,
    auth_headers,
    client,
    seed_avviso,
    seed_subject_with_nas,
)
from .test_tributi_api import setup_database as setup_database


def test_saved_rule_reaches_batch_snapshot_and_later_changes_do_not_rewrite_it(
    tmp_path, monkeypatch
):
    subject_id = seed_subject_with_nas(tmp_path)
    seed_avviso(amount=100, anno=2025, subject_id=subject_id, verified_history=True)
    headers = auth_headers()
    policy = client.post(
        "/ruolo/tributi/calculation-policies",
        headers=headers,
        json={
            "name": "Regola 2025",
            "year_from": 2025,
            "year_to": 2025,
            "bollettino_version": "v2",
        },
    )
    assert policy.status_code == 200, policy.text
    rendered = []

    def capture_print(data, *, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4 batch layout contract")
        rendered.append(data)

    monkeypatch.setattr(
        "app.modules.ruolo.tributi_repositories.generate_batch_reminder_pdf", capture_print
    )
    request = {
        "title": "Anteprima regola salvata",
        "codice_fiscale": ["RSSMRA80A01H501Z"],
        "filters": {"years": [2025], "preview_only": True},
    }
    first = client.post("/ruolo/tributi/solleciti/batches", headers=headers, json=request)
    assert first.status_code == 200, first.text
    assert first.json()["items_generated"] == 1
    first_item_id = UUID(first.json()["items"][0]["id"])
    assert rendered[-1]["bollettino_version"] == "v2"
    changed = client.put(
        f"/ruolo/tributi/calculation-policies/{policy.json()['id']}",
        headers=headers,
        json={
            "name": "Regola 2025",
            "year_from": 2025,
            "year_to": 2025,
            "bollettino_version": "v1",
        },
    )
    assert changed.status_code == 200, changed.text
    second = client.post("/ruolo/tributi/solleciti/batches", headers=headers, json=request)
    assert second.status_code == 200, second.text
    assert second.json()["items_generated"] == 1
    assert rendered[-1]["bollettino_version"] == "v1"
    with TestingSessionLocal() as db:
        first_item = db.get(RuoloTributiReminderBatchItem, first_item_id)
        assert first_item.payload_json["bollettino_version"] == "v2"
        assert (
            Path(first_item.generated_document_path).read_bytes()
            == b"%PDF-1.4 batch layout contract"
        )


def test_real_print_preserves_notice_pages_and_has_readable_matching_payment_codes(
    payload, tmp_path, monkeypatch
):
    pymupdf = pytest.importorskip("pymupdf")
    zxingcpp = pytest.importorskip("zxingcpp")
    pil_image = pytest.importorskip("PIL.Image")
    chromium = service._find_chromium_binary()
    if chromium is None:
        pytest.skip("Chromium richiesto per la verifica della stampa reale")
    monkeypatch.setattr(service, "_find_chromium_binary", lambda: chromium)
    # The long name and special characters must remain complete on both printed receipts.
    name = "AZIENDA AGRICOLA ROSSI & FIGLI <ORISTANO>"
    data = {**payload, "display_name": name}
    printed_pages = {}
    for version in ("v1", "v2"):
        output = tmp_path / f"avviso-{version}.pdf"
        service.generate_batch_reminder_pdf(
            {**data, "bollettino_version": version}, output_path=output
        )
        reader = PdfReader(output)
        printed_pages[version] = [page.extract_text() for page in reader.pages[:-1]]
        with pymupdf.open(output) as document:
            slip = document[-1]
            if version == "v2":
                assert list(reader.pages[-1].mediabox) == [0, 0, 595, 841]
                assert list(reader.pages[-1].cropbox) == [0, 0, 595, 841]
                assert slip.get_text().count(name) == 2
                assert "30/11/2026" in slip.get_text()
                assert "221,55" in slip.get_text()
            else:
                assert float(reader.pages[-1].mediabox.width) == pytest.approx(841.92, abs=0.1)
                assert float(reader.pages[-1].mediabox.height) == pytest.approx(594.96, abs=0.1)
            raster = slip.get_pixmap(matrix=pymupdf.Matrix(3, 3))
            image = pil_image.frombytes("RGB", (raster.width, raster.height), raster.samples)
            symbols = zxingcpp.read_barcodes(image)
            assert {str(symbol.format) for symbol in symbols} == {"Code 128", "Data Matrix"}
            assert [symbol.text for symbol in symbols] == [
                "18012026242500001985120010072148261000000221553896",
                "18012026242500001985120010072148261000000221553896",
            ]
    assert printed_pages["v1"] == printed_pages["v2"]
