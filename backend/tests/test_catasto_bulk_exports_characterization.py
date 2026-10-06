from __future__ import annotations

import asyncio
import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.modules.catasto.routes.anagrafica import execution, exports
from app.modules.elaborazioni.capacitas.models import CapacitasLookupOption, CapacitasTerrenoRow
from app.schemas.catasto_phase1 import (
    CatAnagraficaBulkSearchRowResult,
    CatAnagraficaMatch,
    CatAnagraficaUtenzaSummary,
    CatIntestatarioResponse,
)


class RecordingDatabase:
    def __init__(self, results):
        self.results = iter(results)
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        values = next(self.results)
        return SimpleNamespace(
            all=lambda: values, scalars=lambda: SimpleNamespace(all=lambda: values)
        )


def parcel(**updates):
    values = dict(
        id=UUID(int=1),
        nome_comune="Nome Comune",
        sezione_catastale="A",
        foglio="1",
        particella="2",
        subalterno=None,
    )
    values.update(updates)
    return SimpleNamespace(**values)


def test_owner_export_columns_rank_dates_and_certificate():
    optional_owner = {
        field: None
        for field in (
            "tipo",
            "cognome",
            "nome",
            "luogo_nascita",
            "ragione_sociale",
            "source",
            "last_verified_at",
        )
    }
    owners = [
        CatIntestatarioResponse(
            **optional_owner,
            id=UUID(int=2),
            denominazione="Ente",
            codice_fiscale="CF",
            data_nascita=date(1980, 1, 1),
            deceduto=True,
        ),
        CatIntestatarioResponse(
            **{**optional_owner, "cognome": "Rossi", "nome": "Mario"},
            id=UUID(int=3),
            codice_fiscale="CF2",
            denominazione=None,
            data_nascita=None,
            deceduto=False,
        ),
    ]
    match = CatAnagraficaMatch(
        particella_id=UUID(int=1),
        foglio="1",
        particella="2",
        comune="Nome Comune",
        intestatari=owners,
        utenza_latest=CatAnagraficaUtenzaSummary(id=UUID(int=4), cco="001"),
        cert_com="002",
        cert_pvc="003",
        cert_fra="004",
    )
    result = CatAnagraficaBulkSearchRowResult(
        row_index=1, esito="FOUND", message="OK", matches=[match]
    )
    for kind in ("CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"):
        rows = exports._build_bulk_export_rows(kind, [result])
        assert [row["rank"] for row in rows] == ["1/2", "2/2"]
        assert [row["denominazione"] for row in rows] == ["Ente", "Rossi Mario"]
        assert rows[0]["data_nascita"] == "1980-01-01"
        assert rows[1]["data_nascita"] == ""
        assert rows[0]["deceduto"] == "si" and rows[1]["deceduto"] == ""
        assert rows[0]["link_involture"].endswith("CCO=001&COM=002&PVC=003&FRA=004&CCS=00000")
    assert exports._export_basename("CF_PIVA_PARTICELLE") == "catasto-intestatari-da-cf"


@pytest.mark.parametrize("kind", ["CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"])
def test_bulk_base_column_order_zero_values_and_input_fallback(kind):
    match = CatAnagraficaMatch(
        particella_id=UUID(int=1),
        foglio="1",
        particella="2",
        num_distretto="0",
        superficie_mq=0,
        superficie_grafica_mq=0,
    )
    result = CatAnagraficaBulkSearchRowResult(
        row_index=1,
        esito="FOUND",
        message="OK",
        comune_input="Comune input",
        sezione_input="Sezione input",
        sub_input="Sub input",
        match=match,
    )
    row = exports._build_bulk_export_rows(kind, [result])[0]
    prefix = (
        ["cf_input", "piva_input", "comune", "foglio", "particella", "sub"]
        if kind == "CF_PIVA_PARTICELLE"
        else ["comune", "sezione", "foglio", "particella", "sub"]
    )
    common = {
        "num_distretto": "0",
        "nome_distretto": "",
        "riordino_code": "",
        "riordino_maglia": "",
        "riordino_lotto": "",
        "superficie_mq": 0,
        "superficie_grafica_mq": 0,
        "esito": "Presente in Catasto",
        "trovato in esito consorzio": "Particella non presente in Catasto Consorzio",
        "cco": "",
        "link_involture": "",
        "apri_involture": "",
        "stato_ruolo": "",
        "stato_cnc": "",
    }
    assert list(row)[: len(prefix) + len(common)] == prefix + list(common)
    assert {key: row[key] for key in common} == common
    assert row["comune"] == ("" if kind == "CF_PIVA_PARTICELLE" else "Comune input")
    assert row["sub"] == ("" if kind == "CF_PIVA_PARTICELLE" else "Sub input")


@pytest.mark.parametrize("kind", ["CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"])
@pytest.mark.parametrize(
    "field, value",
    [
        (field, value)
        for field in (
            "num_distretto",
            "nome_distretto",
            "riordino_code",
            "riordino_maglia",
            "riordino_lotto",
            "superficie_mq",
            "superficie_grafica_mq",
        )
        for value in ((None, 0, 12) if field.startswith("superficie") else (None, "", "0"))
    ],
)
def test_bulk_optional_match_columns_preserve_values(kind, field, value):
    match = CatAnagraficaMatch(
        particella_id=UUID(int=1), foglio="1", particella="2", **{field: value}
    )
    result = CatAnagraficaBulkSearchRowResult(row_index=1, esito="FOUND", message="OK", match=match)
    row = exports._build_bulk_export_rows(kind, [result])[0]
    assert row[field] == ("" if value is None else getattr(match, field))


