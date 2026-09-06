"""Browser regression for the radio form observed on the CED on 2026-09-05."""

import asyncio
import shutil
import sys
from pathlib import Path
from urllib.parse import parse_qs

import pytest
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from browser_test_support import make_session

from sister_request_rows import SisterRequestCorrelation
from sister_requests_navigation import find_in_requests_category, select_requests_category


@pytest.mark.parametrize("target_visible", [True, False])
def test_global_counters_do_not_skip_backlog_or_authorize_foreign_downloads(target_visible, caplog):
    async def scenario():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path=shutil.which("google-chrome"), headless=True
            )
            try:
                page = await browser.new_page()
                visits, unexpected = [], []

                async def serve(route):
                    if not route.request.url.endswith("/requests"):
                        unexpected.append(route.request.url)
                        await route.abort()
                        return
                    params = parse_qs(route.request.post_data or "")
                    category = params.get("radioCount", ["espletate"])[0]
                    day = params.get("comboGiorni", ["05/09/2026"])[0]
                    if params:
                        visits.append((category, day))
                    rows = "".join(
                        f'<tr><td>Estranea {i}</td><td><a href="/CheckRichiesta.do?idRichiesta=OTHER-{i}">apri</a></td></tr>'
                        for i in range(40)
                    )
                    if target_visible and (category, day) == ("prelevate", "04/09/2026"):
                        rows += '<tr><td>Visura richiesta</td><td><a href="/CheckRichiesta.do?idRichiesta=TARGET">apri</a></td></tr>'
                    # Counters stay unchanged across days, including the empty current day.
                    if day == "05/09/2026":
                        rows = ""
                    await route.fulfill(
                        body=filtered_form(category, day) + "<table>" + rows + "</table>",
                        content_type="text/html",
                    )

                await page.route("http://sister.test/**", serve)
                await page.goto("http://sister.test/requests")
                session = make_session(page)
                session._session_state.correlation = SisterRequestCorrelation(
                    "local", frozenset(), (), remote_id="TARGET"
                )
                downloaded = []

                async def download(row, _destination):
                    downloaded.append(row.remote_id)
                    return 123

                session._download_correlated_row = download
                result = await session._poll_correlated_tabs(
                    "ESPLETATE 0 PRELEVATE 669", Path("unused.pdf")
                )
                assert result == (123 if target_visible else None)
                assert downloaded == (["TARGET"] if target_visible else [])
                assert visits == [
                    (category, day)
                    for category in ("nonEspletabili", "espletate", "prelevate")
                    for day in ("-", "05/09/2026", "04/09/2026")
                ]
                assert unexpected == []
                assert session.get_request_correlation().remote_id == "TARGET"
            finally:
                await browser.close()

    asyncio.run(scenario())
    if not target_visible:
        assert "elenco potenzialmente limitato" in caplog.text


FORM = """
<form method="post" action="/requests">
  <table><tr>
    <td><input type="radio" name="radioCount" value="espletate" checked>espletate: 0</td>
    <td><input type="radio" name="radioCount" value="nonEspletabili">non evadibili: 246</td>
    <td><input type="radio" name="radioCount" value="prelevate">prelevate: 669</td>
  </tr></table>
  <select name="comboGiorni">
    <option value="05/09/2026">05/09/2026</option>
    <option value="04/09/2026">04/09/2026</option>
    <option value="-">Intero periodo</option>
  </select>
  <input type="submit" name="metodo" value="Aggiorna">
</form>
"""


def filtered_form(category, day):
    return (
        FORM.replace('value="espletate" checked', 'value="espletate"')
        .replace(f'value="{category}"', f'value="{category}" checked')
        .replace(f'<option value="{day}">', f'<option value="{day}" selected>')
    )


@pytest.mark.parametrize(
    "label,value",
    [("Non evadibili", "nonEspletabili"), ("Espletate", "espletate"), ("Prelevate", "prelevate")],
)
def test_real_form_requires_radio_and_submit(label, value):
    async def scenario():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path=shutil.which("google-chrome"), headless=True
            )
            try:
                page = await browser.new_page()
                submitted = []

                async def serve(route):
                    if route.request.method == "POST":
                        submitted.append(parse_qs(route.request.post_data))
                        await route.fulfill(
                            body=filtered_form(value, "-") + "<p id='result'>filtered request</p>",
                            content_type="text/html",
                        )
                    else:
                        await route.fulfill(body=FORM, content_type="text/html")

                await page.route("http://sister.test/**", serve)
                await page.goto("http://sister.test/requests")
                # The old cell click neither checks the radio nor submits the form.
                await page.locator("td").last.click()
                assert submitted == []
                assert await select_requests_category(page, label)
                assert submitted == [
                    {"radioCount": [value], "comboGiorni": ["-"], "metodo": ["Aggiorna"]}
                ]
                assert await page.locator("#result").inner_text() == "filtered request"
            finally:
                await browser.close()

    asyncio.run(scenario())


def test_accumulated_request_found_only_in_previous_day():
    async def scenario():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path=shutil.which("google-chrome"), headless=True
            )
            try:
                page = await browser.new_page()
                submitted = []

                async def serve(route):
                    params = parse_qs(route.request.post_data or "")
                    day = params.get("comboGiorni", [None])[0]
                    if day:
                        submitted.append(day)
                    row_id = "REMOTE-TARGET" if day == "04/09/2026" else "UNRELATED"
                    await route.fulfill(
                        body=filtered_form("espletate", day or "05/09/2026")
                        + f"<p id='request'>{row_id}</p>",
                        content_type="text/html",
                    )

                async def find_row():
                    value = await page.locator("#request").inner_text()
                    return value if value == "REMOTE-TARGET" else None

                await page.route("http://sister.test/**", serve)
                await page.goto("http://sister.test/requests")
                assert (
                    await find_in_requests_category(page, "Espletate", find_row) == "REMOTE-TARGET"
                )
                assert submitted == ["-", "05/09/2026", "04/09/2026"]
            finally:
                await browser.close()

    asyncio.run(scenario())
