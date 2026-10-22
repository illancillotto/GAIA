from __future__ import annotations

import asyncio
import itertools

import pytest

import step_client
from step_browser_scripts import READ_CONTRIBUENTI, READ_SHEET, READ_TRIBUTI
from step_client import StepBrowserClient, StepClientConfig, StepLoginError, _NetworkTracker
from step_rules import StepIntegrityError

PDF = b"%PDF-1.4\n%%EOF"


@pytest.fixture(autouse=True)
def fast_clock(monkeypatch: pytest.MonkeyPatch):
    ticks = itertools.count(step=1.0)

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(step_client.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(step_client.time, "monotonic", lambda: float(next(ticks)))


class Emitter:
    def __init__(self) -> None:
        self.handlers: dict[str, list] = {}

    def on(self, event, handler) -> None:
        self.handlers.setdefault(event, []).append(handler)

    def remove_listener(self, event, handler) -> None:
        self.handlers[event].remove(handler)

    def emit(self, event, value) -> None:
        for handler in list(self.handlers.get(event, [])):
            handler(value)


class Request:
    def __init__(self, resource_type="xhr", failure=None) -> None:
        self.resource_type = resource_type
        self.failure = failure


class Response:
    def __init__(self, status, resource_type="xhr") -> None:
        self.status = status
        self.request = Request(resource_type)


class Download:
    def __init__(self, path) -> None:
        self._path = path
        self.suggested_filename = "Doc_1.pdf"

    async def path(self):
        return self._path


class Locator:
    def __init__(self, page, selector) -> None:
        self.page = page
        self.selector = selector

    @property
    def last(self):
        return self

    async def wait_for(self, state="visible", timeout=None):
        if state == "hidden" and self.page.reject_login:
            raise RuntimeError("still visible")

    async def fill(self, value):
        self.page.actions.append(("fill", self.selector, value))

    async def is_visible(self):
        return self.page.cookie_banner

    async def click(self):
        self.page.actions.append(("click", self.selector))
        hook = self.page.click_hooks.get(self.selector)
        if hook:
            hook()


class Page(Emitter):
    def __init__(self, context) -> None:
        super().__init__()
        self.context = context
        self.actions: list = []
        self.results: dict[str, list] = {}
        self.click_hooks: dict = {}
        self.reject_login = False
        self.cookie_banner = True
        self.closed = False

    def set_default_timeout(self, value):
        self.timeout = value

    async def goto(self, url, wait_until=None):
        self.actions.append(("goto", url))

    def locator(self, selector):
        return Locator(self, selector)

    def get_by_role(self, role, name=None, exact=None):
        label = getattr(name, "pattern", name)
        return Locator(self, f"role:{role}:{label}")

    def get_by_text(self, text, exact=None):
        return Locator(self, f"text:{text}")

    async def evaluate(self, script):
        queue = self.results.get(script, [None])
        return queue.pop(0) if len(queue) > 1 else queue[0]

    async def close(self):
        self.closed = True


class Context(Emitter):
    def __init__(self) -> None:
        super().__init__()
        self.pages: list = []

    async def new_page(self):
        page = Page(self)
        self.pages.append(page)
        return page

    async def close(self):
        raise RuntimeError("already closed")


class Browser:
    def __init__(self) -> None:
        self.context = Context()

    async def new_context(self, **kwargs):
        self.context_kwargs = kwargs
        return self.context

    async def close(self):
        return None


class Playwright:
    def __init__(self) -> None:
        self.browser = Browser()
        self.chromium = self
        self.stopped = False

    async def launch(self, **kwargs):
        self.launch_kwargs = kwargs
        return self.browser

    async def stop(self):
        self.stopped = True


class Factory:
    def __init__(self) -> None:
        self.playwright = Playwright()

    def __call__(self):
        return self

    async def start(self):
        return self.playwright


def run(coro):
    return asyncio.run(coro)


async def _open(config=None, factory=None):
    client = StepBrowserClient(
        config or StepClientConfig(portal_url="https://step.example"),
        playwright_factory=factory or Factory(),
    )
    await client.__aenter__()
    return client


def _list_state(page, rows):
    return {"total": 25, "page": page, "pages": 3, "fields": [], "rows": rows}


def test_browser_path_resolution(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("STEP_BROWSER_PATH", raising=False)
    monkeypatch.setattr(step_client, "_DEFAULT_CHROME_PATH", str(tmp_path / "missing"))
    assert step_client._browser_path(StepClientConfig(portal_url="u", browser_path="/x")) == "/x"
    assert step_client._browser_path(StepClientConfig(portal_url="u")) is None
    chrome = tmp_path / "chrome"
    chrome.write_text("")
    monkeypatch.setattr(step_client, "_DEFAULT_CHROME_PATH", str(chrome))
    assert step_client._browser_path(StepClientConfig(portal_url="u")) == str(chrome)
    monkeypatch.setenv("STEP_BROWSER_PATH", "/env")
    assert step_client._browser_path(StepClientConfig(portal_url="u")) == "/env"


def test_lifecycle_login_and_list_navigation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STEP_BROWSER_PATH", "/chrome")
    factory = Factory()

    async def scenario():
        client = await _open(factory=factory)
        page = client.page
        await client.login("user", "pw")
        page.results[READ_CONTRIBUENTI] = [
            None,
            _list_state(1, [{"a": 1}]),
            _list_state(1, [{"a": 1}]),
            _list_state(2, [{"a": 2}]),
            _list_state(3, [{"a": 3}]),
        ]
        first = await client.open_contribuenti()
        second = await client.go_to_page(2, first)
        third = await client.go_to_page(3, {"page": 1, "rows": second["rows"]})
        page.cookie_banner = False
        await client.login("user", "pw")
        await client.__aexit__(None, None, None)
        return page, first, second, third

    page, first, second, third = run(scenario())
    assert factory.playwright.launch_kwargs == {"headless": True, "executable_path": "/chrome"}
    assert factory.playwright.stopped
    assert first["page"] == 1 and second["page"] == 2 and third["page"] == 3
    clicks = [action[1] for action in page.actions if action[0] == "click"]
    assert "role:button:OK.*accetto i cookie" in clicks and 'img[src$="/successiva.gif"]' in clicks
    assert ("fill", 'input[type="text"]:visible', "3") in page.actions
    assert ("fill", 'input[name="Password"]', "pw") in page.actions


def test_login_rejection_and_navigation_errors() -> None:
    async def scenario():
        client = await _open()
        page = client.page
        page.reject_login = True
        with pytest.raises(StepLoginError):
            await client.login("user", "bad")

        def fail_request():
            page.emit("requestfailed", Request(failure="net::ERR"))
            page.emit("requestfailed", Request(resource_type="image"))

        page.click_hooks['img[src$="/successiva.gif"]'] = fail_request
        with pytest.raises(RuntimeError, match="net::ERR"):
            await client.go_to_page(2, {"page": 1, "rows": []})

        def http_error():
            page.emit("response", Response(500))
            page.emit("response", Response(200))
            page.emit("response", Response(500, resource_type="document"))

        page.click_hooks['img[src$="/successiva.gif"]'] = http_error
        with pytest.raises(RuntimeError, match="HTTP 500"):
            await client.go_to_page(2, {"page": 1, "rows": []})
        page.click_hooks.clear()
        page.results[READ_CONTRIBUENTI] = [_list_state(1, [])]
        with pytest.raises(TimeoutError, match="pagina STEP 2"):
            await client.go_to_page(2, {"page": 1, "rows": []})
        page.results[READ_SHEET] = [None]
        with pytest.raises(TimeoutError, match="Stato atteso"):
            await client._wait_state(READ_SHEET)
        assert page.handlers["requestfailed"] == [client.network._finished]

    run(scenario())


def test_network_tracker() -> None:
    tracker = _NetworkTracker()
    page = Emitter()
    tracker.attach(page)
    image, xhr, failing = Request("image"), Request(), Request(failure="boom")
    for request in (image, xhr, failing):
        page.emit("request", request)
    assert tracker.active == {xhr, failing}
    page.emit("requestfinished", image)
    page.emit("requestfinished", xhr)
    marker = tracker.mark()
    page.emit("requestfailed", failing)
    assert tracker.failures == ["boom"]

    async def waits():
        with pytest.raises(RuntimeError, match="boom"):
            await tracker.wait_idle(marker)
        await tracker.wait_idle(tracker.mark())
        tracker.active.add(xhr)
        with pytest.raises(TimeoutError):
            await tracker.wait_idle(tracker.mark(), timeout_s=3)

    run(waits())


def _sheet(cf="CF1", *, close="close-1", documents=None):
    documents = (
        documents
        if documents is not None
        else [
            {"COD_ENT": "1", "NUM_DOC": "D1", "PRG_COO": 1, "NUM_TRIB": "3", "NOME_PDF": "x.pdf"},
            {"COD_ENT": "1", "NUM_DOC": "D2", "PRG_COO": 1, "NUM_TRIB": "0"},
        ]
    )
    grid = {
        "id": "isc_Doc",
        "fields": [{"name": "NUM_DOC"}, {"name": "NUM_TRIB"}],
        "rows": documents,
        "totalRows": len(documents),
    }
    return {
        "anagrafica": {"Codice fiscale": cf},
        "situazioneContabile": {},
        "grids": [grid],
        "closeId": close,
    }


def _tributi(page, rows, *, close="close-trib"):
    return {
        "total": 3,
        "page": page,
        "pages": 2,
        "rows": [{"NUM_DOC": "D1", "k": key} for key in rows],
        "handleId": "modal",
        "closeId": close,
    }


def test_extract_scheda_reads_tributi_and_pdf(tmp_path) -> None:
    pdf_file = tmp_path / "download.pdf"
    pdf_file.write_bytes(PDF)

    async def scenario():
        client = await _open()
        page = client.page
        page.results[READ_SHEET] = [None, _sheet()]
        page.results[READ_TRIBUTI] = [
            _tributi(1, ["a", "b"]),
            _tributi(1, ["a", "b"]),
            _tributi(2, ["c"]),
        ]

        def open_popup():
            popup = Page(page.context)
            page.context.pages.append(popup)
            page.context.emit("page", popup)
            popup.emit("download", Download(pdf_file))
            popup.emit("download", Download(pdf_file))

        page.click_hooks['a[onclick*="isc_Doc."][onclick*=",0,0)"]'] = open_popup
        scheda = await client.extract_scheda({"COD_FIS_NEW": "CF1", "NUMERODOC": "2"})
        return page, scheda

    page, scheda = run(scenario())
    first, second = scheda["documents"]
    assert [row["k"] for row in first["tributi"]["rows"]] == ["a", "b", "c"]
    assert first["pdf"] == {"status": "downloaded", "content": PDF, "originalFilename": "Doc_1.pdf"}
    assert second["tributi"]["rows"] == [] and second["pdf"]["status"] == "unavailable"
    assert scheda["documentReconciliation"]["status"] == "matched"
    assert page.context.pages[-1].closed
    clicks = [action[1] for action in page.actions if action[0] == "click"]
    assert (
        "#close-trib" in clicks
        and "#close-1" in clicks
        and '#modal img[src$="/successiva.gif"]' in clicks
    )


def test_extract_scheda_integrity_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    async def wait_for_timeout(future, timeout):
        future.cancel()
        raise TimeoutError("no download")

    async def scenario():
        client = await _open()
        page = client.page
        page.results[READ_SHEET] = [_sheet("OTHER")]
        with pytest.raises(StepIntegrityError, match="altro contribuente"):
            await client.extract_scheda({"COD_FIS_NEW": "CF1", "NUMERODOC": "1"})

        page.results[READ_SHEET] = [_sheet(close=None, documents=[])]
        with pytest.raises(StepIntegrityError, match="chiusura"):
            await client.extract_scheda({"COD_FIS_NEW": "CF1", "NUMERODOC": "0"})

        page.results[READ_TRIBUTI] = [{**_tributi(1, ["a"]), "total": 9, "closeId": None}]
        document = {"COD_ENT": "1", "NUM_DOC": "D1", "PRG_COO": 1, "NUM_TRIB": "3"}
        page.results[READ_SHEET] = [_sheet(documents=[document])]
        with pytest.raises(StepIntegrityError, match="dichiarati"):
            await client.extract_scheda({"COD_FIS_NEW": "CF1", "NUMERODOC": "1"})

        monkeypatch.setattr(step_client.asyncio, "wait_for", wait_for_timeout)
        page.results[READ_SHEET] = [
            _sheet(documents=[{**document, "NUM_TRIB": "0", "NOME_COMPLETO": "y"}])
        ]
        with pytest.raises(TimeoutError, match="no download"):
            await client.extract_scheda({"COD_FIS_NEW": "CF1", "NUMERODOC": "1"})
        assert page.handlers["download"] == []

    run(scenario())


def test_exit_without_enter_is_a_no_op() -> None:
    client = StepBrowserClient(
        StepClientConfig(portal_url="https://step.example"), playwright_factory=Factory()
    )
    run(client.__aexit__(None, None, None))
    assert client.browser is None
