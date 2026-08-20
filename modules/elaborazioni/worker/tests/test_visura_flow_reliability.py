from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from test_visura_flow import (
    CaptchaSubmission,
    FakeBrowser,
    FakeRequest,
    SisterNotFoundError,
    VisuraFlowCallbacks,
    _current_correlation,
    _download_if_ready,
    _no_manual_async,
    _send_captcha,
    run_flow,
)


def test_subject_not_found_returns_terminal_status() -> None:
    class SubjectRequest(FakeRequest):
        search_mode = "soggetto"
        subject_kind = "PF"
        subject_id = "RSSMRA80A01H501U"
        request_type = "ATTUALITA"

    class NotFoundBrowser(FakeBrowser):
        async def search_subject_and_open_visura(self, _r) -> str | None:
            return "Nessuna corrispondenza catastale per PF 'RSSMRA80A01H501U'"

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=NotFoundBrowser(),
            request=SubjectRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
        )

    assert result.status == "not_found"
    assert "Nessuna corrispondenza" in (result.error_message or "")


def test_immobile_not_found_returns_terminal_status() -> None:
    class NotFoundBrowser(FakeBrowser):
        async def fill_visura_form(self, _request) -> None:
            raise SisterNotFoundError("Nessun immobile individuato da AdE")

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=NotFoundBrowser(),
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
        )

    assert result.status == "not_found"
    assert result.error_message == "Nessun immobile individuato da AdE"


def test_existing_remote_request_resumes_polling_without_resubmit() -> None:
    class ResumeRequest(FakeRequest):
        sister_remote_state = "pending"
        sister_remote_request_url = "https://sister/richieste?idRichiesta=REMOTE-1"
        sister_remote_request_id = "REMOTE-1"

    class ResumeBrowser(FakeBrowser):
        def __init__(self) -> None:
            super().__init__()
            self.begin_calls = 0
            self.poll_calls = 0

        async def begin_request_correlation(self, _request) -> None:
            self.begin_calls += 1

        async def poll_richieste_for_download(self, destination: Path, richieste_url: str | None = None) -> int:
            self.poll_calls += 1
            assert richieste_url == ResumeRequest.sister_remote_request_url
            return await super().poll_richieste_for_download(destination, richieste_url)

        async def open_visura_form(self) -> None:
            raise AssertionError("La richiesta remota non deve essere reinviata")

    browser = ResumeBrowser()
    remote_states: list[tuple[str | None, str | None, str]] = []
    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=ResumeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
            callbacks=VisuraFlowCallbacks(
                update_remote_state=lambda remote_id, remote_url, state: remote_states.append(
                    (remote_id, remote_url, state)
                )
            ),
        )

    assert result.status == "completed"
    assert browser.begin_calls == 1
    assert browser.poll_calls == 1
    assert [state for _, _, state in remote_states] == ["pending", "downloaded"]


def test_new_request_persists_correlation_baseline() -> None:
    class CorrelatedBrowser(FakeBrowser):
        async def begin_request_correlation(self, _request) -> None:
            self._active_request_correlation = type(
                "Correlation",
                (),
                {"baseline_keys": frozenset({"OLD-2", "OLD-1"})},
            )()

    baselines: list[list[str]] = []

    async def solve_llm(_bytes: bytes) -> str:
        return "neorave"

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=CorrelatedBrowser(),
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
            solve_llm_captcha=solve_llm,
            callbacks=VisuraFlowCallbacks(update_correlation_baseline=baselines.append),
        )

    assert result.status == "completed"
    assert baselines == [["OLD-1", "OLD-2"]]


def test_optional_callbacks_and_browser_capabilities_are_safe() -> None:
    callbacks = VisuraFlowCallbacks()
    callbacks.operation("noop")
    callbacks.remote_state(None, None, "pending")
    callbacks.correlation_baseline([])

    correlation = object()

    class MinimalBrowser:
        def get_request_correlation(self):
            return correlation

        async def submit_captcha(self, text: str) -> bool:
            return text == "ok"

    browser = MinimalBrowser()
    assert _current_correlation(browser) is correlation
    assert asyncio.run(_send_captcha(browser, CaptchaSubmission(text="ok"), callbacks))
    assert (
        asyncio.run(
            _download_if_ready(
                browser,
                FakeRequest(),
                Path("unused.pdf"),
                callbacks,
                "",
            )
        )
        is None
    )
