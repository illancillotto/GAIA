from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sister_browser_reliability import (
    UTC,
    SisterSessionState,
    _is_non_blocking_init_portale_error,
    document_not_yet_produced_error,
    download_valid_pdf,
    is_visura_area_ready,
    raise_if_sister_server_error,
)
from sister_exceptions import (
    SisterInvalidDocumentError,
    SisterRequestCorrelationError,
    SisterServerError,
)
from sister_request_rows import SisterRequestCorrelation


class _Locator:
    def __init__(self, *, text: str = "", count: int = 0, href: str | None = None, error: Exception | None = None):
        self.text = text
        self._count = count
        self.href = href
        self.error = error

    @property
    def first(self):
        return self

    async def inner_text(self, timeout: int | None = None) -> str:
        if self.error is not None:
            raise self.error
        return self.text

    async def get_attribute(self, _name: str, timeout: int | None = None) -> str | None:
        if self.error is not None:
            raise self.error
        return self.href

    async def count(self) -> int:
        return self._count


class _Page:
    def __init__(
        self,
        *,
        url: str = "https://sister3.agenziaentrate.gov.it/Visure/Home.do",
        **options,
    ) -> None:
        self.url = url
        self.body = _Locator(text=options.get("body", ""), error=options.get("body_error"))
        self.link = _Locator(href=options.get("href"), error=options.get("link_error"))
        self.catasto = _Locator(count=options.get("catasto_count", 0))
        self.immobile = _Locator(count=options.get("immobile_count", 0))

    def locator(self, selector: str) -> _Locator:
        if selector == "body":
            return self.body
        if "ConsultazioneRichieste" in selector:
            return self.link
        return self.catasto

    def get_by_role(self, _role: str, name: str) -> _Locator:
        return self.immobile


class _Download:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    async def save_as(self, path: str) -> None:
        Path(path).write_bytes(self.payload)


class _DownloadContext:
    def __init__(self, payload: bytes) -> None:
        self.value = self._value(payload)

    @staticmethod
    async def _value(payload: bytes) -> _Download:
        return _Download(payload)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


class _DownloadPage:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.clicks: list[str] = []

    def expect_download(self, timeout: int):
        assert timeout == 20000
        return _DownloadContext(self.payload)

    async def click(self, selector: str) -> None:
        self.clicks.append(selector)


def _response(status: int, url: str, resource_type: str = "document"):
    return SimpleNamespace(
        status=status,
        url=url,
        request=SimpleNamespace(resource_type=resource_type),
    )


def test_session_state_authentication_submission_and_response_tracking() -> None:
    state = SisterSessionState()
    assert not state.is_authenticated("user", "1050380")
    state.authenticate("user", "1050380", datetime.now(UTC) + timedelta(minutes=5))
    assert state.is_authenticated("user", "1050380")
    assert not state.is_authenticated("other", "1050380")

    state.mark_submitted(None, "https://requests")
    calls: list[tuple[str | None, str | None, str]] = []
    state.correlation = SisterRequestCorrelation("local", frozenset(), (), None)
    state.begin_submission(lambda *args: calls.append(args))
    state.track_response(
        _response(200, "https://sister3.agenziaentrate.gov.it/Visure/CheckRichiesta.do?idRichiesta=ABC-1"),
        "https://requests",
    )
    assert calls == [("ABC-1", "https://requests", "submitted")]
    assert state.correlation.remote_id == "ABC-1"
    assert state.submission_callback is None

    state.begin_submission(lambda *args: calls.append(args))
    state.clear_submission()
    assert state.submission_callback is None
    state.track_response(_response(503, "https://agenziaentrate.gov.it/down", "xhr"), "https://requests")
    assert state.pop_server_error() == (503, "https://agenziaentrate.gov.it/down")
    assert state.pop_server_error() is None


def test_submission_identity_is_updated_without_callback_and_after_empty_notification() -> None:
    state = SisterSessionState(correlation=SisterRequestCorrelation("local", frozenset(), (), None))
    state.mark_submitted("NO-CAPTCHA", "https://requests")
    assert state.correlation.remote_id == "NO-CAPTCHA"
    state.correlation = SisterRequestCorrelation("other", frozenset(), (), None)
    calls = []
    state.begin_submission(lambda *args: calls.append(args))
    state.mark_submitted(None, "https://requests")
    assert state.submission_callback is not None
    state.mark_submitted("LATE-ID", "https://requests")
    assert state.correlation.remote_id == "LATE-ID"
    assert [call[0] for call in calls] == [None, "LATE-ID"]
    assert state.submission_callback is None
    state.mark_submitted(None, "https://requests")
    assert state.correlation.remote_id == "LATE-ID"


def test_submission_callback_can_run_without_correlation() -> None:
    state = SisterSessionState()
    calls = []
    state.begin_submission(lambda *args: calls.append(args))
    state.mark_submitted("ID", "https://requests")
    assert calls == [("ID", "https://requests", "submitted")]


def test_late_response_and_conflicting_identity_cannot_replace_current_request() -> None:
    state = SisterSessionState(correlation=SisterRequestCorrelation("local", frozenset(), (), "ORIGINAL"))
    state.track_response(_response(200, "https://sister3.agenziaentrate.gov.it/Visure/CheckRichiesta.do?idRichiesta=LATE"), "https://requests")
    assert state.correlation.remote_id == "ORIGINAL"
    state.mark_submitted("ORIGINAL", "https://requests")
    with pytest.raises(SisterRequestCorrelationError, match="diverso"):
        state.mark_submitted("OTHER", "https://requests")
    assert state.correlation.remote_id == "ORIGINAL"


