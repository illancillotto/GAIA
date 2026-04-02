from __future__ import annotations

import logging
from urllib.parse import quote

from app.modules.catasto.capacitas.decoder import decode_response
from app.modules.catasto.capacitas.models import CapacitasAnagrafica, CapacitasSearchResult
from app.modules.catasto.capacitas.session import APP_HOSTS, CapacitasSessionManager

logger = logging.getLogger(__name__)

INVOLTURE_HOST = APP_HOSTS["involture"]
AJAX_RICERCA_URL = f"{INVOLTURE_HOST}/pages/ajax/ajaxRicerca.aspx"

_AJAX_HEADERS = {
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}


class InVoltureClient:
    def __init__(self, session_manager: CapacitasSessionManager) -> None:
        self._manager = session_manager

    async def search_anagrafica(
        self,
        q: str,
        tipo: int = 1,
        solo_con_beni: bool = False,
    ) -> CapacitasSearchResult:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        payload = {
            "q": quote(q, safe=""),
            "tipo": "ricanag",
            "soloConBeni": "true" if solo_con_beni else "false",
            "opz": str(tipo),
        }
        referer = f"{INVOLTURE_HOST}/pages/ricercaAnagrafica.aspx?token={token}&app=involture&tenant="

        response = await http.post(
            AJAX_RICERCA_URL,
            data=payload,
            headers={**_AJAX_HEADERS, "Referer": referer},
        )
        response.raise_for_status()
        decoded = decode_response(response.text.strip())
        return _parse_search_result(decoded)

    async def search_by_cf(self, codice_fiscale: str) -> CapacitasSearchResult:
        return await self.search_anagrafica(codice_fiscale, tipo=2)

    async def search_by_cco(self, cco: str, fra: str = "", ccs: str = "") -> CapacitasSearchResult:
        return await self.search_anagrafica(f"{cco}~{fra}~{ccs}", tipo=3)


def _parse_search_result(data: dict | list | str) -> CapacitasSearchResult:
    if isinstance(data, list):
        rows_raw = data
        total = len(data)
    elif isinstance(data, dict):
        rows_raw = data.get("rows", data.get("Rows", []))
        total = int(data.get("total", data.get("records", len(rows_raw))))
    else:
        logger.warning("Struttura risposta inattesa Capacitas: %s", type(data))
        rows_raw = []
        total = 0

    rows: list[CapacitasAnagrafica] = []
    for row in rows_raw:
        try:
            rows.append(CapacitasAnagrafica.model_validate(row))
        except Exception as exc:
            logger.warning("Parse row Capacitas fallito: %s row=%s", exc, row)

    return CapacitasSearchResult(total=total, rows=rows)
