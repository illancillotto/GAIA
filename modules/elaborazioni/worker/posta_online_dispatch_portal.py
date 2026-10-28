"""Pure parsing and network guard for the Posta Online draft pages.

The guard is the last line of defence of a hard rule: INVIA is pressed only by
an operator. Requests that would send, pay or alter the archive are aborted in
every phase, and each phase allows only the writes it needs.
"""

from __future__ import annotations

import html
import re
from decimal import Decimal

from app.modules.ruolo.services.poste_dispatch_work import DraftRow

# inserisciInvii.do is the Poste INVIA. Nothing in GAIA may reach it.
ALWAYS_DENY = re.compile(
    r"inserisciInvii|paga|carrello|cancellaArchivio|modifica\.do|hideInvii", re.IGNORECASE
)
_BASE_POSTS = (
    "gestioneLocalitaProvincia",
    "gestioneListeContatti",
    "incorso",
    "archivio",
    "dettaglio",
)
PHASE_POSTS = {
    "addresses": (*_BASE_POSTS, "autocomplete"),
    "draft": (*_BASE_POSTS, "autocomplete", "gestioneCap", "invioDestinatari"),
    "delete": _BASE_POSTS,
    "reconcile": _BASE_POSTS,
}
_READ_ONLY_DWR = {
    "ConfigurationHelper",
    "UtilHelper",
    "DestinatarioForm",
    "RicevutaFormHelper",
    "ListeView",
}
PHASE_DWR = {"delete": {("InviiColHelper", "eliminaInvio")}}
_DWR_CALL_RE = re.compile(r"c(\d+)-scriptName=([A-Za-z]+)\s+c\1-methodName=([A-Za-z]+)")
_TABLE_RE = re.compile(
    r'<table\b[^>]*id=["\']col_invio_dett["\'][^>]*>(.*?)</table>', re.IGNORECASE | re.DOTALL
)
_ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
_CELL_RE = re.compile(r"<td\b[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)
_PRICE_RE = re.compile(r"(\d+(?:\.\d{3})*,\d{2})")


def _post_endpoint(url: str) -> str:
    match = re.search(r"/col/([A-Za-z]+)\.do", url)
    return match.group(1) if match else ""


def dwr_calls(body: str) -> list[tuple[str, str]]:
    return [(script, method) for _, script, method in _DWR_CALL_RE.findall(body)]


def allows_request(phase: str, method: str, url: str, body: str) -> bool:
    """Decide on one browser request to Poste after login."""
    if ALWAYS_DENY.search(url):
        return False
    if method in ("GET", "HEAD") or phase == "login":
        return True
    if "/dwr/" in url:
        calls = dwr_calls(body)
        extra = PHASE_DWR.get(phase, set())
        return bool(calls) and all(
            script in _READ_ONLY_DWR or (script, name) in extra for script, name in calls
        )
    return _post_endpoint(url) in PHASE_POSTS.get(phase, ())


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_price(text: str) -> Decimal | None:
    match = _PRICE_RE.search(text)
    if match is None:
        return None
    return Decimal(match.group(1).replace(".", "").replace(",", "."))


def _rows(page_html: str) -> list[list[str]]:
    table = _TABLE_RE.search(page_html)
    if table is None:
        return []
    return [
        [_text(cell) for cell in _CELL_RE.findall(row)] for row in _ROW_RE.findall(table.group(1))
    ]


def parse_draft_rows(page_html: str) -> list[DraftRow]:
    """Rows of "Verifica e invia": checkbox, id, name, date, status, price, preview, edit, delete."""
    return [
        DraftRow(
            draft_id=cells[1], name=cells[2], status=cells[4].upper(), price=parse_price(cells[5])
        )
        for cells in _rows(page_html)
        if len(cells) >= 6 and cells[1].isdigit()
    ]


def parse_archive_rows(page_html: str) -> list[tuple[str, str]]:
    """Rows of the archive: id, shipment name, date, price, delete."""
    return [
        (cells[0], cells[1]) for cells in _rows(page_html) if len(cells) >= 4 and cells[0].isdigit()
    ]
