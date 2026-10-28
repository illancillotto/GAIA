"""Browser actions on Posta Online drafts: directory lookup, create, list, delete.

There is deliberately no method that presses INVIA: the operator sends the
drafts from "Verifica e invia" after checking them on Poste.
"""

from __future__ import annotations

import logging
import re
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.modules.ruolo.services.poste_dispatch_address import search_term
from app.modules.ruolo.services.poste_dispatch_work import DraftRow, WorkItem
from posta_online_client import POSTA_ONLINE_ARCHIVE_URL, PostaOnlineBrowserClient
from posta_online_dispatch_portal import allows_request, parse_archive_rows, parse_draft_rows

logger = logging.getLogger(__name__)

POSTA_ONLINE_SEND_HOME_URL = "https://corrispondenza.poste.it/col/home.do"
POSTA_ONLINE_DRAFTS_URL = "https://corrispondenza.poste.it/col/incorso.do"
POSTA_ONLINE_AUTOCOMPLETE_URL = "https://corrispondenza.poste.it/col/autocomplete.do"
AR_PREFIX = "raccomandataar"
MAX_LIST_PAGES = 20


class DraftNotSubmitted(RuntimeError):
    """The form failed before CONTINUA: no draft can exist, a new attempt is safe."""


class DraftSubmitUncertain(RuntimeError):
    """CONTINUA was pressed: only the drafts list or the archive can tell what happened."""