@pytest.mark.parametrize("display", ["Comune", "Comune - Frazione", "Other"])
def test_live_fraction_resolution_order_and_cache(monkeypatch, display):
    option = CapacitasLookupOption(id="1", display=display)
    client = SimpleNamespace(search_frazioni=AsyncMock(return_value=[option]))
    monkeypatch.setattr(
        exports, "_apply_section_frazione_hints", lambda *args, **kwargs: ["missing"]
    )
    cache = {}
    result = asyncio.run(exports._resolve_live_frazione_options(client, "Comune", None, cache))
    assert result == [option] and list(cache.values()) == [[option]]
    client.search_frazioni.assert_awaited_once_with("Comune")


def test_live_retry_clears_section_and_collect_skips_failure(monkeypatch):
    option = CapacitasLookupOption(id="1", display="Comune")
    row = CapacitasTerrenoRow.model_validate({"Foglio": "1", "Partic": "2"})
    client = SimpleNamespace(
        search_terreni=AsyncMock(side_effect=[None, SimpleNamespace(rows=[row])])
    )
    result = asyncio.run(
        exports._search_live_rows_for_fraction(
            client, frazione=option, sezione="A", foglio="1", particella="2", sub=None
        )
    )
    assert result == [row]
    assert [call.args[0].sezione for call in client.search_terreni.await_args_list] == ["A", ""]
    monkeypatch.setattr(
        exports, "_resolve_live_frazione_options", AsyncMock(return_value=[option, option])
    )
    monkeypatch.setattr(
        exports,
        "_search_live_rows_for_fraction",
        AsyncMock(side_effect=[RuntimeError("failed"), [row]]),
    )
    hits = asyncio.run(
        exports._collect_live_search_hits(
            client,
            comune="Comune",
            sezione="A",
            foglio="1",
            particella="2",
            sub=None,
            frazione_cache={},
        )
    )
    assert len(hits) == 1 and hits[0].row is row and hits[0].frazione_id == "1"


def test_sister_latest_extraction_selection_json_and_empty_rows():
    first = parcel(comune_nome="Nome Comune", extraction_id=UUID(int=10))
    older = parcel(comune_nome="Nome Comune", extraction_id=UUID(int=11))
    owner = SimpleNamespace(
        codice_fiscale="CF",
        denominazione="Ente",
        diritto="Proprieta",
        quota="1/1",
        data_nascita=date(1980, 1, 1),
        luogo_nascita="Roma",
    )
    without_date = SimpleNamespace(**{**vars(owner), "data_nascita": None})
    extraction = SimpleNamespace(
        payload_json={"history_events": [{"act": "Atto"}], "related_parcels": []}
    )
    database = RecordingDatabase(
        [
            [
                (first, owner, extraction),
                (first, without_date, extraction),
                (older, owner, extraction),
            ],
            [(first, extraction), (first, extraction)],
        ]
    )
    rows = [{"comune": " nome comune ", "foglio": "1", "particella": "2"}, {"comune": "missing"}]
    exports._attach_sister_data(database, rows)
    assert rows[0]["sister_dati_presenti"] == "si"
    assert [value["data_nascita"] for value in json.loads(rows[0]["sister_dati"])] == [
        "1980-01-01",
        None,
    ]
    assert json.loads(rows[0]["sister_storico"])["eventi"] == [{"act": "Atto"}]
    assert (
        rows[1]["sister_dati"] == rows[1]["sister_storico"] == rows[1]["sister_dati_presenti"] == ""
    )
    exports._attach_sister_data(RecordingDatabase([[], []]), [])


def test_comune_options_and_invalid_downloads():
    options = asyncio.run(
        exports.list_comune_export_options(RecordingDatabase([[(1, "Comune"), (2, "")]]), None)
    )
    assert [(option.codice, option.nome) for option in options] == [("1", "Comune"), ("2", "2")]
    for comune, expected in [(" ", 400), ("123", 404), ("Comune", 404)]:
        with pytest.raises(HTTPException) as failure:
            asyncio.run(
                exports.download_comune_bulk_export(
                    comune, "csv", "gaia", RecordingDatabase([[]]), None
                )
            )
        assert failure.value.status_code == expected


@pytest.mark.parametrize("source", ["gaia", "live"])
@pytest.mark.parametrize("format_name", ["csv", "xlsx"])
def test_download_comune_sources_filename_payload_and_response(monkeypatch, source, format_name):
    first = parcel()
    second = parcel(id=UUID(int=2), nome_comune=None, particella="3")
    database = RecordingDatabase([[first, second], [], []])
    match = CatAnagraficaMatch(particella_id=first.id, foglio="1", particella="2")
    live_result = CatAnagraficaBulkSearchRowResult(
        row_index=1, esito="FOUND", message="OK", match=match
    )
    live = AsyncMock(return_value=SimpleNamespace(results=[live_result]))
    monkeypatch.setattr(execution, "execute_bulk_search_payload", live)
    monkeypatch.setattr(
        exports, "_load_consorzio_presence_by_particella_ids", lambda db, ids: {first.id}
    )
    matches = []

    def build_match(db, value, presente_in_catasto_consorzio):
        matches.append((value.id, presente_in_catasto_consorzio))
        return match

    monkeypatch.setattr(exports, "_build_match", build_match)
    response = asyncio.run(
        exports.download_comune_bulk_export("123", format_name, source, database, None)
    )
    assert (
        f"catasto-intestatari-comune-nome-comune-{source}.{format_name}"
        in response.headers["content-disposition"]
    )
    if source == "live":
        payload, actual_database = live.await_args.args
        assert actual_database is database and payload.include_capacitas_live
        assert [row.comune for row in payload.rows] == ["Nome Comune", "123"]
        assert [row.row_index for row in payload.rows] == [1, 2]
        assert matches == []
    else:
        assert matches == [(first.id, True), (second.id, False)]
        live.assert_not_awaited()
