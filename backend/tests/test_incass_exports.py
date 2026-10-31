from __future__ import annotations

import asyncio
import base64
import json
import zlib
from urllib.parse import parse_qs, quote

import httpx
import pytest

from app.modules.elaborazioni.capacitas.apps.incass.exports import (
    InCassExportClient,
    MinutaTile,
    declared_total,
    minuta_years,
    parse_minuta_tile,
    progress_finished,
    ricerca_export_form,
)
from app.modules.elaborazioni.capacitas.export_http import ExportStepError
from app.modules.elaborazioni.capacitas.export_workbook import rows_to_payload

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TILE_JS = json.dumps({"sp": "spElencoAvvisi_Anno", "showGrid": "true"})


def sz(payload: object) -> str:
    compressor = zlib.compressobj(wbits=-15)
    raw = compressor.compress(json.dumps(payload).encode()) + compressor.flush()
    return "SZ" + base64.b64encode(raw).decode()


def tile(title: str, *, js: str = TILE_JS, tile_id: str = "abc") -> dict[str, str]:
    html = f"<div id='tid_{tile_id}' data-title='{quote(title)}' data-js='{quote(js)}'></div>"
    return {"Tile": quote(html)}


def form(request: httpx.Request) -> dict[str, str]:
    return {
        key: values[0]
        for key, values in parse_qs(request.content.decode(), keep_blank_values=True).items()
    }


class FakeManager:
    def __init__(self, handler):
        self.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    def get_http_client(self):
        return self.http

    def get_token(self):
        return "tok"


class Portal:
    """Fake inCASS reacting to the Avvisi Minuta / Ricerca avvisi calls."""

    def __init__(self, *, status_logs=None, grid=None, in_progress="0", tiles=None):
        self.status_logs = list(status_logs or [[{"Msg": "fine elaborazioni"}]])
        self.grid = (
            grid if grid is not None else {"results": [{"Anno": "2025", "Avviso": "1"}], "total": 1}
        )
        self.in_progress = in_progress
        self.tiles = tiles if tiles is not None else [tile("Avvisi Morosi"), tile("Avvisi Minuta")]
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.rsplit("/", 1)[-1]
        data = form(request) if request.method == "POST" else dict(request.url.params)
        self.calls.append((path, data))
        handler = getattr(self, "_" + path.replace(".aspx", "").replace(".", "_"), None)
        return handler(data) if handler else httpx.Response(200, text="<html>ok</html>")

    def _ajaxTiles(self, data):
        return httpx.Response(200, text=sz(self.tiles) if data["op"] == "get" else "SI")

    def _dlgTileTipo7(self, data):
        return httpx.Response(200, text='var mstrSessionIDDlgTileTipo7 = "sess-1";')

    def _ajaxCheckProgress(self, data):
        if data["op"] == "op_in_progress_v2":
            return httpx.Response(200, text=sz([{"InProgress": self.in_progress}]))
        if data["op"] == "check_status_v2":
            log = self.status_logs.pop(0) if len(self.status_logs) > 1 else self.status_logs[0]
            return httpx.Response(200, text=sz(log) if log else "")
        return httpx.Response(200, text="SI")

    def _ajaxGenericGridKUI(self, data):
        return httpx.Response(200, text=json.dumps(self.grid))

    def _download(self, data):
        return httpx.Response(
            200,
            content=rows_to_payload([{"a": 1}], sheet_title="x").content,
            headers={"content-type": XLSX},
        )

    def _ricercaAvvisi(self, data):
        return httpx.Response(
            200, text='<select id="ContentMain_ddlAnno"><option value="2025">2025</option></select>'
        )

    def _ajaxRicerca(self, data):
        return httpx.Response(200, text="SI")

    def _exportExcel(self, data):
        content = rows_to_payload(
            [{"Anno": "2025"}, {"Anno": "2025"}], sheet_title="Esportazione"
        ).content
        return httpx.Response(200, content=content, headers={"content-type": XLSX})


def make_client(portal: Portal, **kwargs) -> InCassExportClient:
    sleeps: list[float] = []

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)

    client = InCassExportClient(
        FakeManager(portal),
        progress_timeout_seconds=kwargs.pop("timeout", 60),
        sleep=sleep,
        **kwargs,
    )
    client.sleeps = sleeps
    return client


def test_minuta_years_cover_twenty_ruoli():
    years = minuta_years(2026)
    assert years[0] == "2026" and years[-1] == "2007" and len(years) == 20


def test_ricerca_export_form_matches_portal_encoding():
    data = ricerca_export_form("2025")
    assert data["isExport"] == "true" and data["anno"] == "2025"
    assert data["pagamenti"] == "Tutti%20gli%20avvisi" and data["codFisc"] == ""


