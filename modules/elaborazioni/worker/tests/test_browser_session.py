from pathlib import Path
import sys

import pytest


WORKER_ROOT = Path(__file__).resolve().parents[1]

if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from browser_session import BrowserSession


class FakeLocator:
    def __init__(self, *, visible: bool = True, count: int = 1, text: str = "", on_click=None) -> None:
        self.visible = visible
        self._count = count
        self.text = text
        self.on_click = on_click
        self.clicks = 0
        self.waits: list[int | None] = []

    @property
    def first(self) -> "FakeLocator":
        return self

    def nth(self, _index: int) -> "FakeLocator":
        return self

    async def count(self) -> int:
        return self._count

    async def is_visible(self) -> bool:
        return self.visible

    async def inner_text(self, timeout: int | None = None) -> str:
        return self.text

    async def click(self, timeout: int | None = None) -> None:
        self.clicks += 1
        if self.on_click is not None:
            self.on_click()

    async def wait_for(self, timeout: int | None = None) -> None:
        self.waits.append(timeout)


class FakePage:
    def __init__(self, *, url: str = "about:blank", title: str = "", body: str = "") -> None:
        self.url = url
        self._title = title
        self.body = body
        self.gotos: list[str] = []
        self.clicks: list[str] = []
        self.fills: list[tuple[str, str]] = []
        self.waits: list[str] = []
        self.locators: dict[str, FakeLocator] = {}
        self.role_locators: dict[tuple[str, str], FakeLocator] = {}

    async def title(self) -> str:
        return self._title

    async def goto(self, url: str, wait_until: str | None = None) -> None:
        self.gotos.append(url)
        self.url = url

    async def wait_for_load_state(self, state: str, timeout: int | None = None) -> None:
        self.waits.append(state)

    async def click(self, selector: str) -> None:
        self.clicks.append(selector)

    async def fill(self, selector: str, value: str) -> None:
        self.fills.append((selector, value))

    def get_by_role(self, role: str, name: str) -> FakeLocator:
        return self.role_locators.get((role, name), FakeLocator(count=0))

    def locator(self, selector: str) -> FakeLocator:
        if selector == "body":
            return FakeBodyLocator(self.body)
        return self.locators.get(selector, FakeLocator(count=0))


class FakeBodyLocator(FakeLocator):
    def __init__(self, body: str) -> None:
        super().__init__()
        self.body = body

    async def inner_text(self, timeout: int | None = None) -> str:
        return self.body


async def _noop_trace(*_args, **_kwargs) -> None:
    return None


async def _noop_sleep(*_args, **_kwargs) -> None:
    return None


def test_browser_session_classifies_locked_user_page() -> None:
    message = BrowserSession._classify_login_issue(
        "https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp",
        "Utente bloccato",
        "Utente bloccato sul portale SISTER",
    )

    assert message == (
        "Utente SISTER bloccato sul portale Agenzia delle Entrate. "
        "Verificare se esiste gia' una sessione attiva su un'altra postazione o browser."
    )


def test_browser_session_classifies_existing_session_page() -> None:
    message = BrowserSession._classify_login_issue(
        "https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp",
        "Utente bloccato",
        "Utente gia' in sessione sulla stessa o altra postazione.",
    )

    assert message == "Utente SISTER gia' in sessione su un'altra postazione o browser."


def test_browser_session_classifies_rejected_credentials() -> None:
    message = BrowserSession._classify_login_issue(
        "https://iampe.agenziaentrate.gov.it/sam/UI/Login",
        "Accesso non riuscito",
        "Le credenziali inserite non sono valide.",
    )

    assert message == "Credenziali SISTER rifiutate dal portale Agenzia delle Entrate."


def test_tipo_visura_value_matches_sister_current_values() -> None:
    assert BrowserSession.tipo_visura_value("Sintetica") == "4"
    assert BrowserSession.tipo_visura_value("Analitica") == "3"
    assert BrowserSession.tipo_visura_value("Completa") == "0"


