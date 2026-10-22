from __future__ import annotations

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pymupdf
import pytest
from scripts.ruolo import verify_td896_pdf as verify

FIXTURE = Path(__file__).parent / "fixtures" / "td896_su_campu_sample.pdf"
SCRIPT = Path(verify.__file__)
CODELINE = "<012026242500003912> 00001252+22> 001007214826< 896>"
PAYLOAD = "18012026242500003912120010072148261000001252223896"
VALID_IBAN = "IT15L0760117400001007214826"


@pytest.fixture
def sample():
    with pymupdf.open(FIXTURE) as document:
        yield document, document[0]


def _blank_pdf(path: Path, *, width: float = 842, height: float = 595, text: str = "") -> Path:
    document = pymupdf.open()
    page = document.new_page(width=width, height=height)
    if text:
        page.insert_text((40, 400), text, fontsize=9)
    document.save(path)
    document.close()
    return path


def _statuses(checks: list[verify.Check]) -> dict[str, str]:
    return {check.name: check.status for check in checks}


def test_sample_page_passes_every_check(sample) -> None:
    document, page = sample

    checks = verify.verify_page(document, page)

    statuses = _statuses(checks)
    assert statuses.pop("Codice AUT stampa in proprio") == verify.SAMPLE
    assert set(statuses.values()) == {verify.OK}
    assert len(statuses) == 10


def test_main_reports_sample_as_ok_and_exits_zero(capsys) -> None:
    assert verify.main([str(FIXTURE)]) == 0

    output = capsys.readouterr().out
    assert "-- pagina 1" in output
    assert CODELINE in output
    assert "Esito complessivo: OK" in output


def test_main_fails_on_pdf_without_td896_pages(tmp_path, capsys) -> None:
    pdf = _blank_pdf(tmp_path / "lettera.pdf", text="Lettera senza bollettino")

    assert verify.verify_pdf(pdf) == []
    assert verify.main([str(pdf)]) == 1
    output = capsys.readouterr().out
    assert "KO  nessuna pagina con codeline TD 896" in output
    assert "Esito complessivo: KO" in output


def test_script_entry_point_exits_with_main_status(monkeypatch, tmp_path) -> None:
    pdf = _blank_pdf(tmp_path / "vuoto.pdf")
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), str(pdf)])

    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(SCRIPT), run_name="__main__")

    assert exit_info.value.code == 1


def test_print_report_flags_ko_but_not_sample(capsys) -> None:
    sample_only = [(1, [verify.Check("AUT", verify.SAMPLE, "XXXXX")])]
    with_ko = [
        (2, [verify.Check("IBAN", verify.KO, "assente"), verify.Check("AUT", verify.OK, "")])
    ]

    assert verify.print_report(FIXTURE, sample_only) is True
    assert verify.print_report(FIXTURE, with_ko) is False
    assert "KO           IBAN" in capsys.readouterr().out


def test_blank_landscape_page_fails_geometry_and_content_checks(tmp_path) -> None:
    with pymupdf.open(_blank_pdf(tmp_path / "vuoto.pdf")) as document:
        page = document[0]
        match = verify.find_codeline(CODELINE)

        assert verify.check_page_format(page).status == verify.OK
        assert verify.check_module(page) == verify.Check(
            "Modulo 297 x 102 mm", verify.KO, "bordo superiore del modulo non trovato"
        )
        assert verify.check_division(page) == verify.Check(
            "Divisione a 132 mm", verify.KO, "linea verticale non trovata"
        )
        assert verify.check_amount(page, match).status == verify.KO
        assert [check.detail for check in verify.check_barcodes(page, PAYLOAD)] == [
            "simbolo non decodificato",
            "simbolo non decodificato",
        ]
        assert verify.verify_page(document, page) is None


def test_portrait_page_is_rejected(tmp_path) -> None:
    with pymupdf.open(_blank_pdf(tmp_path / "verticale.pdf", width=595, height=842)) as document:
        check = verify.check_page_format(document[0])

    assert check.status == verify.KO
    assert check.detail == "209.9 x 297.0 mm"


