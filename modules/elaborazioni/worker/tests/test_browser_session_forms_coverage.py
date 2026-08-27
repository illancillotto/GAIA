from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


WORKER_ROOT = Path(__file__).resolve().parents[1]
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

import browser_session as browser_module
from browser_test_support import ScriptedLocator, ScriptedPage, make_session, noop_async
from sister_exceptions import SisterNotFoundError


def run(coro):
    return asyncio.run(coro)


def request(**values):
    defaults = {
        "id": "request-1",
        "comune": "ORISTANO",
        "comune_codice": "G113",
        "catasto": "Terreni",
        "sezione": None,
        "foglio": "1",
        "particella": "2",
        "subalterno": None,
        "tipo_visura": "Sintetica",
        "request_type": "ATTUALITA",
        "subject_kind": "PF",
        "subject_id": "RSSMRA80A01H501U",
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def _prepare_form_session(page: ScriptedPage):
    session = make_session(page)
    session._prepare_visura_form_area = noop_async
    page.locators[session.selectors.catasto_selector] = ScriptedLocator()
    return session


def test_open_visura_form_with_and_without_optional_navigation() -> None:
    page = ScriptedPage()
    session = _prepare_form_session(page)
    page.locators[session.selectors.territorio_selector] = ScriptedLocator()
    page.roles[("button", session.selectors.territorio_apply_button_name)] = ScriptedLocator()
    page.roles[("link", session.selectors.immobile_link_name)] = ScriptedLocator()
    run(session.open_visura_form())
    assert page.selects and page.roles[("link", session.selectors.immobile_link_name)].clicks == 1

    page = ScriptedPage()
    session = _prepare_form_session(page)
    run(session.open_visura_form())


@pytest.mark.parametrize(
    ("kind", "has_link", "has_territory"),
    [("PF", True, True), ("PNF", False, True), ("PF", True, False)],
)
def test_open_subject_form_paths(kind: str, has_link: bool, has_territory: bool) -> None:
    page = ScriptedPage()
    session = _prepare_form_session(page)
    if has_territory:
        page.locators[session.selectors.territorio_selector] = ScriptedLocator()
        page.roles[("button", session.selectors.territorio_apply_button_name)] = ScriptedLocator()
    link_name = session.selectors.subject_pf_link_name if kind == "PF" else session.selectors.subject_pnf_link_name
    page.roles[("link", link_name)] = ScriptedLocator(count=1 if has_link else 0)
    run(session.open_subject_form(kind))
    assert bool(page.gotos) is not has_link


@pytest.mark.parametrize(
    ("section_mode", "subalterno", "tipo_visible"),
    [("select", "3", True), ("input", None, False), ("missing", None, False), ("none", None, False)],
)
def test_fill_visura_form_optional_fields(
    section_mode: str,
    subalterno: str | None,
    tipo_visible: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = ScriptedPage()
    session = make_session(page)
    monkeypatch.setattr(browser_module, "select_request_type", noop_async)
    session._ensure_sezione_options_loaded = noop_async
    session._wait_for_visura_submission_state = noop_async
    session._first_visible_count = lambda _selector: _async_value(1 if tipo_visible else 0)
    if section_mode == "select":
        page.locators[session.selectors.sezione_select_selector] = ScriptedLocator()
    elif section_mode == "input":
        page.locators[session.selectors.sezione_input_selector] = ScriptedLocator()
    row = request(sezione="A" if section_mode != "none" else None, subalterno=subalterno)
    tipo_selector = f"{session.selectors.tipo_visura_selector}[value='4']"
    if tipo_visible:
        page.locators[tipo_selector] = ScriptedLocator()
    run(session.fill_visura_form(row))
    assert (session.selectors.foglio_selector, "1") in page.fills
    assert bool(page.locators.get(tipo_selector) and page.locators[tipo_selector].checks) is tipo_visible


def test_fill_historical_immobile_uses_post_submit_visura_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = ScriptedPage()
    session = make_session(page)
    session._wait_for_visura_submission_state = noop_async
    historical_selector = f"{session.selectors.tipo_visura_selector}[value='3']"
    page.locators[historical_selector] = ScriptedLocator()

    async def reject_early_request_type_selection(*_args, **_kwargs) -> None:
        raise AssertionError("immobile form has no separate request-type radio")

    monkeypatch.setattr(browser_module, "select_request_type", reject_early_request_type_selection)

    run(
        session.fill_visura_form(
            request(tipo_visura="Analitica", request_type="STORICA"),
        )
    )

    assert page.locators[historical_selector].checks == 1
    assert session._pending_visura_type == ("Analitica", "3")


async def _async_value(value):
    return value


@pytest.mark.parametrize(
    ("section_mode", "subalterno"),
    [("select", "3"), ("input", None), ("missing", None), ("none", None)],
)
def test_search_immobile_status_form_variants(section_mode: str, subalterno: str | None) -> None:
    page = ScriptedPage()
    session = make_session(page)
    session._ensure_sezione_options_loaded = noop_async
    session._read_immobile_status_payload = lambda: _async_value({"classification": "current"})
    if section_mode == "select":
        page.locators[session.selectors.sezione_select_selector] = ScriptedLocator()
    elif section_mode == "input":
        page.locators[session.selectors.sezione_input_selector] = ScriptedLocator()
    row = request(sezione="A" if section_mode != "none" else None, subalterno=subalterno)
    assert run(session.search_immobile_status(row))["classification"] == "current"


def test_fill_and_search_subject_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    page = ScriptedPage()
    session = make_session(page)
    monkeypatch.setattr(browser_module, "select_request_type", noop_async)
    session._fill_subject_identifier = noop_async
    run(session.fill_subject_form(request()))
    assert page.selects

    session._click_first_visible = noop_async
    session.detect_subject_not_found_message = lambda *_args: _async_value("not found")
    assert run(session.search_subject_and_open_visura(request())) == "not found"

    result = ScriptedLocator()
    page.locators["custom-result"] = result
    session.selectors = replace(
        session.selectors,
        subject_result_selector_candidates=["custom-result"],
        subject_open_visura_button_selectors=["custom-open"],
    )
    session.detect_subject_not_found_message = lambda *_args: _async_value(None)
    run(session.search_subject_and_open_visura(request()))
    assert result.checks == 1

    class CheckFails(ScriptedLocator):
        async def check(self, timeout: int | None = None) -> None:
            raise RuntimeError("check")

    page.locators["custom-result"] = CheckFails()
    run(session.search_subject_and_open_visura(request()))

    session.selectors = replace(session.selectors, subject_result_selector_candidates=["hidden", "custom-result"])
    page.locators["hidden"] = ScriptedLocator(visible=False)
    page.locators["custom-result"] = ScriptedLocator()
    run(session.search_subject_and_open_visura(request()))

    session.selectors = replace(session.selectors, subject_result_selector_candidates=["missing"])
    run(session.search_subject_and_open_visura(request()))


def test_subject_not_found_detection_success_empty_and_read_error() -> None:
    page = ScriptedPage(body="NESSUNA CORRISPONDENZA TROVATA")
    session = make_session(page)
    message = run(session.detect_subject_not_found_message("PF", "ABC"))
    assert "PF 'ABC'" in message
    page.body = "risultato"
    assert run(session.detect_subject_not_found_message(None, None)) is None
    page.body_error = RuntimeError("body")
    assert run(session.detect_subject_not_found_message(None, None)) is None


def test_subject_not_found_preview_all_outcomes(tmp_path: Path) -> None:
    session = make_session(ScriptedPage())
    boxes = iter((None, {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}))
    session._first_visible_bounding_box = lambda _selectors: _async_value(next(boxes))
    assert run(session.capture_subject_not_found_preview(tmp_path)) is None

    top = {"x": 20.0, "y": 30.0, "width": 200.0, "height": 20.0}
    bottom = {"x": 10.0, "y": 100.0, "width": 300.0, "height": 30.0}
    boxes = iter((top, bottom))
    session._first_visible_bounding_box = lambda _selectors: _async_value(next(boxes))
    session.page.evaluate_results = [{"width": 500, "height": 400}]
    preview = run(session.capture_subject_not_found_preview(tmp_path))
    assert preview and Path(preview).exists()

    boxes = iter((top, bottom))
    session._first_visible_bounding_box = lambda _selectors: _async_value(next(boxes))
    session.page.evaluate_error = RuntimeError("size")
    assert run(session.capture_subject_not_found_preview(tmp_path, "broken")) is None


@pytest.mark.parametrize(
    ("body", "classification"),
    [
        ("SOPPRESSO il 01/02/2020 Immobili individuati: 1", "suppressed"),
        ("Immobili individuati: 0", "not_found"),
        ("ELENCO IMMOBILI", "current"),
        ("Immobili individuati: 2", "current"),
        ("testo non classificato", "unknown"),
    ],
)
def test_immobile_status_payload_text_classifications(body: str, classification: str) -> None:
    page = ScriptedPage(body=body)
    session = make_session(page)
    assert run(session._read_immobile_status_payload())["classification"] == classification


def test_immobile_status_payload_blocked_type_and_body_fallback() -> None:
    page = ScriptedPage(body="credenziali errate")
    session = make_session(page)
    assert run(session._read_immobile_status_payload())["classification"] == "blocked"

    page.body = ""
    page.locators[session.selectors.tipo_visura_selector] = ScriptedLocator()
    assert run(session._read_immobile_status_payload())["classification"] == "current"

    page.locators.clear()
    page.body_error = RuntimeError("body")
    session._read_page_state = lambda: _async_value(("url", "title", "fallback"))
    assert run(session._read_immobile_status_payload())["classification"] == "unknown"


def test_submission_wait_immediate_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(browser_module.asyncio, "sleep", noop_async)
    session = make_session()
    session._raise_if_server_error = noop_async
    session._raise_if_document_not_yet_produced = noop_async
    session._raise_unadvanced_visura_submission = noop_async
    for selector in (
        session.selectors.tipo_visura_selector,
        session.selectors.captcha_image_selector,
        session.selectors.save_button_selector,
    ):
        session._first_visible_count = lambda current, target=selector: _async_value(int(current == target))
        run(session._wait_for_visura_submission_state("id"))
    session._first_visible_count = lambda _selector: _async_value(0)
    run(session._wait_for_visura_submission_state("id"))


def test_unadvanced_submission_and_extract_helpers() -> None:
    session = make_session()
    session._read_immobile_status_payload = lambda: _async_value({"classification": "not_found", "message": "none"})
    with pytest.raises(SisterNotFoundError):
        run(session._raise_unadvanced_visura_submission("id"))
    session._read_immobile_status_payload = lambda: _async_value({})
    with pytest.raises(RuntimeError, match="unknown"):
        run(session._raise_unadvanced_visura_submission("id"))
    assert session._extract_immobili_count("Immobili individuati: 12") == 12
    assert session._extract_immobili_count("none") is None
    assert session._extract_suppressed_date("none") is None
    assert session._extract_suppressed_date("01/02/2020 SOPPRESSO") == "01/02/2020"
    assert session._extract_suppressed_date("SOPPRESSO senza data") is None


def test_captcha_reload_capture_and_prepare(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(browser_module.asyncio, "sleep", noop_async)
    page = ScriptedPage()
    session = make_session(page)
    page.locators[session.selectors.captcha_image_selector] = ScriptedLocator(payload=b"captcha")
    run(session.reload_captcha())
    assert run(session.capture_captcha_image()) == b"captcha"
    page.evaluate_error = RuntimeError("reload")
    run(session.reload_captcha())

    session._first_visible_count = lambda selector: _async_value(int(selector == session.selectors.save_button_selector))
    assert run(session.prepare_captcha_or_download()) == "download"
    session._first_visible_count = lambda selector: _async_value(int(selector == session.selectors.captcha_image_selector))
    assert run(session.prepare_captcha_or_download()) == "captcha"


def test_prepare_captcha_loop_results_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(browser_module.asyncio, "sleep", noop_async)
    page = ScriptedPage()
    session = make_session(page)
    page.locators[session.selectors.inoltra_button_selector] = ScriptedLocator()
    calls = iter((0, 0, 1))
    session._first_visible_count = lambda _selector: _async_value(next(calls, 0))
    assert run(session.prepare_captcha_or_download()) == "download"

    calls = iter((0, 0, 0, 1))
    session._first_visible_count = lambda _selector: _async_value(next(calls, 0))
    assert run(session.prepare_captcha_or_download()) == "captcha"

    page.locators[session.selectors.inoltra_button_selector] = ScriptedLocator(count=0)
    calls = iter((0, 0, 1))
    session._first_visible_count = lambda _selector: _async_value(next(calls, 0))
    assert run(session.prepare_captcha_or_download()) == "download"

    session._first_visible_count = lambda _selector: _async_value(0)
    session._raise_if_server_error = noop_async
    session._raise_if_document_not_yet_produced = noop_async
    with pytest.raises(browser_module.TimeoutError):
        run(session.prepare_captcha_or_download())


def test_submit_and_resolve_captcha_paths() -> None:
    page = ScriptedPage()
    session = make_session(page)
    session._resolve_captcha_submission = lambda: _async_value(True)
    session.begin_remote_submission(lambda *_args: None)
    assert run(session.submit_captcha("ABCDE")) is True
    assert session._session_state.submission_callback is None

    session._mark_remote_submitted = lambda _value: None
    assert session._accept_submitted_captcha("ok") is True
    session._resolve_captcha_submission = BrowserSessionResolve(session)
    page.wait_selector_error = None
    assert run(session._resolve_captcha_submission()) is True

    page.wait_selector_error = browser_module.TimeoutError("timeout")
    page.locators[session.selectors.save_button_selector] = ScriptedLocator()
    assert run(session._resolve_captcha_submission()) is True
    page.locators.clear()
    session._raise_if_server_error = noop_async
    session._raise_if_document_not_yet_produced = noop_async
    assert run(session._resolve_captcha_submission()) is False


def BrowserSessionResolve(session):
    return browser_module.BrowserSession._resolve_captcha_submission.__get__(session)


def test_response_and_submission_delegation() -> None:
    session = make_session()
    tracked: list[object] = []
    session._session_state = SimpleNamespace(
        track_response=lambda response, url: tracked.append((response, url)),
        mark_submitted=lambda remote_id, url: tracked.append((remote_id, url)),
    )
    session._track_response("response")
    session._mark_remote_submitted("remote")
    assert len(tracked) == 2
