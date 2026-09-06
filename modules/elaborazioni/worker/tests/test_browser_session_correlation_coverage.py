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
from browser_session import SISTER_REQUESTS_URL
from browser_test_support import ScriptedLocator, ScriptedPage, make_session, noop_async
from sister_exceptions import (
    DocumentNonEvadibileError,
    DocumentNotYetProducedError,
    SisterConventionSelectionError,
    SisterDocumentNotReadyError,
    SisterRequestCorrelationError,
)
from sister_request_rows import SisterRemoteRequestRow, SisterRequestCorrelation


def run(coro):
    return asyncio.run(coro)


async def async_value(value):
    return value


def row(**values) -> SisterRemoteRequestRow:
    defaults = {
        "index": 0,
        "key": "key",
        "remote_id": "remote",
        "state": "pending",
        "text": "row",
        "hrefs": (),
        "download_href": None,
        "delete_href": None,
    }
    defaults.update(values)
    return SisterRemoteRequestRow(**defaults)


def request(**values):
    defaults = {
        "id": "local",
        "subject_id": "RSSMRA80A01H501U",
        "comune": None,
        "foglio": None,
        "particella": None,
        "subalterno": None,
        "sister_remote_request_id": None,
        "sister_remote_state": None,
        "sister_remote_baseline_keys": None,
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def test_request_correlation_restore_new_snapshot_and_getter() -> None:
    session = make_session()
    active = request(
        sister_remote_request_id="remote",
        sister_remote_state="READY",
        sister_remote_baseline_keys=["a"],
    )
    run(session.begin_request_correlation(active))
    assert session.get_request_correlation().remote_id == "remote"

    active.sister_remote_request_id = None
    run(session.begin_request_correlation(active))
    assert session.get_request_correlation().remote_id is None

    session._snapshot_remote_request_rows = lambda: async_value([row()])
    run(session.begin_request_correlation(request()))
    assert session.get_request_correlation().baseline_keys == frozenset({"key"})


def test_capture_debug_snapshot_delegates(tmp_path: Path) -> None:
    session = make_session()
    session._write_artifacts_to_dir = lambda target, label: async_value([str(target / label)])
    assert run(session.capture_debug_snapshot(tmp_path / "nested", "label"))


def test_poll_requests_download_and_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(browser_module, "RICHIESTE_POLL_ATTEMPTS", 2)
    monkeypatch.setattr(browser_module.asyncio, "sleep", noop_async)
    session = make_session(ScriptedPage())
    session._raise_if_server_error = noop_async
    session._poll_body_upper = lambda: async_value("")
    session._poll_correlated_request = lambda *_args: async_value(10)
    assert run(session.poll_richieste_for_download(tmp_path / "out.pdf")) == 10

    session._poll_correlated_request = lambda *_args: async_value(None)
    with pytest.raises(browser_module.TimeoutError):
        run(session.poll_richieste_for_download(tmp_path / "out.pdf", "https://custom"))
    assert session.page.gotos[-1] == "https://custom"

    with pytest.raises(SisterDocumentNotReadyError, match="1 poll iniziali"):
        run(session.poll_richieste_for_download(tmp_path / "out.pdf", max_attempts=1))


def test_poll_body_and_correlated_dispatch() -> None:
    page = ScriptedPage(body="  mixed\nText ")
    session = make_session(page)
    assert run(session._poll_body_upper()) == " MIXED TEXT "
    page.body_error = RuntimeError("body")
    assert run(session._poll_body_upper()) == ""

    session._find_correlated_request_row = lambda: async_value(row(state="ready"))
    session._consume_correlated_row = lambda *_args: async_value(7)
    assert run(session._poll_correlated_request(Path("x"), "")) == 7
    session._consume_correlated_row = lambda *_args: async_value(None)
    session._poll_correlated_tabs = lambda *_args: async_value(8)
    assert run(session._poll_correlated_request(Path("x"), "")) == 8


def test_consume_correlated_row_states(tmp_path: Path) -> None:
    session = make_session()
    session._delete_non_evadibile_row = noop_async
    with pytest.raises(DocumentNonEvadibileError):
        run(session._consume_correlated_row(row(state="non_evadibile"), tmp_path / "x"))
    session._download_correlated_row = lambda *_args: async_value(12)
    assert run(session._consume_correlated_row(row(state="ready"), tmp_path / "x")) == 12
    assert run(session._consume_correlated_row(None, tmp_path / "x")) is None
    assert run(session._consume_correlated_row(row(state="pending"), tmp_path / "x")) is None


def test_poll_correlated_tabs_all_paths(tmp_path: Path) -> None:
    session = make_session()
    found = iter((row(state="pending"), row(state="ready")))
    session._find_correlated_row_in_tab = lambda _tab: async_value(next(found))
    session._consume_correlated_row = lambda *_args: async_value(5)
    assert run(session._poll_correlated_tabs("NON EVADIBILI 1", tmp_path / "x")) == 5

    session._consume_correlated_row = lambda *_args: async_value(None)
    session._download_correlated_row = lambda *_args: async_value(6)
    session._find_correlated_row_in_tab = lambda _tab: async_value(row(state="ready"))
    assert run(session._poll_correlated_tabs("NON EVADIBILI 1 ESPLETATE 1", tmp_path / "x")) == 6
    session._find_correlated_row_in_tab = lambda _tab: async_value(None)
    assert run(session._poll_correlated_tabs("ESPLETATE 1", tmp_path / "x")) is None
    assert run(session._poll_correlated_tabs("", tmp_path / "x")) is None


def test_find_correlated_row_requires_context_and_updates_remote_id(monkeypatch: pytest.MonkeyPatch) -> None:
    session = make_session()
    with pytest.raises(SisterRequestCorrelationError, match="non inizializzata"):
        run(session._find_correlated_request_row())
    session._session_state.correlation = SisterRequestCorrelation("local", frozenset(), ())
    with pytest.raises(SisterRequestCorrelationError, match="ID remoto certo"):
        run(session._find_correlated_request_row())
    correlation = SisterRequestCorrelation("local", frozenset(), (), remote_id="remote")
    session._session_state.correlation = correlation
    monkeypatch.setattr(session, "_extract_remote_request_rows", lambda _page: async_value([row()]))
    monkeypatch.setattr(browser_module, "correlate_remote_row", lambda *_args: row())
    assert run(session._find_correlated_request_row()).remote_id == "remote"
    assert session._session_state.correlation.remote_id == "remote"
    monkeypatch.setattr(browser_module, "correlate_remote_row", lambda *_args: row(remote_id=None))
    assert run(session._find_correlated_request_row()).remote_id is None


@pytest.mark.parametrize(("count", "visible", "expected"), [(0, True, None), (1, False, None), (1, True, "row")])
def test_find_correlated_row_in_tab(count: int, visible: bool, expected: str | None) -> None:
    page = ScriptedPage()
    session = make_session(page)
    page.locators["a:has-text('Tab'), td:has-text('Tab')"] = ScriptedLocator(count=count, visible=visible)
    session._find_correlated_request_row = lambda: async_value(row(text="row"))
    result = run(session._find_correlated_row_in_tab("Tab"))
    assert (result.text if result else None) == expected


def _table_row_locator(link: ScriptedLocator | None = None, action: ScriptedLocator | None = None) -> ScriptedLocator:
    table_row = ScriptedLocator()
    if link is not None:
        table_row.children["a[href*='CheckRichiesta'], a[href*='ConsultazioneRichieste']"] = link
    if action is not None:
        table_row.children["a:has-text('Elimina'), input[value*='Elimina'], button:has-text('Elimina')"] = action
    return table_row


def test_download_correlated_row_href_and_locator_paths(tmp_path: Path) -> None:
    page = ScriptedPage()
    session = make_session(page)
    session._first_visible_count = lambda _selector: async_value(1)
    session.download_pdf = lambda _path: async_value(10)
    assert run(session._download_correlated_row(row(state="ready", download_href="/download"), tmp_path / "x")) == 10

    link = ScriptedLocator()
    page.locators["table tr"] = _table_row_locator(link=link)
    assert run(session._download_correlated_row(row(state="ready"), tmp_path / "x")) == 10
    page.locators["table tr"] = _table_row_locator(link=ScriptedLocator(count=0))
    with pytest.raises(SisterRequestCorrelationError, match="download univoco"):
        run(session._download_correlated_row(row(state="ready"), tmp_path / "x"))
    session._first_visible_count = lambda _selector: async_value(0)
    with pytest.raises(SisterRequestCorrelationError, match="pulsante Salva"):
        run(session._download_correlated_row(row(state="ready", download_href="/download"), tmp_path / "x"))


def test_delete_non_evadibile_href_locator_confirm_and_guards() -> None:
    page = ScriptedPage()
    session = make_session(page)
    confirm_selector = "input[value='Conferma'], button:has-text('Conferma')"
    page.locators[confirm_selector] = ScriptedLocator()
    session._find_correlated_request_row = lambda: async_value(None)
    run(session._delete_non_evadibile_row(row(delete_href="/delete")))

    page.locators[confirm_selector] = ScriptedLocator(visible=False)
    page.locators["table tr"] = _table_row_locator(action=ScriptedLocator())
    run(session._delete_non_evadibile_row(row()))
    page.locators["table tr"] = _table_row_locator(action=ScriptedLocator(count=0))
    with pytest.raises(SisterRequestCorrelationError, match="espone Elimina"):
        run(session._delete_non_evadibile_row(row()))

    session._find_correlated_request_row = lambda: async_value(row())
    with pytest.raises(SisterRequestCorrelationError, match="confermato"):
        run(session._delete_non_evadibile_row(row(delete_href="/delete")))


class SnapshotContext:
    def __init__(self, page: ScriptedPage) -> None:
        self.page = page

    async def new_page(self) -> ScriptedPage:
        return self.page


def test_snapshot_and_row_extraction(monkeypatch: pytest.MonkeyPatch) -> None:
    session = make_session()
    assert run(session._snapshot_remote_request_rows()) == []
    snapshot = ScriptedPage()
    snapshot.locators["table tr"] = ScriptedLocator(
        payload=[{"text": "ready", "hrefs": ["?idRichiesta=1"], "values": []}]
    )
    session._context = SnapshotContext(snapshot)
    monkeypatch.setattr(browser_module, "raise_if_sister_server_error", noop_async)
    assert run(session._snapshot_remote_request_rows()) == []
    assert not snapshot.closed
    assert run(session._extract_remote_request_rows(snapshot))[0].remote_id == "1"

    async def fail(*_args):
        raise RuntimeError("snapshot")

    monkeypatch.setattr(browser_module, "raise_if_sister_server_error", fail)
    assert run(session._snapshot_remote_request_rows()) == []
    assert not snapshot.closed


def test_url_and_error_delegation(monkeypatch: pytest.MonkeyPatch) -> None:
    session = make_session()
    assert session._absolute_sister_url("https://host/x") == "https://host/x"
    assert session._absolute_sister_url("/x").endswith("/x")
    assert session._absolute_sister_url("x").endswith("/x")
    called: list[str] = []

    async def server(*_args):
        called.append("server")

    monkeypatch.setattr(browser_module, "raise_if_sister_server_error", server)
    run(session._raise_if_server_error())

    monkeypatch.setattr(browser_module, "document_not_yet_produced_error", lambda *_args: async_value(None))
    run(session._raise_if_document_not_yet_produced())
    error = DocumentNotYetProducedError()
    monkeypatch.setattr(browser_module, "document_not_yet_produced_error", lambda *_args: async_value(error))
    with pytest.raises(DocumentNotYetProducedError):
        run(session._raise_if_document_not_yet_produced())
    assert called == ["server"]


def test_menu_navigation_and_convention_absence() -> None:
    page = ScriptedPage()
    session = make_session(page)
    page.roles[("link", session.selectors.consultazioni_link_name)] = ScriptedLocator()
    page.roles[("link", session.selectors.visure_link_name)] = ScriptedLocator()
    session._confirm_visura_informativa_if_present = noop_async
    session._select_convention_if_present = lambda: async_value(False)
    run(session._goto_visura_menu())
    assert run(make_session(ScriptedPage())._select_convention_if_present()) is False


def test_convention_missing_target_and_label() -> None:
    page = ScriptedPage()
    session = make_session(page)
    page.locators[session.selectors.convention_radio_selector] = ScriptedLocator()
    target_selector = f"{session.selectors.convention_radio_selector}[value='{session.selectors.convention_id}']"
    page.locators[target_selector] = ScriptedLocator(count=0)
    with pytest.raises(SisterConventionSelectionError, match="non disponibile"):
        run(session._select_convention_if_present())
    page.locators[target_selector] = ScriptedLocator()
    with pytest.raises(SisterConventionSelectionError, match="mancante"):
        run(session._select_convention_if_present())


def test_informativa_and_visura_area_delegate(monkeypatch: pytest.MonkeyPatch) -> None:
    page = ScriptedPage()
    session = make_session(page)
    assert run(session._confirm_visura_informativa_if_present()) is None
    page.url = "Informativa.do"
    session._click_first_visible = noop_async
    run(session._confirm_visura_informativa_if_present())
    monkeypatch.setattr(browser_module, "is_visura_area_ready", lambda *_args: async_value(True))
    assert run(session._is_visura_area_ready()) is True


def test_menu_retry_success_issue_and_exhaustion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(browser_module.asyncio, "sleep", noop_async)
    session = make_session()
    session._raise_if_server_error = noop_async
    calls = iter((browser_module.TimeoutError("x"), None))

    async def retry_once():
        value = next(calls)
        if value:
            raise value

    session._goto_visura_menu = retry_once
    session._read_page_state = lambda: async_value(("url", "title", "body"))
    session._collect_debug_context = lambda *_args: async_value("debug")
    run(session._goto_visura_menu_with_retry())

    monkeypatch.setattr(browser_module, "MENU_NAVIGATION_RETRIES", 0)
    run(session._goto_visura_menu_with_retry())
    monkeypatch.setattr(browser_module, "MENU_NAVIGATION_RETRIES", 3)

    session._goto_visura_menu = lambda: _raise_async(browser_module.TimeoutError("x"))
    session._read_page_state = lambda: async_value(("url", "title", "credenziali errate"))
    with pytest.raises(RuntimeError, match="Credenziali"):
        run(session._goto_visura_menu_with_retry())
    session._read_page_state = lambda: async_value(("url", "title", "body"))
    with pytest.raises(browser_module.TimeoutError):
        run(session._goto_visura_menu_with_retry())


async def _raise_async(exc: Exception):
    raise exc


def test_click_and_visibility_helpers() -> None:
    page = ScriptedPage()
    session = make_session(page)
    page.locators["xpath=//x"] = ScriptedLocator()
    run(session._maybe_click_xpath("//x"))
    run(session._maybe_click_xpath("//missing"))
    page.roles[("button", "Text")] = ScriptedLocator()
    run(session._maybe_click_text("Text"))
    run(session._maybe_click_text("Missing"))

    page.locators["missing"] = ScriptedLocator(count=0)
    page.locators["hidden"] = ScriptedLocator(visible=False)
    page.locators["ok"] = ScriptedLocator()
    run(session._click_first_visible(["missing", "hidden", "ok"]))
    with pytest.raises(browser_module.TimeoutError):
        run(session._click_first_visible(["missing", "hidden"]))
    page.locators["broken"] = ScriptedLocator()
    page.locators["broken"].error = RuntimeError("broken")
    with pytest.raises(RuntimeError, match="broken"):
        run(session._click_first_visible(["broken"]))
    assert run(session._first_visible_count("missing")) == 0
    assert run(session._first_visible_count("hidden")) == 0
    assert run(session._first_visible_count("ok")) == 1
    assert run(session._first_visible_count("broken")) == 0


def test_subject_identifier_and_request_type_helpers() -> None:
    session = make_session(ScriptedPage())
    with pytest.raises(RuntimeError, match="mancante"):
        run(session._fill_subject_identifier(""))
    radio_selector = "input[name='selDatiAna'][value='CF_PF']"
    session.page.locators[radio_selector] = ScriptedLocator()
    captcha = ScriptedLocator()
    captcha.attrs = {"name": "captcha"}
    hidden = ScriptedLocator(visible=False)
    hidden.attrs = {"name": "cf"}
    valid = ScriptedLocator()
    valid.attrs = {"name": "codiceFiscale"}
    candidates = ["input[name*='cod' i][name*='fisc' i]", "input[id*='cod' i][id*='fisc' i]", "input[name*='codice' i][name*='fisc' i]"]
    session.page.locators[candidates[0]] = captcha
    session.page.locators[candidates[1]] = hidden
    session.page.locators[candidates[2]] = valid
    run(session._fill_subject_identifier(" abc "))
    assert valid.fills == ["ABC"]
    session.page.locators.clear()
    with pytest.raises(RuntimeError, match="non trovato"):
        run(session._fill_subject_identifier("ABC"))

def test_privacy_recovery_close_session_and_section(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(browser_module.asyncio, "sleep", noop_async)
    page = ScriptedPage(body="Informativa trattamento dei dati personali")
    session = make_session(page)
    page.roles[("button", "Conferma")] = ScriptedLocator(count=0)
    fallback = "input[type='submit'][value='Conferma'], button:has-text('Conferma')"
    page.locators[fallback] = ScriptedLocator()
    run(session._maybe_accept_privacy_notice())
    page.roles[("button", "Conferma")] = ScriptedLocator()
    run(session._maybe_accept_privacy_notice())
    page.body_error = RuntimeError("body")
    run(session._maybe_accept_privacy_notice())

    session.logout = noop_async
    session.stop = noop_async
    session.start = noop_async
    run(session._recover_locked_session())
    assert page.gotos[-1] == session.selectors.login_url

    selector = "a[href*='CloseSessionsSis']:has-text('Chiudi')"
    page.locators[selector] = ScriptedLocator(count=0)
    assert run(session._click_close_sessions_link()) is False
    parent = ScriptedLocator(count=2)
    parent.items = [ScriptedLocator(visible=False), ScriptedLocator(text="Esci")]
    page.locators[selector] = parent
    assert run(session._click_close_sessions_link()) is False
    parent.items[1] = ScriptedLocator(text="Chiudi")
    assert run(session._click_close_sessions_link()) is True

    page.evaluate_results = [2, 1, 1]
    run(session._ensure_sezione_options_loaded("id"))
    page.locators["input[name='selSezione']"] = ScriptedLocator(count=0)
    run(session._ensure_sezione_options_loaded("id"))
    page.locators["input[name='selSezione']"] = ScriptedLocator()
    run(session._ensure_sezione_options_loaded("id"))


def test_bounding_boxes_and_tipo_values() -> None:
    page = ScriptedPage()
    session = make_session(page)
    page.locators["missing"] = ScriptedLocator(count=0)
    page.locators["broken"] = ScriptedLocator()
    page.locators["broken"].error = RuntimeError("box")
    page.locators["empty"] = ScriptedLocator()
    page.locators["box"] = ScriptedLocator()
    page.locators["box"].box = {"x": 1.0, "y": 2.0, "width": 3.0, "height": 4.0}
    assert run(session._first_visible_bounding_box(["missing", "broken", "empty", "box"])) is not None
    assert run(session._first_visible_bounding_box(["missing"])) is None
    assert session.tipo_visura_value("Sintetica") == "4"
    assert session.tipo_visura_value("Analitica") == "3"
    assert session.tipo_visura_value("Completa") == "0"
