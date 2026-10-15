"""Characterization of the CF_PIVA_PARTICELLE row branch of execute_bulk_search_payload."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from app.modules.catasto.routes.anagrafica import execution
from app.schemas.catasto_phase1 import (
    CatAnagraficaBulkSearchRequest,
    CatAnagraficaBulkSearchRow,
    CatAnagraficaBulkSearchRowResult,
    CatAnagraficaMatch,
)


class _Result:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[object]:
        return self.values


class _DB:
    def __init__(
        self,
        results: list[object],
        *,
        commit_errors: list[Exception] | None = None,
    ) -> None:
        self.results = list(results)
        self.commit_errors = list(commit_errors or [])
        self.statements: list[Any] = []
        self.events: list[str] = []

    def execute(self, statement: Any) -> _Result:
        self.statements.append(statement)
        self.events.append("execute")
        value = self.results.pop(0)
        if isinstance(value, Exception):
            raise value
        return _Result(value)

    def commit(self) -> None:
        self.events.append("commit")
        if self.commit_errors:
            raise self.commit_errors.pop(0)

    def rollback(self) -> None:
        self.events.append("rollback")


class _Resolver:
    instances: list[_Resolver] = []

    def __init__(self, db: object) -> None:
        self.dirty = False
        self.closed = False
        self.enriched: list[object] = []
        _Resolver.instances.append(self)

    async def enrich_match(self, particella: Any, match: CatAnagraficaMatch) -> CatAnagraficaMatch:
        self.enriched.append(particella.id)
        self.dirty = True
        return match.model_copy(update={"note": "live"})

    async def close(self) -> None:
        self.closed = True


def _particella() -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), foglio="1", particella="2")


def _payload(
    *rows: CatAnagraficaBulkSearchRow, live: bool = False
) -> CatAnagraficaBulkSearchRequest:
    return CatAnagraficaBulkSearchRequest(
        kind="CF_PIVA_PARTICELLE", include_capacitas_live=live, rows=list(rows)
    )


@pytest.fixture
def collaborators(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Any]]:
    calls: dict[str, list[Any]] = {"presence": [], "build": []}
    present: set[object] = set()

    def load_presence(db: object, ids: set[object]) -> set[object]:
        calls["presence"].append(set(ids))
        return {pid for pid in ids if pid in present}

    def build_match(
        db: object, particella: Any, *, presente_in_catasto_consorzio: bool
    ) -> CatAnagraficaMatch:
        calls["build"].append((particella.id, presente_in_catasto_consorzio))
        return CatAnagraficaMatch(
            particella_id=particella.id,
            foglio=particella.foglio,
            particella=particella.particella,
            presente_in_catasto_consorzio=presente_in_catasto_consorzio,
        )

    _Resolver.instances = []
    monkeypatch.setattr(execution, "_load_consorzio_presence_by_particella_ids", load_presence)
    monkeypatch.setattr(execution, "_build_match", build_match)
    monkeypatch.setattr(execution, "_CapacitasLiveResolver", _Resolver)
    calls["present"] = [present]
    return calls


def _run(
    payload: CatAnagraficaBulkSearchRequest, db: _DB
) -> tuple[list[CatAnagraficaBulkSearchRowResult], list[tuple[int, int, int, int]]]:
    progress: list[tuple[int, int, int, int]] = []

    async def on_row(
        done: int,
        total: int,
        row: CatAnagraficaBulkSearchRow,
        results: list[CatAnagraficaBulkSearchRowResult],
    ) -> None:
        progress.append((done, total, row.row_index, len(results)))

    response = asyncio.run(
        execution.execute_bulk_search_payload(payload, db, on_row_processed=on_row)
    )
    return response.results, progress


def _params(statement: Any) -> list[object]:
    return list(statement.compile().params.values())


def _sql(statement: Any) -> str:
    return " ".join(str(statement).split())


def test_a_missing_tax_key_is_invalid_without_queries(collaborators: dict[str, list[Any]]) -> None:
    db = _DB([])
    results, progress = _run(
        _payload(CatAnagraficaBulkSearchRow(row_index=3, codice_fiscale="   ", partita_iva="")), db
    )

    assert [r.model_dump(exclude_none=True) for r in results] == [
        {
            "row_index": 3,
            "codice_fiscale_input": "   ",
            "partita_iva_input": "",
            "esito": "INVALID_ROW",
            "message": "Campo obbligatorio mancante (codice_fiscale o partita_iva).",
        }
    ]
    assert results[0].matches is None and results[0].matches_count is None
    assert db.events == []
    assert progress == [(1, 1, 3, 1)]
    assert collaborators["presence"] == []


def test_b_no_particella_ids_skips_second_query_and_still_commits_dirty_live(
    collaborators: dict[str, list[Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    class _DirtyResolver(_Resolver):
        def __init__(self, db: object) -> None:
            super().__init__(db)
            self.dirty = True

    monkeypatch.setattr(execution, "_CapacitasLiveResolver", _DirtyResolver)
    db = _DB([[None, None]])
    results, progress = _run(
        _payload(CatAnagraficaBulkSearchRow(row_index=1, codice_fiscale=" abc "), live=True), db
    )

    result = results[0]
    assert (result.esito, result.message, result.matches_count, result.matches) == (
        "NOT_FOUND",
        "Nessuna particella associata trovata.",
        0,
        [],
    )
    assert result.match is None and result.particella_id is None
    assert db.events == ["execute", "commit"]
    assert "ABC" in _params(db.statements[0])
    assert 200 in _params(db.statements[0])
    resolver = _Resolver.instances[0]
    assert resolver.dirty is False and resolver.closed is True
    assert collaborators["presence"] == [] and collaborators["build"] == []
    assert progress == [(1, 1, 1, 1)]


def test_c_ids_without_current_particelle_are_not_found(
    collaborators: dict[str, list[Any]],
) -> None:
    first, second = uuid4(), uuid4()
    db = _DB([[first, None, second, first], []])
    results, progress = _run(
        _payload(CatAnagraficaBulkSearchRow(row_index=2, codice_fiscale="cf1")), db
    )

    result = results[0]
    assert (result.esito, result.message, result.matches_count, result.matches) == (
        "NOT_FOUND",
        "Nessuna particella associata trovata.",
        0,
        [],
    )
    assert result.model_dump(mode="json") == {
        "row_index": 2,
        "comune_input": None,
        "sezione_input": None,
        "foglio_input": None,
        "particella_input": None,
        "sub_input": None,
        "codice_fiscale_input": "cf1",
        "partita_iva_input": None,
        "esito": "NOT_FOUND",
        "message": "Nessuna particella associata trovata.",
        "particella_id": None,
        "match": None,
        "matches": [],
        "matches_count": 0,
    }
    assert db.events == ["execute", "execute"]
    assert [first, second] in _params(db.statements[1])
    assert collaborators["presence"] == [set()]
    assert progress == [(1, 1, 2, 1)]


def test_d_found_uses_partita_iva_fallback_dedup_order_and_live_enrichment(
    collaborators: dict[str, list[Any]],
) -> None:
    p1, p2 = _particella(), _particella()
    collaborators["present"][0].add(p2.id)
    db = _DB([[p2.id, p1.id, p2.id], [p1, p2]])
    results, _ = _run(
        _payload(
            CatAnagraficaBulkSearchRow(row_index=5, codice_fiscale=" ", partita_iva=" it0123x "),
            live=True,
        ),
        db,
    )

    result = results[0]
    assert (result.esito, result.message, result.matches_count) == ("FOUND", "OK", 2)
    assert result.codice_fiscale_input == " " and result.partita_iva_input == " it0123x "
    assert [m.particella_id for m in result.matches or []] == [p1.id, p2.id]
    assert [m.presente_in_catasto_consorzio for m in result.matches or []] == [False, True]
    assert all(m.note == "live" for m in result.matches or [])
    assert result.match == (result.matches or [])[0] and result.particella_id == p1.id
    assert "IT0123X" in _params(db.statements[0])
    assert [p2.id, p1.id] in _params(db.statements[1])
    utenze_sql, particelle_sql = _sql(db.statements[0]), _sql(db.statements[1])
    assert "FROM cat_utenze_irrigue" in utenze_sql
    assert "ORDER BY cat_utenze_irrigue.anno_campagna DESC LIMIT :param_1" in utenze_sql
    assert db.statements[0].compile().params["param_1"] == 200
    assert "FROM cat_particelle" in particelle_sql
    assert "cat_particelle.is_current IS true" in particelle_sql
    assert particelle_sql.endswith("LIMIT :param_1")
    assert db.statements[1].compile().params["param_1"] == 200
    assert collaborators["presence"] == [{p1.id, p2.id}]
    assert collaborators["build"] == [(p1.id, False), (p2.id, True)]
    resolver = _Resolver.instances[0]
    assert resolver.enriched == [p1.id, p2.id]
    assert db.events == ["execute", "execute", "commit"]
    assert resolver.dirty is False and resolver.closed is True


def test_d2_found_without_live_does_not_commit(collaborators: dict[str, list[Any]]) -> None:
    p1 = _particella()
    db = _DB([[p1.id], [p1]])
    results, _ = _run(_payload(CatAnagraficaBulkSearchRow(row_index=1, codice_fiscale="CF")), db)
    assert results[0].esito == "FOUND" and results[0].particella_id == p1.id
    assert db.events == ["execute", "execute"]
    assert _Resolver.instances == []


def test_e_commit_failure_after_tax_row_appends_found_then_error_and_rolls_back(
    collaborators: dict[str, list[Any]],
) -> None:
    p1 = _particella()
    db = _DB([[p1.id], [p1], []], commit_errors=[RuntimeError("commit boom")])
    results, progress = _run(
        _payload(
            CatAnagraficaBulkSearchRow(row_index=1, codice_fiscale="CF", comune=None),
            CatAnagraficaBulkSearchRow(row_index=2, partita_iva="PIVA"),
            live=True,
        ),
        db,
    )

    assert [(r.row_index, r.esito) for r in results] == [
        (1, "FOUND"),
        (1, "ERROR"),
        (2, "NOT_FOUND"),
    ]
    error = results[1]
    assert error.message == "commit boom"
    assert (error.codice_fiscale_input, error.partita_iva_input, error.comune_input) == (
        "CF",
        None,
        None,
    )
    assert db.events == ["execute", "execute", "commit", "rollback", "execute"]
    assert progress == [(2, 2, 1, 2), (3, 2, 2, 3)]
    resolver = _Resolver.instances[0]
    assert resolver.dirty is False and resolver.closed is True


def test_f_query_failure_yields_error_row_without_rollback_and_continues(
    collaborators: dict[str, list[Any]],
) -> None:
    db = _DB([RuntimeError("db down"), [None]])
    results, progress = _run(
        _payload(
            CatAnagraficaBulkSearchRow(row_index=1, codice_fiscale="CF", partita_iva="PI"),
            CatAnagraficaBulkSearchRow(row_index=2, codice_fiscale="CF2"),
        ),
        db,
    )

    assert [(r.row_index, r.esito, r.message) for r in results] == [
        (1, "ERROR", "db down"),
        (2, "NOT_FOUND", "Nessuna particella associata trovata."),
    ]
    assert (results[0].codice_fiscale_input, results[0].partita_iva_input) == ("CF", "PI")
    assert db.events == ["execute", "execute"]
    assert progress == [(1, 2, 1, 1), (2, 2, 2, 2)]
