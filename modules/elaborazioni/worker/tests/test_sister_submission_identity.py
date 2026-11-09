from __future__ import annotations

import asyncio
import shutil

import pytest
from browser_test_support import ScriptedLocator, ScriptedPage, make_session
from playwright.async_api import async_playwright

from sister_browser_reliability import SisterSessionState, document_not_yet_produced_error
from sister_exceptions import SisterRequestCorrelationError, SisterServerError
from sister_pdf_recovery import poll_for_pdf, validate_requests_page
from sister_request_rows import SisterRequestCorrelation
from sister_submission_identity import (
    IDENTITY_FIELDS,
    REQUESTS_LINKS,
    accept_submitted_captcha,
    capture_submission_identity,
    form_identities,
    identity_event,
    observed_requests_url,
    portal_url,
    submission_url_identity,
)

BASE = "https://sister3.agenziaentrate.gov.it"
LIST = BASE + "/Servizi/ConsultazioneRichieste.do?metodo=lista&numConv=1050380&apertura=T"


def run(coro):
    return asyncio.run(coro)


def page_with_identity(value="2074281792", *, links=None):
    page = ScriptedPage(url=BASE + "/Visure/CheckRichiesta.do")
    page.locators[IDENTITY_FIELDS] = ScriptedLocator(
        payload=[{"value": value, "action": "/Visure/ConsultazioneRichieste.do", "method": "post"}]
    )
    page.locators[REQUESTS_LINKS] = ScriptedLocator(payload=[LIST] if links is None else links)
    return page


def state_with_callback(calls, known=None):
    return SisterSessionState(
        convention_id="1050380",
        correlation=SisterRequestCorrelation("local", frozenset(), (), known),
        submission_callback=lambda *args: calls.append(args),
    )


def test_hidden_form_is_persisted_before_the_page_can_be_lost():
    calls, events = [], []
    state = state_with_callback(calls)
    assert (
        run(capture_submission_identity(page_with_identity(), state, LIST, events.append))
        == "2074281792"
    )
    assert calls == [("2074281792", LIST, "submitted")]
    assert state.correlation.remote_id == "2074281792"
    assert state.submission_callback is None
    assert events[0].outcome == "captured"
    assert events[0].step == "identity_v1_hidden_form"
    assert events[0].context is None  # Identifiers and page contents stay out of telemetry.
    run(capture_submission_identity(page_with_identity(), state, LIST, events.append))
    assert events[-1].outcome == "captured"
    assert len(calls) == 1


@pytest.mark.parametrize("known,other", [("OLD", "NEW"), (None, "NEW")])
def test_conflicting_ids_never_update_the_current_request(known, other):
    calls, events = [], []
    page = page_with_identity(other)
    if known is None:
        page.locators[IDENTITY_FIELDS].payload.append(
            {"value": "ANOTHER", "action": "/Visure/ConsultazioneRichieste.do", "method": "post"}
        )
    state = state_with_callback(calls, known)
    with pytest.raises(SisterRequestCorrelationError, match="diverso"):
        run(capture_submission_identity(page, state, LIST, events.append))
    assert calls == []
    assert state.correlation.remote_id == known
    assert events[-1].outcome == "conflict"


def test_missing_id_is_explicit_and_does_not_invent_an_identity():
    calls, events = [], []
    state = state_with_callback(calls)
    page = ScriptedPage(url=BASE + "/Visure/CheckRichiesta.do")
    assert run(capture_submission_identity(page, state, LIST, events.append)) is None
    assert calls == [(None, LIST, "submitted")]
    assert state.correlation.remote_id is None
    assert events[-1].outcome == "missing"
    identity_event(None, "known", "observed")


def test_form_scope_and_identifiers_are_validated():
    assert (
        form_identities(
            [
                {
                    "value": "wrong",
                    "action": "https://other.example/Visure/ConsultazioneRichieste.do",
                    "method": "post",
                },
                {"value": "wrong", "action": "/unrelated", "method": "post"},
                {"value": "wrong", "action": "/Visure/ConsultazioneRichieste.do", "method": "get"},
            ],
            LIST,
        )
        == set()
    )
    with pytest.raises(SisterRequestCorrelationError, match="non valido"):
        form_identities(
            [
                {
                    "value": "bad value",
                    "action": "/Visure/ConsultazioneRichieste.do",
                    "method": "POST",
                }
            ],
            LIST,
        )
    assert (
        portal_url("http://sister3.agenziaentrate.gov.it/Visure/ConsultazioneRichieste.do", LIST)
        is None
    )


def test_observed_links_respect_origin_convention_and_uniqueness():
    page = page_with_identity(
        links=[
            "https://other.example/Servizi/ConsultazioneRichieste.do?metodo=lista",
            BASE + "/Servizi/ConsultazioneRichieste.do?metodo=lista&numConv=OTHER",
            BASE + "/Servizi/ConsultazioneRichieste.do?metodo=other",
            LIST,
            LIST,
        ]
    )
    assert (
        run(observed_requests_url(page, BASE + "/Visure/ConsultazioneRichieste.do", "1050380"))
        == LIST
    )
    page.locators[REQUESTS_LINKS].payload = []
    assert run(observed_requests_url(page, LIST)) == LIST
    page.locators[REQUESTS_LINKS].payload = [LIST, LIST + "&other=1"]
    with pytest.raises(SisterRequestCorrelationError, match="ambiguo"):
        run(observed_requests_url(page, LIST))


