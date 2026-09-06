"""Regressions for SISTER menu/province states observed after remote recovery."""

import asyncio
import shutil

import pytest
from browser_test_support import make_session
from playwright.async_api import async_playwright


@pytest.mark.parametrize("expanded", [False, True])
def test_reused_menu_does_not_toggle_closed_and_skips_already_accepted_notice(expanded):
    async def scenario():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path=shutil.which("google-chrome"), headless=True
            )
            try:
                page = await browser.new_page()
                page.set_default_timeout(500)
                visits = []
                menu_open = expanded

                async def serve(route):
                    nonlocal menu_open
                    path = route.request.url.split(".gov.it")[-1]
                    visits.append(path)
                    if path == "/Visure/Informativa.do":
                        # SISTER keeps Informativa.do in the URL after prior acceptance.
                        body = '<title>Scelta province</title><select name="listacom"><option value="OR">OR</option></select>'
                    else:
                        if path == "/consultazioni":
                            menu_open = not menu_open
                        body = '<a href="/consultazioni">Consultazioni e Certificazioni</a>'
                        if menu_open:
                            body += '<a href="/Visure/Informativa.do">Visure catastali</a>'
                    await route.fulfill(body=body, content_type="text/html")

                await page.route("**/*", serve)
                await page.goto("https://sister3.agenziaentrate.gov.it/Servizi/")
                session = make_session(page)
                await session._goto_visura_menu()
                assert visits == ["/Servizi/"] + ([] if expanded else ["/consultazioni"]) + [
                    "/Visure/Informativa.do"
                ]
                assert await page.locator(session.selectors.territorio_selector).count() == 1
            finally:
                await browser.close()

    asyncio.run(scenario())
