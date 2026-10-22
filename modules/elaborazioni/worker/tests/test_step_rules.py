from __future__ import annotations

import pytest

from step_rules import (
    ListReference,
    StepIntegrityError,
    TributiCollector,
    expected_tributi,
    fingerprint,
    grid_link_selector,
    record_key,
    sheet_documents,
)


def _page(page: int, rows: int, total: int = 25, pages: int = 3) -> dict:
    return {
        "total": total,
        "page": page,
        "pages": pages,
        "fields": [{"name": "COD_FIS_NEW"}],
        "rows": [{"n": index} for index in range(rows)],
    }


def test_record_key_and_fingerprint() -> None:
    assert record_key({"COD_ENT": "14215", "COD_FIS_NEW": "CF"}) == "14215:CF"
    with pytest.raises(StepIntegrityError):
        record_key({"COD_ENT": "14215"})
    assert fingerprint([1]) == fingerprint([1]) != fingerprint([2])


def test_list_reference_validates_every_page() -> None:
    reference = ListReference.from_first_page(_page(1, 10))
    assert reference.page_of(0) == 1 and reference.page_of(10) == 2
    reference.validate(_page(3, 5))
    for broken, message in (
        (_page(2, 10, total=26), "totale"),
        (_page(3, 4), "righe"),
        ({**_page(2, 10), "fields": []}, "colonne"),
    ):
        with pytest.raises(StepIntegrityError, match=message):
            reference.validate(broken)
    for first in (_page(1, 0), _page(2, 10), _page(1, 10, pages=4)):
        with pytest.raises(StepIntegrityError, match="Paginazione"):
            ListReference.from_first_page(first)


def _grid(rows: list[dict], *, fields=("NUM_DOC", "NUM_TRIB"), total: int | None = None) -> dict:
    return {
        "id": "isc_Grid_1",
        "fields": [{"name": name} for name in fields],
        "rows": rows,
        "totalRows": len(rows) if total is None else total,
    }


def test_sheet_documents_collects_all_document_grids() -> None:
    first = {"COD_ENT": "1", "NUM_DOC": "A", "PRG_COO": 1}
    second = {"COD_ENT": "1", "NUM_DOC": "B", "PRG_COO": 1}
    payments = _grid([{"NUM_QUI": "1"}], fields=("NUM_QUI",))
    entries, reconciliation = sheet_documents([_grid([first]), payments, _grid([second])], "1")
    assert [entry.document["NUM_DOC"] for entry in entries] == ["A", "B"]
    assert reconciliation == {"listed": 1, "observed": 2, "status": "detail_exceeds_list"}
    assert sheet_documents([_grid([first])], 1)[1]["status"] == "matched"

    cases = (
        ([_grid([first], total=2)], "1", "parzialmente"),
        ([payments], "1", "Nessuna tabella"),
        ([_grid([first, first])], "2", "duplicato"),
        ([_grid([first])], "2", "incoerente"),
        ([_grid([first])], None, "incoerente"),
    )
    for grids, expected, message in cases:
        with pytest.raises(StepIntegrityError, match=message):
            sheet_documents(grids, expected)


def test_expected_tributi() -> None:
    assert expected_tributi({"NUM_TRIB": 3}) == 3
    with pytest.raises(StepIntegrityError):
        expected_tributi({"NUM_TRIB": "x"})


def _tributi_page(page: int, rows: list[str], *, total: int = 3, pages: int = 2) -> dict:
    return {
        "total": total,
        "page": page,
        "pages": pages,
        "rows": [{"NUM_DOC": "D", "k": key} for key in rows],
    }


def test_tributi_collector_accepts_only_complete_distinct_pages() -> None:
    collector = TributiCollector(num_doc="D", expected=3)
    collector.start(_tributi_page(1, ["a", "b"]))
    collector.add(_tributi_page(1, ["a", "b"]), 1)
    collector.add(_tributi_page(2, ["c"]), 2)
    result = collector.result()
    assert [row["k"] for row in result["rows"]] == ["a", "b", "c"]
    assert [page["rows"] for page in result["pages"]] == [2, 1]

    for state, message in (
        (_tributi_page(1, ["a", "b"], total=4), "dichiarati"),
        (_tributi_page(1, []), "dichiarati"),
    ):
        with pytest.raises(StepIntegrityError, match=message):
            TributiCollector(num_doc="D", expected=3).start(state)

    repeated = TributiCollector(num_doc="D", expected=4)
    repeated.start(_tributi_page(1, ["a", "b"], total=4))
    repeated.add(_tributi_page(1, ["a", "b"], total=4), 1)
    with pytest.raises(StepIntegrityError, match="ripetuta"):
        repeated.add(_tributi_page(2, ["a", "b"], total=4), 2)
    with pytest.raises(StepIntegrityError, match="incompleta"):
        repeated.add(None, 2)
    with pytest.raises(StepIntegrityError, match="incoerente"):
        repeated.result()

    foreign = TributiCollector(num_doc="OTHER", expected=3)
    foreign.start(_tributi_page(1, ["a", "b"]))
    with pytest.raises(StepIntegrityError, match="documento differente"):
        foreign.add(_tributi_page(1, ["a", "b"]), 1)


def test_grid_link_selector() -> None:
    grid = _grid([], fields=("NUM_DOC", "NUM_TRIB"))
    assert grid_link_selector(grid, 2, "NUM_TRIB") == 'a[onclick*="isc_Grid_1."][onclick*=",2,1)"]'
    with pytest.raises(StepIntegrityError, match="Colonna"):
        grid_link_selector(grid, 0, "NOPE")
