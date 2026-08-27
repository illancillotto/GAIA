from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from browser_test_support import ScriptedLocator, ScriptedPage
from sister_document_validation import reject_unexpected_document_type
from sister_exceptions import SisterInvalidDocumentError
from sister_visura_selection import select_request_type


def test_document_type_mismatch_without_local_file_fails_closed() -> None:
    result = SimpleNamespace(
        document_audit_payload={
            "document_request_type": {
                "matches": False,
                "expected": None,
                "observed": None,
            }
        },
        file_path=None,
    )

    with pytest.raises(
        SisterInvalidDocumentError,
        match="richiesto NON_CLASSIFICATO, scaricato NON_CLASSIFICATO",
    ):
        reject_unexpected_document_type(result)


def test_request_type_selection_tries_the_second_visible_selector() -> None:
    page = ScriptedPage()
    page.locators["label:has-text('Storica')"] = ScriptedLocator()
    page.locators[
        "input[type='radio'] >> xpath=following-sibling::label[contains(., 'Storica')]"
    ] = ScriptedLocator()
    page.evaluate_results = [False, True]

    asyncio.run(select_request_type(page, "STORICA"))

    assert len(page.evaluate_results) == 0