def test_init_portale_error_cannot_be_ignored_off_home_or_with_unreadable_page() -> None:
    endpoint = "https://sister3.agenziaentrate.gov.it/portale-rest/rs/initPortale"
    assert not asyncio.run(_is_non_blocking_init_portale_error(_Page(), 501, endpoint))
    assert not asyncio.run(_is_non_blocking_init_portale_error(
        _Page(url="https://sister3.agenziaentrate.gov.it/Servizi/"), 501, endpoint,
    ))


def test_session_state_ignores_irrelevant_and_malformed_responses() -> None:
    state = SisterSessionState()
    state.track_response(object(), "https://requests")
    state.track_response(_response(500, "https://example.test/down"), "https://requests")
    state.track_response(
        _response(500, "https://sister3.agenziaentrate.gov.it/down", "image"),
        "https://requests",
    )
    assert state.pending_server_error is None


@pytest.mark.parametrize(
    ("payload", "valid"),
    [
        (b"%PDF-1.4\nbody", True),
        (b"short", False),
        (b"NOTPDF-content", False),
    ],
)
def test_download_valid_pdf_is_atomic_and_validates_signature(
    tmp_path: Path,
    payload: bytes,
    valid: bool,
) -> None:
    page = _DownloadPage(payload)
    destination = tmp_path / "nested" / "visura.pdf"
    if valid:
        size = asyncio.run(download_valid_pdf(page, "#save", destination))
        assert size == len(payload)
        assert destination.read_bytes() == payload
    else:
        with pytest.raises(SisterInvalidDocumentError):
            asyncio.run(download_valid_pdf(page, "#save", destination))
        assert not destination.exists()
    assert page.clicks == ["#save"]
    assert not list(destination.parent.glob("*.part"))


def test_raise_if_sister_server_error_prefers_captured_http_error() -> None:
    state = SisterSessionState(pending_server_error=(502, "https://sister/error"))
    with pytest.raises(SisterServerError, match="HTTP 502"):
        asyncio.run(raise_if_sister_server_error(_Page(), state))
    assert state.pending_server_error is None


@pytest.mark.parametrize("body", ["Error 500", "java.lang.NullPointerException", "HTTP Status 500"])
def test_raise_if_sister_server_error_detects_error_pages(body: str) -> None:
    page = _Page(body=body)
    with pytest.raises(SisterServerError, match="SISTER 500"):
        asyncio.run(raise_if_sister_server_error(page, SisterSessionState()))


def test_raise_if_sister_server_error_allows_normal_or_unreadable_pages() -> None:
    asyncio.run(raise_if_sister_server_error(_Page(body="Servizio disponibile"), SisterSessionState()))
    asyncio.run(
        raise_if_sister_server_error(
            _Page(body_error=RuntimeError("detached")),
            SisterSessionState(),
        )
    )


def test_document_not_yet_produced_correlates_relative_requests_link() -> None:
    calls: list[tuple[str | None, str | None, str]] = []
    state = SisterSessionState(submission_callback=lambda *args: calls.append(args))
    page = _Page(
        body="Il documento non e' stato ancora prodotto",
        href="/Visure/ConsultazioneRichieste.do?idRichiesta=REQ-7",
    )

    error = asyncio.run(
        document_not_yet_produced_error(page, state, "https://sister3.agenziaentrate.gov.it", "https://requests")
    )

    assert error is not None
    assert error.remote_id == "REQ-7"
    assert error.richieste_url.endswith("idRichiesta=REQ-7")
    assert calls == [("REQ-7", "https://requests", "submitted")]


def test_document_not_yet_produced_handles_absolute_missing_and_broken_links() -> None:
    normal = asyncio.run(
        document_not_yet_produced_error(_Page(body="Pagina normale"), SisterSessionState(), "https://base", "requests")
    )
    assert normal is None

    absolute = asyncio.run(
        document_not_yet_produced_error(
            _Page(
                body="NON È STATO ANCORA PRODOTTO",
                href="https://sister/ConsultazioneRichieste.do?idRich=R-2",
            ),
            SisterSessionState(),
            "https://base",
            "requests",
        )
    )
    assert absolute is not None and absolute.remote_id == "R-2"

    no_link = asyncio.run(
        document_not_yet_produced_error(
            _Page(body="NON E' STATO ANCORA PRODOTTO"),
            SisterSessionState(),
            "https://base",
            "requests",
        )
    )
    assert no_link is not None and no_link.richieste_url is None

    broken = asyncio.run(
        document_not_yet_produced_error(
            _Page(
                url="https://sister/CheckRichiesta.do?requestId=R-3",
                body_error=RuntimeError("body"),
                link_error=RuntimeError("link"),
            ),
            SisterSessionState(),
            "https://base",
            "requests",
        )
    )
    assert broken is not None and broken.remote_id == "R-3"
    assert broken.richieste_url is None


@pytest.mark.parametrize(
    ("page", "ready"),
    [
        (_Page(url="https://sister/Informativa.do"), False),
        (_Page(url="https://sister/SelezioneConvenzione.do"), False),
        (_Page(url="https://sister/Visure/SelezioneConvenzione.do"), True),
        (_Page(catasto_count=1), True),
        (_Page(url="https://sister/SceltaLink.do"), True),
        (_Page(url="https://sister/RicercaIMM.do"), True),
        (_Page(immobile_count=1), True),
        (_Page(), False),
    ],
)
def test_is_visura_area_ready(page: _Page, ready: bool) -> None:
    selectors = SimpleNamespace(catasto_selector="#catasto", immobile_link_name="Immobile")
    assert asyncio.run(is_visura_area_ready(page, selectors)) is ready