def test_visura_informativa_uses_input_submit_selector() -> None:
    session = BrowserSession.__new__(BrowserSession)
    session.selectors = type("Selectors", (), {"conferma_lettura_button_name": "Conferma Lettura"})()
    page = FakePage(
        url="https://sister3.agenziaentrate.gov.it/Visure/Informativa.do",
        body="Informativa del servizio Visure catastali Conferma Lettura",
    )
    input_selector = "input[type='submit'][value='Conferma Lettura']"
    page.locators[input_selector] = FakeLocator()
    session._page = page
    session.config = type("Config", (), {"debug_artifacts_path": None})()
    session._trace_state = _noop_trace

    import asyncio

    asyncio.run(session._confirm_visura_informativa_if_present())

    assert page.locators[input_selector].clicks == 1
    assert page.waits == ["domcontentloaded"]


def test_recover_locked_session_prefers_chiudi_close_sessions_link(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio
    import browser_session as browser_session_module

    session = BrowserSession.__new__(BrowserSession)
    page = FakePage(
        url="https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp",
        title="Utente bloccato",
    )
    close_link = FakeLocator(text="Chiudi")
    page.locators["a[href*='CloseSessionsSis']:has-text('Chiudi')"] = close_link
    session._page = page
    session.selectors = type(
        "Selectors",
        (),
        {"login_url": "https://iampe.agenziaentrate.gov.it/sam/UI/Login?realm=/agenziaentrate"},
    )()
    session._read_page_state = lambda: _async_tuple(
        "https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp",
        "Utente bloccato",
        "Utente gia' in sessione sulla stessa o altra postazione.",
    )
    session._trace_state = _noop_trace
    session.stop = _noop_trace
    session.start = _noop_trace
    monkeypatch.setattr(browser_session_module.asyncio, "sleep", _noop_sleep)

    asyncio.run(session._recover_locked_session())

    assert close_link.clicks == 1
    assert page.gotos == ["https://iampe.agenziaentrate.gov.it/sam/UI/Login?realm=/agenziaentrate"]


def test_recover_locked_session_falls_back_to_close_sessions_url(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio
    import browser_session as browser_session_module

    session = BrowserSession.__new__(BrowserSession)
    page = FakePage(
        url="https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp",
        title="Utente bloccato",
    )
    session._page = page
    session.selectors = type(
        "Selectors",
        (),
        {"login_url": "https://iampe.agenziaentrate.gov.it/sam/UI/Login?realm=/agenziaentrate"},
    )()
    session._trace_state = _noop_trace
    session.stop = _noop_trace
    session.start = _noop_trace
    monkeypatch.setattr(browser_session_module.asyncio, "sleep", _noop_sleep)

    asyncio.run(session._recover_locked_session())

    assert page.gotos == [
        "https://sister3.agenziaentrate.gov.it/Servizi/CloseSessionsSis",
        "https://iampe.agenziaentrate.gov.it/sam/UI/Login?realm=/agenziaentrate",
    ]


def test_recover_locked_session_does_not_click_header_esci(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio
    import browser_session as browser_session_module

    session = BrowserSession.__new__(BrowserSession)
    page = FakePage(
        url="https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp",
        title="Utente bloccato",
    )
    esci_link = FakeLocator(text="Esci")
    page.locators["a[href*='CloseSessionsSis']"] = esci_link
    session._page = page
    session.selectors = type(
        "Selectors",
        (),
        {"login_url": "https://iampe.agenziaentrate.gov.it/sam/UI/Login?realm=/agenziaentrate"},
    )()
    session._trace_state = _noop_trace
    session.stop = _noop_trace
    session.start = _noop_trace
    monkeypatch.setattr(browser_session_module.asyncio, "sleep", _noop_sleep)

    asyncio.run(session._recover_locked_session())

    assert esci_link.clicks == 0
    assert page.gotos[0] == "https://sister3.agenziaentrate.gov.it/Servizi/CloseSessionsSis"


def test_connection_success_requires_final_logout() -> None:
    session = BrowserSession.__new__(BrowserSession)
    page = FakePage(url="about:blank", title="Home dei Servizi", body="Consultazioni e Certificazioni")
    page.role_locators[("link", "Consultazioni e Certificazioni")] = FakeLocator()
    session._page = page
    session.selectors = type(
        "Selectors",
        (),
        {
            "login_url": "https://iampe.agenziaentrate.gov.it/sam/UI/Login?realm=/agenziaentrate",
            "login_tab_selector": "#tab",
            "username_selector": "#username",
            "password_selector": "#password",
            "login_button_selector": "#submit",
            "confirm_button_xpath": "//input[@value='Conferma']",
            "consultazioni_link_name": "Consultazioni e Certificazioni",
        },
    )()
    session.config = type("Config", (), {"debug_artifacts_path": None})()
    session._trace_state = _noop_trace
    session._maybe_click_xpath = _noop_trace
    logout_calls = 0

    async def fake_logout() -> None:
        nonlocal logout_calls
        logout_calls += 1

    session.logout = fake_logout

    import asyncio

    result = asyncio.run(session.test_connection("USER", "PASSWORD"))

    assert result.reachable is True
    assert result.authenticated is True
    assert logout_calls == 1
    assert "logout finale eseguito" in result.message


def test_connection_fails_when_final_logout_fails() -> None:
    session = BrowserSession.__new__(BrowserSession)
    page = FakePage(url="about:blank", title="Home dei Servizi", body="Consultazioni e Certificazioni")
    page.role_locators[("link", "Consultazioni e Certificazioni")] = FakeLocator()
    session._page = page
    session.selectors = type(
        "Selectors",
        (),
        {
            "login_url": "https://iampe.agenziaentrate.gov.it/sam/UI/Login?realm=/agenziaentrate",
            "login_tab_selector": "#tab",
            "username_selector": "#username",
            "password_selector": "#password",
            "login_button_selector": "#submit",
            "confirm_button_xpath": "//input[@value='Conferma']",
            "consultazioni_link_name": "Consultazioni e Certificazioni",
        },
    )()
    session.config = type("Config", (), {"debug_artifacts_path": None})()
    session._trace_state = _noop_trace
    session._maybe_click_xpath = _noop_trace

    async def fake_logout() -> None:
        raise RuntimeError("logout failed")

    session.logout = fake_logout

    import asyncio

    result = asyncio.run(session.test_connection("USER", "PASSWORD"))

    assert result.reachable is True
    assert result.authenticated is False
    assert result.message is not None
    assert "logout finale non confermato" in result.message


def test_prepare_captcha_or_download_clicks_inoltra_before_captcha(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio
    import browser_session as browser_session_module

    session = BrowserSession.__new__(BrowserSession)
    page = FakePage(url="https://sister3.agenziaentrate.gov.it/Visure/vimm/RicercaIMM.do")
    session._page = page
    session.selectors = type(
        "Selectors",
        (),
        {
            "save_button_selector": "input[name='metodo'][value='Salva']",
            "captcha_image_selector": "img[src*='captcha']",
            "inoltra_button_selector": "input[name='inoltra']",
        },
    )()
    session._trace_state = _noop_trace
    page.locators["input[name='metodo'][value='Salva']"] = FakeLocator(count=0)
    captcha = FakeLocator(count=0, visible=False)

    def reveal_captcha() -> None:
        captcha._count = 1
        captcha.visible = True

    inoltra = FakeLocator(on_click=reveal_captcha)
    page.locators["input[name='inoltra']"] = inoltra
    page.locators["img[src*='captcha']"] = captcha
    monkeypatch.setattr(browser_session_module.asyncio, "sleep", _noop_sleep)

    result = asyncio.run(session.prepare_captcha_or_download())

    assert result == "captcha"
    assert inoltra.clicks == 1


def test_prepare_captcha_or_download_returns_download_without_click() -> None:
    import asyncio

    session = BrowserSession.__new__(BrowserSession)
    page = FakePage(url="https://sister3.agenziaentrate.gov.it/Visure/vimm/RicercaIMM.do")
    session._page = page
    session.selectors = type(
        "Selectors",
        (),
        {
            "save_button_selector": "input[name='metodo'][value='Salva']",
            "captcha_image_selector": "img[src*='captcha']",
            "inoltra_button_selector": "input[name='inoltra']",
        },
    )()
    page.locators["input[name='metodo'][value='Salva']"] = FakeLocator()
    page.locators["input[name='inoltra']"] = FakeLocator()

    result = asyncio.run(session.prepare_captcha_or_download())

    assert result == "download"
    assert page.locators["input[name='inoltra']"].clicks == 0


async def _async_tuple(*values):
    return values
