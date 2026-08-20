from __future__ import annotations

import base64
import copy
import html
import os
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

from pypdf import PdfReader, PdfWriter

from app.modules.ruolo.services.td896 import (
    TD896_DOCUMENT_CODE as _BOLLETTINO_TD_CODE,
    build_td896_barcode_payload,
    build_td896_payment_code,
    td896_amount_code,
    td896_customer_code,
    td896_datamatrix_svg,
)

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MEDIA_TYPE = "application/pdf"
WORD_DOCUMENT_PATH = "word/document.xml"
WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WORD_NAMESPACES = {"w": WORD_NAMESPACE}
DEFAULT_BATCH_REMINDER_TEMPLATE_NAME = "Avviso_Sollecito_Template.docx"
GAIA_PROPOSAL_TEMPLATE_KEY = "__gaia_proposal__"
PARTITARIO_LINE_WIDTH = 80
_BOLLETTINO_POSTAL_ACCOUNT = "1007214826"
_BOLLETTINO_IBAN = "IT15L0760117400001007214826"
_BOLLETTINO_PRINT_AUTHORIZATION = "AUT.DB/SISB/36211 DEL 5/9/2012"
_BOLLETTINO_ACCOUNT_NAME_LINES = (
    "CONSORZIO DI BONIFICA DELL'ORISTANESE -",
    "RISCOSSIONE QUOTE ASSOCIATIVE",
)
_CODE128_PATTERNS = (
    "212222",
    "222122",
    "222221",
    "121223",
    "121322",
    "131222",
    "122213",
    "122312",
    "132212",
    "221213",
    "221312",
    "231212",
    "112232",
    "122132",
    "122231",
    "113222",
    "123122",
    "123221",
    "223211",
    "221132",
    "221231",
    "213212",
    "223112",
    "312131",
    "311222",
    "321122",
    "321221",
    "312212",
    "322112",
    "322211",
    "212123",
    "212321",
    "232121",
    "111323",
    "131123",
    "131321",
    "112313",
    "132113",
    "132311",
    "211313",
    "231113",
    "231311",
    "112133",
    "112331",
    "132131",
    "113123",
    "113321",
    "133121",
    "313121",
    "211331",
    "231131",
    "213113",
    "213311",
    "213131",
    "311123",
    "311321",
    "331121",
    "312113",
    "312311",
    "332111",
    "314111",
    "221411",
    "431111",
    "111224",
    "111422",
    "121124",
    "121421",
    "141122",
    "141221",
    "112214",
    "112412",
    "122114",
    "122411",
    "142112",
    "142211",
    "241211",
    "221114",
    "413111",
    "241112",
    "134111",
    "111242",
    "121142",
    "121241",
    "114212",
    "124112",
    "124211",
    "411212",
    "421112",
    "421211",
    "212141",
    "214121",
    "412121",
    "111143",
    "111341",
    "131141",
    "114113",
    "114311",
    "411113",
    "411311",
    "113141",
    "114131",
    "311141",
    "411131",
    "211412",
    "211214",
    "211232",
    "2331112",
)
_CODE128_START_C = 105
_CODE128_STOP = 106
_HTML_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_NON_DIGIT_RE = re.compile(r"\D+")
_GAIA_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
_GAIA_CBO_LOGO_CANDIDATES = (
    _GAIA_ASSETS_DIR / "cbo-logo.png",
)
_GAIA_PAGOPA_LOGO_CANDIDATES = (
    _GAIA_ASSETS_DIR / "pagopa-logo.png",
)
REGISTERED_MAIL_NOTIFICATION_AMOUNT = Decimal("11.55")


def reminder_storage_dir() -> Path:
    path = Path(tempfile.gettempdir()) / "gaia_ruolo_tributi_reminders"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_reminder_payload(
    *,
    avviso_id: uuid.UUID,
    codice_cnc: str,
    anno_tributario: int,
    nominativo: str | None,
    codice_fiscale: str | None,
    codice_utenza: str | None,
    domicilio: str | None,
    residenza: str | None,
    importo_totale: Any,
    paid_amount: Any,
    saldo_amount: Any,
    generated_at: datetime,
    surcharge_amount: Any = None,
    interest_amount: Any = None,
) -> dict[str, Any]:
    return {
        "avviso_id": str(avviso_id),
        "codice_cnc": codice_cnc,
        "anno_tributario": anno_tributario,
        "nominativo": nominativo,
        "codice_fiscale": codice_fiscale,
        "codice_utenza": codice_utenza,
        "domicilio": domicilio,
        "residenza": residenza,
        "importo_totale": _format_currency(importo_totale),
        "paid_amount": _format_currency(paid_amount),
        "saldo_amount": _format_currency(saldo_amount),
        "surcharge_amount": _format_currency(surcharge_amount),
        "interest_amount": _format_currency(interest_amount),
        "generated_at": generated_at.isoformat(),
    }


def generate_reminder_docx(payload: dict[str, Any], *, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    paragraphs = [
        "Avviso di sollecito pagamento",
        f"Contribuente: {_value(payload.get('nominativo'))}",
        f"CF/P.IVA: {_value(payload.get('codice_fiscale'))}",
        f"Codice CNC: {_value(payload.get('codice_cnc'))}",
        f"Codice utenza: {_value(payload.get('codice_utenza'))}",
        f"Anno tributario: {_value(payload.get('anno_tributario'))}",
        f"Domicilio: {_value(payload.get('domicilio'))}",
        f"Residenza: {_value(payload.get('residenza'))}",
        f"Importo dovuto: {_value(payload.get('importo_totale'))}",
        f"Importo pagato: {_value(payload.get('paid_amount'))}",
        f"Maggiorazione: {_value(payload.get('surcharge_amount'))}",
        f"Interessi: {_value(payload.get('interest_amount'))}",
        f"Saldo da regolarizzare: {_value(payload.get('saldo_amount'))}",
        "Il presente documento e predisposto da GAIA per il reinvio all'utente. Nessun invio automatico e stato effettuato.",
    ]
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _rels_xml())
        archive.writestr("docProps/core.xml", _core_xml(payload))
        archive.writestr("word/document.xml", _document_xml(paragraphs))
        archive.writestr("word/_rels/document.xml.rels", _empty_document_rels_xml())


def build_reminder_filename(*, codice_cnc: str, anno_tributario: int, reminder_id: uuid.UUID) -> str:
    safe_cnc = "".join(ch if ch.isalnum() else "_" for ch in codice_cnc).strip("_") or "avviso"
    return f"sollecito_{anno_tributario}_{safe_cnc}_{str(reminder_id)[:8]}.docx"


def build_batch_reminder_filename(*, codice_fiscale: str, years: list[int]) -> str:
    safe_cf = "".join(ch if ch.isalnum() else "_" for ch in codice_fiscale.upper()).strip("_") or "utenza"
    years_suffix = "-".join(str(year) for year in sorted(set(years))) or "anni"
    return f"{safe_cf}_avviso_sollecito_{years_suffix}.pdf"


