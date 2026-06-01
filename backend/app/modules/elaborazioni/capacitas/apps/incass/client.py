from __future__ import annotations

import html
from urllib.parse import quote

from app.modules.elaborazioni.capacitas.apps import get_capacitas_app
from app.modules.elaborazioni.capacitas.decoder import decode_response
from app.modules.elaborazioni.capacitas.models import (
    CapacitasInCassNoticeDetail,
    CapacitasInCassPartitarioDetail,
    CapacitasInCassSearchResult,
)
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
from app.modules.elaborazioni.capacitas.apps.incass.parsers import (
    parse_incass_notice_detail,
    parse_incass_partitario_dialog,
    parse_incass_search_result,
)

INCASS_APP = get_capacitas_app("incass")
AJAX_RICERCA_URL = f"{INCASS_APP.base_url}/pages/ajax/ajaxRicerca.aspx"
RICERCA_AVVISI_URL = f"{INCASS_APP.base_url}/pages/ricercaAvvisi.aspx"
DETTAGLIO_AVVISO_URL = f"{INCASS_APP.base_url}/pages/dettaglioAvviso.aspx"
DLG_PARTITARIO_URL = f"{INCASS_APP.base_url}/pages/dialog/dlgPartitarioKUI.aspx"

_AJAX_HEADERS = {
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}


class CapacitasInCassSessionExpiredError(RuntimeError):
    pass


class InCassClient:
    def __init__(self, session_manager: CapacitasSessionManager) -> None:
        self._manager = session_manager

    async def refresh_session(self) -> None:
        await self._manager.close()
        await self._manager.login()
        await self._manager.activate_app("incass")
        await self._manager.start_keepalive("incass")

    async def warmup_search_page(self) -> None:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.get(
            RICERCA_AVVISI_URL,
            params={"token": token, "app": "incass", "tenant": ""},
        )
        response.raise_for_status()
        self._ensure_valid_app_response(response, expected_marker="ricercaavvisi")

    async def search_notices(self, identifier: str) -> CapacitasInCassSearchResult:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        payload = {
            "op": "avvisi",
            "isExport": "false",
            "tipoDenominaz": quote("", safe=""),
            "denominaz": quote("", safe=""),
            "tipoNum": quote("avviso", safe=""),
            "avviso": quote("", safe=""),
            "codFisc": quote(identifier.strip().upper(), safe=""),
            "anno": quote("", safe=""),
            "lista": quote("", safe=""),
            "importoDa": quote("", safe=""),
            "importoA": quote("", safe=""),
            "pagamenti": quote("Tutti gli avvisi", safe=""),
            "sgravio": quote("Tutti gli avvisi", safe=""),
            "tipoPagamento": quote("Tutti", safe=""),
            "postalizzazione": quote("Tutti", safe=""),
            "gruppoEtichette": quote("", safe=""),
            "etichetta": quote("", safe=""),
            "valoreEtichetta": quote("", safe=""),
        }
        response = await http.post(
            AJAX_RICERCA_URL,
            data=payload,
            headers={**_AJAX_HEADERS, "Referer": f"{RICERCA_AVVISI_URL}?token={token}&app=incass&tenant="},
        )
        response.raise_for_status()
        self._ensure_valid_app_response(response, expected_marker="ajaxricerca")
        decoded = decode_response(response.text.strip())
        return parse_incass_search_result(decoded, base_url=INCASS_APP.base_url)

    async def fetch_notice_detail(self, avviso: str) -> CapacitasInCassNoticeDetail:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.get(
            DETTAGLIO_AVVISO_URL,
            params={"avviso": avviso, "token": token, "app": "incass", "tenant": ""},
        )
        response.raise_for_status()
        self._ensure_valid_app_response(response, expected_marker="dettaglioavviso")
        detail_url = str(response.url)
        return parse_incass_notice_detail(response.text, detail_url=detail_url, base_url=INCASS_APP.base_url, avviso=avviso)

    async def fetch_notice_partitario(self, avviso: str) -> CapacitasInCassPartitarioDetail | None:
        http = self._manager.get_http_client()
        response = await http.post(
            DLG_PARTITARIO_URL,
            data={"idDlg": "dlg-vis-part-kui", "avviso": avviso},
            headers={**_AJAX_HEADERS, "Referer": f"{DETTAGLIO_AVVISO_URL}?avviso={avviso}"},
        )
        response.raise_for_status()
        self._ensure_valid_app_response(response, expected_marker="dlgpartitariokui")
        return parse_incass_partitario_dialog(response.text, avviso=avviso)

    @staticmethod
    def _ensure_valid_app_response(response, *, expected_marker: str) -> None:
        final_url = str(response.url).lower()
        body = html.unescape(response.text or "").lower()
        if "sso.servizicapacitas.com/pages/login.aspx" in final_url or "name=\"txtusername\"" in body:
            raise CapacitasInCassSessionExpiredError("Sessione inCass scaduta: il portale ha rediretto sulla login SSO.")
        if "/pages/errore.aspx" in final_url:
            raise RuntimeError(f"inCass ha rediretto su errore.aspx durante la chiamata {expected_marker}.")
        if expected_marker not in final_url and "/pages/login.aspx" in final_url:
            raise CapacitasInCassSessionExpiredError(
                f"Sessione inCass non valida durante la chiamata {expected_marker}: URL finale inatteso {final_url}."
            )