def test_module_and_division_out_of_tolerance_are_ko(tmp_path) -> None:
    document = pymupdf.open()
    page = document.new_page(width=842, height=595)
    top = page.rect.height - 110 * verify.MM
    page.draw_rect(
        pymupdf.Rect(0, top, 280 * verify.MM, top + 0.5), color=(0, 0, 0), fill=(0, 0, 0)
    )
    division = 140 * verify.MM
    page.draw_rect(
        pymupdf.Rect(division, top, division + 0.5, page.rect.height),
        color=(0, 0, 0),
        fill=(0, 0, 0),
    )
    page.draw_rect(pymupdf.Rect(10, top + 20, 400 * verify.MM, top + 20.5), color=(0.9, 0.9, 0.9))

    module = verify.check_module(page)
    split = verify.check_division(page)

    assert module.status == verify.KO
    assert module.detail == "280.00 x 110.00 mm"
    assert split.status == verify.KO
    assert split.detail == "140.09 mm"
    document.close()


def test_codeline_with_wrong_mod93_reports_expected_check_digits() -> None:
    match = verify.find_codeline("<012026242500003900> 00001252+22> 001007214826< 896>")

    check = verify.check_codeline(match)

    assert check.status == verify.KO
    assert check.detail.endswith("(controcodice atteso 12)")
    assert verify.find_codeline("nessuna codeline") is None
    assert verify.expected_payload(verify.find_codeline(CODELINE)) == PAYLOAD


def test_barcodes_mismatching_payload_are_ko(sample) -> None:
    _document, page = sample

    code128, datamatrix = verify.check_barcodes(page, "0" * 50)

    assert code128.status == datamatrix.status == verify.KO
    assert code128.detail == f"letto {PAYLOAD}, atteso {'0' * 50}"
    assert datamatrix.detail.endswith("[16x48]")


def test_datamatrix_with_wrong_or_unknown_version_is_ko(sample, monkeypatch) -> None:
    _document, page = sample
    data_matrix = verify.zxingcpp.BarcodeFormat.DataMatrix
    results = [SimpleNamespace(format=data_matrix, text=PAYLOAD, extra={"Version": "18x18"})]
    monkeypatch.setattr(verify.zxingcpp, "read_barcodes", lambda _image: results)

    assert verify.check_barcodes(page, PAYLOAD)[1].detail == f"{PAYLOAD} [18x18]"

    results[0] = SimpleNamespace(format=data_matrix, text=PAYLOAD)
    code128, datamatrix = verify.check_barcodes(page, PAYLOAD)

    assert code128.status == verify.KO
    assert datamatrix == verify.Check("Data Matrix = payload, 16x48", verify.KO, f"{PAYLOAD} [?]")


def test_amount_in_body_different_from_codeline_is_ko(sample) -> None:
    _document, page = sample
    match = verify.find_codeline("<012026242500003912> 00000010+00> 001007214826< 896>")

    check = verify.check_amount(page, match)

    assert check.status == verify.KO
    assert check.detail == "corpo ['1252,22'], codeline 10,00"


@pytest.mark.parametrize(
    ("text", "status", "detail"),
    [
        (f"IBAN {VALID_IBAN}", verify.OK, f"{VALID_IBAN} (ABI 07601)"),
        ("IBAN IT16L0760117400001007214826", verify.KO, "IT16L0760117400001007214826 (ABI 07601)"),
        ("IBAN IT60X0542811101000000123456", verify.KO, "IT60X0542811101000000123456 (ABI 05428)"),
        (
            f"{VALID_IBAN} IT60X0542811101000000123456",
            verify.KO,
            f"{VALID_IBAN}, IT60X0542811101000000123456 (ABI 07601)",
        ),
        ("nessun conto", verify.KO, "IBAN non trovato"),
    ],
)
def test_iban_checks(text, status, detail) -> None:
    assert verify.check_iban(text) == verify.Check("IBAN mod 97 e ABI 07601", status, detail)


