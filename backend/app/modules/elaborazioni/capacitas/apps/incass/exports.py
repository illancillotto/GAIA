"""inCASS Excel exports: "Ricerca avvisi" per anno and the "Avvisi Minuta" tile per ruolo."""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import quote, unquote_plus

from app.modules.elaborazioni.capacitas.apps import get_capacitas_app
from app.modules.elaborazioni.capacitas.decoder import decode_response
from app.modules.elaborazioni.capacitas.export_http import (
    AJAX_HEADERS,
    ExportStepError,
    ensure_portal_response,
    ensure_xlsx,
    kendo_grid_rows,
    parse_select_options,
)
from app.modules.elaborazioni.capacitas.export_workbook import (
    ExportPayload,
    rows_to_payload,
    xlsx_data_rows,
)
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager

INCASS_APP = get_capacitas_app("incass")
PAGES_URL = f"{INCASS_APP.base_url}/pages"
RICERCA_AVVISI_URL = f"{PAGES_URL}/ricercaAvvisi.aspx"
MAIN_URL = f"{PAGES_URL}/main.aspx"
AJAX_RICERCA_URL = f"{PAGES_URL}/ajax/ajaxRicerca.aspx"
AJAX_TILES_URL = f"{PAGES_URL}/ajax/ajaxTiles.aspx"
AJAX_PROGRESS_URL = f"{PAGES_URL}/ajax/ajaxCheckProgress.aspx"
AJAX_GRID_URL = f"{PAGES_URL}/ajax/ajaxGenericGridKUI.aspx"
EXPORT_EXCEL_URL = f"{PAGES_URL}/exportExcel.aspx"
DOWNLOAD_URL = f"{PAGES_URL}/download.aspx"
DLG_TILE_TIPO7_URL = f"{PAGES_URL}/dialog/dlgTileTipo7.aspx"
DLG_TILE_TIPO6_URL = f"{PAGES_URL}/dialog/dlgTileTipo6.aspx"

EXPORT_TIMEOUT_SECONDS = 900.0
MINUTA_TILES_KEY = "elenchi_avvisi"
MINUTA_TILE_TITLE = "avvisi minuta"
MINUTA_YEARS = 20
PROGRESS_DONE_MESSAGES = frozenset({"fine elaborazioni", "fine processo"})
_SESSION_ID_RE = re.compile(r'mstrSessionIDDlgTileTipo7\s*=\s*"([^"]+)"')
_TILE_ATTR_RE = re.compile(r"data-([a-z]+)='([^']*)'", re.IGNORECASE)
_TILE_ID_RE = re.compile(r"id='tid_([^']+)'")


@dataclass(frozen=True, slots=True)
class MinutaTile:
    tile_id: str
    stored_procedure: str

    @property
    def operation(self) -> str:
        return f"OP_{self.stored_procedure}"


def minuta_years(current_year: int) -> list[str]:
    """The ruoli offered by the Avvisi Minuta form: the current year and the 19 before it."""
    return [str(current_year - offset) for offset in range(MINUTA_YEARS)]


def ricerca_export_form(anno: str) -> dict[str, str]:
    empty = quote("", safe="")
    every_notice = quote("Tutti gli avvisi", safe="")
    fields = ("tipoDenominaz", "denominaz", "avviso", "codFisc", "lista", "importoDa", "importoA")
    labels = ("gruppoEtichette", "etichetta", "valoreEtichetta")
    return {
        "op": "avvisi",
        "isExport": "true",
        "tipoNum": quote("avviso", safe=""),
        "anno": quote(anno, safe=""),
        "pagamenti": every_notice,
        "sgravio": every_notice,
        "tipoPagamento": quote("Tutti", safe=""),
        "postalizzazione": quote("Tutti", safe=""),
        **dict.fromkeys(fields + labels, empty),
    }


