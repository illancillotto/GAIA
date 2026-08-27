from __future__ import annotations

import asyncio

import pytest

from browser_test_support import ScriptedLocator, ScriptedPage
from sister_exceptions import SisterInvalidDocumentError
from sister_visura_selection import (
    expected_request_type,
    reconfirm_visura_type,
    request_type_selection_matches,
    select_request_type,
    select_visura_type,
)


def run(coro):
    return asyncio.run(coro)


class ClickErrorLocator(ScriptedLocator):
    async def click(self, timeout: int | None = None) -> None:
        raise RuntimeError("click")


class CheckErrorLocator(ScriptedLocator):
    async def check(self, timeout: int | None = None) -> None:
        raise RuntimeError("check")


class UncheckedLocator(ScriptedLocator):
    async def is_checked(self) -> bool:
        return False


def test_expected_request_type_prefers_explicit_value_and_infers_legacy_visure() -> None:
    assert expected_request_type("storica", "0") == "STORICA"
    assert expected_request_type("attualita", "4") == "ATTUALITA"
    assert expected_request_type(None, "0") == "ATTUALITA"
    assert expected_request_type(None, "3") == "STORICA"


def test_request_type_selection_fails_closed_after_click_or_dom_errors() -> None:
    page = ScriptedPage()
    page.locators["label:has-text('Storica')"] = ScriptedLocator()
    page.evaluate_results = [True]
    run(select_request_type(page, "STORICA"))

    page.locators = {"label:has-text('Attualità')": ScriptedLocator(visible=False)}
    run(select_request_type(page, "ATTUALITA"))

    page.locators["label:has-text('Storica')"] = ClickErrorLocator()
    with pytest.raises(SisterInvalidDocumentError, match="richiesta storica"):
        run(select_request_type(page, "STORICA"))

    page.evaluate_error = RuntimeError("evaluate")
    assert run(request_type_selection_matches(page, "Storica")) is False


def test_visura_type_selection_handles_missing_optional_and_required_radios() -> None:
    page = ScriptedPage()
    run(select_visura_type(page, "input[name='tipoVisura']", "Completa", "0", required=False))
    with pytest.raises(SisterInvalidDocumentError, match="non ha esposto"):
        run(select_visura_type(page, "input[name='tipoVisura']", "Analitica", "3", required=True))


@pytest.mark.parametrize(
    ("locator", "message"),
    [
        (CheckErrorLocator(), "non ha selezionato"),
        (UncheckedLocator(), "non ha confermato"),
    ],
)
def test_visura_type_selection_rejects_unconfirmed_radios(locator: ScriptedLocator, message: str) -> None:
    page = ScriptedPage()
    page.locators["input[name='tipoVisura'][value='3']"] = locator

    with pytest.raises(SisterInvalidDocumentError, match=message):
        run(select_visura_type(page, "input[name='tipoVisura']", "Analitica", "3", required=True))


def test_reconfirm_visura_type_handles_retry_and_separate_captcha_page() -> None:
    page = ScriptedPage()
    selector = "input[name='tipoVisura'][value='3']"
    page.locators[selector] = ScriptedLocator()

    run(reconfirm_visura_type(page, "input[name='tipoVisura']", ("Analitica", "3")))
    run(reconfirm_visura_type(page, "input[name='tipoVisura']", None))

    assert page.locators[selector].checks == 1

    page.locators = {}
    run(reconfirm_visura_type(page, "input[name='tipoVisura']", ("Analitica", "3")))
