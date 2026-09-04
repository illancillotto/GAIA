from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

import pytest

WORKER_ROOT = Path(__file__).resolve().parents[1]

if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

SisterNotFoundError = importlib.import_module("sister_exceptions").SisterNotFoundError
visura_flow = importlib.import_module("visura_flow")
VisuraFlowCallbacks = visura_flow.VisuraFlowCallbacks
_immobile_section_attempts = visura_flow._immobile_section_attempts
_prepare_immobile_request = visura_flow._prepare_immobile_request


class SimaxisRequest:
    id = "simaxis-request"
    comune = "Simaxis"
    comune_codice = "I743#SIMAXIS#2#2"

    def __init__(self, section: str | None = None) -> None:
        self.sezione = section


class SectionBrowser:
    def __init__(self, *, fail_sections: set[str] | None = None) -> None:
        self.fail_sections = fail_sections or set()
        self.open_calls = 0
        self.sections: list[str | None] = []

    async def open_visura_form(self) -> None:
        self.open_calls += 1

    async def fill_visura_form(self, request) -> None:
        self.sections.append(request.sezione)
        if request.sezione in self.fail_sections:
            raise SisterNotFoundError("Nessun immobile individuato da AdE")

    async def prepare_captcha_or_download(self) -> str:
        return "download"

    async def download_pdf(self, document_path: Path) -> int:
        document_path.write_bytes(b"%PDF-1.4\n")
        return document_path.stat().st_size


def _run_immobile_flow(browser, request, document_path: Path, operations: list[str] | None = None):
    callbacks = VisuraFlowCallbacks(
        update_operation=operations.append if operations is not None else None
    )
    return asyncio.run(_prepare_immobile_request(browser, request, document_path, callbacks))


def test_simaxis_tries_section_b_only_after_not_found_in_a(tmp_path: Path) -> None:
    browser = SectionBrowser(fail_sections={"A"})
    request = SimaxisRequest()
    operations: list[str] = []

    result = _run_immobile_flow(browser, request, tmp_path / "visura.pdf", operations)

    assert result is not None
    assert result.status == "completed"
    assert browser.open_calls == 2
    assert browser.sections == ["A", "B"]
    assert request.sezione == "B"
    assert any("sezione B" in operation for operation in operations)


def test_simaxis_reports_not_found_only_after_both_sections(tmp_path: Path) -> None:
    browser = SectionBrowser(fail_sections={"A", "B"})

    result = _run_immobile_flow(browser, SimaxisRequest("A"), tmp_path / "visura.pdf")

    assert result is not None
    assert result.status == "not_found"
    assert browser.sections == ["A", "B"]
    assert (
        result.error_message == "Nessun immobile individuato da AdE nelle sezioni A e B di Simaxis."
    )


def test_simaxis_does_not_fallback_after_generic_error(tmp_path: Path) -> None:
    class FailingBrowser(SectionBrowser):
        async def fill_visura_form(self, request) -> None:
            self.sections.append(request.sezione)
            raise RuntimeError("SISTER non disponibile")

    browser = FailingBrowser()

    with pytest.raises(RuntimeError, match="SISTER non disponibile"):
        _run_immobile_flow(browser, SimaxisRequest(), tmp_path / "visura.pdf")

    assert browser.open_calls == 1
    assert browser.sections == ["A"]


def test_section_attempts_preserve_explicit_and_unrelated_sections() -> None:
    assert _immobile_section_attempts(SimaxisRequest("B")) == ("B",)
    assert _immobile_section_attempts(SimaxisRequest("C")) == ("C",)
    assert _immobile_section_attempts(type("Request", (), {"comune": "Oristano"})()) == (None,)
    assert _immobile_section_attempts(type("Request", (), {"comune": " simaxis "})()) == ("A", "B")
