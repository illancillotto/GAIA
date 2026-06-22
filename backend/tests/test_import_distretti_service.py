from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.catasto_phase1 import CatImportBatch
from app.modules.catasto.services import import_distretti as service


class _FakeResult:
    def __init__(self, *, scalar_one=None, scalar_one_or_none=None, rowcount=None) -> None:
        self._scalar_one = scalar_one
        self._scalar_one_or_none = scalar_one_or_none
        self.rowcount = rowcount

    def scalar_one(self):
        return self._scalar_one

    def scalar_one_or_none(self):
        return self._scalar_one_or_none


class _FakeDb:
    def __init__(self, results: list[_FakeResult], *, existing_batch=None) -> None:
        self._results = list(results)
        self._existing_batch = existing_batch
        self.executed: list[tuple[str, dict | None]] = []
        self.added: list[object] = []
        self.flushes = 0
        self.commits = 0
        self.refreshes: list[tuple[object, list[str] | None]] = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.executed.append((sql, params))
        if not self._results:
            raise AssertionError(f"Unexpected execute call for SQL: {sql}")
        return self._results.pop(0)

    def get(self, model, key):
        if model is CatImportBatch:
            return self._existing_batch
        return None

    def add(self, obj) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        self.flushes += 1

    def refresh(self, obj, attribute_names=None) -> None:
        self.refreshes.append((obj, attribute_names))

    def commit(self) -> None:
        self.commits += 1


def test_finalize_distretti_shapefile_import_raises_when_staging_table_is_missing() -> None:
    db = _FakeDb([_FakeResult(scalar_one=False)])

    with pytest.raises(ValueError, match="Tabella staging non trovata"):
        service.finalize_distretti_shapefile_import(db, created_by=7, staging_table="missing_stage")

    assert db.commits == 0
    assert db.added == []


def test_finalize_distretti_shapefile_import_raises_when_geometry_column_is_missing() -> None:
    batch_id = uuid4()
    db = _FakeDb(
        [
            _FakeResult(scalar_one=True),
            _FakeResult(scalar_one=4),
            _FakeResult(scalar_one_or_none=None),
        ]
    )
    logs: list[str] = []

    with pytest.raises(ValueError, match="Nessuna colonna geometry trovata"):
        service.finalize_distretti_shapefile_import(
            db,
            created_by=9,
            staging_table="cat_distretti_stage",
            batch_id=batch_id,
            filename="distretti.zip",
            log_callback=logs.append,
        )

    batch = next(item for item in db.added if isinstance(item, CatImportBatch))
    assert batch.id == batch_id
    assert batch.filename == "distretti.zip"
    assert batch.tipo == "shapefile_distretti"
    assert batch.status == "processing"
    assert db.flushes == 1
    assert logs == ["Staging distretti: 4 righe trovate — avvio finalizzazione…"]


def test_finalize_distretti_shapefile_import_raises_when_no_valid_districts_are_found(monkeypatch: pytest.MonkeyPatch) -> None:
    applied_settings: list[list[str]] = []
    monkeypatch.setattr(service, "_apply_best_effort_local_settings", lambda current_db, settings: applied_settings.append(settings))

    db = _FakeDb(
        [
            _FakeResult(scalar_one=True),
            _FakeResult(scalar_one=6),
            _FakeResult(scalar_one_or_none="geom"),
            _FakeResult(),  # update transform
            _FakeResult(),  # create raw temp
            _FakeResult(scalar_one=1),
            _FakeResult(scalar_one=2),
            _FakeResult(),  # create agg temp
            _FakeResult(scalar_one=0),
        ]
    )
    logs: list[str] = []

    with pytest.raises(ValueError, match="Nessun distretto valido"):
        service.finalize_distretti_shapefile_import(
            db,
            created_by=5,
            source_srid=3003,
            staging_table="cat_distretti_stage",
            log_callback=logs.append,
        )

    assert any("Trasformazione geometrie distretti da SRID 3003" in msg for msg in logs)
    assert any("Distretti [1/4]" in msg for msg in logs)
    assert any("Distretti [2/4]" in msg for msg in logs)
    assert applied_settings and "SET LOCAL jit = off" in applied_settings[0]


