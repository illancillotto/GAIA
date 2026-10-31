"""HTTP helpers shared by the Capacitas Excel export clients (inCASS, inBOLLETTINI)."""

from __future__ import annotations

import html
import json
import re

import httpx

AJAX_HEADERS = {
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}
_LOGIN_MARKERS = ("sso.servizicapacitas.com/pages/login.aspx", "/pages/login.aspx")


class ExportStepError(RuntimeError):
    """A portal step that did not complete; ``retryable`` decides if a new attempt is worth it."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class SessionExpiredError(ExportStepError):
    """The Capacitas session is gone: the next attempt must log in again."""


def ensure_portal_response(response: httpx.Response, *, step: str) -> None:
    """Fail on HTTP errors, SSO redirects and the portal error page."""
    response.raise_for_status()
    final_url = str(response.url).lower()
    if (
        any(marker in final_url for marker in _LOGIN_MARKERS)
        or 'name="txtusername"' in response.text.lower()
    ):
        raise SessionExpiredError(f"Sessione Capacitas scaduta durante {step}.")
    if "/pages/errore.aspx" in final_url:
        raise ExportStepError(f"Il portale ha rediretto su errore.aspx durante {step}.")
    if response.text.startswith("NO"):
        raise ExportStepError(
            f"Errore applicativo Capacitas durante {step}: {response.text[2:300]}"
        )


def parse_select_options(page_html: str, select_id: str) -> list[str]:
    """Non-empty option values of ``<select id=select_id>``, in page order."""
    match = re.search(
        rf'<select[^>]+id="{re.escape(select_id)}"[^>]*>(.*?)</select>',
        page_html,
        re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        raise ExportStepError(f"Elenco {select_id} non trovato nella pagina.", retryable=False)
    values = re.findall(r'<option[^>]*value="([^"]*)"', match.group(1), re.IGNORECASE)
    return [html.unescape(value).strip() for value in values if value.strip()]


def _kendo_grid_payload(body: str, *, step: str) -> dict[str, object]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ExportStepError(f"{step}: risposta non JSON ({body[:120]!r}).") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ExportStepError(f"{step}: risposta senza elenco results.")
    if payload.get("err"):
        raise ExportStepError(f"{step}: il portale ha segnalato un errore: {payload['err']}")
    return payload


def kendo_grid_rows(body: str, *, step: str) -> list[dict[str, object]]:
    """Rows of a Kendo grid read (``{"results": [...], "total": n, "err": ...}``), checked for completeness."""
    payload = _kendo_grid_payload(body, step=step)
    rows = [row for row in payload["results"] if isinstance(row, dict)]
    total = payload.get("total")
    if isinstance(total, int) and total != len(rows):
        raise ExportStepError(f"{step}: ricevute {len(rows)} righe su {total} dichiarate.")
    return rows


def ensure_xlsx(response: httpx.Response, *, step: str) -> bytes:
    content_type = response.headers.get("content-type", "").lower()
    if "spreadsheetml" not in content_type or not response.content.startswith(b"PK"):
        raise ExportStepError(
            f"{step}: risposta non Excel ({content_type or 'senza content-type'})."
        )
    return response.content
