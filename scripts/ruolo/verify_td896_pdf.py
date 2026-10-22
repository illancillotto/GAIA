#!/usr/bin/env python3
"""Verifica di campionatura dei bollettini TD 896 GAIA su PDF gia generati.

Dipendenze solo di sviluppo (non servono al backend):

    pip install -r scripts/ruolo/requirements-verify-td896.txt

Uso:

    python scripts/ruolo/verify_td896_pdf.py avviso.pdf [altro.pdf ...]

Ogni pagina A4 orizzontale con una codeline TD 896 viene trattata come un
bollettino. Lo script stampa una tabella OK/KO per pagina ed esce con codice 1
se almeno un controllo e KO. Il codice AUT segnaposto (XXXXX) e riportato come
CAMPIONATURA, non come errore.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pymupdf
import zxingcpp

MM = 72 / 25.4
TOLERANCE_MM = 0.5
PAGE_TOLERANCE_MM = 1.0
DPI = 600
MODULE_WIDTH_MM = 297.0
MODULE_HEIGHT_MM = 102.0
DIVISION_X_MM = 132.0
EXPECTED_ABI = "07601"
EXPECTED_DM_VERSION = "16x48"

CODELINE_RE = re.compile(r"<(\d{18})> (\d{8}\+\d{2})> (\d{12})< 896>")
AMOUNT_RE = re.compile(r"^\d{1,3}(?:\.\d{3})*,\d{2}$")
IBAN_RE = re.compile(r"IT\d{2}[A-Z]\d{10}[0-9A-Z]{12}")
AUTHORIZATION_RE = re.compile(r"AUT\.DB/SISB/\S+ DEL \S+")
FONT_XREF_RE = re.compile(r"\((\d+) 0 R\)")

OK = "OK"
KO = "KO"
SAMPLE = "CAMPIONATURA"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def _status(condition: bool) -> str:
    return OK if condition else KO


def _black(color: tuple[float, ...] | None) -> bool:
    return color is not None and all(channel < 0.2 for channel in color)


def _rule_rects(page: pymupdf.Page) -> list[pymupdf.Rect]:
    rects = []
    for drawing in page.get_drawings():
        if _black(drawing.get("fill")) or _black(drawing.get("color")):
            rects.append(drawing["rect"])
    return rects


def check_page_format(page: pymupdf.Page) -> Check:
    width, height = page.rect.width / MM, page.rect.height / MM
    ok = abs(width - 297) <= PAGE_TOLERANCE_MM and abs(height - 210) <= PAGE_TOLERANCE_MM
    return Check("Pagina A4 orizzontale", _status(ok), f"{width:.1f} x {height:.1f} mm")


def check_module(page: pymupdf.Page) -> Check:
    horizontals = [r for r in _rule_rects(page) if r.width > 100 * MM and r.height < 1.5 * MM]
    if not horizontals:
        return Check("Modulo 297 x 102 mm", KO, "bordo superiore del modulo non trovato")
    top = min(r.y0 for r in horizontals if r.y0 > page.rect.height / 3)
    top_edges = [r for r in horizontals if abs(r.y0 - top) < 0.5 * MM]
    width = (max(r.x1 for r in top_edges) - min(r.x0 for r in top_edges)) / MM
    height = (page.rect.height - top) / MM
    ok = (
        abs(width - MODULE_WIDTH_MM) <= TOLERANCE_MM
        and abs(height - MODULE_HEIGHT_MM) <= TOLERANCE_MM
    )
    return Check("Modulo 297 x 102 mm", _status(ok), f"{width:.2f} x {height:.2f} mm")


def check_division(page: pymupdf.Page) -> Check:
    verticals = [r for r in _rule_rects(page) if r.height > 80 * MM and r.width < 1.5 * MM]
    if not verticals:
        return Check("Divisione a 132 mm", KO, "linea verticale non trovata")
    x_mm = min(((r.x0 + r.x1) / 2 / MM for r in verticals), key=lambda x: abs(x - DIVISION_X_MM))
    return Check(
        "Divisione a 132 mm", _status(abs(x_mm - DIVISION_X_MM) <= TOLERANCE_MM), f"{x_mm:.2f} mm"
    )


def find_codeline(text: str) -> re.Match[str] | None:
    return CODELINE_RE.search(" ".join(text.split()))


def check_codeline(match: re.Match[str]) -> Check:
    customer = match.group(1)
    mod93_ok = int(customer[:16]) % 93 == int(customer[16:])
    detail = match.group(0) + (
        "" if mod93_ok else f" (controcodice atteso {int(customer[:16]) % 93:02d})"
    )
    return Check("Codeline e controcodice mod 93", _status(mod93_ok), detail)


def expected_payload(match: re.Match[str]) -> str:
    customer, amount, account = match.group(1), match.group(2).replace("+", ""), match.group(3)
    return f"18{customer}12{account}10{amount}3896"


def check_barcodes(page: pymupdf.Page, payload: str) -> list[Check]:
    pixmap = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
    image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width)
    results = zxingcpp.read_barcodes(image)
    checks = []
    for label, barcode_format in (
        ("Code 128", zxingcpp.BarcodeFormat.Code128),
        ("Data Matrix", zxingcpp.BarcodeFormat.DataMatrix),
    ):
        found = [result for result in results if result.format == barcode_format]
        if not found:
            checks.append(Check(f"{label} = payload", KO, "simbolo non decodificato"))
            continue
        text = found[0].text
        detail = text if text == payload else f"letto {text}, atteso {payload}"
        if barcode_format == zxingcpp.BarcodeFormat.DataMatrix:
            version = (getattr(found[0], "extra", None) or {}).get("Version", "?")
            detail = f"{detail} [{version}]"
            checks.append(
                Check(
                    f"{label} = payload, {EXPECTED_DM_VERSION}",
                    _status(text == payload and version == EXPECTED_DM_VERSION),
                    detail,
                )
            )
        else:
            checks.append(Check(f"{label} = payload", _status(text == payload), detail))
    return checks


def check_amount(page: pymupdf.Page, match: re.Match[str]) -> Check:
    integer, cents = match.group(2).split("+")
    codeline_amount = f"{int(integer)},{cents}"
    body_amounts = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                text = span["text"].strip()
                if AMOUNT_RE.match(text) and span["bbox"][1] > page.rect.height / 3:
                    body_amounts.append(text.replace(".", ""))
    ok = bool(body_amounts) and all(amount == codeline_amount for amount in body_amounts)
    return Check(
        "Importo corpo = codeline",
        _status(ok),
        f"corpo {sorted(set(body_amounts))}, codeline {codeline_amount}",
    )


def iban_mod97_ok(iban: str) -> bool:
    rearranged = iban[4:] + iban[:4]
    digits = "".join(str(int(character, 36)) for character in rearranged)
    return int(digits) % 97 == 1


def check_iban(text: str) -> Check:
    ibans = IBAN_RE.findall(re.sub(r"\s", "", text))
    if not ibans:
        return Check("IBAN mod 97 e ABI 07601", KO, "IBAN non trovato")
    unique = sorted(set(ibans))
    ok = len(unique) == 1 and iban_mod97_ok(unique[0]) and unique[0][5:10] == EXPECTED_ABI
    return Check(
        "IBAN mod 97 e ABI 07601", _status(ok), f"{', '.join(unique)} (ABI {unique[0][5:10]})"
    )


def _font_family(document: pymupdf.Document, font_xref: int) -> str:
    kind, value = document.xref_get_key(font_xref, "FontDescriptor")
    if kind != "xref":
        kind, value = document.xref_get_key(font_xref, "DescendantFonts")
        if kind != "array":
            return ""
        descendant = int(value.strip("[]").split()[0])
        kind, value = document.xref_get_key(descendant, "FontDescriptor")
        if kind != "xref":
            return ""
    descriptor = int(value.split()[0])
    _kind, family = document.xref_get_key(descriptor, "FontFamily")
    return family.strip("()")


def check_codeline_font(document: pymupdf.Document, page: pymupdf.Page) -> Check:
    page_fonts = {font[3]: font[0] for font in page.get_fonts(full=True)}
    families = set()
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                if "896>" not in span["text"] and "+" not in span["text"]:
                    continue
                xref_match = FONT_XREF_RE.search(span["font"])
                xref = int(xref_match.group(1)) if xref_match else page_fonts.get(span["font"])
                if xref:
                    families.add(_font_family(document, xref))
    ok = families == {"OCR B"}
    return Check(
        'Font codeline FontFamily "OCR B"',
        _status(ok),
        ", ".join(sorted(families)) or "nessun font",
    )


def check_payer_name(text: str) -> Check:
    lines = [line for line in text.splitlines() if line.strip().startswith("eseguito da:")]
    truncated = [line for line in lines if "..." in line or "…" in line]
    detail = lines[0].strip() if lines else "riga 'eseguito da' non trovata"
    return Check('Nome versante senza "..."', _status(bool(lines) and not truncated), detail)


def check_authorization(text: str) -> Check:
    match = AUTHORIZATION_RE.search(text)
    if not match:
        return Check("Codice AUT stampa in proprio", KO, "codice non trovato")
    if "XXXXX" in match.group(0):
        return Check("Codice AUT stampa in proprio", SAMPLE, match.group(0))
    return Check("Codice AUT stampa in proprio", OK, match.group(0))


def verify_page(document: pymupdf.Document, page: pymupdf.Page) -> list[Check] | None:
    text = page.get_text()
    match = find_codeline(text)
    if match is None:
        return None
    return [
        check_page_format(page),
        check_module(page),
        check_division(page),
        check_codeline(match),
        *check_barcodes(page, expected_payload(match)),
        check_amount(page, match),
        check_iban(text),
        check_codeline_font(document, page),
        check_payer_name(text),
        check_authorization(text),
    ]


def verify_pdf(path: Path) -> list[tuple[int, list[Check]]]:
    with pymupdf.open(path) as document:
        results = []
        for page in document:
            checks = verify_page(document, page)
            if checks is not None:
                results.append((page.number + 1, checks))
        return results


def print_report(path: Path, results: list[tuple[int, list[Check]]]) -> bool:
    print(f"\n== {path}")
    if not results:
        print("   KO  nessuna pagina con codeline TD 896")
        return False
    all_ok = True
    for page_number, checks in results:
        print(f"-- pagina {page_number}")
        width = max(len(check.name) for check in checks)
        for check in checks:
            all_ok &= check.status != KO
            print(f"   {check.status:<12} {check.name:<{width}}  {check.detail}")
    return all_ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf", nargs="+", type=Path)
    args = parser.parse_args(argv)
    all_ok = True
    for path in args.pdf:
        all_ok &= print_report(path, verify_pdf(path))
    print(f"\nEsito complessivo: {OK if all_ok else KO}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