def test_finalize_distretti_shapefile_import_completes_and_updates_existing_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    batch_id = uuid4()
    existing_batch = CatImportBatch(
        id=batch_id,
        filename="seed.zip",
        tipo="shapefile_distretti",
        anno_campagna=None,
        hash_file=None,
        righe_totali=0,
        righe_importate=0,
        righe_anomalie=0,
        status="processing",
        report_json={"seed": True},
        created_by=11,
    )
    dropped: list[str] = []
    applied_settings: list[list[str]] = []
    monkeypatch.setattr(service, "drop_staging_table", lambda current_db, table_name: dropped.append(table_name))
    monkeypatch.setattr(service, "_apply_best_effort_local_settings", lambda current_db, settings: applied_settings.append(settings))

    db = _FakeDb(
        [
            _FakeResult(scalar_one=True),
            _FakeResult(scalar_one=10),
            _FakeResult(scalar_one_or_none="shape"),
            _FakeResult(),  # no transform because source_srid=4326? won't be consumed
        ],
        existing_batch=existing_batch,
    )
    # Replace results with exact path for source_srid=4326: no transform call
    db = _FakeDb(
        [
            _FakeResult(scalar_one=True),
            _FakeResult(scalar_one=10),
            _FakeResult(scalar_one_or_none="shape"),
            _FakeResult(),  # create raw temp
            _FakeResult(scalar_one=2),
            _FakeResult(scalar_one=3),
            _FakeResult(),  # create agg temp
            _FakeResult(scalar_one=5),
            _FakeResult(),  # create delta temp
            _FakeResult(scalar_one=1),
            _FakeResult(scalar_one=2),
            _FakeResult(scalar_one=2),
            _FakeResult(scalar_one=4),
            _FakeResult(),  # update distretti
            _FakeResult(),  # insert distretti
            _FakeResult(),  # close current versions
            _FakeResult(rowcount=3),  # insert versions
        ],
        existing_batch=existing_batch,
    )
    logs: list[str] = []

    result = service.finalize_distretti_shapefile_import(
        db,
        created_by=11,
        source_srid=4326,
        staging_table="cat_distretti_stage",
        batch_id=batch_id,
        filename="distretti-final.zip",
        log_callback=logs.append,
        cleanup_staging=True,
    )

    assert result["batch_id"] == str(batch_id)
    assert result["status"] == "completed"
    report = result["report"]
    assert report["seed"] is True
    assert report["staging_table"] == "cat_distretti_stage"
    assert report["righe_staging"] == 10
    assert report["distretti_validi"] == 5
    assert report["distretti_inseriti"] == 1
    assert report["distretti_aggiornati"] == 2
    assert report["distretti_invariati"] == 2
    assert report["distretti_versionati"] == 3
    assert report["distretti_assenti_nello_snapshot"] == 4
    assert report["righe_scartate_senza_numero"] == 2
    assert report["righe_scartate_senza_geometria"] == 3
    assert report["valid_from"]
    assert existing_batch.filename == "distretti-final.zip"
    assert existing_batch.righe_totali == 10
    assert existing_batch.righe_importate == 5
    assert existing_batch.righe_anomalie == 5
    assert existing_batch.status == "completed"
    assert existing_batch.completed_at is not None
    assert db.commits == 1
    assert dropped == ["cat_distretti_stage"]
    assert applied_settings and "SET LOCAL work_mem = '512MB'" in applied_settings[0]
    assert any("Distretti [4/4]" in msg for msg in logs)
    assert db.refreshes == [(existing_batch, ["report_json"])]
    assert not any("ST_Transform" in sql for sql, _ in db.executed)


def test_finalize_distretti_shapefile_import_can_skip_staging_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    dropped: list[str] = []
    monkeypatch.setattr(service, "drop_staging_table", lambda current_db, table_name: dropped.append(table_name))
    monkeypatch.setattr(service, "_apply_best_effort_local_settings", lambda current_db, settings: None)

    db = _FakeDb(
        [
            _FakeResult(scalar_one=True),
            _FakeResult(scalar_one=1),
            _FakeResult(scalar_one_or_none="geom"),
            _FakeResult(),  # transform update
            _FakeResult(),  # create raw temp
            _FakeResult(scalar_one=0),
            _FakeResult(scalar_one=0),
            _FakeResult(),  # create agg temp
            _FakeResult(scalar_one=1),
            _FakeResult(),  # create delta temp
            _FakeResult(scalar_one=1),
            _FakeResult(scalar_one=0),
            _FakeResult(scalar_one=0),
            _FakeResult(scalar_one=0),
            _FakeResult(),  # update distretti
            _FakeResult(),  # insert distretti
            _FakeResult(),  # close current versions
            _FakeResult(rowcount=1),
        ]
    )

    service.finalize_distretti_shapefile_import(
        db,
        created_by=3,
        source_srid=3003,
        staging_table="cat_distretti_stage",
        cleanup_staging=False,
    )

    assert dropped == []
    assert any("ST_Transform" in sql for sql, _ in db.executed)