def generate_batch_reminder_pdf(
    payload: dict[str, Any],
    *,
    output_path: Path,
    libreoffice_binary: str | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if payload.get("template_path") == GAIA_PROPOSAL_TEMPLATE_KEY:
        _generate_gaia_proposal_pdf(payload, output_path=output_path)
        return

    with tempfile.TemporaryDirectory(prefix="gaia_tributi_batch_") as temp_dir:
        working_dir = Path(temp_dir)
        docx_path = working_dir / f"{output_path.stem}.docx"
        generate_batch_reminder_docx(payload, output_path=docx_path)
        converted_path = convert_docx_to_pdf(
            docx_path,
            output_dir=working_dir,
            libreoffice_binary=libreoffice_binary,
        )
        shutil.copyfile(converted_path, output_path)


def generate_batch_reminder_docx(payload: dict[str, Any], *, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if payload.get("template_path") == GAIA_PROPOSAL_TEMPLATE_KEY:
        payload = {**payload, "template_path": "Template GAIA"}
    template_path = Path(str(payload.get("template_path") or ""))
    if template_path.is_file():
        _generate_batch_reminder_docx_from_template(payload, template_path=template_path, output_path=output_path)
        return

    paragraphs = _batch_intro_paragraphs(payload)
    paragraphs.extend(_batch_partitario_paragraphs(payload))
    _write_simple_docx(payload, paragraphs=paragraphs, output_path=output_path)


def _generate_gaia_proposal_pdf(payload: dict[str, Any], *, output_path: Path) -> None:
    chromium_binary = _find_chromium_binary()
    if not chromium_binary:
        raise RuntimeError("Chromium non trovato: impossibile generare la preview del template GAIA")

    temp_parent = _chromium_accessible_temp_parent(chromium_binary)
    with tempfile.TemporaryDirectory(
        prefix="gaia_tributi_proposal_",
        dir=str(temp_parent) if temp_parent is not None else None,
    ) as temp_dir:
        working_dir = Path(temp_dir)
        main_pdf_path = _render_gaia_html_to_pdf(
            _gaia_proposal_html(payload, include_partitario=False, include_bollettino=False),
            chromium_binary=chromium_binary,
            working_dir=working_dir,
            stem=f"{output_path.stem}_main",
        )
        partitario_pdf_path = _render_gaia_html_to_pdf(
            _gaia_proposal_html(payload, include_main=False, include_bollettino=False),
            chromium_binary=chromium_binary,
            working_dir=working_dir,
            stem=f"{output_path.stem}_partitario",
        )
        bollettino_pdf_path = _render_gaia_html_to_pdf(
            _gaia_proposal_html(payload, include_main=False, include_partitario=False),
            chromium_binary=chromium_binary,
            working_dir=working_dir,
            stem=f"{output_path.stem}_bollettino",
        )
        _merge_pdf_files([main_pdf_path, partitario_pdf_path, bollettino_pdf_path], output_path=output_path)


def _render_gaia_html_to_pdf(
    html_text: str,
    *,
    chromium_binary: str,
    working_dir: Path,
    stem: str,
) -> Path:
    html_path = working_dir / f"{stem}.html"
    pdf_path = working_dir / f"{stem}.pdf"
    html_path.write_text(html_text, encoding="utf-8")
    subprocess.run(
        [
            chromium_binary,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if not pdf_path.exists():
        raise RuntimeError("Conversione PDF template GAIA non riuscita")
    return pdf_path


def _merge_pdf_files(pdf_paths: Iterable[Path], *, output_path: Path) -> None:
    writer = PdfWriter()
    for pdf_path in pdf_paths:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            writer.add_page(page)
    with output_path.open("wb") as output_file:
        writer.write(output_file)


def _find_chromium_binary() -> str | None:
    configured_binary = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if configured_binary and Path(configured_binary).exists():
        return configured_binary
    for candidate in ("chromium", "chromium-browser", "google-chrome"):
        binary = shutil.which(candidate)
        if binary:
            return binary
    snap_chromium = Path("/snap/bin/chromium")
    if snap_chromium.exists():
        return str(snap_chromium)
    return _find_playwright_chromium_binary()


def _find_playwright_chromium_binary() -> str | None:
    for root in _playwright_browser_roots():
        for pattern in ("chromium-*/chrome-linux/chrome", "chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium"):
            for candidate in sorted(root.glob(pattern), reverse=True):
                if candidate.exists():
                    return str(candidate)
    return None


def _playwright_browser_roots() -> list[Path]:
    roots: list[Path] = []
    configured_root = os.getenv("PLAYWRIGHT_BROWSERS_PATH")
    if configured_root and configured_root != "0":
        roots.append(Path(configured_root).expanduser())
    roots.extend(
        [
            Path("/ms-playwright"),
            Path.home() / ".cache" / "ms-playwright",
        ]
    )
    return roots


def _chromium_accessible_temp_parent(chromium_binary: str) -> Path | None:
    if not chromium_binary.startswith("/snap/"):
        return None
    for temp_parent in (
        Path.home() / "gaia_tributi_pdf_tmp",
        Path.home() / ".cache" / "gaia" / "tributi_pdf",
        Path.cwd() / "gaia_tributi_pdf_tmp",
    ):
        try:
            temp_parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        return temp_parent
    return None


def _default_batch_reminder_template_path() -> Path:
    return Path(__file__).resolve().parents[1] / "templates" / DEFAULT_BATCH_REMINDER_TEMPLATE_NAME


def _gaia_logo_html(*, candidates: Iterable[Path], alt: str, fallback: str) -> str:
    escaped_alt = html.escape(alt)
    data_uri = _first_image_data_uri(candidates)
    if data_uri:
        return f'<img class="logo-image" role="img" aria-label="{escaped_alt}" alt="{escaped_alt}" src="{data_uri}">'
    if fallback == "CBO":
        return _cbo_inline_logo_svg(alt)
    if fallback == "pagoPA":
        return _pagopa_inline_logo_svg(alt)
    return html.escape(fallback)


def _cbo_inline_logo_svg(alt: str) -> str:
    return f"""<svg role="img" aria-label="{html.escape(alt)}" viewBox="0 0 180 105" xmlns="http://www.w3.org/2000/svg">
<rect width="180" height="105" rx="12" fill="#2f80bd"/>
<rect y="82" width="180" height="23" fill="#244f7c"/>
<text x="90" y="64" text-anchor="middle" font-family="Georgia, serif" font-size="50" font-weight="800" fill="#ffffff">CBO</text>
<rect x="75" y="18" width="30" height="22" rx="3" fill="none" stroke="#ffffff" stroke-width="2"/>
<path d="M90 22v14M83 29h14M81 36h18" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>
</svg>"""


def _pagopa_inline_logo_svg(alt: str) -> str:
    return f"""<svg role="img" aria-label="{html.escape(alt)}" viewBox="0 0 180 105" xmlns="http://www.w3.org/2000/svg">
<rect width="180" height="105" rx="12" fill="#ffffff"/>
<text x="88" y="47" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="32" font-weight="800" fill="#0073ce">pagoPA</text>
<path d="M47 62c20 26 66 27 88 2" fill="none" stroke="#0073ce" stroke-width="8" stroke-linecap="round"/>
<path d="M45 61l4 28 21-18z" fill="#0073ce"/>
</svg>"""


def _first_image_data_uri(candidates: Iterable[Path]) -> str | None:
    for path in candidates:
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        media_type = "image/png" if suffix == ".png" else "image/svg+xml" if suffix == ".svg" else None
        if media_type is None:
            continue
        try:
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError:
            continue
        return f"data:{media_type};base64,{encoded}"
    return None


def _gaia_proposal_html(
    payload: dict[str, Any],
    *,
    include_main: bool = True,
    include_partitario: bool = True,
    include_bollettino: bool = True,
) -> str:
    field_values = _batch_template_field_values(payload)
    yearly_rows = _batch_yearly_row_values(payload)
    partitario_sections_html = _gaia_partitario_sections_html(_batch_partitario_lines(payload))
    cbo_logo_html = _gaia_logo_html(
        candidates=_GAIA_CBO_LOGO_CANDIDATES,
        alt="Logo Consorzio di Bonifica dell'Oristanese",
        fallback="CBO",
    )
    pagopa_logo_html = _gaia_logo_html(
        candidates=_GAIA_PAGOPA_LOGO_CANDIDATES,
        alt="Logo pagoPA",
        fallback="pagoPA",
    )
    notification_amount = _format_template_number(payload.get("notification_amount") or REGISTERED_MAIL_NOTIFICATION_AMOUNT)
    summary_rows = "".join(
        "<tr>"
        f"<td>{html.escape(row['Anno_Ruolo'])}</td>"
        f"<td class=\"notice-number\">{html.escape(row['Rif_Ruolo'])}</td>"
        f"<td>{html.escape(row['M_648'])}</td>"
        f"<td>{html.escape(row['M_668'])}</td>"
        f"<td>{html.escape(row['M_985'])}</td>"
        f"<td>{html.escape(row['Magg_Applicate'])}</td>"
        f"<td>{html.escape(row['Interessi'])}</td>"
        f"<td>{html.escape(row['Riscosso'])}</td>"
        "<td>0,00</td>"
        "</tr>"
        for row in yearly_rows
    )
    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>GAIA - Proposta Avviso/Sollecito</title>
<style>
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: #17231e; font-family: Arial, Helvetica, sans-serif; font-size: 10.2pt; line-height: 1.28; }}
.page {{ width: 210mm; min-height: 297mm; break-after: page; page-break-after: always; position: relative; padding: 12mm 18mm 12mm 13mm; }}
.page:last-child {{ break-after: auto; page-break-after: auto; }}
.front {{ font-size: 11.45pt; line-height: 1.28; }}
.header {{ display: grid; grid-template-columns: 39mm 1fr 39mm; align-items: center; gap: 5mm; padding-bottom: 5mm; border-bottom: 1.6pt solid #1f5d45; }}
.brand {{ display: grid; place-content: center; position: relative; height: 23mm; border-radius: 4mm; border: 1pt solid #d9e3dd; font-weight: 900; text-align: center; overflow: hidden; }}
.brand svg {{ display: block; width: 100%; height: 100%; }}
.logo-image {{ display: block; position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }}
.brand.cbo {{ color: #213d66; font-size: 23pt; letter-spacing: -1.5pt; }}
.brand.cbo .logo-image {{ inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center; }}
.brand.pagopa {{ justify-self: end; width: 39mm; color: #0b6eb4; font-size: 15pt; }}
.head-title {{ text-align: center; }}
.head-title h1 {{ margin: 0; font-family: Georgia, serif; font-size: 21.5pt; line-height: 1.05; }}
.head-title p {{ margin: 1.5mm 0 0; font-weight: 700; font-size: 10.2pt; }}
.notice-title {{ margin: 5mm 0 4.5mm; padding: 3mm 4mm; background: linear-gradient(90deg, #1f5d45, #2c7558); color: white; border-radius: 2.5mm; font-weight: 800; text-align: center; font-size: 13.2pt; }}
.grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; }}
.card {{ border: 1pt solid #cfd8d2; border-radius: 3mm; overflow: hidden; background: #fff; }}
.card h2 {{ margin: 0; padding: 2.4mm 3mm; background: #e7f0ea; color: #1f5d45; font-size: 10.2pt; text-transform: uppercase; letter-spacing: .4pt; }}
.body {{ padding: 3mm; }}
.kv {{ display: grid; grid-template-columns: 28mm 1fr; gap: 1.2mm 2mm; }}
.kv b {{ color: #5b6b63; font-size: 8.9pt; }}
.recipient {{ font-weight: 800; font-size: 11.3pt; }}
.pay-band {{ margin-top: 5mm; display: grid; grid-template-columns: 56mm 1fr; gap: 4mm; align-items: stretch; }}
.amount {{ background: #f8f5ec; border: 1.3pt solid #b18b3d; border-radius: 3mm; padding: 4mm; }}
.amount .label {{ text-transform: uppercase; color: #745821; font-size: 8.7pt; font-weight: 800; letter-spacing: .4pt; }}
.amount .euro {{ font-family: Georgia, serif; font-size: 28pt; color: #1f5d45; font-weight: 900; margin: 1.5mm 0; }}
.instructions {{ border-left: 3pt solid #1f5d45; padding-left: 4mm; }}
.instructions h2 {{ margin: 0 0 2mm; color: #1f5d45; font-size: 13pt; }}
.instructions p {{ margin: 1mm 0; }}
.summary {{ margin-top: 4mm; width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 8.05pt; }}
.summary col.role {{ width: 13%; }}
.summary col.notice {{ width: 16%; }}
.summary col.opere {{ width: 14%; }}
.summary col.utenza {{ width: 11%; }}
.summary col.quota {{ width: 14%; }}
.summary col.magg {{ width: 8%; }}
.summary col.interessi {{ width: 8%; }}
.summary col.versate {{ width: 10%; }}
.summary col.spese {{ width: 6%; }}
.summary th {{ background: #eef3f0; color: #1f5d45; border: 1px solid #cfd8d2; padding: 1mm .75mm; text-align: left; overflow-wrap: anywhere; }}
.summary td {{ border: 1px solid #cfd8d2; padding: 1.05mm .75mm; text-align: right; }}
.summary td:first-child {{ text-align: left; font-weight: 800; }}
.summary .notice-number {{ white-space: nowrap; text-align: left; font-size: 7.35pt; letter-spacing: -.12pt; }}
.note {{ margin-top: 3mm; padding-top: 2.4mm; border-top: 1px solid #cfd8d2; font-size: 9.15pt; line-height: 1.16; color: #2e3934; text-align: justify; }}
.privacy {{ margin-top: 1.6mm; }}
.rev {{ position: absolute; bottom: 0; left: 0; font-size: 7.5pt; color: #5b6b63; }}
.legal h2 {{ text-align: center; margin: 0 0 2.4mm; font-size: 10.2pt; font-weight: 800; }}
.legal-copy {{ font-size: 8.75pt; line-height: .97; padding-bottom: 16mm; width: 100%; }}
.legal-copy p {{ margin: 0 0 .08mm; text-align: justify; }}
.legal-copy ul {{ margin: -.55mm 0 .16mm 8mm; padding: 0; }}
.legal-copy li {{ margin: 0; padding: 0; }}
.warning em {{ font-style: italic; text-decoration: underline; }}
.signature {{ position: absolute; right: 0; bottom: 4mm; width: 78mm; text-align: center; font-family: Georgia, 'Times New Roman', serif; color: #1a211d; }}
.signature .title {{ font-size: 7.8pt; font-weight: 700; letter-spacing: .25pt; }}
.signature .name {{ font-size: 8.4pt; font-weight: 600; margin-top: .3mm; }}
.signature .rule {{ width: 38mm; border-top: .7pt solid #87958e; margin: 1mm auto .75mm; }}
.signature .note {{ font-size: 5.9pt; line-height: 1.05; color: #39443f; border: 0; margin: 0; padding: 0; }}
.bollettino-page {{ padding: 0; overflow: hidden; color: #111; background: #fff; }}
.bollettino-sheet {{ position: absolute; inset: 0; width: 210mm; height: 297mm; overflow: hidden; font: 9.8pt Arial, Helvetica, sans-serif; }}
.bollettino-landscape {{ position: absolute; top: 292mm; left: 6mm; width: 297mm; height: 210mm; padding: 5.5mm 6.5mm; overflow: hidden; transform-origin: top left; transform: rotate(-90deg) scale(.940); }}
.bollettino-methods {{ position: relative; height: 52mm; min-height: 52mm; }}
.bollettino-methods h2 {{ position: absolute; top: 0; left: 0; right: 0; margin: 0; text-align: center; font-size: 11pt; }}
.bollettino-methods-box {{ position: absolute; left: 0; right: 0; top: 8.5mm; bottom: 0; border: 1.2pt solid #111; overflow: hidden; }}
.bollettino-methods-box-inner {{ padding: 3.5mm; }}
.bollettino-methods p {{ margin: .8mm 0; }}
.bollettino-methods .indent {{ margin-left: 13mm; }}
.bollettino-methods .under {{ text-decoration: underline; }}
.bollettino-bonifico {{ margin-top: 5mm; border: 1.2pt solid #111; min-height: 25mm; padding: 4mm; text-align: center; }}
.bollettino-bonifico h3 {{ margin: 0 0 5mm; font-size: 9.8pt; text-transform: uppercase; }}
.bollettino-bonifico p {{ margin: 2mm 0; }}
.bollettino-coupons {{ margin-top: 21mm; margin-left: -6.5mm; margin-right: -6.5mm; width: 297mm; height: 102mm; display: grid; grid-template-columns: 132mm 165mm; gap: 0; font-family: "Courier New", monospace; }}
.bollettino-slip {{ height: 102mm; min-height: 0; padding: 0; position: relative; color: #111; border-top: 1pt solid #333; overflow: hidden; }}
.bollettino-slip.accredito {{ border-left: 1pt solid #333; }}
.bollettino-slip .band {{ position: absolute; left: 0; right: 0; top: 0; height: 4mm; padding: .6mm 6mm 0; background: #d6d6d6; border-bottom: .8pt solid #333; font: 6.6pt Arial, sans-serif; text-transform: uppercase; display: flex; justify-content: space-between; }}
.bollettino-logo-cbo {{ position: absolute; left: 6mm; top: 7.5mm; width: 20mm; height: 15mm; display: flex; align-items: center; justify-content: center; }}
.bollettino-logo-cbo img {{ max-width: 20mm; max-height: 15mm; object-fit: contain; filter: grayscale(100%); }}
.bollettino-euro-block {{ position: absolute; top: 7.5mm; left: 7.5mm; width: 13mm; text-align: center; }}
.bollettino-slip.versamento .bollettino-euro-block {{ left: 28mm; }}
.bollettino-euro-mark {{ width: 7mm; height: 7mm; margin: 0 auto .6mm; background: #222; color: white; display: grid; place-content: center; font: 800 13pt Georgia, serif; }}
.bollettino-small-label {{ font: 6.5pt Arial, sans-serif; text-transform: uppercase; color: #333; }}
.bollettino-account-row {{ position: absolute; top: 9.5mm; left: 23mm; right: 40mm; white-space: nowrap; }}
.bollettino-slip.versamento .bollettino-account-row {{ left: 44mm; }}
.bollettino-account {{ font-weight: 800; letter-spacing: 1.6pt; font-size: 10.6pt; }}
.bollettino-amount-row {{ position: absolute; top: 9.5mm; right: 7.5mm; width: 31mm; text-align: right; }}
.bollettino-amount {{ font-weight: 800; letter-spacing: 1.7pt; font-size: 11.2pt; }}
.bollettino-iban {{ position: absolute; top: 18mm; left: 7.5mm; right: 6mm; display: flex; justify-content: center; gap: 2mm; align-items: center; white-space: nowrap; }}
.bollettino-slip.versamento .bollettino-iban {{ left: 39mm; right: 3mm; }}
.bollettino-boxes {{ display: grid; grid-template-columns: repeat(27, 2.52mm); width: max-content; white-space: nowrap; }}
.bollettino-boxes span {{ height: 3.8mm; border: .4pt solid #cfcfcf; border-right: 0; display: grid; place-content: center; font-size: 7.7pt; line-height: 1; }}
.bollettino-boxes span:last-child {{ border-right: .4pt solid #cfcfcf; }}
.bollettino-intestato-label {{ position: absolute; top: 24.5mm; left: 7.5mm; }}
.bollettino-intestato {{ position: absolute; top: 28mm; left: 7.5mm; right: 7.5mm; font-size: 10.25pt; font-weight: 800; letter-spacing: 1.45pt; line-height: 1.12; }}
.bollettino-eseguito {{ position: absolute; top: 36.8mm; left: 7.5mm; right: 61mm; max-height: 17mm; overflow: hidden; font-size: 8.25pt; line-height: 1.05; }}
.bollettino-eseguito-address {{ display: block; margin-top: .7mm; font-size: 7.05pt; line-height: 1.04; white-space: normal; overflow-wrap: break-word; }}
.bollettino-slip.accredito .bollettino-eseguito {{ left: 60mm; right: 4mm; top: 35.2mm; max-height: 16mm; }}
.bollettino-details {{ position: absolute; left: 7.5mm; right: 61mm; top: 58.5mm; font-size: 9.1pt; line-height: 1.18; }}
.bollettino-slip.accredito .bollettino-details {{ left: 60mm; right: 8mm; top: 53mm; }}
.bollettino-customer {{ position: absolute; left: 7.5mm; top: 42mm; font-size: 13pt; font-weight: 800; letter-spacing: 1.5pt; }}
.bollettino-barcode-svg {{ position: absolute; right: 10mm; top: 64mm; width: 93mm; height: 12mm; display: block; }}
.bollettino-barcode-number {{ position: absolute; right: 10mm; top: 76.3mm; width: 93mm; text-align: center; font: 5.8pt Arial, Helvetica, sans-serif; letter-spacing: .15pt; }}
.bollettino-barcode-note {{ position: absolute; right: 10mm; top: 79.2mm; width: 93mm; text-align: center; font: 4.9pt Arial, Helvetica, sans-serif; color: #444; text-transform: uppercase; }}
.bollettino-postmark {{ position: absolute; width: 55mm; height: 34mm; border: .65pt dashed #d1d1d1; text-align: center; color: #444; }}
.bollettino-slip.versamento .bollettino-postmark {{ right: 6mm; top: 49mm; height: 28mm; }}
.bollettino-slip.accredito .bollettino-postmark {{ left: 55mm; top: 82mm; width: 38mm; height: 7mm; border-color: transparent; }}
.bollettino-postmark-label {{ margin-top: 10mm; font: 6.2pt Arial, Helvetica, sans-serif; text-transform: uppercase; letter-spacing: .18pt; }}
.bollettino-slip.accredito .bollettino-postmark-label {{ margin-top: 0; }}
.bollettino-postmark-code {{ font: 5.5pt Arial, Helvetica, sans-serif; color: #555; line-height: 1; }}
.bollettino-datamatrix {{ position: absolute; right: 5mm; top: 77mm; width: 48.75mm; height: 18.75mm; display: block; }}
.bollettino-codeline {{ position: absolute; left: 0; right: 0; bottom: 4mm; height: 9mm; font-size: 11.4pt; letter-spacing: .65pt; white-space: nowrap; }}
.bollettino-codeline span {{ position: absolute; top: 0; }}
.bollettino-codeline .field-customer {{ left: 7.5mm; }}
.bollettino-codeline .field-amount {{ left: 74mm; }}
.bollettino-codeline .field-account {{ left: 108mm; }}
.bollettino-codeline .field-td {{ right: 7.5mm; text-align: right; }}
.bollettino-authorization {{ position: absolute; right: 8mm; top: 4.8mm; font: 5.8pt Arial, Helvetica, sans-serif; letter-spacing: .2pt; }}
.partitario-page {{ break-before: page; page-break-before: always; min-height: 297mm; }}
.partitario-page:first-child {{ break-before: auto; page-break-before: auto; }}
.partitario-title {{ margin: 0 0 3mm; color: #1f5d45; font: 800 14pt Arial, sans-serif; border-bottom: 1.2pt solid #1f5d45; padding-bottom: 2mm; }}
.partitario {{ font-family: "Courier New", monospace; font-size: 10.45pt; line-height: 1.14; max-width: 100%; color: #111; }}
.partitario-line {{ display: block; white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; }}
</style>
</head>
<body>
{f'''
<section class="page front">
  <div class="header">
    <div class="brand cbo">{cbo_logo_html}</div>
    <div class="head-title"><h1>Consorzio di Bonifica<br>dell'Oristanese</h1><p>DPGRS N. 239 del 04.12.96</p></div>
    <div class="brand pagopa">{pagopa_logo_html}</div>
  </div>
  <div class="notice-title">AVVISO/SOLLECITO DI PAGAMENTO N. {html.escape(field_values['Avviso_n'])}<br>{html.escape(field_values['Oggetto_Ruoli'])}</div>
  <div class="grid-2">
    <div class="card"><h2>Ente creditore</h2><div class="body kv">
      <b>Codice fiscale</b><span>90022600952</span><b>Sede</b><span>Via Cagliari 170 - 09170 Oristano</span>
      <b>Telefono</b><span>0783 3150</span><b>Sito</b><span>www.bonificaoristanese.it</span>
      <b>E-mail</b><span>catasto@bonificaoristanese.it</span><b>PEC</b><span>protocollo.cbo@pec.it</span>
    </div></div>
    <div class="card"><h2>Destinatario avviso</h2><div class="body">
      <div class="recipient">{html.escape(field_values['Denominazione'])}</div>
      <p>{html.escape(field_values['INDIRIZZO'])}<br>{html.escape(' '.join(value for value in (field_values['CAP'], field_values['CITTA'], field_values['PROVINCIA']) if value and value != '-'))}</p>
      <div class="kv"><b>Codice fiscale</b><span>{html.escape(field_values['CodFiscale'])}</span></div>
    </div></div>
  </div>
  <div class="pay-band">
    <div class="amount"><div class="label">Quanto e quando pagare</div><div class="euro">€. {html.escape(field_values['Complessivo'])}</div><div><b>entro il {html.escape(field_values['Scadenza'])}</b><br>UNICA SOLUZIONE</div></div>
    <div class="instructions"><h2>Come pagare</h2><p>Il pagamento potrà essere effettuato mediante bonifico bancario al Conto Corrente:</p><p><b>Intestato a:</b> CONSORZIO DI BONIFICA DELL'ORISTANESE - RISCOSSIONE QUOTE ASSOCIATIVE</p><p><b>IBAN:</b> IT15L0760117400001007214826</p><p><b>Causale:</b> {html.escape(field_values['CodFiscale'])}; {html.escape(field_values['Avviso_n'])}</p></div>
  </div>
  <table class="summary"><colgroup><col class="role"><col class="notice"><col class="opere"><col class="utenza"><col class="quota"><col class="magg"><col class="interessi"><col class="versate"><col class="spese"></colgroup><thead><tr><th>Ruolo</th><th>Numero avviso</th><th>0648 Opere irrigue</th><th>0668 Utenza</th><th>0985 Quota istituzionale</th><th>Magg.</th><th>Interessi</th><th>Somme versate</th><th>Altre spese</th></tr></thead><tbody>{summary_rows}<tr><td>SN01 Spese Notifica</td><td colspan="7"></td><td>{html.escape(notification_amount)}</td></tr></tbody></table>
  <div class="note">
    Si può richiedere, direttamente presso gli uffici dell'Ente, una diversa dilazione del pagamento. Per maggiori chiarimenti contattare l'Ente o recarsi presso la sede nei seguenti giorni: Lunedi e giovedì 11.00 - 13.00, - tel. 0783 3150212.
    <div class="privacy"><strong>INFORMATIVA SUL TRATTAMENTO DEI DATI PERSONALI:</strong> lo scrivente Consorzio, titolare del trattamento dei dati personali, li utilizza esclusivamente per le finalità istituzionali previste dalla legge, anche quando comunicate a terzi. Il trattamento dei Suoi dati avviene anche mediante l'utilizzo di strumenti elettronici, con logistiche strettamente correlate alle predette finalità nel rispetto del D.LGS n. 196/2003.</div>
  </div>
  <div class="rev">Rev.2026/01</div>
</section>
<section class="page legal">
  <h2>Comunicazioni per il Contribuente</h2>
  <div class="legal-copy">{_gaia_legal_html(field_values)}</div>
  <div class="signature"><div class="title">IL DIRETTORE GENERALE</div><div class="name">Dott. Maurizio Scanu</div><div class="rule"></div><div class="note">Sottoscrizione originale sostituita da firma a stampa<br>ex art. 3 D. Lgs. n. 39 del 12.02.1993 - Giusta Det. DG n. 01/2022</div></div>
</section>
''' if include_main else ''}
{partitario_sections_html if include_partitario else ''}
{f'''
<section class="page bollettino-page">
{_gaia_bollettino_html(field_values, payload)}
</section>
''' if include_bollettino else ''}
</body>
</html>"""


def _gaia_partitario_sections_html(lines: Iterable[str], *, lines_per_page: int = 58) -> str:
    normalized_lines = list(lines)
    if not normalized_lines:
        normalized_lines = [""]
    sections: list[str] = []
    total_pages = (len(normalized_lines) + lines_per_page - 1) // lines_per_page
    for index in range(0, len(normalized_lines), lines_per_page):
        page_lines = normalized_lines[index : index + lines_per_page]
        page_number = (index // lines_per_page) + 1
        title = f"Dettaglio partitario allegato - pagina {page_number} di {total_pages}"
        sections.append(
            '<section class="page partitario-page">'
            f'<div class="partitario-title">{html.escape(title)}</div>'
            f'<div class="partitario">{_gaia_partitario_lines_html(page_lines)}</div>'
            "</section>"
        )
    return "".join(sections)


def _gaia_partitario_lines_html(lines: Iterable[str]) -> str:
    return "".join(
        f'<div class="partitario-line">{html.escape(line) if line else "&nbsp;"}</div>'
        for line in lines
    )


def _gaia_legal_html(field_values: dict[str, str]) -> str:
    legal_blocks = _extract_gaia_legal_blocks(_default_batch_reminder_template_path())
    if legal_blocks:
        return _gaia_legal_blocks_html(legal_blocks, field_values)
    return _gaia_fallback_legal_html(field_values)


def _extract_gaia_legal_blocks(template_path: Path) -> list[dict[str, Any]]:
    if not template_path.is_file():
        return []
    try:
        with zipfile.ZipFile(template_path, "r") as archive:
            document_xml = archive.read(WORD_DOCUMENT_PATH)
        root = ET.fromstring(document_xml)
    except Exception:
        return []

    body = root.find(".//w:body", WORD_NAMESPACES)
    if body is None:
        return []

    children = list(body)
    legal_start = _find_body_text_index(children, "Comunicazioni per il Contribuente")
    if legal_start is None:
        return []
    signature_start = _find_body_text_index(children[legal_start + 1 :], "IL DIRETTORE GENERALE")
    legal_end = legal_start + 1 + signature_start if signature_start is not None else len(children)

    blocks: list[dict[str, Any]] = []
    for element in children[legal_start + 1 : legal_end]:
        text = _word_paragraph_text(element)
        if not text:
            continue
        blocks.append({"text": text, "list": _is_word_list_paragraph(element)})
    return blocks


def _word_paragraph_text(element: ET.Element) -> str:
    parts: list[str] = []
    text_tag = f"{{{WORD_NAMESPACE}}}t"
    tab_tag = f"{{{WORD_NAMESPACE}}}tab"
    break_tag = f"{{{WORD_NAMESPACE}}}br"
    for node in element.iter():
        if node.tag == text_tag and node.text:
            parts.append(node.text)
        elif node.tag == tab_tag:
            parts.append(" ")
        elif node.tag == break_tag:
            parts.append("\n")
    text = "".join(parts).replace("\xa0", " ")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _is_word_list_paragraph(element: ET.Element) -> bool:
    return element.find(".//w:numPr", WORD_NAMESPACES) is not None


def _gaia_legal_blocks_html(blocks: list[dict[str, Any]], field_values: dict[str, str]) -> str:
    chunks: list[str] = []
    in_list = False
    for block in blocks:
        text = _replace_legal_placeholders(str(block["text"]), field_values)
        if block["list"]:
            if not in_list:
                chunks.append("<ul>")
                in_list = True
            chunks.append(f"<li>{html.escape(text)}</li>")
            continue
        if in_list:
            chunks.append("</ul>")
            in_list = False
        chunks.append(_gaia_legal_paragraph_html(text))
    if in_list:
        chunks.append("</ul>")
    return "\n".join(chunks)


def _replace_legal_placeholders(text: str, field_values: dict[str, str]) -> str:
    for field_name, value in field_values.items():
        text = text.replace(f"«{field_name}»", value)
    return text


def _gaia_legal_paragraph_html(text: str) -> str:
    labels = (
        "Informazioni di carattere generale.",
        "Informazioni sul tributo.",
        "Scadenza del Pagamento:",
        "Determinazione del Contributo.",
        "Detraibilità del contributo.",
        "Modalità di ricorso al presente avviso di pagamento.",
        "Richiesta di Voltura / Variazione:",
        "Informazione sulla riscossione mediante Avvisi di Pagamento:",
        "AVVERTENZA IMPORTANTE:",
    )
    for label in labels:
        if text.startswith(label):
            return f"<p><strong>{html.escape(label)}</strong>{html.escape(text[len(label) :])}</p>"
    return f"<p>{html.escape(text)}</p>"


def _gaia_fallback_legal_html(field_values: dict[str, str]) -> str:
    tax_code = html.escape(field_values["CodFiscale"])
    notice_number = html.escape(field_values["Avviso_n"])
    return f"""
    <p><strong>Informazioni di carattere generale.</strong> Il Consorzio di Bonifica dell'Oristanese è un Ente Pubblico ex art. 59 R.D. 215/1933 e art. 14 L.R. 06/2008. Il contributo consortile costituisce la quota dovuta da ciascun consorziato per le spese di manutenzione e gestione delle opere di bonifica, nonché per le spese di funzionamento dell'Ente. Sono tenuti al pagamento i proprietari di terreni ricadenti nel perimetro consortile e serviti dalla rete consortile di distribuzione dell'acqua ad uso irriguo. I contributi di bonifica sono oneri reali sulla proprietà, sono esigibili con le norme per l'esazione dei tributi e seguono il regime di riscossione delle imposte. Il contributo consortile è annuale e le volture producono effetti a partire dal ruolo dell'anno successivo.</p>
    <p><strong>Informazioni sul tributo.</strong> L'Avviso di Pagamento si riferisce ai tributi istituzionali, manutenzione opere irrigue e utenza irrigua, emessi in acconto in attesa dell'approvazione del Rendiconto di gestione. L'emissione dei ruoli è disposta dagli atti deliberativi dell'Ente pubblicati all'albo.</p>
    <p>Dilazione del pagamento. Il contribuente può richiedere, direttamente presso gli uffici dell'Ente, una dilazione del pagamento del presente AVVISO fino a:</p><ul><li>n. 18 rate per gli importi superiori ai 5.000,00 euro; n. 12 rate per gli importi da 1.000,00 euro a 5.000,00 euro;</li><li>n. 6 rate per gli importi da 500,01 euro a 1.000,00 euro; n. 4 rate per gli importi da 300,01 euro a 500,00 euro;</li><li>n. 2 rate per gli importi da 100,00 euro a 300,00 euro; non sono previste dilazioni per importi inferiori a 100,00 euro;</li></ul>
    <p><strong>Scadenza del Pagamento:</strong> Si ricorda che in caso di mancato pagamento nel termine indicato, verranno attivate le procedure previste dal D.P.R. n. 602/1973 e successive modificazioni con conseguente aggravio delle spese per la riscossione coattiva.</p>
    <p>Il pagamento potrà essere effettuato anche mediante bonifico bancario al Conto Corrente:<br>Intestato a: CONSORZIO DI BONIFICA DELL'ORISTANESE - RISCOSSIONE QUOTE ASSOCIATIVE<br>Iban: IT15L0760117400001007214826 - Causale: indicare codice fiscale {tax_code} e numero dell'avviso di pagamento {notice_number}</p>
    <p><strong>Determinazione del Contributo.</strong> Il tributo istituzionale è dovuto per le spese di funzionamento dell'Ente (cod. 0985). Il tributo per la manutenzione opere irrigue (cod. 0648) è dovuto per le spese di manutenzione ordinaria delle opere irrigue. Il contributo utenza (cod. 0668) è dovuto da coloro che hanno utilizzato la risorsa idrica ed è commisurato ai criteri del Piano di Classifica e Riparto.</p>
    <p><strong>Detraibilità del contributo.</strong> I contributi del Consorzio hanno natura tributaria. Il contributo istituzionale e il contributo opere irrigue sono deducibili dal reddito lordo da denunciare ai fini fiscali; il contributo utenza non è invece deducibile.</p>
    <p><strong>Modalità di ricorso al presente avviso di pagamento.</strong></p><ul><li>Direttamente al Consorzio di Bonifica dell'Oristanese mediante raccomandata A/R da inviarsi alla sede legale: Via Cagliari 170, 09170 ORISTANO, ovvero mediante PEC all'indirizzo protocollo.cbo@pec.it.</li></ul>
    <p><strong>Richiesta di Voltura / Variazione:</strong> Il contribuente potrà segnalare al Consorzio qualsiasi correzione di dati anagrafici e/o di trasferimento della proprietà mediante invio di apposita comunicazione:</p><ul><li>Via posta all'indirizzo del Consorzio: 09170 Oristano - Via Cagliari, 170</li><li>Via e-mail a uno dei seguenti indirizzi: catasto@bonificaoristanese.it, tributi.cbo@pec.it;</li></ul>
    <p><strong>Informazione sulla riscossione mediante Avvisi di Pagamento:</strong> La riscossione ordinaria dei contributi di bonifica iscritti a ruolo viene fatta precedere da una fase di riscossione volontaria realizzata mediante avvisi di pagamento, consentendo al contribuente di evitare i diritti di notifica altrimenti dovuti all'Agente della Riscossione.</p>
    <p class="warning"><strong>AVVERTENZA IMPORTANTE:</strong> IL MANCATO PAGAMENTO DEL PRESENTE AVVISO, NON GIUSTIFICA IL MANCATO O TARDIVO VERSAMENTO DEL TRIBUTO DOVUTO. PERTANTO, È OBBLIGO DEL CONTRIBUENTE ATTIVARSI PER ADEMPIERE AL PAGAMENTO DEL DOVUTO ALLA SCADENZA PREFISSATA. <em>Tale omissione comporta il conseguente avvio della RISCOSSIONE COATTIVA del credito tributario in oggetto.</em></p>
    <p>Il responsabile del procedimento è il Direttore Generale del Consorzio, Dott. Maurizio Scanu.</p>
    """


def _gaia_bollettino_html(field_values: dict[str, str], payload: dict[str, Any]) -> str:
    values = _gaia_bollettino_values(field_values, payload)
    return f"""
  <div class="bollettino-sheet">
  <div class="bollettino-landscape">
    <div class="bollettino-methods">
      <h2>MODALITA' DI PAGAMENTO: <span>I pagamenti possono essere effettuati:</span></h2>
      <div class="bollettino-methods-box">
        <div class="bollettino-methods-box-inner">
          <p><strong>Presso qualsiasi ufficio postale</strong> utilizzando ESCLUSIVAMENTE i bollettini allegati al presente avviso;</p>
          <p><strong>On-line:</strong></p>
          <p class="indent">- <span class="under">per i correntisti postali:</span> tramite BancoPostaOnLine (funzione "Paga bollettino");</p>
          <p class="indent">- <span class="under">per i non correntisti:</span> sul sito www.poste.it - previa registrazione (funzione "Paga bollettino") con addebito su Carta di Credito VISA e MasterCard o con Carta PostePay.</p>
          <p class="indent">- <span class="under">per i clienti POSTEMOBILE:</span> tramite servizio "Semplifica" addebitando l'importo sul Conto BancoPosta o sulla Postepay associati alla tua SIM PosteMobile.</p>
          <p><strong>Altre modalità:</strong></p>
        </div>
      </div>
    </div>
    <div class="bollettino-bonifico">
      <h3>MODALITA' DI PAGAMENTO A MEZZO BONIFICO BANCARIO</h3>
      <p>Il bonifico per il pagamento dell'importo richiesto con il presente avviso, dovrà riportare la seguente <strong>causale: {html.escape(values['bonifico_causale'])}</strong></p>
      <p>Versamenti eseguiti con <span class="under">causale difforme</span> da quanto indicato <span class="under">potrebbero non essere correttamente rendicontati</span> dal sistema.</p>
    </div>
    <div class="bollettino-coupons">
      {_gaia_bollettino_slip_html(values, title="Ricevuta di Versamento", kind="versamento")}
      {_gaia_bollettino_slip_html(values, title="Ricevuta di Accredito", kind="accredito")}
    </div>
    </div>
  </div>"""


def _gaia_bollettino_slip_html(values: dict[str, str], *, title: str, kind: str) -> str:
    is_accredito = kind == "accredito"
    logo_html = "" if is_accredito else f'<div class="bollettino-logo-cbo">{values["cbo_logo_html"]}</div>'
    authorization_html = (
        f'<div class="bollettino-authorization">{html.escape(_BOLLETTINO_PRINT_AUTHORIZATION)}</div>'
        if is_accredito
        else ""
    )
    barcode_html = (
        f'{values["barcode_svg"]}<div class="bollettino-barcode-number">{html.escape(values["barcode_number"])}</div>'
        '<div class="bollettino-barcode-note">Importante: non scrivere nella zona sottostante</div>'
        if is_accredito
        else _gaia_bollettino_datamatrix_html(values["barcode_number"])
    )
    customer_html = (
        f'<div class="bollettino-customer">{html.escape(values["customer_code"])}</div>'
        if is_accredito
        else ""
    )
    codeline_html = (
        '<div class="bollettino-codeline">'
        f'<span class="field-customer">&lt;{html.escape(values["customer_code"])}&gt;</span>'
        f'<span class="field-amount">{html.escape(values["amount_code"])}&gt;</span>'
        f'<span class="field-account">{html.escape(values["postal_account_code"])}&lt;</span>'
        f'<span class="field-td">{_BOLLETTINO_TD_CODE}&gt;</span>'
        "</div>"
        if is_accredito
        else ""
    )
    causale_row = "" if is_accredito else f"<div>Causale: &nbsp;&nbsp;&nbsp; {html.escape(values['causale'])}</div>"
    return f"""
    <div class="bollettino-slip {html.escape(kind)}">
      <div class="band"><span>Conti correnti postali - {html.escape(title)}</span><span>BancoPosta</span></div>
      {authorization_html}
      {logo_html}
      <div class="bollettino-euro-block"><div class="bollettino-euro-mark">€</div><div class="bollettino-small-label">TD 896</div></div>
      <div class="bollettino-account-row"><span class="bollettino-small-label">sul C/C n.</span> <span class="bollettino-account">{html.escape(values['postal_account'])}</span></div>
      <div class="bollettino-amount-row"><div class="bollettino-small-label">di Euro</div><div class="bollettino-amount">{html.escape(values['amount'])}</div></div>
      <div class="bollettino-iban"><span class="bollettino-small-label">Codice IBAN</span><span class="bollettino-boxes">{values['iban_boxes_html']}</span></div>
      <div class="bollettino-small-label bollettino-intestato-label">Intestato a</div>
      <div class="bollettino-intestato">{html.escape(values['account_line_1'])}<br>{html.escape(values['account_line_2'])}</div>
      <div class="bollettino-eseguito">eseguito da: {html.escape(values['payer_name'])}<span class="bollettino-eseguito-address">{html.escape(values['payer_address'])}</span></div>
      {customer_html}
      {_gaia_bollettino_postmark_html()}
      <div class="bollettino-details">
        <div>Scadenza: {html.escape(values['due_date'])} - Rata unica</div>
        <div>Esercizio: &nbsp;&nbsp; {html.escape(values['esercizio'])}{' Causale: ' + html.escape(values['causale']) if is_accredito else ''}</div>
        {causale_row}
        <div>Importo: &nbsp;&nbsp;&nbsp; {html.escape(values['amount'])}</div>
      </div>
      {barcode_html}
      {codeline_html}
    </div>"""


def _gaia_bollettino_postmark_html() -> str:
    return """
        <div class="bollettino-postmark">
          <div class="bollettino-postmark-label">BOLLO DELL'UFFICIO POSTALE</div>
          <div class="bollettino-postmark-code">codice cliente</div>
        </div>"""


def _gaia_bollettino_datamatrix_html(value: str) -> str:
    return _gaia_bollettino_datamatrix_svg(value)


def _gaia_bollettino_datamatrix_svg(value: str) -> str:
    return td896_datamatrix_svg(value)


def _gaia_bollettino_values(field_values: dict[str, str], payload: dict[str, Any]) -> dict[str, str]:
    amount = field_values["Complessivo"]
    notice_number = field_values["Avviso_n"]
    payment_code = build_td896_payment_code(
        notice_number=notice_number,
        amount=amount,
        postal_account=_BOLLETTINO_POSTAL_ACCOUNT,
    )
    return {
        "account_line_1": _BOLLETTINO_ACCOUNT_NAME_LINES[0],
        "account_line_2": _BOLLETTINO_ACCOUNT_NAME_LINES[1],
        "amount": amount,
        "amount_code": payment_code.amount_code,
        "barcode_number": payment_code.barcode_payload,
        "barcode_svg": _gaia_bollettino_code128_svg(payment_code.barcode_payload),
        "bonifico_causale": f"A {notice_number} CF {field_values['CodFiscale']}",
        "causale": _gaia_bollettino_causale(payload, notice_number),
        "cbo_logo_html": _gaia_bollettino_cbo_logo_html(),
        "customer_code": payment_code.customer_code,
        "codeline": payment_code.codeline,
        "due_date": _gaia_bollettino_due_date(payload),
        "esercizio": _gaia_bollettino_esercizio(payload),
        "iban_boxes_html": _gaia_bollettino_iban_boxes_html(_BOLLETTINO_IBAN),
        "iban_spaced": " ".join(_BOLLETTINO_IBAN),
        "payer_address": _gaia_bollettino_payer_address(field_values),
        "payer_name": _gaia_bollettino_payer_name(field_values["Denominazione"]),
        "postal_account": _BOLLETTINO_POSTAL_ACCOUNT,
        "postal_account_code": payment_code.postal_account_code,
    }


def _gaia_bollettino_payer_address(field_values: dict[str, str]) -> str:
    return " ".join(field_values.get("INDIRIZZO_SPEDIZIONE", "").split())


def _gaia_bollettino_payer_name(value: str, *, max_length: int = 42) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[: max_length - 3].rstrip()}..."


def _gaia_bollettino_barcode_payload(customer_code: str, amount_code: str, postal_account_code: str) -> str:
    return build_td896_barcode_payload(customer_code, amount_code, postal_account_code)


def _gaia_bollettino_code128_svg(value: str) -> str:
    codes = _gaia_code128c_codes(value)
    x_position = 0
    rects: list[str] = []
    for code in codes:
        pattern = _CODE128_PATTERNS[code]
        draw_bar = True
        for width_text in pattern:
            width = int(width_text)
            if draw_bar:
                rects.append(f'<rect x="{x_position}" y="0" width="{width}" height="60"/>')
            x_position += width
            draw_bar = not draw_bar
    return (
        '<svg class="bollettino-barcode-svg" role="img" aria-label="Codice a barre TD 896" '
        f'viewBox="0 0 {x_position} 60" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{x_position}" height="60" fill="#fff"/>'
        '<g fill="#111">'
        f'{"".join(rects)}'
        "</g></svg>"
    )


def _gaia_code128c_codes(value: str) -> list[int]:
    if not value.isdigit() or len(value) % 2:
        raise ValueError("Il payload Code128-C deve contenere un numero pari di cifre")
    data_codes = [int(value[index : index + 2]) for index in range(0, len(value), 2)]
    checksum = (_CODE128_START_C + sum(code * position for position, code in enumerate(data_codes, start=1))) % 103
    return [_CODE128_START_C, *data_codes, checksum, _CODE128_STOP]


def _gaia_bollettino_cbo_logo_html() -> str:
    data_uri = _first_image_data_uri(_GAIA_CBO_LOGO_CANDIDATES)
    if data_uri:
        return f'<img alt="CBO" src="{data_uri}">'
    return "<strong>CBO</strong>"


def _gaia_bollettino_iban_boxes_html(iban: str) -> str:
    return "".join(f"<span>{html.escape(character)}</span>" for character in iban)


def _gaia_bollettino_customer_code(notice_number: str) -> str:
    return td896_customer_code(notice_number)


def _gaia_bollettino_causale(payload: dict[str, Any], notice_number: str) -> str:
    for key in ("bollettino_causale", "payment_reason_code", "causale"):
        raw_value = payload.get(key)
        if isinstance(raw_value, str) and raw_value.strip():
            return raw_value.strip()
    digits = _NON_DIGIT_RE.sub("", notice_number)
    if len(digits) >= 9:
        return digits[6:9]
    return digits or notice_number


def _gaia_bollettino_amount_code(amount: str) -> str:
    return td896_amount_code(amount)


def _gaia_bollettino_due_date(payload: dict[str, Any]) -> str:
    raw_date = payload.get("due_date") or payload.get("deadline")
    if isinstance(raw_date, str):
        try:
            return datetime.fromisoformat(raw_date.replace("Z", "+00:00")).strftime("%d/%m/%Y")
        except ValueError:
            if raw_date.strip():
                return raw_date.strip().replace(".", "/")
    generated_at = payload.get("generated_at")
    if isinstance(generated_at, str) and generated_at.strip():
        with suppress(ValueError):
            created_at = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            return (created_at + timedelta(days=30)).strftime("%d/%m/%Y")
    return (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%d/%m/%Y")


def _gaia_bollettino_esercizio(payload: dict[str, Any]) -> str:
    years = _sorted_payload_years(payload, _batch_yearly_values(payload))
    if not years:
        return ""
    suffix = str(years[-1])[-2:]
    return f"{suffix}{suffix}"


def _generate_batch_reminder_docx_from_template(
    payload: dict[str, Any],
    *,
    template_path: Path,
    output_path: Path,
) -> None:
    field_values = _batch_template_field_values(payload)
    yearly_rows = _batch_yearly_row_values(payload)
    partitario_xml = _partitario_lines_xml(_batch_partitario_lines(payload))
    with zipfile.ZipFile(template_path, "r") as source, zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == WORD_DOCUMENT_PATH:
                document_xml = data.decode("utf-8")
                if _is_default_batch_reminder_template(template_path):
                    document_xml = _stable_default_batch_template_xml(
                        document_xml,
                        payload=payload,
                        field_values=field_values,
                        yearly_rows=yearly_rows,
                    )
                else:
                    document_xml = _expand_yearly_summary_rows(document_xml, yearly_rows)
                document_xml = _replace_template_field_results(document_xml, field_values)
                document_xml = _append_partitario_xml(document_xml, partitario_xml)
                data = document_xml.encode("utf-8")
            target.writestr(item, data)


def _batch_intro_paragraphs(payload: dict[str, Any]) -> list[str]:
    paragraphs = [
        "Avviso di sollecito pagamento",
        f"Numero avviso: {_value(payload.get('notice_number'))}",
        f"Contribuente: {_value(payload.get('display_name'))}",
        f"CF/P.IVA: {_value(payload.get('codice_fiscale'))}",
        f"Anni inclusi: {_value(', '.join(str(year) for year in payload.get('years', [])))}",
        f"Importo dovuto: {_value(payload.get('due_amount'))}",
        f"Importo pagato: {_value(payload.get('paid_amount'))}",
        f"Saldo da regolarizzare: {_value(payload.get('saldo_amount'))}",
        f"Template di riferimento: {_value(payload.get('template_path'))}",
    ]
    return paragraphs


def _batch_partitario_paragraphs(payload: dict[str, Any]) -> list[str]:
    return ["", *_batch_partitario_lines(payload)]


def _batch_partitario_lines(payload: dict[str, Any]) -> list[str]:
    raw_lines = _stored_partitario_lines(payload)
    if raw_lines:
        return raw_lines

    lines = [
        "=" * PARTITARIO_LINE_WIDTH,
        "ELENCO DELLE PARTITE SOGGETTE A CONTRIBUTO".center(PARTITARIO_LINE_WIDTH),
        "=" * PARTITARIO_LINE_WIDTH,
    ]
    for avviso in payload.get("avvisi", []):
        for partita in avviso.get("partite", []):
            lines.extend(
                [
                    f"Partita {_value(partita.get('codice_partita'))} beni in comune di {_value(partita.get('comune_nome'))}",
                    _partitario_contribuente_line(payload, partita),
                    _partitario_cointestati_line(partita),
                    "Anno Trib Descrizione                                               Ruolo",
                    _partitario_tributo_line(avviso, partita, "0648", "Contributo Opere Irrigue", "importo_0648"),
                    _partitario_tributo_line(avviso, partita, "0668", "Contributo utenza", "importo_0668"),
                    _partitario_tributo_line(avviso, partita, "0985", "Consorzio Quote Ordinarie", "importo_0985"),
                    "Dom. Dis. Fog. Part. Sub Sup.Cata. Sup.Irr. Colt.        Manut.   Irrig.      Ist.",
                ]
            )
            for particella in partita.get("particelle", []):
                lines.append(_partitario_particella_line(particella))
            lines.append("=" * PARTITARIO_LINE_WIDTH)
    lines.append("Legenda:========================================================================")
    lines.extend(
        [
            "     Dom.=Domanda irrigua           Dis.=codice Distretto",
            "     Fog.=Foglio catastale          Part.=Particella catastale   Sub=Subalterno",
            "Sup.Cata.=Superficie catastale  Sup.Irr.=Superficie irrigata  Colt.=Coltura",
            "  Manut.=Manutenzione(0648)      Irrig.=Irrigazione(0668)",
            "     Ist.=Istituzionale(0985)",
        ]
    )
    return [line for line in lines if line is not None]


def _stored_partitario_lines(payload: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    lines: list[str] = []
    for source in _partitario_sources(payload):
        text = _partitario_text_from_source(source)
        if not text or text in seen:
            continue
        seen.add(text)
        if lines:
            lines.append("")
        lines.extend(_split_partitario_text(text))
    return lines


def _partitario_sources(payload: dict[str, Any]) -> Iterable[Any]:
    yield payload.get("partitario")
    for key in ("partitario_raw_html", "partitario_info_html", "partitario_info_text", "partitario_text"):
        yield payload.get(key)
    for avviso in payload.get("avvisi", []):
        if not isinstance(avviso, dict):
            continue
        yield avviso.get("partitario")
        for key in ("partitario_raw_html", "partitario_info_html", "partitario_info_text", "partitario_text"):
            yield avviso.get(key)


def _partitario_text_from_source(source: Any) -> str | None:
    if isinstance(source, str):
        return source.strip() or None
    if not isinstance(source, dict):
        return None
    for key in ("raw_html", "info_html", "info_text", "text"):
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _split_partitario_text(text: str) -> list[str]:
    candidates = _HTML_BR_RE.split(text) if _HTML_BR_RE.search(text) else text.splitlines()
    lines: list[str] = []
    for candidate in candidates:
        cleaned = html.unescape(_HTML_TAG_RE.sub("", candidate)).replace("\xa0", " ")
        for line in cleaned.splitlines():
            if line.strip():
                lines.append(line.rstrip())
    return _trim_partitario_ui_noise(lines)


def _trim_partitario_ui_noise(lines: list[str]) -> list[str]:
    header_index = next(
        (
            index
            for index, line in enumerate(lines)
            if "ELENCO DELLE PARTITE SOGGETTE A CONTRIBUTO" in line
        ),
        None,
    )
    if header_index is None:
        return lines
    start_index = header_index
    for index in range(header_index - 1, -1, -1):
        if set(lines[index].strip()) == {"="}:
            start_index = index
            break
    return _trim_partitario_footer_actions(lines[start_index:])


def _trim_partitario_footer_actions(lines: list[str]) -> list[str]:
    trimmed = list(lines)
    while trimmed:
        footer_text = " ".join(trimmed[-1].split()).casefold()
        if footer_text in {"chiudi", "scarica", "chiudi scarica"}:
            trimmed.pop()
            continue
        break
    return trimmed


def _partitario_contribuente_line(payload: dict[str, Any], partita: dict[str, Any]) -> str:
    name = _value(partita.get("contribuente") or payload.get("display_name"))
    cf = _value(partita.get("contribuente_cf") or payload.get("codice_fiscale"))
    return f"Contribuente: {name[:46]:<46} C.F. {cf}"


def _partitario_cointestati_line(partita: dict[str, Any]) -> str | None:
    co_intestati = partita.get("co_intestati_raw")
    if not co_intestati:
        return None
    return f"Co-intestato con: {co_intestati}"


def _partitario_tributo_line(avviso: dict[str, Any], partita: dict[str, Any], codice: str, descrizione: str, amount_key: str) -> str:
    amount = _format_partitario_amount(partita.get(amount_key)) or "0,00"
    year = _value(avviso.get("anno_tributario"))
    comune = _value(partita.get("comune_nome"))
    description = f"Beni in {comune} - {descrizione}"
    return f"{year:<4} {codice:<4} {description[:55]:<55} {amount:>10} euro"


def _partitario_particella_line(particella: dict[str, Any]) -> str:
    return (
        f"{_blank_dash(particella.get('domanda_irrigua')):>4} "
        f"{_blank_dash(particella.get('distretto')):>4} "
        f"{_blank_dash(particella.get('foglio')):>4} "
        f"{_blank_dash(particella.get('particella')):>5} "
        f"{_blank_dash(particella.get('subalterno')):>3} "
        f"{_format_partitario_sup_catastale(particella):>9} "
        f"{_format_partitario_sup_irrigata(particella):>8} "
        f"{_blank_dash(particella.get('coltura'))[:10]:<10} "
        f"{_format_partitario_amount(particella.get('importo_manut')):>8} "
        f"{_format_partitario_amount(particella.get('importo_irrig')):>7} "
        f"{_format_partitario_amount(particella.get('importo_ist')):>7}"
    ).rstrip()


def _blank_dash(value: Any) -> str:
    text = _value(value)
    return "" if text == "-" else text


def _format_partitario_sup_catastale(particella: dict[str, Any]) -> str:
    value = particella.get("sup_catastale_are")
    if value in (None, ""):
        ha = _decimal_or_none(particella.get("sup_catastale_ha"))
        value = (ha * Decimal("100")) if ha is not None else None
    return _format_partitario_integer(value)


def _format_partitario_sup_irrigata(particella: dict[str, Any]) -> str:
    value = particella.get("sup_irrigata_raw")
    if value in (None, ""):
        ha = _decimal_or_none(particella.get("sup_irrigata_ha"))
        value = (ha * Decimal("10000")) if ha is not None else None
    return _format_partitario_integer(value)


def _format_partitario_integer(value: Any) -> str:
    amount = _decimal_or_none(value)
    if amount is None:
        return ""
    integer = int(amount.quantize(Decimal("1"), rounding="ROUND_HALF_UP"))
    return f"{integer:,}".replace(",", ".")


def _format_partitario_amount(value: Any) -> str:
    if value in (None, "", "-"):
        return ""
    return _format_template_number(value)


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    text = str(value).replace("EUR", "").strip()
    try:
        return Decimal(text.replace(".", "").replace(",", ".")) if "," in text else Decimal(text)
    except Exception:
        return None


def _write_simple_docx(payload: dict[str, Any], *, paragraphs: list[str], output_path: Path) -> None:
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _rels_xml())
        archive.writestr("docProps/core.xml", _core_xml(payload))
        archive.writestr("word/document.xml", _document_xml(paragraphs))
        archive.writestr("word/_rels/document.xml.rels", _empty_document_rels_xml())


def _batch_template_field_values(payload: dict[str, Any]) -> dict[str, str]:
    yearly = _batch_yearly_values(payload)
    address = _batch_address_values(payload)
    yearly_references = _yearly_reference_summary(yearly)
    years = _sorted_payload_years(payload, yearly)
    payment_base_amount = _decimal_or_zero(payload.get("saldo_amount") or payload.get("due_amount"))
    notification_amount = _decimal_or_zero(payload.get("notification_amount") or REGISTERED_MAIL_NOTIFICATION_AMOUNT)
    total_amount = payment_base_amount + notification_amount
    return {
        "Avviso_n": _value(payload.get("notice_number")),
        "Denominazione": _value(payload.get("display_name")),
        "INDIRIZZO": address["indirizzo"],
        "CAP": address["cap"],
        "CITTA": address["citta"],
        "PROVINCIA": address["provincia"],
        "DOMICILIO": address["domicilio"],
        "RESIDENZA": address["residenza"],
        "INDIRIZZO_SPEDIZIONE": address["indirizzo_spedizione"],
        "Complessivo": _format_template_number(total_amount),
        "Scadenza": _gaia_bollettino_due_date(payload),
        "CodFiscale": _value(payload.get("codice_fiscale")),
        "Oggetto_Ruoli": _role_subject_label(years),
        "Rif_Ruoli": yearly_references,
        "Rif_2022": yearly.get(2022, {}).get("codice_cnc", ""),
        "Rif_2023": yearly.get(2023, {}).get("codice_cnc", ""),
        "M_648": _format_template_number(yearly.get(2022, {}).get("0648")),
        "M_668": _format_template_number(yearly.get(2022, {}).get("0668")),
        "M_985": _format_template_number(yearly.get(2022, {}).get("0985")),
        "Magg_Applicate": _format_template_number(yearly.get(2022, {}).get("surcharge")),
        "Interessi": _format_template_number(yearly.get(2022, {}).get("interest")),
        "Riscosso": _format_template_number(yearly.get(2022, {}).get("paid")),
        "M_6481": _format_template_number(yearly.get(2023, {}).get("0648")),
        "M_6681": _format_template_number(yearly.get(2023, {}).get("0668")),
        "M_9851": _format_template_number(yearly.get(2023, {}).get("0985")),
        "Magg_Applicate1": _format_template_number(yearly.get(2023, {}).get("surcharge")),
        "Interessi1": _format_template_number(yearly.get(2023, {}).get("interest")),
        "Riscosso1": _format_template_number(yearly.get(2023, {}).get("paid")),
    }


def _replace_template_field_results(document_xml: str, field_values: dict[str, str]) -> str:
    updated_xml = document_xml
    for field_name, value in field_values.items():
        updated_xml = updated_xml.replace(f"«{field_name}»", html.escape(value))
    return updated_xml


def _is_default_batch_reminder_template(template_path: Path) -> bool:
    return template_path.name == DEFAULT_BATCH_REMINDER_TEMPLATE_NAME


def _stable_default_batch_template_xml(
    document_xml: str,
    *,
    payload: dict[str, Any],
    field_values: dict[str, str],
    yearly_rows: list[dict[str, str]],
) -> str:
    try:
        root = ET.fromstring(document_xml)
        fragment_root = ET.fromstring(
            f'<w:fragment xmlns:w="{WORD_NAMESPACE}">'
            f"{_stable_default_first_page_xml(payload, field_values=field_values, yearly_rows=yearly_rows)}"
            "</w:fragment>"
        )
    except ET.ParseError:
        return document_xml

    body = root.find(".//w:body", WORD_NAMESPACES)
    if body is None:
        return document_xml

    children = list(body)
    section = body.find("./w:sectPr", WORD_NAMESPACES)
    legal_start = _find_body_text_index(children, "Comunicazioni per il Contribuente")
    legal_elements = children[legal_start:] if legal_start is not None else []
    if section in legal_elements:
        legal_elements = legal_elements[: legal_elements.index(section)]
    legal_elements = _compact_legal_signature_elements(legal_elements)

    for child in children:
        body.remove(child)

    for element in list(fragment_root):
        body.append(element)
    body.append(ET.fromstring(_page_break_paragraph_xml()))
    for element in legal_elements:
        body.append(element)
    if section is not None:
        body.append(section)

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _find_body_text_index(elements: list[ET.Element], text: str) -> int | None:
    for index, element in enumerate(elements):
        if text in _element_text(element):
            return index
    return None


def _element_text(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.findall(".//w:t", WORD_NAMESPACES))


def _compact_legal_signature_elements(elements: list[ET.Element]) -> list[ET.Element]:
    start_index = _find_body_text_index(elements, "IL DIRETTORE GENERALE")
    end_index = _find_body_text_index(elements, "ex art 3 D. Lgs. n. 39")
    if start_index is None or end_index is None or end_index < start_index:
        return elements
    compact_signature = ET.fromstring(_legal_signature_paragraph_xml())
    return [*elements[:start_index], compact_signature, *elements[end_index + 1 :]]


def _legal_signature_paragraph_xml() -> str:
    lines = [
        "IL DIRETTORE GENERALE",
        "Dott. Maurizio Scanu",
        "Sottoscrizione originale sostituita da firma a stampa",
        "ex art 3 D. Lgs. n. 39 del 12.02.1993 - Giusta Det. DG n. 01/2022",
    ]
    runs = "".join(
        f'<w:r><w:rPr><w:rFonts w:ascii="Garamond" w:hAnsi="Garamond"/>'
        f'<w:sz w:val="12"/><w:szCs w:val="12"/></w:rPr>'
        f'<w:t xml:space="preserve">{html.escape(line)}</w:t></w:r>'
        + ("<w:r><w:br/></w:r>" if index < len(lines) - 1 else "")
        for index, line in enumerate(lines)
    )
    return (
        f'<w:p xmlns:w="{WORD_NAMESPACE}">'
        "<w:pPr>"
        '<w:keepLines/>'
        '<w:jc w:val="right"/>'
        '<w:spacing w:before="0" w:after="0" w:line="180" w:lineRule="auto"/>'
        "</w:pPr>"
        f"{runs}"
        "</w:p>"
    )


def _stable_default_first_page_xml(
    payload: dict[str, Any],
    *,
    field_values: dict[str, str],
    yearly_rows: list[dict[str, str]],
) -> str:
    notice_title = f"AVVISO/SOLLECITO DI PAGAMENTO N. {field_values['Avviso_n']} - {field_values['Oggetto_Ruoli']}"
    amount = f"€. {field_values['Complessivo']}"
    recipient_lines = [
        field_values["Denominazione"],
        field_values["INDIRIZZO"],
        " ".join(
            value
            for value in (field_values["CAP"], field_values["CITTA"], field_values["PROVINCIA"])
            if value and value != "-"
        ),
    ]
    recipient_lines = [line for line in recipient_lines if line and line != "-"]

    return "".join(
        [
            _docx_paragraph(notice_title, bold=True, size=22, align="center", after=160),
            _stable_address_table_xml(recipient_lines),
            _docx_paragraph("", after=120),
            _stable_creditor_table_xml(),
            _docx_paragraph("", after=120),
            _stable_payment_summary_table_xml(amount, field_values),
            _docx_paragraph("COME PAGARE", bold=True, size=20, align="center", before=120, after=80),
            _docx_paragraph(
                "Il pagamento potrà essere effettuato mediante bonifico bancario al Conto Corrente:",
                size=18,
                after=60,
            ),
            _docx_paragraph(
                "Intestato a: CONSORZIO DI BONIFICA DELL’ORISTANESE - RISCOSSIONE QUOTE ASSOCIATIVE",
                size=18,
                after=40,
            ),
            _docx_paragraph("Iban: IT15L0760117400001007214826 -", size=18, after=40),
            _docx_paragraph(
                f"Causale: {field_values['CodFiscale']}; {field_values['Avviso_n']}",
                size=18,
                after=140,
            ),
            _stable_yearly_summary_table_xml(field_values, yearly_rows),
            _docx_paragraph(
                "Per maggiori chiarimenti contattare l’Ente o recarsi presso la sede nei seguenti giorni: "
                "Lunedi e giovedì 11.00 - 13.00, - tel. 0783 3150212",
                size=16,
                before=130,
                after=80,
            ),
            _docx_paragraph(
                "INFORMATIVA SUL TRATTAMENTO DEI DATI PERSONALI: lo scrivente Consorzio, titolare del trattamento "
                "dei dati personali, li utilizza esclusivamente per le finalità istituzionali previste dalla legge, "
                "anche quando comunicate a terzi. Il trattamento dei Suoi dati avviene anche mediante l’utilizzo di "
                "strumenti elettronici, con logistiche strettamente correlate alle predette finalità nel rispetto del D.LGS n. 196/2003.",
                size=15,
                after=80,
            ),
            _docx_paragraph("Rev.2024/11", size=14, after=0),
        ]
    )


def _stable_address_table_xml(recipient_lines: list[str]) -> str:
    recipient = "<w:br/>".join(recipient_lines)
    return _docx_table(
        [
            [
                _docx_cell("", width=5100),
                _docx_cell(recipient, width=5100, bold=True, size=18),
            ]
        ],
        width=10200,
        borders=False,
    )


def _stable_creditor_table_xml() -> str:
    creditor = (
        "Ente creditore <w:br/>"
        "Codice Fiscale: 90022600952<w:br/>"
        "Consorzio di Bonifica dell’Oristanese<w:br/>"
        "Sede: Via Cagliari 170 - 09170 Oristano<w:br/>"
        "Telefono 0783 3150<w:br/>"
        "Sito www.bonificaoristanese.it<w:br/>"
        "E-mail catasto@bonificaoristanese.it<w:br/>"
        "PEC protocollo.cbo@pec.it"
    )
    return _docx_table(
        [[_docx_cell(creditor, width=4700, size=17), _docx_cell("", width=5500)]],
        width=10200,
        borders=False,
    )


def _stable_payment_summary_table_xml(amount: str, field_values: dict[str, str]) -> str:
    return _docx_table(
        [
            [
                _docx_cell("QUANTO E QUANDO PAGARE", width=5100, bold=True, size=18, shading="D9EAD3"),
                _docx_cell(
                    f"Destinatario Avviso Codice Fiscale {field_values['CodFiscale']}",
                    width=5100,
                    bold=True,
                    size=18,
                    shading="D9EAD3",
                ),
            ],
            [
                _docx_cell(
                    f"{amount}<w:br/>entro il {html.escape(field_values['Scadenza'])} - UNICA SOLUZIONE<w:br/><w:br/>"
                    "Si può richiedere, direttamente presso gli uffici dell’Ente, una diversa dilazione del pagamento.",
                    width=5100,
                    bold=True,
                    size=18,
                ),
                _docx_cell(field_values["Denominazione"], width=5100, bold=True, size=18),
            ],
        ],
        width=10200,
        borders=False,
    )


def _stable_yearly_summary_table_xml(field_values: dict[str, str], yearly_rows: list[dict[str, str]]) -> str:
    title = f"RIEPILOGO IMPORTI DOVUTI (rif avvisi di pagamento {field_values['Rif_Ruoli']})"
    rows = [
        [_docx_cell(title, width=10200, bold=True, size=16, shading="F2F2F2", grid_span=9)],
        [
            _docx_cell("", width=1150, bold=True, size=15, shading="F2F2F2"),
            _docx_cell("Numero<w:br/>avviso", width=1550, bold=True, size=14, shading="F2F2F2"),
            _docx_cell("0648<w:br/>Contributo opere irrigue (Euro)", width=1200, bold=True, size=14, shading="F2F2F2"),
            _docx_cell("0668<w:br/>Contributo utenza (Euro)", width=1200, bold=True, size=14, shading="F2F2F2"),
            _docx_cell("0985<w:br/>Quota istituzionale (Euro)", width=1200, bold=True, size=14, shading="F2F2F2"),
            _docx_cell("M001<w:br/>Maggiorazioni (Euro)", width=900, bold=True, size=14, shading="F2F2F2"),
            _docx_cell("I001<w:br/>Interessi (Euro)", width=900, bold=True, size=14, shading="F2F2F2"),
            _docx_cell("Somme Versate (Euro)", width=1050, bold=True, size=14, shading="F2F2F2"),
            _docx_cell("Altre spese", width=1050, bold=True, size=14, shading="F2F2F2"),
        ],
    ]
    for row in yearly_rows:
        rows.append(
            [
                _docx_cell(row["Anno_Ruolo"], width=1150, bold=True, size=15),
                _docx_cell(row["Rif_Ruolo"], width=1550, size=14),
                _docx_cell(row["M_648"], width=1200, size=15, align="right"),
                _docx_cell(row["M_668"], width=1200, size=15, align="right"),
                _docx_cell(row["M_985"], width=1200, size=15, align="right"),
                _docx_cell(row["Magg_Applicate"], width=900, size=15, align="right"),
                _docx_cell(row["Interessi"], width=900, size=15, align="right"),
                _docx_cell(row["Riscosso"], width=1050, size=15, align="right"),
                _docx_cell("0,00", width=1050, size=15, align="right"),
            ]
        )
    rows.append(
        [
            _docx_cell("SN01<w:br/>Spese Notifica (Euro)", width=9150, bold=True, size=14, grid_span=8),
            _docx_cell(_format_template_number(REGISTERED_MAIL_NOTIFICATION_AMOUNT), width=1050, size=15, align="right"),
        ]
    )
    return _docx_table(rows, width=10200, borders=True)


def _docx_table(rows: list[list[str]], *, width: int, borders: bool) -> str:
    borders_xml = ""
    if borders:
        borders_xml = (
            "<w:tblBorders>"
            '<w:top w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
            '<w:left w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
            '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
            '<w:right w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
            '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
            '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
            "</w:tblBorders>"
        )
    body = "".join(f"<w:tr>{''.join(row)}</w:tr>" for row in rows)
    return (
        "<w:tbl>"
        "<w:tblPr>"
        f'<w:tblW w:w="{width}" w:type="dxa"/>'
        '<w:tblLayout w:type="fixed"/>'
        f"{borders_xml}"
        "</w:tblPr>"
        f"{body}"
        "</w:tbl>"
    )


def _docx_cell(
    content: str,
    *,
    width: int,
    size: int | None = None,
    bold: bool = False,
    align: str = "left",
    shading: str | None = None,
    grid_span: int | None = None,
) -> str:
    span_xml = f'<w:gridSpan w:val="{grid_span}"/>' if grid_span else ""
    shading_xml = f'<w:shd w:fill="{shading}" w:val="clear"/>' if shading else ""
    return (
        "<w:tc>"
        "<w:tcPr>"
        f'<w:tcW w:w="{width}" w:type="dxa"/>'
        f"{span_xml}{shading_xml}"
        '<w:tcMar><w:top w:w="70" w:type="dxa"/><w:left w:w="90" w:type="dxa"/>'
        '<w:bottom w:w="70" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tcMar>'
        "</w:tcPr>"
        f"{_docx_paragraph(content, size=size, bold=bold, align=align, after=0)}"
        "</w:tc>"
    )


def _docx_paragraph(
    content: str,
    *,
    size: int | None = None,
    bold: bool = False,
    align: str = "left",
    before: int = 0,
    after: int = 0,
) -> str:
    size_xml = f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>' if size else ""
    bold_xml = "<w:b/><w:bCs/>" if bold else ""
    run_properties = f"<w:rPr>{bold_xml}{size_xml}</w:rPr>"
    runs: list[str] = []
    parts = str(content).split("<w:br/>")
    for index, part in enumerate(parts):
        if part:
            runs.append(f'<w:r>{run_properties}<w:t xml:space="preserve">{html.escape(part)}</w:t></w:r>')
        elif not parts or len(parts) == 1:
            runs.append(f"<w:r>{run_properties}</w:r>")
        if index < len(parts) - 1:
            runs.append("<w:r><w:br/></w:r>")
    return (
        "<w:p>"
        "<w:pPr>"
        f'<w:jc w:val="{align}"/>'
        f'<w:spacing w:before="{before}" w:after="{after}"/>'
        "</w:pPr>"
        f"{''.join(runs)}"
        "</w:p>"
    )


def _page_break_paragraph_xml() -> str:
    return f'<w:p xmlns:w="{WORD_NAMESPACE}"><w:r><w:br w:type="page"/></w:r></w:p>'



def _append_partitario_xml(document_xml: str, partitario_xml: str) -> str:
    try:
        root = ET.fromstring(document_xml)
        fragment_root = ET.fromstring(
            f'<w:fragment xmlns:w="{WORD_NAMESPACE}">{partitario_xml}</w:fragment>'
        )
    except ET.ParseError:
        section_index = document_xml.rfind("<w:sectPr")
        if section_index >= 0:
            return f"{document_xml[:section_index]}{partitario_xml}{document_xml[section_index:]}"
        return document_xml.replace("</w:body>", f"{partitario_xml}</w:body>")

    body = root.find(".//w:body", WORD_NAMESPACES)
    if body is None:
        return document_xml

    section = body.find("./w:sectPr", WORD_NAMESPACES)
    insert_at = list(body).index(section) if section is not None else len(body)
    for offset, paragraph in enumerate(list(fragment_root)):
        body.insert(insert_at + offset, paragraph)

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _paragraphs_xml(paragraphs: list[str]) -> str:
    return "".join(f"<w:p><w:r><w:t>{html.escape(text)}</w:t></w:r></w:p>" for text in paragraphs)


def _partitario_lines_xml(lines: list[str]) -> str:
    return "".join(
        "<w:p>"
        '<w:pPr><w:jc w:val="left"/><w:spacing w:before="0" w:after="0" w:line="220" w:lineRule="auto"/></w:pPr>'
        "<w:r>"
        '<w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New"/>'
        '<w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr>'
        f'<w:t xml:space="preserve">{html.escape(line)}</w:t>'
        "</w:r>"
        "</w:p>"
        for line in lines
    )


def _batch_yearly_row_values(payload: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year, values in sorted(_batch_yearly_values(payload).items()):
        rows.append(
            {
                "Anno_Ruolo": f"Ruolo {year}",
                "Rif_Ruolo": _display_notice_numbers(values.get("codice_cnc")),
                "M_648": _format_template_number(values.get("0648")),
                "M_668": _format_template_number(values.get("0668")),
                "M_985": _format_template_number(values.get("0985")),
                "Magg_Applicate": _format_template_number(values.get("surcharge")),
                "Interessi": _format_template_number(values.get("interest")),
                "Riscosso": _format_template_number(values.get("paid")),
            }
        )
    if rows:
        return rows
    return [
        {
            "Anno_Ruolo": "Ruolo -",
            "Rif_Ruolo": "",
            "M_648": _format_template_number(0),
            "M_668": _format_template_number(0),
            "M_985": _format_template_number(0),
            "Magg_Applicate": _format_template_number(0),
            "Interessi": _format_template_number(0),
            "Riscosso": _format_template_number(0),
        }
    ]


def _display_notice_numbers(value: Any) -> str:
    text = _value(value)
    if text == "-":
        return text
    return ", ".join(_display_notice_number(part) for part in text.split(", "))


def _display_notice_number(value: Any) -> str:
    text = _value(value)
    return text[3:] if text.startswith("01.") else text


def _expand_yearly_summary_rows(document_xml: str, yearly_rows: list[dict[str, str]]) -> str:
    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError:
        return document_xml

    target_table = None
    target_index = None
    template_row = None
    row_tag = f"{{{WORD_NAMESPACE}}}tr"
    for table in root.findall(".//w:tbl", WORD_NAMESPACES):
        rows = list(table.findall(f"./{row_tag}"))
        for index, row in enumerate(rows):
            if _xml_element_contains_placeholder(row, "Anno_Ruolo"):
                target_table = table
                target_index = index
                template_row = row
                break
        if template_row is not None:
            break

    if target_table is None or target_index is None or template_row is None:
        return document_xml

    target_table.remove(template_row)
    for offset, row_values in enumerate(yearly_rows):
        row_clone = copy.deepcopy(template_row)
        row_xml = ET.tostring(row_clone, encoding="unicode")
        row_xml = _replace_template_field_results(row_xml, row_values)
        target_table.insert(target_index + offset, ET.fromstring(row_xml))

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _xml_element_contains_placeholder(element: ET.Element, field_name: str) -> bool:
    placeholder = f"«{field_name}»"
    for node in element.iter():
        text = getattr(node, "text", None)
        if text and placeholder in text:
            return True
    return False


def _batch_yearly_values(payload: dict[str, Any]) -> dict[int, dict[str, Decimal | str]]:
    yearly: dict[int, dict[str, Decimal | str]] = {}
    for avviso in payload.get("avvisi", []):
        year = _int_value(avviso.get("anno_tributario"))
        if year is None:
            continue
        values = yearly.setdefault(
            year,
            {
                "codice_cnc": "",
                "0648": Decimal("0.00"),
                "0668": Decimal("0.00"),
                "0985": Decimal("0.00"),
                "paid": Decimal("0.00"),
                "surcharge": Decimal("0.00"),
                "interest": Decimal("0.00"),
            },
        )
        codice_cnc = _value(avviso.get("codice_cnc"))
        values["codice_cnc"] = codice_cnc if not values["codice_cnc"] else f"{values['codice_cnc']}, {codice_cnc}"
        values["0648"] = _decimal_or_zero(values["0648"]) + _decimal_or_zero(avviso.get("importo_totale_0648"))
        values["0668"] = _decimal_or_zero(values["0668"]) + _decimal_or_zero(avviso.get("importo_totale_0668"))
        values["0985"] = _decimal_or_zero(values["0985"]) + _decimal_or_zero(avviso.get("importo_totale_0985"))
        values["paid"] = _decimal_or_zero(values["paid"]) + _decimal_or_zero(avviso.get("paid_amount"))
        values["surcharge"] = _decimal_or_zero(values["surcharge"]) + _decimal_or_zero(avviso.get("surcharge_amount"))
        values["interest"] = _decimal_or_zero(values["interest"]) + _decimal_or_zero(avviso.get("interest_amount"))
    return yearly


def _batch_address_values(payload: dict[str, Any]) -> dict[str, str]:
    avvisi = payload.get("avvisi", [])
    first_avviso = avvisi[0] if avvisi else {}
    residence_raw = _value(first_avviso.get("residenza_raw"))
    domicile_raw = _value(first_avviso.get("domicilio_raw"))
    residence = _split_address_components(residence_raw)
    domicile = _split_address_components(domicile_raw)
    raw_address = residence["address"] or domicile["address"] or residence_raw or domicile_raw
    cap = residence["cap"] or domicile["cap"]
    city = residence["city"] or domicile["city"] or _value(payload.get("comune"))
    province = residence["province"] or domicile["province"]
    shipping_address = _join_address_parts(raw_address, cap=cap, city=city, province=province)
    return {
        "indirizzo": raw_address,
        "cap": cap,
        "citta": city if city and city != "-" else _value(payload.get("comune")),
        "provincia": province,
        "domicilio": domicile_raw,
        "residenza": residence_raw,
        "indirizzo_spedizione": shipping_address,
    }


def _split_address_components(raw_value: str) -> dict[str, str]:
    normalized = " ".join(raw_value.split())
    cap_match = re.search(r"\b(\d{5})\b", normalized)
    province_match = re.search(r"\(([A-Z]{2})\)|\b([A-Z]{2})\b\s*$", normalized)
    province = (province_match.group(1) or province_match.group(2)) if province_match else ""
    if not cap_match:
        return {"address": normalized, "cap": "", "city": "", "province": province}
    before_cap = normalized[: cap_match.start()].strip(" ,-")
    after_cap = normalized[cap_match.end() :].strip(" ,-")
    city = re.sub(r"\([A-Z]{2}\)|\b[A-Z]{2}\b\s*$", "", after_cap).strip(" ,-")
    return {"address": before_cap, "cap": cap_match.group(1), "city": city, "province": province}


def _join_address_parts(address: str, *, cap: str, city: str, province: str) -> str:
    city_line = " ".join(value for value in (cap, city, province) if value and value != "-")
    return " ".join(value for value in (address, city_line) if value and value != "-")


def _sorted_payload_years(
    payload: dict[str, Any],
    yearly: dict[int, dict[str, Decimal | str]],
) -> list[int]:
    years = {
        parsed_year
        for year in payload.get("years", [])
        for parsed_year in [_int_value(year)]
        if parsed_year is not None
    }
    if years:
        return sorted(years)
    return sorted(yearly)


def _role_subject_label(years: list[int]) -> str:
    if not years:
        return "Tributi Consortili"
    if len(years) == 1:
        return f"Tributi Consortili anno {years[0]}"
    return f"Tributi Consortili anni {_join_human_list(str(year) for year in years)}"


def _yearly_reference_summary(yearly: dict[int, dict[str, Decimal | str]]) -> str:
    references = []
    for year, values in sorted(yearly.items()):
        codice_cnc = _value(values.get("codice_cnc"))
        if codice_cnc == "-":
            continue
        references.append(f"{year}: {codice_cnc}")
    return "; ".join(references) or "-"


def _join_human_list(values: Iterable[str | int]) -> str:
    items = [str(value) for value in values if str(value)]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} e {items[1]}"
    return f"{', '.join(items[:-1])} e {items[-1]}"


def _format_template_number(value: Any) -> str:
    amount = _decimal_or_zero(value).quantize(Decimal("0.01"))
    return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _decimal_or_zero(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    text = str(value).replace("EUR", "").strip()
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


def _int_value(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def convert_docx_to_pdf(
    docx_path: Path,
    *,
    output_dir: Path,
    libreoffice_binary: str | None = None,
) -> Path:
    binary = libreoffice_binary or shutil.which("libreoffice") or shutil.which("soffice")
    if not binary:
        raise RuntimeError("LibreOffice non trovato: impossibile convertire il sollecito in PDF")
    completed = subprocess.run(
        [binary, "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(docx_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if completed.returncode != 0:
        error_output = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"Conversione PDF fallita: {error_output or completed.returncode}")
    pdf_path = output_dir / f"{docx_path.stem}.pdf"
    if not pdf_path.exists():
        raise RuntimeError("Conversione PDF completata senza file di output")
    return pdf_path


def _format_currency(value: Any) -> str | None:
    if value is None:
        return None
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    return f"{amount} EUR"


def _value(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value)


def _document_xml(paragraphs: list[str]) -> str:
    body = "".join(
        f"<w:p><w:r><w:t>{html.escape(text)}</w:t></w:r></w:p>"
        for text in paragraphs
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}<w:sectPr><w:pgSz w:w=\"11906\" w:h=\"16838\"/><w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\"/></w:sectPr></w:body>"
        "</w:document>"
    )


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        "</Types>"
    )


def _rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        "</Relationships>"
    )


def _empty_document_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    )


def _core_xml(payload: dict[str, Any]) -> str:
    created_at = html.escape(str(payload.get("generated_at") or datetime.now(timezone.utc).isoformat()))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<dc:title>Sollecito pagamento tributi</dc:title>"
        "<dc:creator>GAIA Ruolo</dc:creator>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{created_at}</dcterms:created>'
        "</cp:coreProperties>"
    )
