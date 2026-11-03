from __future__ import annotations

import asyncio
import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

import posta_online_dispatch as dispatch
from app.modules.ruolo.services.poste_dispatch_work import WorkItem

LABEL = "VIA CAGLIARI 170, ORISTANO (OR), 09170"
MANUAL = "INSERISCI L'INDIRIZZO MANUALMENTE"


def run(coro):
    return asyncio.run(coro)


class Locator:
    def __init__(self, page, selector, state):
        self.page, self.selector = page, selector
        self.count_value = state.get("count", 1)
        self.visible = state.get("visible", True)
        self.text, self.texts = state.get("text", ""), list(state.get("texts", ()))
        self.value = state.get("value", "")
        self.href = state.get("href")

    async def count(self):
        return self.count_value

    async def is_visible(self):
        return self.visible

    async def inner_text(self):
        return self.text

    async def all_inner_texts(self):
        return self.texts

    async def input_value(self):
        return self.value

    async def get_attribute(self, name):
        assert name == "href"
        return self.href

    def nth(self, index):
        return Locator(self.page, f"{self.selector}[{index}]", {})

    def __getattr__(self, action):
        async def record(*args, **_kwargs):
            if self.selector in self.page.fail_on:
                raise RuntimeError(f"{action} failed on {self.selector}")
            self.page.log.append(
                (action, self.selector, *[arg for arg in args if not isinstance(arg, int)])
            )
            if action == "press_sequentially" and self.selector == "#raccomandataarlocalita":
                self.page.locators["ul.ui-autocomplete:visible li"] = {
                    "texts": self.page.city_options
                }

        return record


class Page:
    def __init__(self, pages=(), next_hrefs=(), **locators):
        self.pages, self.log, self.fail_on, self.url_error = list(pages), [], set(), None
        self.locators = locators
        self.city_options = ["ORISTANO (OR)"]
        self.next_hrefs, self.goto_waits = list(next_hrefs), []

    def locator(self, selector):
        if selector == 'ul.pagination a[aria-label="Next"]' and self.next_hrefs:
            href = self.next_hrefs[min(len(self.goto_waits) - 1, len(self.next_hrefs) - 1)]
            return Locator(self, selector, {"count": 1, "href": href})
        if selector == 'ul.pagination a[aria-label="Next"]':
            return Locator(self, selector, {"count": 0})
        default = {"visible": False} if selector == "#alertCookie-confirm" else {}
        return Locator(self, selector, self.locators.get(selector, default))

    async def goto(self, url, **_kwargs):
        self.log.append(("goto", url))
        self.goto_waits.append(_kwargs.get("wait_until"))

    async def content(self):
        return self.pages.pop(0) if self.pages else ""

    async def evaluate(self, script, value):
        self.log.append(("evaluate", script, value))

    async def wait_for_load_state(self, *_args, **_kwargs):
        return None

    async def wait_for_timeout(self, _ms):
        return None

    async def wait_for_url(self, *_args, **_kwargs):
        if self.url_error:
            raise self.url_error


