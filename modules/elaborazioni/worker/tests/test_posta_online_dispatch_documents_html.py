"""Exercise the actual FileLists, SHA-256 script and storage lifecycle in Chromium."""

from __future__ import annotations

import asyncio
import hashlib
import shutil
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from playwright.async_api import async_playwright
from test_posta_online_dispatch import _item

import posta_online_dispatch as dispatch
from posta_online_dispatch import (
    POSTA_ONLINE_SEND_HOME_URL,
    DraftNotSubmitted,
    PostaOnlineDispatchPortal,
)

FORM = Path(__file__).parent / "fixtures" / "poste_document_form.html"


async def _browser_scenario(action, home_url=POSTA_ONLINE_SEND_HOME_URL):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=shutil.which("google-chrome"), headless=True
        )
        try:
            page = await browser.new_page()
            if home_url == POSTA_ONLINE_SEND_HOME_URL:
                await page.route(
                    "**/*", lambda route: route.fulfill(path=FORM, content_type="text/html")
                )
            client = SimpleNamespace(
                page=page,
                throttle=SimpleNamespace(wait=AsyncMock()),
                _prepare_login_page=AsyncMock(),
            )
            portal = PostaOnlineDispatchPortal(client)
            portal._open_ar_form = AsyncMock()
            portal._fill_recipient = AsyncMock()
            await page.goto(home_url)
            await action(portal)
        finally:
            await browser.close()


def test_home_navigation_restores_the_old_notice_and_new_shipment_removes_it(tmp_path):
    source = tmp_path / "GAIA_020210000815390.pdf"
    source.write_bytes(b"%PDF-current-notice")

    async def scenario(portal):
        page = portal.page
        await page.evaluate("""() => sessionStorage.setItem('file_0', JSON.stringify({
            name: 'GAIA_020210000654720.pdf', body: '%PDF-previous-notice'
        }))""")
        # Regression reproduction: opening home.do directly restores the old file.
        await page.goto(POSTA_ONLINE_SEND_HOME_URL)
        await page.locator("#file").set_input_files(str(source))
        assert await page.locator(".file-upload-item").count() == 2
        with pytest.raises(RuntimeError, match="Allegati Poste non conformi"):
            await portal._verify_document(source)
        await portal._fill_form(_item(), source)
        assert await page.locator(".file-upload-item").count() == 1
        await portal._verify_document(source)
        # Simulate the next notice: the prior document is still in browser storage.
        await page.evaluate("""() => sessionStorage.setItem('file_0', JSON.stringify({
            name: 'GAIA_020210000815390.pdf', body: '%PDF-current-notice'
        }))""")
        second = tmp_path / "GAIA_020210000910370.pdf"
        second.write_bytes(b"%PDF-next-notice")
        await portal._fill_form(_item(), second)
        await portal._verify_document(second)
        multipart = await page.evaluate("""async () => {
            const form = new FormData(document.forms[0]);
            return await Promise.all(Array.from(form.entries())
                .filter(([key, value]) => value instanceof File && value.size)
                .map(async ([key, value]) => [key, value.name, await value.text()]));
        }""")
        assert multipart == [["files0", second.name, "%PDF-next-notice"]]

    asyncio.run(_browser_scenario(scenario))


@pytest.mark.parametrize(
    "corruption", ["hidden", "content", "card", "queue", "count", "text", "slot"]
)
def test_any_mismatch_between_source_and_submitted_documents_stops_continua(tmp_path, corruption):
    source = tmp_path / "GAIA_020210000815390.pdf"
    source.write_bytes(b"%PDF-correct")

    async def scenario(portal):
        page = portal.page
        original_fill = portal._fill_recipient

        async def corrupt(item):
            await original_fill(item)
            await page.evaluate(
                """mode => {
                const makeFiles = body => {
                    const dt = new DataTransfer();
                    dt.items.add(new File([body], 'GAIA_020210000815390.pdf'));
                    return dt.files;
                };
                if (mode === 'hidden') document.getElementById('file1').files = makeFiles('extra');
                if (mode === 'content') document.getElementById('file0').files = makeFiles('%PDF-foreign');
                if (mode === 'card') document.querySelector('.file-upload-item div').textContent = 'other.pdf';
                if (mode === 'queue') mainDt.push(new File(['extra'], 'extra.pdf'));
                if (mode === 'count') indexCount++;
                if (mode === 'text') document.getElementById('testo').value = 'previous letter';
                if (mode === 'slot') {
                    document.getElementById('file1').files = document.getElementById('file0').files;
                    document.getElementById('file0').value = '';
                }
            }""",
                corruption,
            )

        portal._fill_recipient = corrupt
        before_submit = AsyncMock()
        with pytest.raises(DraftNotSubmitted, match="Allegati Poste non conformi"):
            await portal.create_draft(_item(), source.read_bytes(), before_submit)
        before_submit.assert_not_awaited()
        assert await page.locator("#continua").count() == 1
        assert page.url == POSTA_ONLINE_SEND_HOME_URL

    asyncio.run(_browser_scenario(scenario))


def test_browser_hashes_binary_pdf_bytes_instead_of_trusting_filename_and_size(tmp_path):
    source = tmp_path / "binary.pdf"
    source.write_bytes(b"%PDF-\x00\xff\xfe\x80")

    async def scenario(portal):
        from posta_online_dispatch import _DOCUMENT_STATE

        await portal._open_clean_form()
        await portal.page.locator("#file").set_input_files(str(source))
        state = await portal.page.evaluate(_DOCUMENT_STATE)
        assert state["files"][0]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
        await portal._verify_document(source)

    asyncio.run(_browser_scenario(scenario))


def test_two_consecutive_submissions_each_send_only_their_own_pdf(monkeypatch):
    submitted = []

    class Receiver(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(FORM.read_bytes())

        def do_POST(self):
            submitted.append(self.rfile.read(int(self.headers["Content-Length"])))
            self.do_GET()

        def log_message(self, *_args):
            pass

    async def scenario(portal):
        page = portal.page
        first = _item()
        second = replace(_item(), shipment_name="GAIA 020210000815390")
        await portal.create_draft(first, b"%PDF-first-notice", AsyncMock())
        # This is the state the real portal leaves behind after the first upload.
        await page.evaluate("""() => sessionStorage.setItem('file_0', JSON.stringify({
            name: 'GAIA_020217801062586.pdf', body: '%PDF-first-notice'
        }))""")
        await portal.create_draft(second, b"%PDF-second-notice", AsyncMock())
        assert len(submitted) == 2
        assert submitted[0].count(b'filename="GAIA_020217801062586.pdf"') == 1
        assert b"%PDF-first-notice" in submitted[0]
        assert submitted[1].count(b'filename="GAIA_020210000815390.pdf"') == 1
        assert b"%PDF-second-notice" in submitted[1]
        assert b"%PDF-first-notice" not in submitted[1]
        assert b"GAIA_020217801062586.pdf" not in submitted[1]

    with ThreadingHTTPServer(("127.0.0.1", 0), Receiver) as server:
        home_url = f"http://127.0.0.1:{server.server_port}/col/home.do"
        monkeypatch.setattr(dispatch, "POSTA_ONLINE_SEND_HOME_URL", home_url)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            asyncio.run(_browser_scenario(scenario, home_url))
        finally:
            server.shutdown()
            thread.join()
