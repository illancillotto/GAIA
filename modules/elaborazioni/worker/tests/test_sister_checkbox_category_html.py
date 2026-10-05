import asyncio
import shutil
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from playwright.async_api import async_playwright

from browser_session import BrowserSession
from sister_exceptions import SisterInvalidDocumentError, SisterNonEvadibileReviewRequiredError
from sister_request_rows import SisterRequestCorrelation, correlate_remote_row
from sister_requests_navigation import read_correlated_category_row
from sister_worker_reliability import SisterRequestRepository, is_recoverable_credential_error


@pytest.mark.parametrize(
    "category,label,expected",
    [
        ("nonEspletabili", "Non evadibili", "review"),
        ("espletate", "Espletate", "ready"),
        ("prelevate", "Prelevate", "ready"),
        ("espletate", "Non evadibili", "unknown"),
    ],
)
def test_checkbox_only_row_uses_verified_category_without_remote_actions(category, label, expected):
    async def scenario():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path=shutil.which("google-chrome"), headless=True
            )
            try:
                page = await browser.new_page()
                await page.set_content(
                    f'<input type="radio" name="radioCount" value="{category}" checked>'
                    "<table><tr><th>Richiesta del</th><th>Oggetto</th><th>elimina</th></tr>"
                    "<tr><td>05/10/2026 08:36:48</td><td>VISURA FG. 6 PART. 377</td>"
                    '<td><input type="checkbox" name="idElemento" value="2060784896"></td>'
                    "</tr><tr><td>Altra richiesta</td><td>VISURA</td>"
                    '<td><input type="checkbox" name="idElemento" value="999"></td></tr></table>'
                    '<input type="submit" name="metodo" value="Elimina">'
                    '<script>window.actions=0;document.addEventListener("click",()=>actions++);</script>'
                )
                correlation = SisterRequestCorrelation("local", frozenset(), (), "2060784896")

                async def find_row():
                    return correlate_remote_row(
                        await BrowserSession._extract_remote_request_rows(page), correlation
                    )

                if expected == "review":
                    with pytest.raises(SisterNonEvadibileReviewRequiredError) as captured:
                        await read_correlated_category_row(page, label, find_row)
                    assert not is_recoverable_credential_error(
                        captured.value, SisterInvalidDocumentError
                    )
                else:
                    result = await read_correlated_category_row(page, label, find_row)
                    assert result.remote_id == "2060784896"
                    assert result.state == expected
                assert await page.evaluate("window.actions") == 0
                assert await page.locator("input[name='idElemento']:checked").count() == 0
                assert (await find_row()).state == "unknown"
            finally:
                await browser.close()

    asyncio.run(scenario())


def test_review_error_stops_request_without_defer_or_false_deletion(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_MASTER_KEY", Fernet.generate_key().decode())
    from worker import CatastoWorker, _SisterBatchRuntime

    error = SisterNonEvadibileReviewRequiredError("SISTER non evadibile: richiesta conservata")
    runtime = object.__new__(_SisterBatchRuntime)
    runtime.worker = MagicMock()
    runtime.worker._is_recoverable_credential_error = CatastoWorker._is_recoverable_credential_error
    runtime.credential_pool = MagicMock()
    runtime.batch_id = uuid4()
    runtime.request_repository = MagicMock()
    runtime.shared_state_lock = asyncio.Lock()
    runtime.credential_server_error_counts = {}
    runtime._restart_browser = AsyncMock(return_value=None)
    runtime._defer_recoverable_error = AsyncMock()
    credential = SimpleNamespace(id=uuid4(), sister_username="test")
    selection = SimpleNamespace(request_id=uuid4(), execution_token=uuid4())
    session = SimpleNamespace(browser=None)
    asyncio.run(runtime._handle_request_error(credential, session, selection, error))
    runtime._defer_recoverable_error.assert_not_awaited()
    runtime.request_repository.fail_request.assert_called_once_with(
        runtime.batch_id, selection.request_id, str(error), selection.execution_token
    )
    request = SimpleNamespace(
        sister_remote_request_id="2060784896",
        sister_remote_state="pending",
        sister_first_submitted_at="original",
        sister_credential_id=credential.id,
    )
    SisterRequestRepository._mark_request_failed(request, str(error), "Verifica manuale")
    assert request.status == "failed"
    assert request.retry_not_before is None
    assert request.sister_remote_request_id == "2060784896"
    assert request.sister_remote_state == "pending"
    assert request.sister_first_submitted_at == "original"
    assert request.sister_credential_id == credential.id
