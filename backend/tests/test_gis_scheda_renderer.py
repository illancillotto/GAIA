from __future__ import annotations

import html
from io import BytesIO

from app.modules.gis.scheda_territoriale import renderer
from pypdf import PdfReader, PdfWriter


def _pdf() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.write(output)
    return output.getvalue()


def _snapshot() -> dict:
    return {
        "collected_at": "2026-09-01T09:00:00Z",
        "parcel": {
            "nome_comune": "Oristano",
            "foglio": "12",
            "particella": "34",
            "subalterno": None,
            "superficie_mq": 1000,
            "superficie_grafica_mq": 980,
            "num_distretto": "2",
            "nome_distretto": "Nord",
        },
        "interrogation": {
            "gaia": {
                "sources": [
                    {
                        "title": "Ruolo",
                        "status": "ok",
                        "data": [{"anno": 2026}],
                        "message": None,
                    }
                ]
            },
            "catasto_ufficiale": {"sources": []},
            "territorio": {
                "sources": [
                    {
                        "title": "Uso suolo",
                        "status": "failed",
                        "data": [],
                        "message": "timeout",
                    }
                ]
            },
        },
        "excluded_layers": [{"title": "Vincolo", "reason": "No can_view"}],
        "attributions": ["Fonte RAS", "Agenzia delle Entrate"],
        "map_extract": {
            "status": "ok",
            "data_url": "data:image/png;base64,eA==",
            "scale": "1:5.000",
            "attribution": "Fonte RAS",
        },
    }


class _Page:
    def __init__(self) -> None:
        self.html = ""

    def set_content(self, content: str, wait_until: str) -> None:
        self.html = content
        assert wait_until == "networkidle"

    def pdf(self, **options: object) -> bytes:
        assert options == {"format": "A4", "print_background": True}
        return _pdf()


class _Browser:
    def __init__(self) -> None:
        self.page = _Page()
        self.closed = False

    def new_page(self) -> _Page:
        return self.page

    def close(self) -> None:
        self.closed = True


class _Playwright:
    def __init__(self, browser: _Browser) -> None:
        self.chromium = self
        self.browser = browser

    def launch(self, headless: bool) -> _Browser:
        assert headless is True
        return self.browser


class _Context:
    def __init__(self, browser: _Browser) -> None:
        self.value = _Playwright(browser)

    def __enter__(self) -> _Playwright:
        return self.value

    def __exit__(self, *args: object) -> None:
        del args


def test_renderer_puts_disclaimer_sources_map_attribution_and_exclusions_in_html() -> (
    None
):
    rendered = renderer.render_html(_snapshot())
    assert renderer.DISCLAIMER in html.unescape(rendered)
    assert html.unescape(rendered).index(renderer.DISCLAIMER) < rendered.index(
        "Identificativi"
    )
    assert "Uso suolo" in rendered and "timeout" in rendered
    assert "Fonte RAS" in rendered and "No can_view" in rendered
    assert "Agenzia delle Entrate" in rendered
    assert "data:image/png;base64,eA==" in rendered


def test_renderer_builds_valid_pdf_with_simulated_chromium() -> None:
    browser = _Browser()
    result = renderer.render_pdf(_snapshot(), lambda: _Context(browser))
    assert len(PdfReader(BytesIO(result)).pages) == 1
    assert renderer.DISCLAIMER in html.unescape(browser.page.html)
    assert browser.closed is True


def test_renderer_describes_empty_sources_missing_map_and_no_exclusions() -> None:
    snapshot = _snapshot() | {
        "interrogation": {},
        "excluded_layers": [],
        "attributions": [],
        "map_extract": {"status": "failed", "message": "offline"},
    }
    rendered = renderer.render_html(snapshot)
    assert rendered.count("Nessun dato.") == 3
    assert "Nessuna esclusione autorizzativa." in rendered
    assert "Nessuna sorgente esterna consultata." in rendered
    assert "Estratto non disponibile: offline" in rendered
