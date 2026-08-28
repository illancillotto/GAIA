from __future__ import annotations

import html
import json
from collections.abc import Callable
from io import BytesIO
from typing import Any

from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

DISCLAIMER = (
    "Documento prodotto da GAIA a fini istruttori interni. Non ha valore "
    "certificativo. I dati di fonte esterna sono riportati alla data di "
    "consultazione indicata e restano di titolarita dell'ente che li pubblica."
)


def _source_sections(snapshot: dict[str, Any]) -> str:
    interrogation = snapshot.get("interrogation", {})
    blocks: list[str] = []
    for key, label in (
        ("gaia", "Dati GAIA"),
        ("catasto_ufficiale", "Catasto ufficiale"),
        ("territorio", "Territorio, colture, vincoli e pericolosita"),
    ):
        sources = interrogation.get(key, {}).get("sources", [])
        rows = "".join(
            f"<article><h3>{html.escape(str(source.get('title', 'Sorgente')))}</h3>"
            f"<p>Esito: {html.escape(str(source.get('status', 'unknown')))} - "
            f"{html.escape(str(source.get('message') or 'dato disponibile'))}</p>"
            f"<pre>{html.escape(json.dumps(source.get('data', []), ensure_ascii=False, default=str, indent=2))}</pre></article>"
            for source in sources
        )
        blocks.append(
            f"<section><h2>{label}</h2>{rows or '<p>Nessun dato.</p>'}</section>"
        )
    return "".join(blocks)


def render_html(snapshot: dict[str, Any]) -> str:
    parcel = snapshot.get("parcel", {})
    excluded = snapshot.get("excluded_layers", [])
    attributions = snapshot.get("attributions", [])
    map_extract = snapshot.get("map_extract", {})
    excluded_html = (
        "".join(
            f"<li>{html.escape(str(item.get('title')))}: {html.escape(str(item.get('reason')))}</li>"
            for item in excluded
        )
        or "<li>Nessuna esclusione autorizzativa.</li>"
    )
    map_html = (
        f'<img src="{html.escape(str(map_extract.get("data_url")))}" alt="Estratto ortofoto">'
        if map_extract.get("status") == "ok"
        else f"<p>Estratto non disponibile: {html.escape(str(map_extract.get('message', 'n/d')))}</p>"
    )
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><style>
    @page {{ size: A4; margin: 14mm; }} body {{ font-family: Arial, sans-serif; color:#17211d; }}
    .disclaimer {{ border:3px solid #8a3b12; background:#fff4e8; padding:14px; font-weight:bold; }}
    table {{ border-collapse:collapse; width:100%; }} td,th {{ border:1px solid #ccd5cf; padding:6px; }}
    article {{ break-inside:avoid; border:1px solid #d9e0dc; padding:8px; margin:8px 0; }}
    pre {{ white-space:pre-wrap; font-size:9px; }} img {{ width:100%; max-height:125mm; object-fit:contain; }}
    </style></head><body><h1>Scheda territoriale particella</h1>
    <div class="disclaimer">{html.escape(DISCLAIMER)}</div>
    <p>Consultazione: {html.escape(str(snapshot.get("collected_at", "n/d")))}</p>
    <h2>Identificativi catastali e consortili</h2><table>
    <tr><th>Comune</th><td>{html.escape(str(parcel.get("nome_comune", "n/d")))}</td></tr>
    <tr><th>Foglio / particella / subalterno</th><td>{html.escape(str(parcel.get("foglio")))} / {html.escape(str(parcel.get("particella")))} / {html.escape(str(parcel.get("subalterno") or "-"))}</td></tr>
    <tr><th>Superficie reale / grafica</th><td>{html.escape(str(parcel.get("superficie_mq")))} / {html.escape(str(parcel.get("superficie_grafica_mq")))} mq</td></tr>
    <tr><th>Distretto</th><td>{html.escape(str(parcel.get("num_distretto")))} - {html.escape(str(parcel.get("nome_distretto")))}</td></tr></table>
    {_source_sections(snapshot)}
    <section><h2>Estratto di mappa su ortofoto</h2>{map_html}<p>Scala {html.escape(str(map_extract.get("scale", "n/d")))}</p><p>{html.escape(str(map_extract.get("attribution", "")))}</p></section>
    <section><h2>Attribuzioni delle sorgenti consultate</h2><ul>{"".join(f"<li>{html.escape(str(value))}</li>" for value in attributions) or "<li>Nessuna sorgente esterna consultata.</li>"}</ul></section>
    <section><h2>Layer esclusi per autorizzazione</h2><ul>{excluded_html}</ul></section>
    </body></html>"""


def render_pdf(
    snapshot: dict[str, Any],
    playwright_factory: Callable[[], Any] = sync_playwright,
) -> bytes:
    with playwright_factory() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(render_html(snapshot), wait_until="networkidle")
            chromium_pdf = page.pdf(format="A4", print_background=True)
        finally:
            browser.close()
    reader = PdfReader(BytesIO(chromium_pdf))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
