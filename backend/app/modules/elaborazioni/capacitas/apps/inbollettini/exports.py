"""inBOLLETTINI "Registro Bollettini Manuali" export (the data behind the grid's Esporta button)."""

from __future__ import annotations

from app.modules.elaborazioni.capacitas.apps import get_capacitas_app
from app.modules.elaborazioni.capacitas.export_http import (
    AJAX_HEADERS,
    ensure_portal_response,
    kendo_grid_rows,
    parse_select_options,
)
from app.modules.elaborazioni.capacitas.export_workbook import ExportPayload, rows_to_payload
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager

INBOLLETTINI_APP = get_capacitas_app("inbollettini")
REGISTRO_URL = f"{INBOLLETTINI_APP.base_url}/pages/registroBollettiniKUI.aspx"
AJAX_RICERCA_URL = f"{INBOLLETTINI_APP.base_url}/pages/ajax/ajaxRicerca.aspx"
REGISTRO_TIMEOUT_SECONDS = 600.0


class InBollettiniExportClient:
    def __init__(self, session_manager: CapacitasSessionManager) -> None:
        self._manager = session_manager

    async def list_esercizi(self) -> list[str]:
        http = self._manager.get_http_client()
        response = await http.get(
            REGISTRO_URL,
            params={"token": self._manager.get_token(), "app": INBOLLETTINI_APP.key, "tenant": ""},
        )
        ensure_portal_response(response, step="apertura Registro Bollettini")
        return parse_select_options(response.text, "ContentMain_ddlEsercizio")

    async def export_registro(self, esercizio: str) -> ExportPayload:
        http = self._manager.get_http_client()
        response = await http.post(
            AJAX_RICERCA_URL,
            data={
                "op": "registroBoll",
                "esercizio": esercizio,
                "cc": "",
                "causaleBoll": "",
                "statoAvviso": "",
                "dataDa": "",
                "dataA": "",
            },
            headers={**AJAX_HEADERS, "Referer": REGISTRO_URL},
            timeout=REGISTRO_TIMEOUT_SECONDS,
        )
        step = f"registro bollettini esercizio {esercizio}"
        ensure_portal_response(response, step=step)
        rows = kendo_grid_rows(response.text, step=step)
        return rows_to_payload(rows, sheet_title=f"Registro {esercizio}")
