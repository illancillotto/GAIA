from __future__ import annotations

import asyncio
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

    async def count(self):
        return self.count_value

    async def is_visible(self):
        return self.visible

    async def inner_text(self):
        return self.text

    async def all_inner_texts(self):
        return self.texts

    def nth(self, index):
        return Locator(self.page, f"{self.selector}[{index}]", {})

    def __getattr__(self, action):
        async def record(*args, **_kwargs):
            if self.selector in self.page.fail_on:
                raise RuntimeError(f"{action} failed on {self.selector}")
            self.page.log.append(
                (action, self.selector, *[arg for arg in args if not isinstance(arg, int)])
            )

        return record


class Page:
    def __init__(self, pages=(), **locators):
        self.pages, self.log, self.fail_on, self.url_error = list(pages), [], set(), None
        self.locators = locators

    def locator(self, selector):
        return Locator(self, selector, self.locators.get(selector, {}))

    async def goto(self, url, **_kwargs):
        self.log.append(("goto", url))

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
        ".has-error": {"count": 0},
        "ul.ui-autocomplete:visible li": {
            "texts": ["VIA ORISTANO 170, CAGLIARI (CA), 09127", LABEL, MANUAL]
        },
    }
    return Page(**(defaults | locators))


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
        Client(Page([REAL_DRAFT_PAGE, REAL_DRAFT_PAGE]), next_pages=1)
    )
    assert [row.draft_id for row in run(portal.list_drafts())] == ["12269236", "12269236"]
    portal = dispatch.PostaOnlineDispatchPortal(Client(Page([ARCHIVE_PAGE]), next_pages=0))
    assert run(portal.archive_index()) == ({"GAIA 020217801062586": ["11280322"]}, True)


def test_overlong_lists_are_reported_as_incomplete(monkeypatch):
    monkeypatch.setattr(dispatch, "MAX_LIST_PAGES", 2)
    portal = dispatch.PostaOnlineDispatchPortal(Client(Page(), next_pages=5))
    assert run(portal.archive_index()) == ({}, False)
    with pytest.raises(RuntimeError, match="troppe pagine"):
        run(portal.list_drafts())


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