def test_parse_minuta_tile_reads_id_and_procedure():
    parsed = parse_minuta_tile(["noise", tile("Avvisi Minuta", tile_id="t-9")])
    assert parsed == MinutaTile("t-9", "spElencoAvvisi_Anno")
    assert parsed.operation == "OP_spElencoAvvisi_Anno"


@pytest.mark.parametrize("payload", [{}, [tile("Avvisi Morosi")], [tile("Avvisi Minuta", js="{}")]])
def test_parse_minuta_tile_missing_is_not_retryable(payload):
    with pytest.raises(ExportStepError) as excinfo:
        parse_minuta_tile(payload)
    assert excinfo.value.retryable is False


def test_progress_finished_states():
    assert progress_finished([{"Msg": "Analisi per Ruolo 2025"}]) is False
    assert progress_finished([{"Msg": "x"}, {"Msg": " Fine processo "}]) is True
    with pytest.raises(ExportStepError, match="expects parameter"):
        progress_finished(
            [{"Msg": "ERRORE: Procedure expects parameter '@Anno'"}, {"Msg": "fine processo"}]
        )


def test_declared_total_uses_truncation_marker_only_when_larger():
    assert declared_total([]) == 0
    assert declared_total([{"__TotRighe": 50}, {}]) == 50
    assert declared_total([{"__TotRighe": 1}, {}]) == 2
    assert declared_total([{"__TotRighe": "50"}]) == 1


def test_export_avvisi_minuta_runs_procedure_and_reads_grid():
    portal = Portal(
        status_logs=[[{"Msg": "Analisi per Ruolo 2025"}], [], [{"Msg": "fine elaborazioni"}]]
    )
    client = make_client(portal)

    payload = asyncio.run(client.export_avvisi_minuta("2025"))

    assert payload.rows == 1
    assert client.sleeps == [3.0, 3.0]
    paths = [path for path, _ in portal.calls]
    assert paths[:4] == [
        "main.aspx",
        "ajaxTiles.aspx",
        "dlgTileTipo7.aspx",
        "ajaxCheckProgress.aspx",
    ]
    esegui = next(data for path, data in portal.calls if data.get("op") == "esegui-sp")
    assert esegui["params"] == quote("Anno_input=Ruolo+2025&Anno=2025", safe="")
    assert esegui["mode"] == "async-tile7" and esegui["tipoOp"] == "OP_spElencoAvvisi_Anno"
    ops = [data.get("op") for _, data in portal.calls]
    assert ops.index("clear_check_v2") < ops.index("get-data-grid-tile-6")


def test_export_avvisi_minuta_uses_server_export_when_grid_truncated():
    portal = Portal(grid={"results": [{"__TotRighe": 9000, "Anno": "2025"}]})
    payload = asyncio.run(make_client(portal).export_avvisi_minuta("2025"))
    assert payload.rows == 9000
    assert ("download.aspx", {"op": "export-grd-tile6", "forzaDownload": "true"}) in portal.calls


def test_export_avvisi_minuta_refuses_when_portal_busy():
    with pytest.raises(ExportStepError, match="in corso"):
        asyncio.run(make_client(Portal(in_progress="1")).export_avvisi_minuta("2025"))


def test_export_avvisi_minuta_times_out():
    portal = Portal(status_logs=[[{"Msg": "Analisi"}]])
    with pytest.raises(ExportStepError, match="non conclusa entro 0s"):
        asyncio.run(make_client(portal, timeout=0).export_avvisi_minuta("2025"))


def test_export_avvisi_minuta_requires_session_id(monkeypatch):
    portal = Portal()
    monkeypatch.setattr(
        portal, "_dlgTileTipo7", lambda data: httpx.Response(200, text="<html></html>")
    )
    with pytest.raises(ExportStepError, match="senza sessione"):
        asyncio.run(make_client(portal).export_avvisi_minuta("2025"))


def test_export_avvisi_minuta_ignores_non_list_status(monkeypatch):
    portal = Portal(status_logs=[{"Msg": "x"}, [{"Msg": "fine processo"}]])
    payload = asyncio.run(make_client(portal).export_avvisi_minuta("2025"))
    assert payload.rows == 1


def test_ricerca_years_and_export():
    portal = Portal()
    client = make_client(portal)

    async def scenario():
        return await client.list_ricerca_years(), await client.export_ricerca_avvisi("2025")

    years, payload = asyncio.run(scenario())

    assert years == ["2025"]
    assert payload.rows == 2
    ajax = next(data for path, data in portal.calls if path == "ajaxRicerca.aspx")
    assert ajax["isExport"] == "true" and ajax["anno"] == "2025"
    assert ("exportExcel.aspx", {"op": "ricerca-avvisi"}) in portal.calls
