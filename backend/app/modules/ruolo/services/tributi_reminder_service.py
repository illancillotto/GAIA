from __future__ import annotations

import html
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


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
