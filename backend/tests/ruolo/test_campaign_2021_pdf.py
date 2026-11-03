from copy import deepcopy
from io import BytesIO

import pymupdf
import pytest
from pypdf import PdfReader, PdfWriter

from app.modules.ruolo.services import campaign_2021_pdf as pdf
from app.modules.ruolo.services import campaign_2021_summary as summary
from app.modules.ruolo.services import tributi_reminder_service as renderer
from app.modules.ruolo.services.notice_preview import PREVIEW_LABEL

from .test_campaign_2021 import NUMBER
from .test_notice_presentation import _payload


def payload(interest, fee):
    result = _payload([2021])
    total = 106 + interest
    result.update(
        notice_number=NUMBER,
        bollettino_causale=NUMBER,
        saldo_amount=str(total),
        notification_amount=fee,
        paid_amount="0.00",
        due_date="2026-12-15",
        campaign_2021_snapshot={
            "load": "100.00",
            "residual": "100.00",
            "difference": "0.00",
            "total": str(total),
        },
    )
    result["avvisi"][0].update(
        codice_cnc=NUMBER,
        rateization_fee_amount=0,
        importo_totale_0648="100.00",
        importo_totale_0668="0.00",
        importo_totale_0985="0.00",
        paid_amount="0.00",
        surcharge_amount="6.00",
        interest_amount=str(interest),
        saldo_amount=str(total),
    )
    return result


@pytest.mark.parametrize("interest,fee", [(0, "0.00"), (19.68, "11.55")])
def test_real_preview_keeps_four_pages_approved_total_and_interest(interest, fee, tmp_path):
    sample = payload(interest, fee)
    content = pdf.render_preview(sample)
    document = PdfReader(BytesIO(content))
    assert len(document.pages) == 4
    assert all(PREVIEW_LABEL in page.extract_text() for page in document.pages)
    front = " ".join(document.pages[0].extract_text().split())
    assert "Differenza contabile F-J (non equivale a incasso)" in front
    assert "Carico (emesso)" in front and "Residuo contabile" in front
    assert "PAGAMENTO GIÀ EFFETTUATO" in front and "scadenza 15/12/2026" in front
    assert ("Interessi" in front) == bool(interest)
    with pymupdf.open(stream=content, filetype="pdf") as visual:
        assert all(
            abs(page.rect.width - 595) < 2 and abs(page.rect.height - 842) < 2 for page in visual
        )
        assert len(visual[0].search_for(NUMBER)) >= 1
    original = deepcopy(sample)
    original.pop("campaign_2021_snapshot")
    path = tmp_path / "original.pdf"
    renderer.generate_batch_reminder_pdf(original, output_path=path)
    unchanged = PdfReader(path)
    for index in (1, 2, 3):
        assert unchanged.pages[index].extract_text() in document.pages[index].extract_text()


def test_summary_rejects_unknown_markup_and_keeps_legacy_output(monkeypatch):
    assert summary.accounting_rows(None, 9) == ""
    monkeypatch.setattr(summary, "notice_summary_html", lambda *args: "unexpected")
    assert summary.campaign_summary_html([], "0", None, None) == "unexpected"
    with pytest.raises(ValueError, match="non riconosciuto"):
        summary.campaign_summary_html([], "0", None, {})


def test_native_renderer_mismatch_never_produces_a_deliverable(monkeypatch):
    def invalid(payload, output_path):
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        with output_path.open("wb") as stream:
            writer.write(stream)

    monkeypatch.setattr(pdf, "generate_batch_reminder_pdf", invalid)
    with pytest.raises(ValueError, match="non riscontrato"):
        pdf.render_preview(payload(0, "0.00"))
