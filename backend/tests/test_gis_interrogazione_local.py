from __future__ import annotations

from typing import Any

import pytest
from app.modules.gis.interrogazione import local_probes
from app.modules.gis.interrogazione.models import InterrogationPoint


class _Mappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _Result:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> _Mappings:
        return _Mappings(self._rows)


class _Session:
    def __init__(self, results: list[list[dict[str, Any]]]) -> None:
        self.results = list(results)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: object, params: dict[str, Any]) -> _Result:
        self.calls.append((str(statement), params))
        return _Result(self.results.pop(0))


def _point() -> InterrogationPoint:
    return InterrogationPoint(lon=9.1, lat=39.2, srid=4326, radius_m=150)


def test_local_probes_use_spatial_operators_and_link_parcel_data() -> None:
    session = _Session(
        [
            [{"id": "parcel-1", "foglio": "12", "particella": "34"}],
            [{"id": "district-1", "num_distretto": "2"}],
            [{"id": "delivery-1", "distance_m": 12.5}],
            [{"id": 7, "codice": "C-7", "distance_m": 4.0}],
            [{"id": "dui-1", "coltura": "riso"}],
            [{"tipo": "ruolo", "id": "role-1"}],
        ]
    )

    results = local_probes.probe_gaia(session, _point())  # type: ignore[arg-type]

    assert [item.status for item in results] == ["ok"] * 6
    assert [item.source_id for item in results] == [
        "particella",
        "distretto",
        "punto_consegna",
        "rete_condotte",
        "dui",
        "ruolo_utenze",
    ]
    sql = "\n".join(call[0] for call in session.calls)
    assert sql.count("ST_Intersects") == 3
    assert sql.count("ST_DWithin") == 2
    assert sql.count("ST_Expand") == 2
    assert "network.rete_condotte" in sql
    assert session.calls[-1][1] == {"particella_id": "parcel-1"}
    assert all(call[1].get("radius_m") == 150 for call in session.calls[:5])
    assert all(item.duration_ms >= 0 for item in results)


def test_local_probes_return_empty_and_skip_relation_query_without_parcel() -> None:
    session = _Session([[], [], [], [], []])

    results = local_probes.probe_gaia(session, _point())  # type: ignore[arg-type]

    assert len(session.calls) == 5
    assert all(item.status == "empty" for item in results)
    assert [item.message for item in results] == [
        "Nessun elemento trovato.",
        "Nessun elemento trovato.",
        "Nessun elemento trovato.",
        "Nessuna condotta nel raggio.",
        "Nessun elemento trovato.",
        "Nessun elemento trovato.",
    ]
    assert results[3].status == "empty"
    assert results[-1].data == []


def test_local_database_errors_propagate_to_the_orchestrator() -> None:
    class _BrokenSession:
        def execute(self, statement: object, params: dict[str, Any]) -> None:
            del statement, params
            raise RuntimeError("postgis unavailable")

    with pytest.raises(RuntimeError, match="postgis unavailable"):
        local_probes.probe_gaia(_BrokenSession(), _point())  # type: ignore[arg-type]
