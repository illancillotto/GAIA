"""Chromium print conversion, including the measured page box of the Poste v2 layout."""

import subprocess
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject


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
        capture_output=True,
        text=True,
    )
    if not pdf_path.exists():
        raise RuntimeError("Conversione PDF template GAIA non riuscita")
    if 'class="poste-v2"' in html_text:
        _restore_poste_page_box(pdf_path)
    return pdf_path


def _restore_poste_page_box(pdf_path: Path) -> None:
    # Chromium quantizes paper dimensions to 1/100 inch (594.96 x 840.96 pt).
    # Restore the specimen's exact boxes without scaling or moving the printed artwork.
    reader = PdfReader(pdf_path)
    if len(reader.pages) != 1:
        raise RuntimeError("Il bollettino versione 2 deve occupare una sola pagina")
    writer = PdfWriter()
    page = reader.pages[0]
    page.mediabox = RectangleObject((0, 0, 595, 841))
    page.cropbox = RectangleObject((0, 0, 595, 841))
    writer.add_page(page)
    with pdf_path.open("wb") as output:
        writer.write(output)