def test_url_identity_has_a_narrow_origin_and_path_scope():
    assert submission_url_identity(BASE + "/Visure/CheckRichiesta.do?idRichiesta=R1") == "R1"
    assert submission_url_identity(LIST + "&idRichiesta=R1") == "R1"
    assert submission_url_identity(BASE + "/unrelated?idRichiesta=R1") is None
    assert submission_url_identity("https://other/Visure/CheckRichiesta.do?idRichiesta=R1") is None
    calls = []
    page = ScriptedPage(url=BASE + "/Visure/CheckRichiesta.do?idRichiesta=R1")
    page.locators[IDENTITY_FIELDS] = ScriptedLocator(
        payload=[{"value": "WRONG", "action": "/unrelated", "method": "post"}]
    )
    events = []
    assert (
        run(capture_submission_identity(page, state_with_callback(calls), LIST, events.append))
        == "R1"
    )
    assert events[-1].step == "identity_v1_known"


def test_persistence_failure_is_not_reported_as_persisted():
    events = []
    state = state_with_callback([])

    def fail(*_args):
        raise RuntimeError("storage")

    state.submission_callback = fail
    with pytest.raises(RuntimeError, match="storage"):
        run(capture_submission_identity(page_with_identity(), state, LIST, events.append))
    assert events == []


def test_acceptance_and_pending_capture_share_the_hidden_form_identity():
    calls = []
    session = make_session(page_with_identity())
    session._session_state = state_with_callback(calls)
    assert run(accept_submitted_captcha(session, "accepted", LIST)) is True
    assert calls[0][0] == "2074281792"
    page = page_with_identity()
    page.body = "Il documento non e' stato ancora prodotto"
    calls.clear()
    error = run(document_not_yet_produced_error(page, state_with_callback(calls), LIST))
    assert error.remote_id == "2074281792"
    assert error.richieste_url == LIST
    assert calls[0][0] == "2074281792"


def test_error_page_is_rejected_before_correlation_or_download(tmp_path):
    page = ScriptedPage(url=LIST, body="Il sistema non è in grado di soddisfare la richiesta")
    session = make_session(page)
    events = []
    session._gaia_emit_sister_telemetry = events.append
    session._raise_if_server_error = lambda: asyncio.sleep(0)

    async def should_not_download(*_args):
        pytest.fail("Error page must not be correlated")

    session._poll_correlated_request = should_not_download
    with pytest.raises(SisterServerError, match="controlli assenti"):
        run(poll_for_pdf(session, tmp_path / "out.pdf", LIST, 1, 0, True))
    assert events[-1].event_type == "recovery_navigation"
    assert events[-1].outcome == "error"
    page.locators["input[name='radioCount']"] = ScriptedLocator()
    run(validate_requests_page(page, None))


@pytest.mark.parametrize("table_markup", [False, True])
def test_real_html_form_is_bound_before_a_download_and_survives_restart(tmp_path, table_markup):
    async def scenario():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path=shutil.which("google-chrome"), headless=True
            )
            try:
                page = await browser.new_page()
                outer_open, row_open, row_close, outer_close = (
                    ("<table>", "<tr><td>", "</td></tr>", "</table>")
                    if table_markup
                    else ("", "", "", "")
                )
                await page.route(
                    "**/*",
                    lambda route: route.fulfill(
                        body=f'''<title>Documento pronto</title>{outer_open}
                  <form name="VisualizzaDocumentiFB" action="/Visure/ConsultazioneRichieste.do" method="post">{row_open}
                    <input type="hidden" name="idRichiesta" value="2074281792">
                    <input type="submit" name="metodo" value="Salva">{row_close}</form>{outer_close}
                  <input type="hidden" name="idRichiesta" value="ORPHAN">
                  <a href="{LIST}">Richieste</a>''',
                        content_type="text/html",
                    ),
                )
                await page.goto(BASE + "/Visure/CheckRichiesta.do")
                if table_markup:
                    assert await page.locator("form input[name='idRichiesta']").count() == 0
                    assert await page.locator("input[name='idRichiesta']").first.evaluate(
                        "node => node.form !== null"
                    )
                calls = []
                state = state_with_callback(calls)
                await capture_submission_identity(page, state, LIST)
                resumed = state_with_callback([], calls[0][0])
                assert await capture_submission_identity(page, resumed, LIST) == "2074281792"
            finally:
                await browser.close()

    run(scenario())


def test_legacy_list_fallback_is_repaired_without_changing_document_actions():
    page = ScriptedPage()
    legacy = LIST.replace("/Servizi/", "/Visure/")
    assert run(observed_requests_url(page, legacy)) == LIST
    document = BASE + "/Visure/ConsultazioneRichieste.do?idRichiesta=R1"
    assert run(observed_requests_url(page, document)) == document
    assert (
        run(
            observed_requests_url(
                page, "https://other/Visure/ConsultazioneRichieste.do?metodo=lista"
            )
        )
        == "https://other/Visure/ConsultazioneRichieste.do?metodo=lista"
    )
