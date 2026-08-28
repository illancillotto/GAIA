from __future__ import annotations

import asyncio

import pytest
from posta_online_client import PostaOnlineBrowserClient, PostaOnlineScrapeConfig
from test_posta_online_client import FakeLocator, FakePage


def test_exit_scrape_archive_and_retry_residual_branches() -> None:
    calls: list[str] = []

    class Browser:
        async def close(self) -> None:
            calls.append("browser.close")

    class Playwright:
        async def stop(self) -> None:
            calls.append("playwright.stop")

    client = PostaOnlineBrowserClient(PostaOnlineScrapeConfig())
    client._browser = Browser()
    client._playwright = Playwright()
    asyncio.run(client.__aexit__())
    assert calls == ["browser.close", "playwright.stop"]

    empty = PostaOnlineBrowserClient(PostaOnlineScrapeConfig())
    asyncio.run(empty.__aexit__())

    class NoFetchClient(PostaOnlineBrowserClient):
        async def discover_archive_invii(self):
            raise AssertionError("archive checkpoint must be reused")

    no_contacts = NoFetchClient(
        PostaOnlineScrapeConfig(include_contacts=False, include_details=False)
    )
    payload = asyncio.run(
        no_contacts.scrape_registered_mails(
            resume_payload={"archive_ids": ["A"], "completed_scopes": ["archive"]}
        )
    )
    assert payload["archive_ids"] == ["A"]

    no_pages = PostaOnlineBrowserClient(PostaOnlineScrapeConfig(max_pages=0))
    no_pages._page = FakePage()
    assert asyncio.run(no_pages.discover_archive_invii()) == []

    duplicate_client = PostaOnlineBrowserClient(
        PostaOnlineScrapeConfig(max_pages=2, max_details=10)
    )
    duplicate_page = FakePage(html_pages=["idInvio=1111", "idInvio=1111"])
    duplicate_page.locators["ul.pagination a"] = FakeLocator(href="/next")
    duplicate_client._page = duplicate_page
    duplicate_client.throttle.wait = lambda _label: asyncio.sleep(0)
    assert asyncio.run(duplicate_client.discover_archive_invii()) == ["1111"]

    no_attempts = PostaOnlineBrowserClient(PostaOnlineScrapeConfig(max_retries=-2))
    with pytest.raises(RuntimeError, match="fallito"):
        asyncio.run(no_attempts._request_with_backoff("empty", lambda: None))
