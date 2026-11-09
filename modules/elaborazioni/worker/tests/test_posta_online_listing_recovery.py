import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from posta_online_listing_recovery import ListingUnavailable, load_listing

URL = "https://corrispondenza.poste.it/col/incorso.do?page=2"


def client(*, counts=(1,), body="", navigate=None, attached=None):
    table = SimpleNamespace(
        count=AsyncMock(side_effect=counts), wait_for=AsyncMock(side_effect=attached)
    )
    content = SimpleNamespace(inner_text=AsyncMock(return_value=body))
    page = SimpleNamespace(
        goto=AsyncMock(side_effect=navigate),
        locator=lambda selector: table if selector == "#col_invio_dett" else content,
    )
    return SimpleNamespace(
        page=page,
        throttle=SimpleNamespace(wait=AsyncMock(), wait_retry=AsyncMock()),
    ), table


def test_normal_page_is_loaded_once_without_refresh():
    c, table = client()
    asyncio.run(load_listing(c, URL, "draft"))
    c.page.goto.assert_awaited_once_with(URL, wait_until="commit")
    table.wait_for.assert_awaited_once_with(state="attached")
    c.throttle.wait_retry.assert_not_called()


@pytest.mark.parametrize("message", ["Oops! Si è verificato un errore", "OPS riprova più tardi"])
def test_oops_is_refreshed_once_on_the_same_page_after_cooldown(message):
    c, table = client(counts=(0, 1), body=message)
    asyncio.run(load_listing(c, URL, "reconcile"))
    assert c.page.goto.await_count == 2
    assert all(call.args[0] == URL for call in c.page.goto.await_args_list)
    c.throttle.wait_retry.assert_awaited_once_with("dispatch:list-refresh", 1)
    table.wait_for.assert_awaited_once()


@pytest.mark.parametrize("stage", ["navigation", "table"])
def test_timeout_retries_only_the_read_without_any_submit_action(stage):
    kwargs = {"navigate": [PlaywrightTimeoutError("Timeout"), None]}
    if stage == "table":
        kwargs = {"counts": (1, 1), "attached": [PlaywrightTimeoutError("Timeout"), None]}
    c, _ = client(**kwargs)
    asyncio.run(load_listing(c, URL, "draft"))
    assert c.page.goto.await_count == 2
    c.throttle.wait_retry.assert_awaited_once()


def test_second_failure_escalates_to_job_retry_instead_of_endless_refreshes():
    c, _ = client(counts=(0, 0), body="Oops")
    with pytest.raises(ListingUnavailable, match="Oops"):
        asyncio.run(load_listing(c, URL, "reconcile"))
    assert c.page.goto.await_count == 2
    c.throttle.wait_retry.assert_awaited_once()


def test_a_missing_table_still_waits_and_never_becomes_a_false_empty_list():
    c, table = client(counts=(0,), body="Elenco in caricamento")
    asyncio.run(load_listing(c, URL, "reconcile"))
    table.wait_for.assert_awaited_once_with(state="attached")


def test_nontransient_errors_do_not_refresh():
    c, _ = client(navigate=RuntimeError("Sessione non autorizzata"))
    with pytest.raises(RuntimeError, match="non autorizzata"):
        asyncio.run(load_listing(c, URL, "reconcile"))
    c.page.goto.assert_awaited_once()
    c.throttle.wait_retry.assert_not_called()


@pytest.mark.parametrize(
    "url",
    [
        "https://corrispondenza.poste.it/col/invioDestinatari.do",
        "https://corrispondenza.poste.it/col/inserisciInvii.do",
        "https://corrispondenza.poste.it/col/paga.do",
        "http://corrispondenza.poste.it/col/incorso.do",
        "https://other.test/col/incorso.do",
    ],
)
def test_submission_payment_or_external_pages_are_never_refreshed(url):
    c, _ = client()
    with pytest.raises(ValueError, match="solo sugli elenchi"):
        asyncio.run(load_listing(c, url, "draft"))
    c.page.goto.assert_not_called()


def test_archive_pages_use_the_same_recovery():
    c, _ = client()
    asyncio.run(load_listing(c, "https://corrispondenza.poste.it/col/archivio.do", "reconcile"))
    c.page.goto.assert_awaited_once()