def test_iban_mod97() -> None:
    assert verify.iban_mod97_ok(VALID_IBAN) is True
    assert verify.iban_mod97_ok("IT16L0760117400001007214826") is False


class _FakeDocument:
    def __init__(self, keys: dict[tuple[int, str], tuple[str, str]]) -> None:
        self.keys = keys

    def xref_get_key(self, xref: int, key: str) -> tuple[str, str]:
        return self.keys.get((xref, key), ("null", "null"))


def test_font_family_follows_descriptor_and_descendant_fonts() -> None:
    document = _FakeDocument(
        {
            (1, "FontDescriptor"): ("xref", "10 0 R"),
            (10, "FontFamily"): ("string", "(OCR B)"),
            (2, "DescendantFonts"): ("array", "[3 0 R]"),
            (3, "FontDescriptor"): ("xref", "10 0 R"),
            (4, "DescendantFonts"): ("array", "[5 0 R]"),
        }
    )

    assert verify._font_family(document, 1) == "OCR B"
    assert verify._font_family(document, 2) == "OCR B"
    assert verify._font_family(document, 4) == ""
    assert verify._font_family(document, 6) == ""


def test_codeline_font_other_than_ocr_b_is_ko(tmp_path) -> None:
    with pymupdf.open(_blank_pdf(tmp_path / "helvetica.pdf", text=CODELINE)) as document:
        check = verify.check_codeline_font(document, document[0])

    assert check == verify.Check('Font codeline FontFamily "OCR B"', verify.KO, "nessun font")


def test_codeline_font_resolves_xref_from_span_name_or_reports_missing_font() -> None:
    document = _FakeDocument(
        {(7, "FontDescriptor"): ("xref", "8 0 R"), (8, "FontFamily"): ("string", "(OCR B)")}
    )

    def page(font: str) -> SimpleNamespace:
        span = {"text": "896>", "font": font}
        return SimpleNamespace(
            get_fonts=lambda full: [],
            get_text=lambda _mode: {"blocks": [{"lines": [{"spans": [span]}]}, {"type": 1}]},
        )

    assert verify.check_codeline_font(document, page("Font(7 0 R)")).status == verify.OK
    assert verify.check_codeline_font(document, page("Sconosciuto")) == verify.Check(
        'Font codeline FontFamily "OCR B"', verify.KO, "nessun font"
    )


@pytest.mark.parametrize(
    ("text", "status", "detail"),
    [
        ("eseguito da: ROSSI MARIO\n", verify.OK, "eseguito da: ROSSI MARIO"),
        ("eseguito da: AZIENDA AGRICOLA...\n", verify.KO, "eseguito da: AZIENDA AGRICOLA..."),
        ("  eseguito da: AZIENDA …\n", verify.KO, "eseguito da: AZIENDA …"),
        ("nessun versante\n", verify.KO, "riga 'eseguito da' non trovata"),
    ],
)
def test_payer_name_must_not_be_truncated(text, status, detail) -> None:
    assert verify.check_payer_name(text) == verify.Check(
        'Nome versante senza "..."', status, detail
    )


@pytest.mark.parametrize(
    ("text", "status", "detail"),
    [
        ("AUT.DB/SISB/E/12345 DEL 01/02/2026", verify.OK, "AUT.DB/SISB/E/12345 DEL 01/02/2026"),
        ("AUT.DB/SISB/XXXXX DEL XX/XX/XXXX", verify.SAMPLE, "AUT.DB/SISB/XXXXX DEL XX/XX/XXXX"),
        ("autorizzazione assente", verify.KO, "codice non trovato"),
    ],
)
def test_authorization_code(text, status, detail) -> None:
    assert verify.check_authorization(text) == verify.Check(
        "Codice AUT stampa in proprio", status, detail
    )
