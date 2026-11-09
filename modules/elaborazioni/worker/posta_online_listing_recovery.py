"""One safe GET refresh for Poste lists; submission actions are never repeated."""

import re
from urllib.parse import urlparse

from playwright.async_api import TimeoutError as PlaywrightTimeoutError


class ListingUnavailable(RuntimeError):
    """The portal returned its temporary Oops page instead of a list."""


async def _read_once(client, url: str, phase: str) -> None:
    await client.throttle.wait(f"dispatch:{phase}")
    await client.page.goto(url, wait_until="commit")
    table = client.page.locator("#col_invio_dett")
    if await table.count() == 0:
        body = await client.page.locator("body").inner_text(timeout=5000)
        if re.search(r"\b(?:oops|ops)\b", body, re.IGNORECASE):
            raise ListingUnavailable("Poste Oops: elenco temporaneamente non disponibile")
    await table.wait_for(state="attached")


async def load_listing(client, url: str, phase: str) -> None:
    parsed = urlparse(url)
    if (parsed.scheme, parsed.netloc, parsed.path) not in {
        ("https", "corrispondenza.poste.it", "/col/incorso.do"),
        ("https", "corrispondenza.poste.it", "/col/archivio.do"),
    }:
        raise ValueError("Il refresh automatico è consentito solo sugli elenchi Poste")
    try:
        await _read_once(client, url, phase)
    except (PlaywrightTimeoutError, ListingUnavailable):
        # Existing throttle: 30-40 seconds, plus the normal per-request delay.
        await client.throttle.wait_retry("dispatch:list-refresh", 1)
        await _read_once(client, url, phase)
