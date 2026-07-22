from __future__ import annotations

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
from typing import Any


DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MEDIA_TYPE = "application/pdf"
WORD_DOCUMENT_PATH = "word/document.xml"


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
    template_path = Path(str(payload.get("template_path") or ""))
    if template_path.is_file():
        _generate_batch_reminder_docx_from_template(payload, template_path=template_path, output_path=output_path)
        return

    paragraphs = _batch_intro_paragraphs(payload)
    paragraphs.extend(_batch_partitario_paragraphs(payload))
    _write_simple_docx(payload, paragraphs=paragraphs, output_path=output_path)


def _generate_batch_reminder_docx_from_template(
    payload: dict[str, Any],
    *,
    template_path: Path,
    output_path: Path,
) -> None:
    field_values = _batch_template_field_values(payload)
    partitario_xml = _paragraphs_xml(_batch_partitario_paragraphs(payload))
    with zipfile.ZipFile(template_path, "r") as source, zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == WORD_DOCUMENT_PATH:
                document_xml = data.decode("utf-8")
                document_xml = _replace_template_field_results(document_xml, field_values)
                document_xml = _append_partitario_xml(document_xml, partitario_xml)
                data = document_xml.encode("utf-8")
            target.writestr(item, data)


def _batch_intro_paragraphs(payload: dict[str, Any]) -> list[str]:
    paragraphs = [
        "Avviso di sollecito pagamento",
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
    paragraphs = ["", "Partitario"]
    for avviso in payload.get("avvisi", []):
        paragraphs.extend(
            [
                "",
                f"Avviso CNC {avviso.get('codice_cnc')} - anno {avviso.get('anno_tributario')}",
                f"Dovuto {_value(avviso.get('importo_totale_euro'))} - pagato {_value(avviso.get('paid_amount'))} - saldo {_value(avviso.get('saldo_amount'))}",
            ]
        )
        for partita in avviso.get("partite", []):
            paragraphs.extend(
                [
                    f"Partita {partita.get('codice_partita')} beni in comune di {partita.get('comune_nome')}",
                    f"Tributi: manutenzione {_value(partita.get('importo_0648'))}; irriguo {_value(partita.get('importo_0985'))}; istituzionale {_value(partita.get('importo_0668'))}",
                    "Dom. Dis. Fog. Part. Sub Sup.Cata. Sup.Irr. Colt. Manut. Irrig. Ist.",
                ]
            )
            for particella in partita.get("particelle", []):
                paragraphs.append(
                    " ".join(
                        _value(particella.get(key))
                        for key in (
                            "domanda_irrigua",
                            "distretto",
                            "foglio",
                            "particella",
                            "subalterno",
                            "sup_catastale_ha",
                            "sup_irrigata_ha",
                            "coltura",
                            "importo_manut",
                            "importo_irrig",
                            "importo_ist",
                        )
                    )
                )
    paragraphs.append("Documento predisposto da GAIA. Nessun invio automatico e stato effettuato.")
    return paragraphs


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
    return {
        "Avviso_n": ", ".join(_value(avviso.get("codice_cnc")) for avviso in payload.get("avvisi", [])) or "-",
        "Denominazione": _value(payload.get("display_name")),
        "INDIRIZZO": address["indirizzo"],
        "CAP": address["cap"],
        "CITTA": address["citta"],
        "PROVINCIA": address["provincia"],
        "Complessivo": _format_template_number(payload.get("saldo_amount") or payload.get("due_amount")),
        "CodFiscale": _value(payload.get("codice_fiscale")),
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


def _append_partitario_xml(document_xml: str, partitario_xml: str) -> str:
    section_index = document_xml.rfind("<w:sectPr")
    if section_index >= 0:
        return f"{document_xml[:section_index]}{partitario_xml}{document_xml[section_index:]}"
    return document_xml.replace("</w:body>", f"{partitario_xml}</w:body>")


def _paragraphs_xml(paragraphs: list[str]) -> str:
    return "".join(f"<w:p><w:r><w:t>{html.escape(text)}</w:t></w:r></w:p>" for text in paragraphs)


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
