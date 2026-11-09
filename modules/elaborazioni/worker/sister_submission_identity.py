"""Capture a SISTER identity from the current submission, before leaving its page."""

from __future__ import annotations

import logging
import re
from urllib.parse import parse_qs, urljoin, urlsplit

from sister_exceptions import SisterRequestCorrelationError
from sister_request_rows import extract_remote_id
from sister_telemetry import SisterTelemetryRecord

IDENTITY_VERSION = "identity_v1"
REQUESTS_PATHS = {"/Servizi/ConsultazioneRichieste.do", "/Visure/ConsultazioneRichieste.do"}
IDENTITY_FIELDS = "input[type='hidden'][name='idRichiesta']"
REQUESTS_LINKS = "a[href*='ConsultazioneRichieste.do']"
logger = logging.getLogger(__name__)


def portal_url(value: str, base: str) -> str | None:
    candidate = urljoin(base, value)
    parsed = urlsplit(candidate)
    if parsed.scheme != "https" or parsed.netloc != "sister3.agenziaentrate.gov.it":
        return None
    return candidate if parsed.path in REQUESTS_PATHS else None


async def observed_requests_url(page, fallback: str, convention: str | None = None) -> str:
    links = await page.locator(REQUESTS_LINKS).evaluate_all(
        "nodes => nodes.map(node => node.getAttribute('href'))"
    )
    candidates = set()
    for href in links:
        url = portal_url(href, fallback)
        query = parse_qs(urlsplit(url or "").query)
        if url and (query.get("metodo") == ["lista"] or submission_url_identity(url)):
            if convention and query.get("numConv", [convention]) != [convention]:
                continue
            candidates.add(url)
    if len(candidates) > 1:
        raise SisterRequestCorrelationError("Collegamento elenco richieste SISTER ambiguo")
    return next(iter(candidates), requests_list_fallback(fallback))


def requests_list_fallback(url: str) -> str:
    """Repair legacy list URLs without changing the document POST endpoint."""
    parsed = urlsplit(url)
    if portal_url(url, url) and parse_qs(parsed.query).get("metodo") == ["lista"]:
        return parsed._replace(path="/Servizi/ConsultazioneRichieste.do").geturl()
    return url


def identity_event(emit, source: str, outcome: str, url: str | None = None) -> None:
    if emit is not None:
        emit(
            SisterTelemetryRecord(
                "remote_identity",
                f"{IDENTITY_VERSION}_{source}",
                outcome=outcome,
                severity="warning" if outcome in {"missing", "conflict"} else "info",
                endpoint=url,
            )
        )


def form_identities(fields: list[dict], base: str) -> set[str]:
    identities = set()
    for field in fields:
        value = str(field["value"]).strip()
        if portal_url(field["action"], base) and field["method"].lower() == "post":
            if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
                raise SisterRequestCorrelationError("Identificativo form SISTER non valido")
            identities.add(value)
    return identities


def submission_url_identity(url: str) -> str | None:
    parsed = urlsplit(url)
    paths = REQUESTS_PATHS | {"/Visure/CheckRichiesta.do"}
    if parsed.scheme == "https" and parsed.netloc == "sister3.agenziaentrate.gov.it":
        if parsed.path in paths:
            return extract_remote_id((url,))
    return None


async def capture_submission_identity(page, state, fallback: str, emit=None) -> str | None:
    """Persist only evidence tied to this submission; conflicting evidence stops it."""
    fields = await page.locator(IDENTITY_FIELDS).evaluate_all(
        """nodes => nodes.filter(node => node.form).map(node => ({value: node.value,
            action: node.form.getAttribute('action') || '', method: node.form.method}))"""
    )
    identities = form_identities(fields, fallback)
    source = "hidden_form" if identities else "known"
    url = await observed_requests_url(page, fallback, state.convention_id)
    known = state.correlation.remote_id if state.correlation is not None else None
    identities.update([known] if known else [])
    identities.update(
        filter(None, (submission_url_identity(page.url), submission_url_identity(url)))
    )
    if len(identities) > 1:
        identity_event(emit, source, "conflict")
        raise SisterRequestCorrelationError("ID form SISTER diverso dalla richiesta corrente")
    remote_id = next(iter(identities), None)
    state.mark_submitted(remote_id, url)
    outcome = "captured" if remote_id else "missing"
    identity_event(emit, source, outcome, url)
    return remote_id


async def accept_submitted_captcha(browser, message: str, requests_url: str) -> bool:
    await capture_submission_identity(
        browser.page,
        browser._session_state,
        requests_url,
        getattr(browser, "_gaia_emit_sister_telemetry", None),
    )
    logger.info(message)
    return True
