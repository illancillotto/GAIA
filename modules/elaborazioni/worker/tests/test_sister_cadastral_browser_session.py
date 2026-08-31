from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


WORKER_ROOT = Path(__file__).resolve().parents[1]
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from browser_session import BrowserSession
from sister_cadastral_browser_session import _recover_required_section, install_cadastral_section_recovery


class SectionPage:
    def __init__(self, values: list[str], *, required: bool = True) -> None:
        self.values = values
        self.required = required
        self.selected: list[tuple[str, str]] = []
        self.clicks: list[str] = []

    async def evaluate(self, _expression: str, *, arg=None):
        if isinstance(arg, list):
            return self.required
        assert arg == "select[name='sezione']"
        return self.values

    async def select_option(self, selector: str, *, value: str) -> None:
        self.selected.append((selector, value))

    async def click(self, selector: str) -> None:
        self.clicks.append(selector)


async def _required_section_payload() -> dict[str, object]:
    return {
        "classification": "current",
        "raw_text_excerpt": "Elenco Immobili La sezione è obbligatoria per il comune specificato.",
    }


async def _noop(*_args, **_kwargs) -> None:
    return None


def _session(values: list[str], *, required: bool = True) -> tuple[BrowserSession, SectionPage]:
    session = BrowserSession.__new__(BrowserSession)
    page = SectionPage(values, required=required)
    session._page = page
    setattr(
        session,
        "selectors",
        SimpleNamespace(
            sezione_select_selector="select[name='sezione']",
            visura_button_selector="input[name='scelta'][value='Visura']",
        ),
    )
    session._read_immobile_status_payload = _required_section_payload
    session._ensure_sezione_options_loaded = _noop
    return session, page


def test_existing_batch_wait_runs_before_section_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegated: list[str] = []
    session, page = _session(["A"], required=False)

    async def base_wait(self: BrowserSession, request_id: str) -> None:
        delegated.append(request_id)
        if len(delegated) == 1:
            page.required = True
            raise RuntimeError(
                f"Submit visura non avanzato per richiesta {request_id}: classification=current"
            )

    monkeypatch.setattr(BrowserSession, "_wait_for_visura_submission_state", base_wait)

    asyncio.run(_recover_required_section(session, "req-batch-first", base_wait))

    assert page.selected == [("select[name='sezione']", "A")]
    assert page.clicks == ["input[name='scelta'][value='Visura']"]
    assert delegated == ["req-batch-first", "req-batch-first"]


def test_required_section_recovery_selects_unique_value_and_resubmits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegated: list[str] = []

    async def base_wait(self: BrowserSession, request_id: str) -> None:
        delegated.append(request_id)
        if len(delegated) == 1:
            raise RuntimeError(
                f"Submit visura non avanzato per richiesta {request_id}: classification=current"
            )

    monkeypatch.setattr(BrowserSession, "_wait_for_visura_submission_state", base_wait)
    session, page = _session(["", "A"])

    asyncio.run(_recover_required_section(session, "req-arborea", base_wait))

    assert page.selected == [("select[name='sezione']", "A")]
    assert page.clicks == ["input[name='scelta'][value='Visura']"]
    assert delegated == ["req-arborea", "req-arborea"]


def test_required_section_recovery_rejects_duplicate_valid_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_error = RuntimeError(
        "Submit visura non avanzato per richiesta req-duplicate: classification=current"
    )

    async def base_wait(self: BrowserSession, request_id: str) -> None:
        raise original_error

    monkeypatch.setattr(BrowserSession, "_wait_for_visura_submission_state", base_wait)
    session, page = _session(["", "A", "A"])

    with pytest.raises(RuntimeError) as captured:
        asyncio.run(_recover_required_section(session, "req-duplicate", base_wait))

    assert captured.value is original_error
    assert page.selected == []
    assert page.clicks == []


def test_required_section_recovery_does_not_guess_between_multiple_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegated: list[str] = []
    original_error = RuntimeError(
        "Submit visura non avanzato per richiesta req-ambiguous: classification=current"
    )

    async def base_wait(self: BrowserSession, request_id: str) -> None:
        delegated.append(request_id)
        raise original_error

    monkeypatch.setattr(BrowserSession, "_wait_for_visura_submission_state", base_wait)
    session, page = _session(["A", "B"])

    with pytest.raises(RuntimeError) as captured:
        asyncio.run(_recover_required_section(session, "req-ambiguous", base_wait))

    assert captured.value is original_error
    assert page.selected == []
    assert page.clicks == []
    assert delegated == ["req-ambiguous"]


def test_normal_submission_delegates_without_inspecting_section_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegated: list[str] = []

    async def base_wait(self: BrowserSession, request_id: str) -> None:
        delegated.append(request_id)

    monkeypatch.setattr(BrowserSession, "_wait_for_visura_submission_state", base_wait)
    session, page = _session(["A"], required=False)

    asyncio.run(_recover_required_section(session, "req-normal", base_wait))

    assert page.selected == []
    assert page.clicks == []
    assert delegated == ["req-normal"]


