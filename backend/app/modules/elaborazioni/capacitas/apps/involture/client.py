from __future__ import annotations

import logging
from urllib.parse import quote

from app.modules.elaborazioni.capacitas.apps import get_capacitas_app
from app.modules.elaborazioni.capacitas.decoder import decode_response
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagraficaDetail,
    CapacitasAnagrafica,
    CapacitasLookupOption,
    CapacitasSearchResult,
    CapacitasStoricoAnagraficaRow,
    CapacitasTerreniSearchRequest,
    CapacitasTerreniSearchResult,
    CapacitasTerrenoCertificato,
    CapacitasTerrenoDetail,
)
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
from app.modules.elaborazioni.capacitas.apps.involture.parsers import (
    parse_anagrafica_detail_html,
    parse_certificato_html,
    parse_lookup_option_rows,
    parse_lookup_options,
    parse_storico_anagrafica_rows,
    parse_terreni_search_result,
    parse_terreno_detail_html,
)

logger = logging.getLogger(__name__)

INVOLTURE_APP = get_capacitas_app("involture")


class CapacitasSessionExpiredError(RuntimeError):
    """Raised when Capacitas responds with a session-expired payload (e.g. 'NOSessione scaduta')."""
AJAX_RICERCA_URL = f"{INVOLTURE_APP.base_url}/pages/ajax/ajaxRicerca.aspx"
AJAX_FRAZIONI_URL = f"{INVOLTURE_APP.base_url}/pages/ajax/ajaxFrazioni.aspx"
AJAX_SEZIONI_URL = f"{INVOLTURE_APP.base_url}/pages/ajax/ajaxSezioni.aspx"
AJAX_FOGLI_URL = f"{INVOLTURE_APP.base_url}/pages/ajax/ajaxFogli.aspx"
AJAX_GRID_URL = f"{INVOLTURE_APP.base_url}/pages/ajax/ajaxGrid.aspx"
RICERCA_TERRENI_URL = f"{INVOLTURE_APP.base_url}/pages/ricercaTerreni.aspx"
CERTIFICATO_URL = f"{INVOLTURE_APP.base_url}/pages/rptCertificato.aspx"
DETTAGLIO_TERRENO_URL = f"{INVOLTURE_APP.base_url}/pages/dettaglioTerreno.aspx"
AJAX_STORICO_URL = f"{INVOLTURE_APP.base_url}/pages/ajax/ajaxStorico.aspx"
DLG_STORICO_ANAG_URL = f"{INVOLTURE_APP.base_url}/pages/dialog/dlgStoricoAnag.aspx"
DLG_DETTAGLIO_ANAG_URL = f"{INVOLTURE_APP.base_url}/pages/dialog/dlgNuovaAnagrafica.aspx"
DETTAGLIO_ANAG_URL = f"{INVOLTURE_APP.base_url}/pages/dettaglioAnagrafica.aspx"

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

    async def relogin(self) -> None:
        logger.info("InVoltureClient: re-login Capacitas in corso")
        await self._manager.login()
        await self._manager.activate_app("involture")
        logger.info("InVoltureClient: re-login completato")

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
        referer = INVOLTURE_APP.main_url(token)

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

    async def search_frazioni(self, query: str) -> list[CapacitasLookupOption]:
        return await self._lookup(
            AJAX_FRAZIONI_URL,
            payload={"op": "get_frazioni", "filter": quote(query, safe="")},
        )

    async def load_sezioni(self, frazione_id: str) -> list[CapacitasLookupOption]:
        return await self._lookup(
            AJAX_SEZIONI_URL,
            payload={"op": "sez_t", "fra": quote(frazione_id, safe="")},
        )

    async def load_fogli(self, frazione_id: str, sezione: str = "") -> list[CapacitasLookupOption]:
        return await self._lookup(
            AJAX_FOGLI_URL,
            payload={"op": "fog_t", "fra": quote(frazione_id, safe=""), "sez": quote(sezione, safe="")},
        )

    async def search_terreni(self, request: CapacitasTerreniSearchRequest) -> CapacitasTerreniSearchResult:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.post(
            AJAX_GRID_URL,
            data={
                "op": "get-data-source",
                "modulo": quote("terreni_ricerca", safe=""),
                "salva": "true",
                "frazione": quote(request.frazione_id, safe=""),
                "sezione": quote(request.sezione, safe=""),
                "foglio": quote(request.foglio, safe=""),
                "mappale": quote(request.particella, safe=""),
                "sub": quote(request.sub, safe=""),
                "qualita": quote(request.qualita, safe=""),
                "caratura": quote(request.caratura, safe=""),
                "caraturaVal": quote(request.caratura_val, safe=""),
                "inEssere": "true" if request.in_essere else "false",
                "inDomIrr": "true" if request.in_dom_irr else "false",
                "limitaRisultati": "true" if request.limita_risultati else "false",
            },
            headers={**_AJAX_HEADERS, "Referer": f"{RICERCA_TERRENI_URL}?token={token}&app=involture&tenant="},
        )
        response.raise_for_status()
        decoded = decode_response(response.text.strip())
        return parse_terreni_search_result(decoded)

    async def fetch_certificato(
        self,
        *,
        cco: str,
        com: str,
        pvc: str,
        fra: str,
        ccs: str,
        bc: str = "HomRicTer",
    ) -> CapacitasTerrenoCertificato:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.get(
            CERTIFICATO_URL,
            params={
                "CCO": cco,
                "COM": com,
                "PVC": pvc,
                "FRA": fra,
                "CCS": ccs,
                "BC": bc,
                "token": token,
                "app": "involture",
                "tenant": "",
            },
        )
        response.raise_for_status()
        return parse_certificato_html(response.text)

    async def fetch_terreno_detail(self, *, external_row_id: str, bc: str = "HomRicTer") -> CapacitasTerrenoDetail:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.get(
            DETTAGLIO_TERRENO_URL,
            params={
                "BC": bc,
                "ID": external_row_id,
                "token": token,
                "app": "involture",
                "tenant": "",
            },
        )
        response.raise_for_status()
        return parse_terreno_detail_html(response.text)

    async def fetch_anagrafica_history(self, *, idxana: str) -> list[CapacitasStoricoAnagraficaRow]:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.get(
            AJAX_STORICO_URL,
            params={"op": "ana", "IDXAna": idxana},
            headers={**_AJAX_HEADERS, "Referer": f"{DLG_STORICO_ANAG_URL}?IDXana={idxana}&token={token}&app=involture&tenant="},
        )
        response.raise_for_status()
        try:
            decoded = decode_response(response.text.strip())
        except ValueError as exc:
            message = str(exc).casefold()
            if "errore applicativo capacitas" in message and ("storic" in message or "anagraf" in message):
                return []
            raise
        return parse_storico_anagrafica_rows(decoded)

    async def fetch_anagrafica_detail(self, *, history_id: str) -> CapacitasAnagraficaDetail:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.get(
            DLG_DETTAGLIO_ANAG_URL,
            params={"ID": history_id, "storica": "1", "token": token, "app": "involture", "tenant": ""},
        )
        response.raise_for_status()
        return parse_anagrafica_detail_html(response.text)

    async def fetch_current_anagrafica_detail(self, *, idxana: str, idxesa: str) -> CapacitasAnagraficaDetail:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.get(
            DETTAGLIO_ANAG_URL,
            params={"IDXANA": idxana, "IDXEsa": idxesa, "token": token, "app": "involture", "tenant": ""},
        )
        response.raise_for_status()
        return parse_anagrafica_detail_html(response.text)

    async def _lookup(self, url: str, payload: dict[str, str]) -> list[CapacitasLookupOption]:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.post(
            url,
            data=payload,
            headers={**_AJAX_HEADERS, "Referer": f"{RICERCA_TERRENI_URL}?token={token}&app=involture&tenant="},
        )
        response.raise_for_status()
        try:
            decoded = decode_response(response.text.strip())
            if isinstance(decoded, list):
                return parse_lookup_option_rows(decoded)
            if isinstance(decoded, dict):
                rows = decoded.get("rows", decoded.get("Rows", []))
                if isinstance(rows, list):
                    return parse_lookup_option_rows(rows)
            if isinstance(decoded, str):
                return parse_lookup_options(decoded)
            raise ValueError(f"lookup payload type inatteso: {type(decoded).__name__}")
        except Exception as exc:
            snippet = " ".join(response.text.strip().split())[:240]
            if "NOSessione" in snippet or "sessione scaduta" in snippet.lower():
                raise CapacitasSessionExpiredError(
                    f"Sessione Capacitas scaduta su {url}. snippet={snippet}"
                ) from exc
            raise RuntimeError(
                f"Capacitas lookup fallito su {url}: payload non riconosciuto. "
                f"final_url={response.url} snippet={snippet}"
            ) from exc


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
