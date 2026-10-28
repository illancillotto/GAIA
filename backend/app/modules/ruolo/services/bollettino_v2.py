"""Measured Poste layout, with the supplied specimen's fixed artwork and authorization."""

from __future__ import annotations

import base64
import html
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.modules.ruolo.services.td896 import (
    build_td896_payment_code,
    td896_datamatrix_svg,
    td896_esercizio,
)

_BOLLETTINO_POSTAL_ACCOUNT = "1007214826"
_BOLLETTINO_IBAN = "IT15L0760117400001007214826"
_BOLLETTINO_ACCOUNT_NAME_LINES = (
    "CONSORZIO DI BONIFICA DELL'ORISTANESE -",
    "RISCOSSIONE QUOTE ASSOCIATIVE",
)
_ASSETS = Path(__file__).resolve().parents[1] / "assets"
_BASE = base64.b64encode((_ASSETS / "bollettino-v2-base.svg").read_bytes()).decode("ascii")
_OCR_FONT = (_ASSETS / "OCRB.otf.b64").read_text(encoding="ascii").strip()


def bollettino_layout_html(
    fields: dict[str, str],
    payload: dict[str, Any],
    *,
    render_v1: Callable[[dict[str, str], dict[str, Any]], str],
    render_barcode: Callable[[str], str],
    causale: str,
) -> str:
    """Select the saved rule's layout; old snapshots without a version retain v1."""
    if payload.get("bollettino_version") == "v2":
        return bollettino_v2_html(fields, payload, barcode_renderer=render_barcode, causale=causale)
    return render_v1(fields, payload)


def bollettino_v2_html(
    fields: dict[str, str],
    payload: dict[str, Any],
    *,
    barcode_renderer: Callable[[str], str],
    causale: str,
) -> str:
    """Keep the original 595 x 841 pt page, with its landscape artwork rotated inside it."""
    code = build_td896_payment_code(
        notice_number=fields["Avviso_n"],
        amount=fields["Complessivo"],
        postal_account=_BOLLETTINO_POSTAL_ACCOUNT,
    )
    amount = fields["Complessivo"]
    text = [
        _text(280.8, 342.2, amount, ocr=True),
        _text(718.7, 342.2, amount, ocr=True),
        _text(389.3, 433.5, code.customer_code, ocr=True),
        _text(
            389.3,
            571.8,
            f"<{code.customer_code}>      {code.amount_code}>  {code.postal_account_code}<  896>",
            ocr=True,
        ),
        _payer(fields, x=30.9, name_x=72.9),
        _payer(fields, x=532.1, name_x=576.9),
        _details(fields, payload, causale=causale),
    ]
    reason = html.escape(f"causale: A {fields['Avviso_n']} CF {fields['CodFiscale']}")
    barcode = barcode_renderer(code.barcode_payload)
    matrix = td896_datamatrix_svg(code.barcode_payload)
    return f"""
<style>
@page bollettino {{ size: 595pt 841pt; margin: 0; }}
@font-face {{ font-family: PosteOCR; src: url(data:font/otf;base64,{_OCR_FONT}) format("opentype"); }}
.bollettino-page {{ width: 595pt; height: 841pt; min-height: 841pt; padding: 0; }}
.poste-v2 {{ position: absolute; left: 0; top: 0; width: 841pt; height: 595pt;
  transform-origin: 0 0; transform: translateY(841pt) rotate(-90deg); }}
.poste-v2 .base, .poste-v2 .variable {{ position: absolute; inset: 0; width: 841pt; height: 595pt; }}
.poste-v2 .reason {{ position: absolute; left: 508.25pt; top: 208.15pt;
  font: bold 9pt Arial, sans-serif; white-space: nowrap; }}
.poste-v2 .bollettino-barcode-svg {{ left: 532.1pt; top: 485.3pt; width: 263.5pt; height: 30.4pt; }}
.poste-v2 .barcode-number {{ position: absolute; left: 532.1pt; top: 515.7pt; width: 263.5pt;
  text-align: center; font: 7.5pt/1 Arial, sans-serif; white-space: nowrap; }}
.poste-v2 .bollettino-datamatrix {{ left: 222.7pt; top: 533.3pt; width: 129.25pt; height: 45.95pt; }}
</style>
<div class="poste-v2">
<img class="base" alt="Modello postale versione 2" src="data:image/svg+xml;base64,{_BASE}">
<svg class="variable" viewBox="0 0 841 595" xmlns="http://www.w3.org/2000/svg">
{"".join(text)}</svg>
<span class="reason">{reason}</span>
{barcode}<span class="barcode-number">{code.barcode_payload}</span>{matrix}
</div>"""


def _text(x: float, y: float, value: str, *, ocr: bool = False, width: float = 0) -> str:
    normalized = " ".join(value.split()) if not ocr else value
    # Courier's measured advance includes the specimen's 0.15 pt character spacing.
    size = min(9.75, (width / max(len(normalized), 1) - 0.15) / 0.6) if width else 9.75
    if size < 6:
        raise ValueError("Nome o indirizzo troppo lungo per il bollettino versione 2")
    family = "PosteOCR" if ocr else "Courier New, Courier, monospace"
    spacing = 0 if ocr else 0.15
    advance = (
        f' textLength="{len(normalized) * 6.747}" lengthAdjust="spacingAndGlyphs"' if ocr else ""
    )
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
        f'letter-spacing="{spacing}" xml:space="preserve"{advance}>{html.escape(normalized)}</text>'
    )


def _payer(fields: dict[str, str], *, x: float, name_x: float) -> str:
    city = " ".join(
        value
        for value in (fields["CAP"], fields["CITTA"], fields["PROVINCIA"])
        if value and value != "-"
    )
    return "".join(
        (
            _text(name_x, 414.35, fields["Denominazione"], width=230),
            _text(x, 428.35, fields["INDIRIZZO"], width=270),
            _text(x, 442.5, city, width=270),
        )
    )


def _details(fields: dict[str, str], payload: dict[str, Any], *, causale: str) -> str:
    year = td896_esercizio(payload)
    amount = fields["Complessivo"]
    right_year = f"Esercizio: {year}" + (f" Causale: {causale}" if causale else "")
    rows = [
        (30.9, 456.9, f"Scadenza:{fields['Scadenza']} - Rata Unica"),
        (30.9, 469.5, f"Esercizio:    {year}"),
        (30.9, 494.7, f"Importo:      {amount}"),
        (532.1, 456.9, f"Scadenza:{fields['Scadenza']} - Rata Unica"),
        (532.1, 469.5, right_year),
        (532.1, 482.1, f"Importo: {amount}"),
    ]
    if causale:
        rows.append((30.9, 482.1, f"Causale:      {causale}"))
    return "".join(_text(x, y, value) for x, y, value in rows)