def test_non_section_batch_error_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    original_error = RuntimeError(
        "Submit visura non avanzato per richiesta req-batch-error: classification=unknown"
    )

    async def base_wait(self: BrowserSession, request_id: str) -> None:
        raise original_error

    monkeypatch.setattr(BrowserSession, "_wait_for_visura_submission_state", base_wait)
    session, page = _session(["A"], required=False)

    with pytest.raises(RuntimeError) as captured:
        asyncio.run(_recover_required_section(session, "req-batch-error", base_wait))

    assert captured.value is original_error
    assert page.selected == []
    assert page.clicks == []


def test_authoritative_batch_error_is_not_overridden_by_required_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_error = RuntimeError("SISTER 500 dal flusso batch")

    async def base_wait(self: BrowserSession, request_id: str) -> None:
        raise original_error

    monkeypatch.setattr(BrowserSession, "_wait_for_visura_submission_state", base_wait)
    session, page = _session(["A"], required=True)

    with pytest.raises(RuntimeError) as captured:
        asyncio.run(_recover_required_section(session, "req-server-error", base_wait))

    assert captured.value is original_error
    assert page.selected == []
    assert page.clicks == []


def test_recovery_inspection_error_preserves_batch_error() -> None:
    original_error = RuntimeError(
        "Submit visura non avanzato per richiesta req-inspection: classification=current"
    )
    inspection_error = ValueError("DOM non leggibile")
    session, page = _session(["A"], required=True)

    async def base_wait(self: BrowserSession, request_id: str) -> None:
        raise original_error

    async def fail_evaluate(_expression: str, *, arg=None):
        raise inspection_error

    page.evaluate = fail_evaluate

    with pytest.raises(RuntimeError) as captured:
        asyncio.run(_recover_required_section(session, "req-inspection", base_wait))

    assert captured.value is original_error
    assert captured.value.__cause__ is inspection_error
    assert page.selected == []
    assert page.clicks == []


def test_recovery_option_inspection_error_preserves_batch_error() -> None:
    original_error = RuntimeError(
        "Submit visura non avanzato per richiesta req-options-error: classification=current"
    )
    inspection_error = ValueError("Opzioni non leggibili")
    session, page = _session(["A"], required=True)

    async def base_wait(self: BrowserSession, request_id: str) -> None:
        raise original_error

    async def fail_options(_expression: str, *, arg=None):
        if isinstance(arg, list):
            return True
        raise inspection_error

    page.evaluate = fail_options

    with pytest.raises(RuntimeError) as captured:
        asyncio.run(_recover_required_section(session, "req-options-error", base_wait))

    assert captured.value is original_error
    assert captured.value.__cause__ is inspection_error
    assert page.selected == []
    assert page.clicks == []


def test_required_section_recovery_rejects_zero_valid_options() -> None:
    original_error = RuntimeError(
        "Submit visura non avanzato per richiesta req-zero: classification=current"
    )
    session, page = _session(["", "  "], required=True)

    async def base_wait(self: BrowserSession, request_id: str) -> None:
        raise original_error

    with pytest.raises(RuntimeError) as captured:
        asyncio.run(_recover_required_section(session, "req-zero", base_wait))

    assert captured.value is original_error
    assert page.selected == []
    assert page.clicks == []


def test_second_batch_wait_failure_does_not_trigger_another_resubmit() -> None:
    second_error = RuntimeError("Seconda attesa batch non avanzata")
    calls: list[str] = []
    session, page = _session(["A"], required=True)

    async def base_wait(self: BrowserSession, request_id: str) -> None:
        calls.append(request_id)
        if len(calls) == 1:
            raise RuntimeError(
                f"Submit visura non avanzato per richiesta {request_id}: classification=current"
            )
        raise second_error

    with pytest.raises(RuntimeError) as captured:
        asyncio.run(_recover_required_section(session, "req-second-failure", base_wait))

    assert captured.value is second_error
    assert calls == ["req-second-failure", "req-second-failure"]
    assert page.selected == [("select[name='sezione']", "A")]
    assert page.clicks == ["input[name='scelta'][value='Visura']"]


def test_recovery_installer_is_noop_without_target_method(monkeypatch: pytest.MonkeyPatch) -> None:
    import sister_cadastral_browser_session as recovery_module

    monkeypatch.setattr(recovery_module, "BrowserSession", object)

    recovery_module.install_cadastral_section_recovery()


def test_reliability_module_installs_cadastral_section_recovery() -> None:
    import ast

    source = (WORKER_ROOT / "sister_worker_reliability.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]

    assert any(
        node.module == "sister_cadastral_browser_session"
        and any(alias.name == "install_cadastral_section_recovery" for alias in node.names)
        for node in imports
    )
    assert any(
        isinstance(node.func, ast.Name) and node.func.id == "install_cadastral_section_recovery"
        for node in calls
    )


def test_recovery_installer_is_idempotent() -> None:
    delegated: list[str] = []

    async def base_wait(self: BrowserSession, request_id: str) -> None:
        delegated.append(request_id)

    original = BrowserSession._wait_for_visura_submission_state
    try:
        BrowserSession._wait_for_visura_submission_state = base_wait
        install_cadastral_section_recovery()
        installed = BrowserSession._wait_for_visura_submission_state
        session, _page = _session([], required=False)
        asyncio.run(installed(session, "req-installed"))
        install_cadastral_section_recovery()

        assert BrowserSession._wait_for_visura_submission_state is installed
        assert delegated == ["req-installed"]
    finally:
        BrowserSession._wait_for_visura_submission_state = original