class PostaOnlineDispatchPortal:
    def __init__(self, client: PostaOnlineBrowserClient) -> None:
        self.client = client
        self.phase = "login"
        self.blocked: list[dict[str, str]] = []

    @property
    def page(self):
        return self.client.page

    async def install_guard(self) -> None:
        await self.client.context.route("**/*", self._guard)

    async def _guard(self, route) -> None:
        request = route.request
        host = urlparse(request.url).hostname or ""
        body = (
            (request.post_data_buffer or b"").decode("latin-1")
            if request.method not in ("GET", "HEAD")
            else ""
        )
        if "poste" in host and not allows_request(self.phase, request.method, request.url, body):
            self.blocked.append({"phase": self.phase, "method": request.method, "url": request.url})
            logger.warning(
                "Poste dispatch: richiesta bloccata %s %s (fase %s)",
                request.method,
                request.url,
                self.phase,
            )
            await route.abort()
            return
        await route.continue_()

    async def _open(self, url: str) -> None:
        await self.client.throttle.wait(f"dispatch:{self.phase}")
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.client._prepare_login_page(self.page)

    async def open_send_form(self) -> None:
        """The directory lookup is a call of the "Crea spedizione" page: open it first."""
        await self._open(POSTA_ONLINE_SEND_HOME_URL)

    async def suggestions(self, term: str) -> list[dict[str, Any]]:
        await self.client.throttle.wait("dispatch:autocomplete")
        response = await self.client.context.request.post(
            POSTA_ONLINE_AUTOCOMPLETE_URL,
            form={"street": re.sub(r"[^\w\s]", "", term)},
            headers={"X-Requested-With": "XMLHttpRequest", "Referer": POSTA_ONLINE_SEND_HOME_URL},
        )
        if response.status >= 400:
            raise RuntimeError(f"Stradario Poste HTTP {response.status}")
        payload = await response.json()
        return (
            [item for item in payload if isinstance(item, dict)]
            if isinstance(payload, list)
            else []
        )

    async def _all_pages(self, url: str, parse) -> tuple[list, bool]:
        await self._open(url)
        rows: list = []
        for _ in range(MAX_LIST_PAGES):
            rows.extend(parse(await self.page.content()))
            if not await self.client._goto_next_archive_page(self.page):
                return rows, True
        return rows, False

    async def list_drafts(self) -> list[DraftRow]:
        rows, complete = await self._all_pages(POSTA_ONLINE_DRAFTS_URL, parse_draft_rows)
        if not complete:
            raise RuntimeError(
                "Verifica e invia ha troppe pagine: ridurre le bozze presenti su Poste"
            )
        return rows

    async def archive_index(self) -> tuple[dict[str, list[str]], bool]:
        """Shipment ids by name; complete is False when the archive was not read to the end."""
        rows, complete = await self._all_pages(POSTA_ONLINE_ARCHIVE_URL, parse_archive_rows)
        index: dict[str, list[str]] = {}
        for shipment_id, name in rows:
            index.setdefault(name, []).append(shipment_id)
        return index, complete

    async def delete_draft(self, draft_id: str) -> None:
        """Delete one draft by id with the row's own action, never through the shared selection."""
        await self._open(POSTA_ONLINE_DRAFTS_URL)
        if await self.page.locator(f"input[name='invioCheck'][id='{draft_id}']").count() != 1:
            raise RuntimeError(f"Bozza {draft_id} non presente in Verifica e invia")
        previous, self.phase = self.phase, "delete"
        try:
            await self.page.evaluate("draftId => DeleteInvio(draftId)", draft_id)
            await self.page.wait_for_load_state("domcontentloaded")
            await self.page.wait_for_timeout(3000)
        finally:
            self.phase = previous

    async def create_draft(
        self, item: WorkItem, artifact: bytes, before_submit: Callable[[], Awaitable[None]]
    ) -> None:
        """Fill "Crea spedizione" for one AR recipient and press CONTINUA once."""
        try:
            with tempfile.TemporaryDirectory(prefix="gaia_poste_") as directory:
                path = Path(directory) / f"{item.shipment_name.replace(' ', '_')}.pdf"
                path.write_bytes(artifact)
                await self._fill_form(item, path)
        except Exception as exc:
            raise DraftNotSubmitted(str(exc)) from exc
        await before_submit()
        try:
            await self.page.locator("#continua").click()
            await self.page.wait_for_url(
                re.compile(r"incorso\.do|invioDestinatari\.do"), timeout=90000
            )
        except Exception as exc:
            raise DraftSubmitUncertain(str(exc)) from exc

    async def _fill_form(self, item: WorkItem, path: Path) -> None:
        await self._open(POSTA_ONLINE_SEND_HOME_URL)
        await self.page.locator("input[name=nomeInvio]").fill(item.shipment_name)
        await self.page.locator("#file").set_input_files(str(path))
        await self.page.wait_for_timeout(4000)
        await self._open_ar_form()
        await self._fill_recipient(item)
        await self.page.locator(f"#{AR_PREFIX}_add_dest_button").click()
        await self.page.wait_for_timeout(4000)
        badge = (await self.page.locator(f"#{AR_PREFIX}Summary").inner_text()).strip()
        if badge != "1" or await self.page.locator(".has-error").count():
            raise RuntimeError(f"Destinatari nel modulo Poste: {badge!r}, attesi 1 senza errori")

    async def _open_ar_form(self) -> None:
        """The AR switch replaces the panel; the portal may remember the AR choice."""
        remembered = self.page.locator(f"a[onclick*=\"registraForm('{AR_PREFIX}')\"]")
        if await remembered.count():
            await remembered.click()
        else:
            await self.page.locator("a[onclick*=\"registraForm('raccomandata')\"]").click()
            await self.page.wait_for_timeout(2000)
            await self.page.locator("#swlabel").click()
        await self.page.wait_for_timeout(2000)
        if not await self.page.locator(f"#{AR_PREFIX}nome").is_visible():
            raise RuntimeError("Modulo Raccomandata A/R non attivato")

    async def _fill_recipient(self, item: WorkItem) -> None:
        recipient = item.recipient
        await self.page.locator(f"#{AR_PREFIX}nome").fill(recipient["name"])
        await self.page.locator(f"#{AR_PREFIX}descrizione").fill(recipient["name_extra"])
        address = item.poste_address or {}
        label = (
            address.get("label")
            if address.get("mode") == "directory"
            else "INSERISCI L'INDIRIZZO MANUALMENTE"
        )
        await self._choose_suggestion(search_term(recipient), label)
        if address.get("mode") != "directory":
            await self._fill_manual_address(recipient)

    async def _choose_suggestion(self, term: str, label: str) -> None:
        field = self.page.locator(f"#{AR_PREFIX}indirizzoautocomplete")
        await field.click()
        await field.fill("")
        await field.press_sequentially(re.sub(r"[^\w\s]", "", term), delay=120)
        await self.page.wait_for_timeout(5000)
        options = self.page.locator("ul.ui-autocomplete:visible li")
        texts = [text.strip() for text in await options.all_inner_texts()]
        if label not in texts:
            raise RuntimeError(f"Indirizzo {label!r} non proposto dallo stradario Poste")
        await options.nth(texts.index(label)).click()
        await self.page.wait_for_timeout(2500)

    async def _fill_manual_address(self, recipient: dict[str, str]) -> None:
        for selector in (f"#{AR_PREFIX}indirizzo", f"#{AR_PREFIX}indirizzoautocomplete"):
            field = self.page.locator(selector)
            if await field.is_visible():
                await field.fill(recipient["address"])
                break
        else:
            raise RuntimeError("Campo indirizzo manuale non trovato nel modulo Poste")
        city = self.page.locator(f"#{AR_PREFIX}localita")
        await city.click()
        await city.press_sequentially(recipient["city"], delay=100)
        await city.press("Tab")
        await self.page.wait_for_timeout(4000)
        await self.page.locator(f"#{AR_PREFIX}cap").select_option(recipient["cap"])
        await self.page.locator(f"#{AR_PREFIX}provincia").fill(recipient["province"])