def _minuta_tile_from_item(item: object) -> MinutaTile | None:
    tile_html = unquote_plus(str(item.get("Tile", ""))) if isinstance(item, dict) else ""
    attrs = {key.lower(): unquote_plus(value) for key, value in _TILE_ATTR_RE.findall(tile_html)}
    tile_id = _TILE_ID_RE.search(tile_html)
    if attrs.get("title", "").strip().lower() != MINUTA_TILE_TITLE or tile_id is None:
        return None
    stored_procedure = str(json.loads(attrs.get("js") or "{}").get("sp", "")).strip()
    return MinutaTile(tile_id.group(1), stored_procedure) if stored_procedure else None


def parse_minuta_tile(tiles_payload: object) -> MinutaTile:
    items = tiles_payload if isinstance(tiles_payload, list) else []
    found = next(filter(None, map(_minuta_tile_from_item, items)), None)
    if found is not None:
        return found
    raise ExportStepError(
        "Tile 'Avvisi Minuta' non trovato in Situazione Economica > Elenchi Avvisi.",
        retryable=False,
    )


def progress_finished(log: list[dict[str, object]]) -> bool:
    """Read the "Avanzamento elaborazione" log; an ``ERRORE`` line fails the step."""
    messages = [str(entry.get("Msg", "")).strip() for entry in log]
    errors = [message for message in messages if message.upper().startswith("ERRORE")]
    if errors:
        raise ExportStepError(f"Elaborazione Avvisi Minuta in errore: {errors[0][:300]}")
    return any(message.lower() in PROGRESS_DONE_MESSAGES for message in messages)


def declared_total(rows: list[dict[str, object]]) -> int:
    """Rows the server holds: ``__TotRighe`` when the grid was truncated, else the rows received."""
    total = rows[0].get("__TotRighe") if rows else None
    return total if isinstance(total, int) and total > len(rows) else len(rows)


