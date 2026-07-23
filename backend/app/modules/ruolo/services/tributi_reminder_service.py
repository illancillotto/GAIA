from __future__ import annotations

import copy
import html
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MEDIA_TYPE = "application/pdf"
WORD_DOCUMENT_PATH = "word/document.xml"
WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WORD_NAMESPACES = {"w": WORD_NAMESPACE}
DEFAULT_BATCH_REMINDER_TEMPLATE_NAME = "Avviso_Sollecito_Template.docx"
GAIA_PROPOSAL_TEMPLATE_KEY = "__gaia_proposal__"
PARTITARIO_LINE_WIDTH = 80
_HTML_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


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
        html_path = working_dir / f"{output_path.stem}.html"
        local_pdf_path = working_dir / output_path.name
        html_path.write_text(_gaia_proposal_html(payload), encoding="utf-8")
        subprocess.run(
            [
                chromium_binary,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--no-pdf-header-footer",
                f"--print-to-pdf={local_pdf_path}",
                html_path.as_uri(),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if not local_pdf_path.exists():
            raise RuntimeError("Conversione PDF template GAIA non riuscita")
        shutil.copyfile(local_pdf_path, output_path)


def _find_chromium_binary() -> str | None:
    for candidate in ("chromium", "chromium-browser", "google-chrome"):
        binary = shutil.which(candidate)
        if binary:
            return binary
    snap_chromium = Path("/snap/bin/chromium")
    return str(snap_chromium) if snap_chromium.exists() else None


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


def _gaia_proposal_html(payload: dict[str, Any]) -> str:
    field_values = _batch_template_field_values(payload)
    yearly_rows = _batch_yearly_row_values(payload)
    partitario = "\n".join(_batch_partitario_lines(payload))
    summary_rows = "".join(
        "<tr>"
        f"<td>{html.escape(row['Anno_Ruolo'])}</td>"
        f"<td>{html.escape(row['M_648'])}</td>"
        f"<td>{html.escape(row['M_668'])}</td>"
        f"<td>{html.escape(row['M_985'])}</td>"
        f"<td>{html.escape(row['Magg_Applicate'])}</td>"
        "<td>0,00</td>"
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
@page {{ size: A4; margin: 12mm 18mm 12mm 13mm; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: #17231e; font-family: Arial, Helvetica, sans-serif; font-size: 10.2pt; line-height: 1.28; }}
.page {{ min-height: 273mm; break-after: page; page-break-after: always; position: relative; }}
.page:last-child {{ break-after: auto; page-break-after: auto; }}
.header {{ display: grid; grid-template-columns: 39mm 1fr 36mm; align-items: center; gap: 5mm; padding-bottom: 5mm; border-bottom: 1.6pt solid #1f5d45; }}
.brand {{ display: grid; place-content: center; height: 23mm; border-radius: 4mm; border: 1pt solid #d9e3dd; font-weight: 900; text-align: center; }}
.brand.cbo {{ color: #213d66; font-size: 23pt; letter-spacing: -1.5pt; }}
.brand.pagopa {{ justify-self: end; width: 31mm; color: #0b6eb4; font-size: 15pt; }}
.head-title {{ text-align: center; }}
.head-title h1 {{ margin: 0; font-family: Georgia, serif; font-size: 20pt; line-height: 1.05; }}
.head-title p {{ margin: 1.5mm 0 0; font-weight: 700; font-size: 9.5pt; }}
.notice-title {{ margin: 6mm 0 5mm; padding: 3.2mm 4mm; background: linear-gradient(90deg, #1f5d45, #2c7558); color: white; border-radius: 2.5mm; font-weight: 800; text-align: center; font-size: 12pt; }}
.grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; }}
.card {{ border: 1pt solid #cfd8d2; border-radius: 3mm; overflow: hidden; background: #fff; }}
.card h2 {{ margin: 0; padding: 2.4mm 3mm; background: #e7f0ea; color: #1f5d45; font-size: 9.5pt; text-transform: uppercase; letter-spacing: .4pt; }}
.body {{ padding: 3mm; }}
.kv {{ display: grid; grid-template-columns: 28mm 1fr; gap: 1.2mm 2mm; }}
.kv b {{ color: #5b6b63; font-size: 8.4pt; }}
.recipient {{ font-weight: 800; font-size: 10.5pt; }}
.pay-band {{ margin-top: 5mm; display: grid; grid-template-columns: 56mm 1fr; gap: 4mm; align-items: stretch; }}
.amount {{ background: #f8f5ec; border: 1.3pt solid #b18b3d; border-radius: 3mm; padding: 4mm; }}
.amount .label {{ text-transform: uppercase; color: #745821; font-size: 8pt; font-weight: 800; letter-spacing: .4pt; }}
.amount .euro {{ font-family: Georgia, serif; font-size: 25pt; color: #1f5d45; font-weight: 900; margin: 1.5mm 0; }}
.instructions {{ border-left: 3pt solid #1f5d45; padding-left: 4mm; }}
.instructions h2 {{ margin: 0 0 2mm; color: #1f5d45; font-size: 12pt; }}
.instructions p {{ margin: 1mm 0; }}
.summary {{ margin-top: 5mm; width: 100%; border-collapse: collapse; font-size: 7.8pt; }}
.summary th {{ background: #eef3f0; color: #1f5d45; border: 1px solid #cfd8d2; padding: 1.35mm; text-align: left; }}
.summary td {{ border: 1px solid #cfd8d2; padding: 1.3mm; text-align: right; }}
.summary td:first-child {{ text-align: left; font-weight: 800; }}
.note {{ margin-top: 4mm; padding-top: 3mm; border-top: 1px solid #cfd8d2; font-size: 8.3pt; color: #2e3934; }}
.rev {{ position: absolute; bottom: 0; left: 0; font-size: 7.5pt; color: #5b6b63; }}
.legal h2 {{ text-align: center; margin: 0 0 2.4mm; font-size: 10.2pt; font-weight: 800; }}
.legal-copy {{ font-size: 7.35pt; line-height: 1.0; padding-bottom: 18mm; width: 100%; }}
.legal-copy p {{ margin: 0 0 .3mm; text-align: justify; }}
.legal-copy ul {{ margin: -.35mm 0 .42mm 8mm; padding: 0; }}
.legal-copy li {{ margin: 0; padding: 0; }}
.warning em {{ font-style: italic; text-decoration: underline; }}
.signature {{ position: absolute; right: 0; bottom: 4mm; width: 78mm; text-align: center; font-family: Georgia, 'Times New Roman', serif; color: #1a211d; }}
.signature .title {{ font-size: 7.8pt; font-weight: 700; letter-spacing: .25pt; }}
.signature .name {{ font-size: 8.4pt; font-weight: 600; margin-top: .3mm; }}
.signature .rule {{ width: 38mm; border-top: .7pt solid #87958e; margin: 1mm auto .75mm; }}
.signature .note {{ font-size: 5.9pt; line-height: 1.05; color: #39443f; border: 0; margin: 0; padding: 0; }}
.partitario-title {{ margin: 0 0 3mm; color: #1f5d45; font: 800 11pt Arial, sans-serif; border-bottom: 1.2pt solid #1f5d45; padding-bottom: 2mm; }}
.partitario {{ font-family: "Courier New", monospace; font-size: 7.8pt; line-height: 1.08; white-space: pre; color: #111; }}
</style>
</head>
<body>
<section class="page">
  <div class="header">
    <div class="brand cbo">CBO</div>
    <div class="head-title"><h1>Consorzio di Bonifica<br>dell'Oristanese</h1><p>DPGRS N. 239 del 04.12.96</p></div>
    <div class="brand pagopa">pagoPA</div>
  </div>
  <div class="notice-title">AVVISO/SOLLECITO DI PAGAMENTO N. {html.escape(field_values['Avviso_n'])} - {html.escape(field_values['Oggetto_Ruoli'])}</div>
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
    <div class="amount"><div class="label">Quanto e quando pagare</div><div class="euro">€. {html.escape(field_values['Complessivo'])}</div><div><b>entro il 21.12.2024</b><br>UNICA SOLUZIONE</div></div>
    <div class="instructions"><h2>Come pagare</h2><p>Il pagamento potrà essere effettuato mediante bonifico bancario al Conto Corrente:</p><p><b>Intestato a:</b> CONSORZIO DI BONIFICA DELL'ORISTANESE - RISCOSSIONE QUOTE ASSOCIATIVE</p><p><b>IBAN:</b> IT15L0760117400001007214826</p><p><b>Causale:</b> {html.escape(field_values['CodFiscale'])}; {html.escape(field_values['Avviso_n'])}</p></div>
  </div>
  <table class="summary"><thead><tr><th>Ruolo</th><th>0648 Opere irrigue</th><th>0668 Utenza</th><th>0985 Quota istituzionale</th><th>Magg.</th><th>Interessi</th><th>Somme versate</th><th>Altre spese</th></tr></thead><tbody>{summary_rows}<tr><td>SN01 Spese Notifica</td><td colspan="6"></td><td>11,55</td></tr></tbody></table>
  <div class="note">Si può richiedere, direttamente presso gli uffici dell'Ente, una diversa dilazione del pagamento. Per maggiori chiarimenti contattare l'Ente nei giorni Lunedi e giovedì 11.00 - 13.00, tel. 0783 3150212.</div>
  <div class="rev">Rev.2024/11</div>
</section>
<section class="page legal">
  <h2>Comunicazioni per il Contribuente</h2>
  <div class="legal-copy">{_gaia_legal_html(field_values)}</div>
  <div class="signature"><div class="title">IL DIRETTORE GENERALE</div><div class="name">Dott. Maurizio Scanu</div><div class="rule"></div><div class="note">Sottoscrizione originale sostituita da firma a stampa<br>ex art. 3 D. Lgs. n. 39 del 12.02.1993 - Giusta Det. DG n. 01/2022</div></div>
</section>
<section class="page">
  <div class="partitario-title">Dettaglio partitario allegato</div>
  <div class="partitario">{html.escape(partitario)}</div>
</section>
</body>
</html>"""


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
    return lines


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
    return {
        "Avviso_n": _value(payload.get("notice_number")),
        "Denominazione": _value(payload.get("display_name")),
        "INDIRIZZO": address["indirizzo"],
        "CAP": address["cap"],
        "CITTA": address["citta"],
        "PROVINCIA": address["provincia"],
        "Complessivo": _format_template_number(payload.get("saldo_amount") or payload.get("due_amount")),
        "CodFiscale": _value(payload.get("codice_fiscale")),
        "Oggetto_Ruoli": _role_subject_label(years),
        "Rif_Ruoli": yearly_references,
        "Rif_2022": yearly.get(2022, {}).get("codice_cnc", ""),
        "Rif_2023": yearly.get(2023, {}).get("codice_cnc", ""),
        "M_648": _format_template_number(yearly.get(2022, {}).get("0648")),
        "M_668": _format_template_number(yearly.get(2022, {}).get("0668")),
        "M_985": _format_template_number(yearly.get(2022, {}).get("0985")),
        "Magg_Applicate": _format_template_number(0),
        "Riscosso": _format_template_number(yearly.get(2022, {}).get("paid")),
        "M_6481": _format_template_number(yearly.get(2023, {}).get("0648")),
        "M_6681": _format_template_number(yearly.get(2023, {}).get("0668")),
        "M_9851": _format_template_number(yearly.get(2023, {}).get("0985")),
        "Magg_Applicate1": _format_template_number(0),
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
                    f"{amount}<w:br/>entro il 21.12.2024 - UNICA SOLUZIONE<w:br/><w:br/>"
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
        [_docx_cell(title, width=10200, bold=True, size=16, shading="F2F2F2", grid_span=8)],
        [
            _docx_cell("", width=1400, bold=True, size=15, shading="F2F2F2"),
            _docx_cell("0648<w:br/>Contributo opere irrigue (Euro)", width=1350, bold=True, size=14, shading="F2F2F2"),
            _docx_cell("0668<w:br/>Contributo utenza (Euro)", width=1350, bold=True, size=14, shading="F2F2F2"),
            _docx_cell("0985<w:br/>Quota istituzionale (Euro)", width=1350, bold=True, size=14, shading="F2F2F2"),
            _docx_cell("M001<w:br/>Maggiorazioni (Euro)", width=1200, bold=True, size=14, shading="F2F2F2"),
            _docx_cell("I001<w:br/>Interessi (Euro)", width=1100, bold=True, size=14, shading="F2F2F2"),
            _docx_cell("Somme Versate (Euro)", width=1200, bold=True, size=14, shading="F2F2F2"),
            _docx_cell("Altre spese", width=1250, bold=True, size=14, shading="F2F2F2"),
        ],
    ]
    for row in yearly_rows:
        rows.append(
            [
                _docx_cell(row["Anno_Ruolo"], width=1400, bold=True, size=15),
                _docx_cell(row["M_648"], width=1350, size=15, align="right"),
                _docx_cell(row["M_668"], width=1350, size=15, align="right"),
                _docx_cell(row["M_985"], width=1350, size=15, align="right"),
                _docx_cell(row["Magg_Applicate"], width=1200, size=15, align="right"),
                _docx_cell("0,00", width=1100, size=15, align="right"),
                _docx_cell(row["Riscosso"], width=1200, size=15, align="right"),
                _docx_cell("0,00", width=1250, size=15, align="right"),
            ]
        )
    rows.append(
        [
            _docx_cell("SN01<w:br/>Spese Notifica (Euro)", width=8950, bold=True, size=14, grid_span=7),
            _docx_cell("11,55", width=1250, size=15, align="right"),
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
                "Rif_Ruolo": _value(values.get("codice_cnc")),
                "M_648": _format_template_number(values.get("0648")),
                "M_668": _format_template_number(values.get("0668")),
                "M_985": _format_template_number(values.get("0985")),
                "Magg_Applicate": _format_template_number(0),
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
            "Riscosso": _format_template_number(0),
        }
    ]


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
            },
        )
        codice_cnc = _value(avviso.get("codice_cnc"))
        values["codice_cnc"] = codice_cnc if not values["codice_cnc"] else f"{values['codice_cnc']}, {codice_cnc}"
        values["0648"] = _decimal_or_zero(values["0648"]) + _decimal_or_zero(avviso.get("importo_totale_0648"))
        values["0668"] = _decimal_or_zero(values["0668"]) + _decimal_or_zero(avviso.get("importo_totale_0668"))
        values["0985"] = _decimal_or_zero(values["0985"]) + _decimal_or_zero(avviso.get("importo_totale_0985"))
        values["paid"] = _decimal_or_zero(values["paid"]) + _decimal_or_zero(avviso.get("paid_amount"))
    return yearly


def _batch_address_values(payload: dict[str, Any]) -> dict[str, str]:
    avvisi = payload.get("avvisi", [])
    first_avviso = avvisi[0] if avvisi else {}
    raw_address = _value(first_avviso.get("domicilio_raw") or first_avviso.get("residenza_raw"))
    raw_city = _value(first_avviso.get("residenza_raw") or payload.get("comune"))
    cap_match = re.search(r"\b(\d{5})\b", f"{raw_address} {raw_city}")
    provincia_match = re.search(r"\(([A-Z]{2})\)|\b([A-Z]{2})\b\s*$", raw_city)
    city = re.sub(r"\b\d{5}\b", "", raw_city)
    city = re.sub(r"\([A-Z]{2}\)|\b[A-Z]{2}\b\s*$", "", city).strip(" ,-")
    return {
        "indirizzo": raw_address,
        "cap": cap_match.group(1) if cap_match else "",
        "citta": city if city and city != "-" else _value(payload.get("comune")),
        "provincia": (provincia_match.group(1) or provincia_match.group(2)) if provincia_match else "",
    }


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