class DocumentLocator(Locator):
    """Model the new-shipment reset and the bytes retained by the upload control."""

    async def click(self):
        await super().__getattr__("click")()
        self.page.documents = []

    async def set_input_files(self, filename):
        await super().__getattr__("set_input_files")(filename)
        path = Path(filename)
        self.page.documents.append({
            "slot": "file0", "name": path.name, "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })


class DocumentPage(Page):
    """Document lifecycle is independent of the paginated list page test double."""

    def __init__(self, **locators):
        super().__init__(**locators)
        self.documents = []

    def locator(self, selector):
        if selector in ("#crea_spedizione", "#file"):
            return DocumentLocator(self, selector, self.locators.get(selector, {}))
        return super().locator(selector)

    async def evaluate(self, script):
        assert script == dispatch._DOCUMENT_STATE
        return {"files": self.documents, "cards": [f["name"] for f in self.documents],
                "queued": len(self.documents), "count": len(self.documents), "text": ""}

    @asynccontextmanager
    async def expect_navigation(self, **kwargs):
        assert kwargs == {"wait_until": "load"}
        yield


class Response:
    def __init__(self, status=200, payload=None):
        self.status, self.payload = status, payload

    async def json(self):
        return self.payload


class Client:
    def __init__(self, page, response=None, next_pages=0):
        self.page, self.next_pages, self.routes, self.posts = page, next_pages, [], []
        self.throttle = SimpleNamespace(wait=self._wait)
        request = SimpleNamespace(post=self._post)
        self.response = response or Response(payload=[])
        self.context = SimpleNamespace(route=self._route, request=request)

    async def _wait(self, _label):
        return None

    async def _route(self, pattern, handler):
        self.routes.append((pattern, handler))

    async def _post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return self.response

    async def _prepare_login_page(self, _page):
        return None

    async def _goto_next_archive_page(self, _page):
        self.next_pages -= 1
        return self.next_pages >= 0


class Route:
    def __init__(self, method, url, body=b""):
        self.request = SimpleNamespace(method=method, url=url, post_data_buffer=body)
        self.outcome = None

    async def abort(self):
        self.outcome = "abort"

    async def continue_(self):
        self.outcome = "continue"


def _item(mode="directory"):
    recipient = {
        "name": "ROSSI MARIO",
        "name_extra": "",
        "address": "VIA CAGLIARI 170",
        "cap": "09170",
        "city": "ORISTANO",
        "province": "OR",
    }
    address = {"mode": "directory", "label": LABEL} if mode == "directory" else {"mode": "manual"}
    return WorkItem(uuid4(), "GAIA 020217801062586", "address_ok", recipient, address, None)


def _form_page(**locators):
    defaults = {
        "a[onclick*=\"registraForm('raccomandataar')\"]": {"count": 0},
        "#raccomandataarSummary": {"text": " 1 "},
        "#raccomandataarprovincia": {"value": "OR", "visible": False},
        ".has-error": {"count": 0},
        "ul.ui-autocomplete:visible li": {
            "texts": ["VIA ORISTANO 170, CAGLIARI (CA), 09127", LABEL, MANUAL]
        },
    }
    return DocumentPage(**(defaults | locators))


def test_guard_blocks_invia_and_lets_reads_through():
    portal = dispatch.PostaOnlineDispatchPortal(Client(Page()))
    run(portal.install_guard())
    assert portal.client.routes[0][0] == "**/*"
    portal.phase = "draft"
    invia = Route("POST", "https://corrispondenza.poste.it/col/inserisciInvii.do", b"\xd3")
    run(portal._guard(invia))
    read = Route("GET", "https://corrispondenza.poste.it/col/incorso.do")
    run(portal._guard(read))
    other = Route("POST", "https://cdn.example.test/collect", b"x")
    run(portal._guard(other))
    assert (invia.outcome, read.outcome, other.outcome) == ("abort", "continue", "continue")
    assert portal.blocked == [{"phase": "draft", "method": "POST", "url": invia.request.url}]


def test_directory_suggestions_use_the_portal_endpoint():
    page = Page()
    client = Client(page, Response(payload=[{"street": "VIA CAGLIARI"}, "noise"]))
    portal = dispatch.PostaOnlineDispatchPortal(client)
    run(portal.open_send_form())
    assert page.log == [("goto", dispatch.POSTA_ONLINE_SEND_HOME_URL)]
    assert run(portal.suggestions("VIA CAGLIARI, 170 ORISTANO")) == [{"street": "VIA CAGLIARI"}]
    url, kwargs = client.posts[0]
    assert url.endswith("/col/autocomplete.do") and kwargs["form"] == {
        "street": "VIA CAGLIARI 170 ORISTANO"
    }
    client.response = Response(payload={"error": True})
    assert run(portal.suggestions("VIA ROMA 1")) == []
    client.response = Response(status=500)
    with pytest.raises(RuntimeError, match="HTTP 500"):
        run(portal.suggestions("VIA ROMA 1"))


def test_lists_read_every_page():
    from tests.test_posta_online_dispatch_portal import ARCHIVE_PAGE, REAL_DRAFT_PAGE

    portal = dispatch.PostaOnlineDispatchPortal(
        Client(Page([REAL_DRAFT_PAGE, REAL_DRAFT_PAGE], next_hrefs=["?page=2", None]))
    )
    assert [row.draft_id for row in run(portal.list_drafts())] == ["12269236", "12269236"]
    portal = dispatch.PostaOnlineDispatchPortal(Client(Page([ARCHIVE_PAGE]), next_pages=0))
    assert run(portal.archive_index()) == ({"GAIA 020217801062586": ["11280322"]}, True)


def test_overlong_lists_are_reported_as_incomplete(monkeypatch):
    monkeypatch.setattr(dispatch, "MAX_LIST_PAGES", 2)
    portal = dispatch.PostaOnlineDispatchPortal(
        Client(Page(next_hrefs=[f"?page={i}" for i in range(2, 8)]))
    )
    assert run(portal.archive_index()) == ({}, False)
    portal = dispatch.PostaOnlineDispatchPortal(
        Client(Page(next_hrefs=[f"?page={i}" for i in range(2, 8)]))
    )
    with pytest.raises(RuntimeError, match="troppe pagine"):
        run(portal.list_drafts())


def test_list_navigation_uses_committed_pages_and_requires_the_table():
    page = Page(next_hrefs=["?page=2", None])
    portal = dispatch.PostaOnlineDispatchPortal(Client(page))
    run(portal.list_drafts())
    assert page.goto_waits == ["commit", "commit"]
    assert ("goto", dispatch.POSTA_ONLINE_DRAFTS_URL + "?page=2") in page.log
    assert [entry[:2] for entry in page.log].count(("wait_for", "#col_invio_dett")) == 2
    assert not any(entry[0] == "click" for entry in page.log)


def test_missing_list_table_never_reports_an_empty_complete_list():
    page = Page()
    page.fail_on.add("#col_invio_dett")
    with pytest.raises(RuntimeError, match="wait_for failed"):
        run(dispatch.PostaOnlineDispatchPortal(Client(page)).list_drafts())


@pytest.mark.parametrize("target", ["https://other.test/col/incorso.do", "/col/inserisciInvii.do", "http://corrispondenza.poste.it/col/incorso.do"])
def test_pagination_cannot_leave_the_requested_list(target):
    page = Page(next_hrefs=[target])
    with pytest.raises(RuntimeError, match="fuori dall'elenco"):
        run(dispatch.PostaOnlineDispatchPortal(Client(page)).list_drafts())
    assert len(page.goto_waits) == 1


def test_repeated_pagination_is_an_error_not_a_complete_snapshot():
    page = Page(next_hrefs=[dispatch.POSTA_ONLINE_DRAFTS_URL])
    with pytest.raises(RuntimeError, match="ripetuta"):
        run(dispatch.PostaOnlineDispatchPortal(Client(page)).list_drafts())


def test_lists_can_read_all_thirty_pages_of_a_campaign_account():
    page = Page(next_hrefs=[*[f"?page={i}" for i in range(2, 31)], None])
    run(dispatch.PostaOnlineDispatchPortal(Client(page)).list_drafts())
    assert len(page.goto_waits) == 30


def test_a_pending_draft_without_id_cannot_be_deleted():
    page = Page()
    with pytest.raises(RuntimeError, match="attendere l'identificativo"):
        run(dispatch.PostaOnlineDispatchPortal(Client(page)).delete_draft(None))
    assert page.log == []


def test_delete_uses_the_row_action_of_that_draft_only():
    page = Page(**{"input[name='invioCheck'][id='12269236']": {"count": 1}})
    portal = dispatch.PostaOnlineDispatchPortal(Client(page))
    portal.phase = "reconcile"
    run(portal.delete_draft("12269236"))
    assert ("evaluate", "draftId => DeleteInvio(draftId)", "12269236") in page.log
    assert portal.phase == "reconcile"
    page.locators["input[name='invioCheck'][id='12269236']"] = {"count": 0}
    with pytest.raises(RuntimeError, match="non presente"):
        run(portal.delete_draft("12269236"))


def test_create_draft_fills_one_ar_recipient_and_presses_continua_once():
    page = _form_page()
    portal = dispatch.PostaOnlineDispatchPortal(Client(page))
    submitted = []

    async def before_submit():
        submitted.append(True)

    run(portal.create_draft(_item(), b"%PDF", before_submit))
    actions = [entry[:2] for entry in page.log]
    assert ("fill", "input[name=nomeInvio]") in actions and ("click", "#swlabel") in actions
    assert ("click", "ul.ui-autocomplete:visible li[1]") in actions
    assert actions.count(("click", "#continua")) == 1 and submitted == [True]
    uploaded = next(entry for entry in page.log if entry[0] == "set_input_files")
    assert Path(uploaded[2]).name == "GAIA_020217801062586.pdf" and not Path(uploaded[2]).exists()


def test_legacy_cookie_notice_is_closed_before_filling_the_form():
    page = _form_page(**{"#alertCookie-confirm": {"visible": True}})
    client = Client(page)

    async def prepare_page(_page):
        # The generic fallback disables pointer events on legacy banners.
        page.fail_on.add("#alertCookie-confirm")

    client._prepare_login_page = prepare_page
    portal = dispatch.PostaOnlineDispatchPortal(client)

    async def before_submit():
        return None

    run(portal.create_draft(_item("manual"), b"%PDF", before_submit))
    actions = [entry[:2] for entry in page.log]
    assert actions.index(("click", "#alertCookie-confirm")) < actions.index(
        ("fill", "input[name=nomeInvio]")
    )


def test_uploaded_pdf_remains_available_until_form_submission_completes():
    page = _form_page()
    portal = dispatch.PostaOnlineDispatchPortal(Client(page))
    uploaded = []

    async def before_submit():
        path = Path(next(entry[2] for entry in page.log if entry[0] == "set_input_files"))
        assert path.read_bytes() == b"%PDF-notice"
        uploaded.append(path)

    async def navigation(*_args, **_kwargs):
        assert uploaded[0].read_bytes() == b"%PDF-notice"

    page.wait_for_url = navigation
    run(portal.create_draft(_item(), b"%PDF-notice", before_submit))
    assert not uploaded[0].exists()


def test_previous_documents_are_removed_before_uploading_the_next_notice():
    page = _form_page()
    page.documents = [{"name": "previous.pdf", "slot": "file0"}]
    portal = dispatch.PostaOnlineDispatchPortal(Client(page))

    async def before_submit():
        assert len(page.documents) == 1
        assert page.documents[0]["name"] == "GAIA_020217801062586.pdf"

    run(portal.create_draft(_item(), b"%PDF-new", before_submit))
    actions = [entry[:2] for entry in page.log]
    assert actions.index(("click", "#crea_spedizione")) < actions.index(("set_input_files", "#file"))


def test_a_failed_new_shipment_reset_cannot_submit_or_upload():
    page = _form_page()
    page.documents = [{"name": "previous.pdf", "slot": "file0"}]

    async def no_reset():
        pass

    page.locators["#crea_spedizione"] = {}
    original_locator = page.locator

    def locator(selector):
        result = original_locator(selector)
        if selector == "#crea_spedizione":
            result.click = no_reset
        return result

    page.locator = locator
    portal = dispatch.PostaOnlineDispatchPortal(Client(page))

    async def before_submit():
        pytest.fail("An unclean form must not reach the submitting state")

    with pytest.raises(dispatch.DraftNotSubmitted, match="Allegati Poste non conformi"):
        run(portal.create_draft(_item(), b"%PDF-new", before_submit))
    assert not any(entry[0] == "set_input_files" for entry in page.log)


def test_a_second_document_added_during_recipient_entry_blocks_continua():
    page = _form_page()
    portal = dispatch.PostaOnlineDispatchPortal(Client(page))
    original_fill = portal._fill_recipient

    async def fill_with_stale_document(item):
        await original_fill(item)
        page.documents.append({"name": "previous.pdf", "slot": "file1"})

    portal._fill_recipient = fill_with_stale_document

    async def before_submit():
        pytest.fail("Mixed documents must not reach the submitting state")

    with pytest.raises(dispatch.DraftNotSubmitted, match="Allegati Poste non conformi"):
        run(portal.create_draft(_item(), b"%PDF-new", before_submit))
    assert ("click", "#continua") not in [entry[:2] for entry in page.log]


def test_remembered_ar_form_and_manual_address():
    page = _form_page(
        **{
            "a[onclick*=\"registraForm('raccomandataar')\"]": {"count": 1},
            "#raccomandataarindirizzo": {"visible": False},
        }
    )
    portal = dispatch.PostaOnlineDispatchPortal(Client(page))

    async def before_submit():
        return None

    run(portal.create_draft(_item("manual"), b"%PDF", before_submit))
    actions = [entry[:2] for entry in page.log]
    assert ("click", "#swlabel") not in actions and (
        "click",
        "ul.ui-autocomplete:visible li[2]",
    ) in actions
    assert ("fill", "#raccomandataarindirizzoautocomplete", "VIA CAGLIARI 170") in page.log
    assert ("select_option", "#raccomandataarcap", "09170") in page.log
    city_click = actions.index(("click", "ul.ui-autocomplete:visible li[0]"))
    address_fill = page.log.index(
        ("fill", "#raccomandataarindirizzoautocomplete", "VIA CAGLIARI 170")
    )
    cap_select = actions.index(("select_option", "#raccomandataarcap"))
    assert city_click < address_fill < cap_select
    assert ("fill", "#raccomandataarprovincia") not in actions
    assert ("press", "#raccomandataarlocalita", "Tab") not in page.log


@pytest.mark.parametrize(
    "suggestions",
    [[], ["ORISTANO (CA)"], ["ORISTANO (OR)", "ORISTANO (OR)"]],
)
def test_manual_city_must_match_notice_city_and_province_once(suggestions):
    page = _form_page()
    page.city_options = suggestions
    portal = dispatch.PostaOnlineDispatchPortal(Client(page))

    async def before_submit():
        pytest.fail("CONTINUA must not be reached")

    with pytest.raises(dispatch.DraftNotSubmitted, match=r"Comune.*non proposto univocamente"):
        run(portal.create_draft(_item("manual"), b"%PDF", before_submit))
    actions = [entry[:2] for entry in page.log]
    assert ("fill", "#raccomandataarindirizzo") not in actions
    assert ("click", "#continua") not in actions


def test_manual_address_keeps_notice_street_when_city_selection_enables_cap():
    page = _form_page(**{"#raccomandataarprovincia": {"value": "MI", "visible": False}})
    page.city_options = ["MILANO MARITTIMA (RA)", "MILANO (MI)"]
    portal = dispatch.PostaOnlineDispatchPortal(Client(page))
    item = _item("manual")
    item.recipient.update(address="VIA VIGONI 5", city="MILANO", province="MI", cap="20122")

    async def before_submit():
        actions = [entry[:2] for entry in page.log]
        selected = actions.index(("click", "ul.ui-autocomplete:visible li[1]"))
        assert selected < actions.index(("fill", "#raccomandataarindirizzo"))
        assert selected < actions.index(("select_option", "#raccomandataarcap"))

    run(portal.create_draft(item, b"%PDF", before_submit))
    assert ("fill", "#raccomandataarindirizzo", "VIA VIGONI 5") in page.log
    assert ("select_option", "#raccomandataarcap", "20122") in page.log
    assert ("fill", "#raccomandataarprovincia", "MI") not in page.log


def test_manual_province_must_match_notice_before_continua():
    page = _form_page(**{"#raccomandataarprovincia": {"value": "CA", "visible": False}})
    portal = dispatch.PostaOnlineDispatchPortal(Client(page))

    async def before_submit():
        pytest.fail("CONTINUA must not be reached")

    with pytest.raises(dispatch.DraftNotSubmitted, match=r"Provincia Poste.*diversa"):
        run(portal.create_draft(_item("manual"), b"%PDF", before_submit))
    assert ("click", "#continua") not in [entry[:2] for entry in page.log]


def test_missing_notice_cap_stops_manual_address_before_continua():
    page = _form_page()
    page.fail_on.add("#raccomandataarcap")
    portal = dispatch.PostaOnlineDispatchPortal(Client(page))

    async def before_submit():
        pytest.fail("CONTINUA must not be reached")

    with pytest.raises(dispatch.DraftNotSubmitted, match="select_option failed"):
        run(portal.create_draft(_item("manual"), b"%PDF", before_submit))
    assert ("click", "#continua") not in [entry[:2] for entry in page.log]


@pytest.mark.parametrize(
    "locators,message",
    [
        ({"#raccomandataarnome": {"visible": False}}, "A/R non attivato"),
        (
            {
                "#raccomandataarindirizzo": {"visible": False},
                "#raccomandataarindirizzoautocomplete": {"visible": False},
            },
            "indirizzo manuale",
        ),
        ({"ul.ui-autocomplete:visible li": {"texts": []}}, "non proposto"),
        ({"#raccomandataarSummary": {"text": "2"}}, "attesi 1"),
        ({".has-error": {"count": 1}}, "attesi 1"),
    ],
)
def test_form_problems_stop_before_continua(locators, message):
    page = _form_page(**locators)
    portal = dispatch.PostaOnlineDispatchPortal(Client(page))
    item = _item("manual" if "manuale" in message else "directory")

    async def before_submit():
        pytest.fail("CONTINUA must not be reached")

    with pytest.raises(dispatch.DraftNotSubmitted, match=message):
        run(portal.create_draft(item, b"%PDF", before_submit))
    assert ("click", "#continua") not in [entry[:2] for entry in page.log]


def test_a_missing_navigation_after_continua_is_uncertain():
    page = _form_page()
    page.url_error = TimeoutError("no navigation")
    portal = dispatch.PostaOnlineDispatchPortal(Client(page))

    async def before_submit():
        return None

    with pytest.raises(dispatch.DraftSubmitUncertain, match="no navigation"):
        run(portal.create_draft(_item(), b"%PDF", before_submit))