class InCassExportClient:
    def __init__(
        self,
        session_manager: CapacitasSessionManager,
        *,
        progress_timeout_seconds: float,
        poll_interval_seconds: float = 3.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._manager = session_manager
        self._progress_timeout = progress_timeout_seconds
        self._poll_interval = poll_interval_seconds
        self._sleep = sleep

    def _app_params(self) -> dict[str, str]:
        return {"token": self._manager.get_token(), "app": INCASS_APP.key, "tenant": ""}

    async def _post(self, url: str, data: dict[str, str], *, step: str, ajax: bool = True):
        headers = {**AJAX_HEADERS, "Referer": MAIN_URL} if ajax else {"Referer": MAIN_URL}
        response = await self._manager.get_http_client().post(
            url, data=data, headers=headers, timeout=EXPORT_TIMEOUT_SECONDS
        )
        ensure_portal_response(response, step=step)
        return response

    async def list_ricerca_years(self) -> list[str]:
        response = await self._manager.get_http_client().get(
            RICERCA_AVVISI_URL, params=self._app_params()
        )
        ensure_portal_response(response, step="apertura Ricerca avvisi")
        return parse_select_options(response.text, "ContentMain_ddlAnno")

    async def export_ricerca_avvisi(self, anno: str) -> ExportPayload:
        step = f"ricerca avvisi anno {anno}"
        await self._post(AJAX_RICERCA_URL, ricerca_export_form(anno), step=step)
        response = await self._manager.get_http_client().get(
            EXPORT_EXCEL_URL,
            params={"op": "ricerca-avvisi"},
            headers={"Referer": RICERCA_AVVISI_URL},
            timeout=EXPORT_TIMEOUT_SECONDS,
        )
        ensure_portal_response(response, step=step)
        content = ensure_xlsx(response, step=step)
        return ExportPayload(content=content, rows=xlsx_data_rows(content))

    async def export_avvisi_minuta(self, anno: str) -> ExportPayload:
        step = f"avvisi minuta ruolo {anno}"
        tile = await self._minuta_tile()
        session_id = await self._open_minuta_dialog(tile)
        await self._start_minuta(tile, session_id, anno, step=step)
        await self._wait_for_progress(tile, session_id, step=step)
        await self._post(
            AJAX_PROGRESS_URL,
            {
                "op": "clear_check_v2",
                "sessionID": session_id,
                "tipoOp": quote(tile.operation, safe=""),
            },
            step=step,
        )
        return await self._minuta_grid(anno, step=step)

    async def _minuta_tile(self) -> MinutaTile:
        await self._manager.get_http_client().get(MAIN_URL, params=self._app_params())
        response = await self._post(
            AJAX_TILES_URL, {"op": "get", "key": MINUTA_TILES_KEY}, step="elenco tile"
        )
        return parse_minuta_tile(decode_response(response.text.strip()))

    async def _open_minuta_dialog(self, tile: MinutaTile) -> str:
        response = await self._post(
            DLG_TILE_TIPO7_URL,
            {
                "IDTile": tile.tile_id,
                "sp": tile.stored_procedure,
                "showGrid": "true",
                "titleGrid": quote("Risultato analisi Avvisi per annualità", safe=""),
                "tipo": "7",
                "IDDlg": "dialog-web",
            },
            step="apertura Avvisi Minuta",
            ajax=False,
        )
        match = _SESSION_ID_RE.search(response.text)
        if match is None:
            raise ExportStepError("Dialog Avvisi Minuta senza sessione di elaborazione.")
        return match.group(1)

    async def _start_minuta(
        self, tile: MinutaTile, session_id: str, anno: str, *, step: str
    ) -> None:
        operation = quote(tile.operation, safe="")
        response = await self._post(
            AJAX_PROGRESS_URL,
            {"op": "op_in_progress_v2", "sessionID": session_id, "tipoOp": operation},
            step=step,
        )
        state = decode_response(response.text.strip())
        if not (isinstance(state, list) and state and str(state[0].get("InProgress")) == "0"):
            raise ExportStepError(
                f"{step}: un'altra elaborazione Avvisi Minuta e in corso sul portale."
            )
        form = f"Anno_input=Ruolo+{anno}&Anno={anno}"
        await self._post(
            AJAX_TILES_URL,
            {
                "op": "esegui-sp",
                "sp": quote(tile.stored_procedure, safe=""),
                "tipoOp": operation,
                "mode": "async-tile7",
                "showGrid": "true",
                "params": quote(form, safe=""),
            },
            step=step,
        )

    async def _wait_for_progress(self, tile: MinutaTile, session_id: str, *, step: str) -> None:
        deadline = time.monotonic() + self._progress_timeout
        data = {
            "op": "check_status_v2",
            "sessionID": session_id,
            "tipoOp": quote(tile.operation, safe=""),
            "isKendo": "true",
        }
        while time.monotonic() < deadline:
            response = await self._post(AJAX_PROGRESS_URL, data, step=step)
            body = response.text.strip()
            log = decode_response(body) if body else []
            if progress_finished(log if isinstance(log, list) else []):
                return
            await self._sleep(self._poll_interval)
        raise ExportStepError(
            f"{step}: elaborazione non conclusa entro {self._progress_timeout:.0f}s."
        )

    async def _minuta_grid(self, anno: str, *, step: str) -> ExportPayload:
        await self._post(DLG_TILE_TIPO6_URL, {"IDDlg": "dialog-generic-kui"}, step=step, ajax=False)
        response = await self._post(AJAX_GRID_URL, {"op": "get-data-grid-tile-6"}, step=step)
        rows = kendo_grid_rows(response.text, step=step)
        total = declared_total(rows)
        if total == len(rows):
            return rows_to_payload(rows, sheet_title=f"Minuta {anno}")
        # Grid truncated by the portal: use its server-side export, like the browser does.
        download = await self._post(
            DOWNLOAD_URL, {"op": "export-grd-tile6", "forzaDownload": "true"}, step=step, ajax=False
        )
        return ExportPayload(content=ensure_xlsx(download, step=step), rows=total)
