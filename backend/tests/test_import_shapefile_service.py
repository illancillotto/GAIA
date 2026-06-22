from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.catasto_phase1 import CatImportBatch
from app.modules.catasto.services import import_shapefile as service


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
        self.rollbacks = 0
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

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def refresh(self, obj, attribute_names=None) -> None:
        self.refreshes.append((obj, attribute_names))


def test_build_ogr_pg_connection_string_and_escape_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service.settings, "database_url", "postgresql://user:pw@db.example:5433/gaia")
    assert service._build_ogr_pg_connection_string() == "PG:host=db.example port=5433 dbname=gaia user=user password=pw"

    monkeypatch.setattr(service.settings, "database_url", "postgresql://user@db.example/gaia")
    assert service._build_ogr_pg_connection_string() == "PG:host=db.example port=5432 dbname=gaia user=user"

    monkeypatch.setattr(service.settings, "database_url", "sqlite:///tmp/test.db")
    with pytest.raises(ValueError, match="PostgreSQL"):
        service._build_ogr_pg_connection_string()

    monkeypatch.setattr(service.settings, "database_url", "postgresql:///gaia")
    with pytest.raises(ValueError, match="incompleta"):
        service._build_ogr_pg_connection_string()

    assert service._escape_sql_string("O'Hara") == "O''Hara"


def test_drop_staging_table_and_apply_best_effort_settings() -> None:
    class _RollbackErrorDb(_FakeDb):
        def rollback(self) -> None:
            self.rollbacks += 1
            raise RuntimeError("boom")

    db = _RollbackErrorDb([_FakeResult()])
    service.drop_staging_table(db, "cat_stage")
    assert db.rollbacks == 1
    assert db.commits == 1
    assert 'DROP TABLE IF EXISTS "cat_stage"' in db.executed[0][0]

    db2 = _FakeDb([_FakeResult(), _FakeResult()])

    def execute_with_one_failure(statement, params=None):
        sql = str(statement)
        db2.executed.append((sql, params))
        if "BAD" in sql:
            raise RuntimeError("bad setting")
        return _FakeResult()

    db2.execute = execute_with_one_failure  # type: ignore[method-assign]
    service._apply_best_effort_local_settings(db2, ["SET LOCAL ok = 1", "SET LOCAL BAD = 1"])
    assert db2.rollbacks == 1


def test_load_zip_to_staging_happy_path_and_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    zip_buffer = io.BytesIO()
    import zipfile

    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("shape/test.shp", b"dummy")
        zf.writestr("shape/test.dbf", b"dummy")
        zf.writestr("shape/test.shx", b"dummy")
    zip_bytes = zip_buffer.getvalue()

    class _FakeTemporaryDirectory:
        def __enter__(self):
            return str(tmp_path)

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FakeReader:
        def __init__(self, shp_path, encoding):
            if encoding == "utf-8":
                raise RuntimeError("bad utf8")
            self._len = 8

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __len__(self):
            return self._len

    class _FakeStdout:
        def __iter__(self):
            return iter(["0...10...50...", "100 - done"])

        def close(self):
            return None

    class _FakeProcess:
        def __init__(self):
            self.stdout = _FakeStdout()

        def wait(self):
            return 0

    monkeypatch.setattr(service.tempfile, "TemporaryDirectory", _FakeTemporaryDirectory)
    monkeypatch.setattr(service.os, "walk", lambda root: iter([(str(tmp_path / "shape"), [], ["test.shp", "test.dbf"])]))
    monkeypatch.setattr(service, "_build_ogr_pg_connection_string", lambda: "PG:ok")
    monkeypatch.setattr(service.subprocess, "Popen", lambda *args, **kwargs: _FakeProcess())
    monkeypatch.setattr(service, "pyshp", None, raising=False)
    import shapefile as real_pyshp
    monkeypatch.setattr(real_pyshp, "Reader", _FakeReader)

    progress: list[tuple[int, int]] = []
    filename = service.load_zip_to_staging(
        _FakeDb([]),
        zip_bytes=zip_bytes,
        source_srid=3003,
        staging_table="cat_stage",
        progress_callback=lambda done, total: progress.append((done, total)),
    )

    assert filename == "test.shp"
    assert progress[0] == (0, 8)
    assert progress[-1] == (8, 8)

    monkeypatch.setattr(service.os, "walk", lambda root: iter([(str(tmp_path), [], ["README.txt"])]))
    with pytest.raises(ValueError, match="Nessun file .shp trovato"):
        service.load_zip_to_staging(_FakeDb([]), zip_bytes=zip_bytes)

    monkeypatch.setattr(service.os, "walk", lambda root: iter([(str(tmp_path / "shape"), [], ["test.shp"])]))

    class _BadProcess(_FakeProcess):
        def wait(self):
            return 9

    monkeypatch.setattr(service.subprocess, "Popen", lambda *args, **kwargs: _BadProcess())
    with pytest.raises(ValueError, match="exit code 9"):
        service.load_zip_to_staging(_FakeDb([]), zip_bytes=zip_bytes)


def test_load_zip_to_staging_without_callback_and_reader_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    zip_buffer = io.BytesIO()
    import zipfile

    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("shape/test.shp", b"dummy")
    zip_bytes = zip_buffer.getvalue()

    class _FakeTemporaryDirectory:
        def __enter__(self):
            return str(tmp_path)

        def __exit__(self, exc_type, exc, tb):
            return False

    class _NoStdoutProcess:
        def __init__(self):
            self.stdout = None

        def wait(self):
            return 0

    monkeypatch.setattr(service.tempfile, "TemporaryDirectory", _FakeTemporaryDirectory)
    monkeypatch.setattr(service.os, "walk", lambda root: iter([(str(tmp_path / "shape"), [], ["test.shp"])]))
    monkeypatch.setattr(service, "_build_ogr_pg_connection_string", lambda: "PG:ok")
    monkeypatch.setattr(service.subprocess, "Popen", lambda *args, **kwargs: _NoStdoutProcess())

    class _AlwaysFailReader:
        def __init__(self, shp_path, encoding):
            raise RuntimeError(f"bad {encoding}")

    import shapefile as real_pyshp

    monkeypatch.setattr(real_pyshp, "Reader", _AlwaysFailReader)
    with pytest.raises(RuntimeError, match="bad latin-1"):
        service.load_zip_to_staging(_FakeDb([]), zip_bytes=zip_bytes)

    class _ReaderOk:
        def __init__(self, shp_path, encoding):
            self._len = 2

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __len__(self):
            return self._len

    monkeypatch.setattr(real_pyshp, "Reader", _ReaderOk)
    assert service.load_zip_to_staging(_FakeDb([]), zip_bytes=zip_bytes, source_srid=0) == "test.shp"


def test_finalize_shapefile_import_prechecks_and_fast_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "get_capacitas_code_by_catastale", lambda: {"A001": 165})
    monkeypatch.setattr(service, "get_official_name_by_catastale", lambda: {"A001": "Comune Test"})

    missing_db = _FakeDb([_FakeResult(scalar_one=False)])
    with pytest.raises(ValueError, match="Tabella staging non trovata"):
        service.finalize_shapefile_import(missing_db, created_by=7)

    no_geom_db = _FakeDb(
        [
            _FakeResult(scalar_one=True),
            _FakeResult(scalar_one=3),
            _FakeResult(scalar_one_or_none=None),
        ]
    )
    with pytest.raises(ValueError, match="Nessuna colonna geometry"):
        service.finalize_shapefile_import(no_geom_db, created_by=7)

    dropped: list[str] = []
    monkeypatch.setattr(service, "drop_staging_table", lambda current_db, staging_table="cat_particelle_staging": dropped.append(staging_table))
    monkeypatch.setattr(service, "_apply_best_effort_local_settings", lambda current_db, statements: None)

    batch_id = uuid4()
    fast_db = _FakeDb(
        [
            _FakeResult(scalar_one=True),
            _FakeResult(scalar_one=12),
            _FakeResult(scalar_one_or_none="wkb_geometry"),
            _FakeResult(scalar_one=0),  # current particelle count
            _FakeResult(),  # create temp fast stage
            _FakeResult(),  # create index
            _FakeResult(scalar_one=5),  # deduped count
            _FakeResult(),  # insert chunk
        ]
    )
    logs: list[str] = []

    result = service.finalize_shapefile_import(
        fast_db,
        created_by=3,
        source_srid=4326,
        staging_table="cat_stage",
        batch_id=batch_id,
        filename="particelle.zip",
        log_callback=logs.append,
    )

    batch = next(item for item in fast_db.added if isinstance(item, CatImportBatch))
    assert result["batch_id"] == str(batch_id)
    assert result["status"] == "completed"
    assert result["report"]["fast_path_empty_db"] is True
    assert result["report"]["records_deduped_unique"] == 5
    assert result["report"]["records_inserted_current"] == 5
    assert batch.filename == "particelle.zip"
    assert batch.righe_totali == 12
    assert batch.righe_importate == 5
    assert batch.status == "completed"
    assert fast_db.commits == 1
    assert dropped == ["cat_stage"]
    assert any("Fast path DB vuoto [2/4]" in msg for msg in logs)


def test_finalize_shapefile_import_fast_path_existing_batch_without_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service, "get_capacitas_code_by_catastale", lambda: {"A001": 165})
    monkeypatch.setattr(service, "get_official_name_by_catastale", lambda: {"A001": "Comune Test"})
    monkeypatch.setattr(service, "_apply_best_effort_local_settings", lambda current_db, statements: None)

    dropped: list[str] = []
    monkeypatch.setattr(service, "drop_staging_table", lambda current_db, staging_table="cat_particelle_staging": dropped.append(staging_table))

    batch_id = uuid4()
    existing_batch = CatImportBatch(
        id=batch_id,
        filename="seed.zip",
        tipo="shapefile",
        anno_campagna=None,
        hash_file=None,
        righe_totali=1,
        righe_importate=1,
        righe_anomalie=0,
        status="processing",
        report_json={"seed": True},
        created_by=11,
    )
    db = _FakeDb(
        [
            _FakeResult(scalar_one=True),
            _FakeResult(scalar_one=4),
            _FakeResult(scalar_one_or_none="geom"),
            _FakeResult(scalar_one=0),
            _FakeResult(),
            _FakeResult(),
            _FakeResult(scalar_one=2),
            _FakeResult(),
        ],
        existing_batch=existing_batch,
    )

    result = service.finalize_shapefile_import(
        db,
        created_by=11,
        source_srid=None,
        staging_table="cat_stage",
        batch_id=batch_id,
        filename=None,
        cleanup_staging=False,
    )

    assert result["status"] == "completed"
    assert result["report"]["seed"] is True
    assert result["report"]["records_deduped_unique"] == 2
    assert result["report"]["records_inserted_current"] == 2
    assert existing_batch.filename == "seed.zip"
    assert existing_batch.righe_totali == 4
    assert existing_batch.righe_importate == 2
    assert db.refreshes == [(existing_batch, ["report_json"])]
    assert db.commits == 1
    assert dropped == []
    assert not any('SET "geom" = ST_Transform' in sql for sql, _ in db.executed)


def test_finalize_shapefile_import_scd2_path_updates_existing_batch_and_transforms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "get_capacitas_code_by_catastale", lambda: {"A001": 165, "B002": 166})
    monkeypatch.setattr(service, "get_official_name_by_catastale", lambda: {"A001": "Comune Uno", "B002": "Comune Due"})
    applied: list[list[str]] = []
    dropped: list[str] = []
    monkeypatch.setattr(service, "_apply_best_effort_local_settings", lambda current_db, statements: applied.append(statements))
    monkeypatch.setattr(service, "drop_staging_table", lambda current_db, staging_table="cat_particelle_staging": dropped.append(staging_table))

    batch_id = uuid4()
    existing_batch = CatImportBatch(
        id=batch_id,
        filename="seed.zip",
        tipo="shapefile",
        anno_campagna=None,
        hash_file=None,
        righe_totali=0,
        righe_importate=0,
        righe_anomalie=0,
        status="processing",
        report_json={"seed": True},
        created_by=9,
    )
    db = _FakeDb(
        [
            _FakeResult(scalar_one=True),
            _FakeResult(scalar_one=20),
            _FakeResult(scalar_one_or_none="geom"),
            _FakeResult(),  # transform
            _FakeResult(scalar_one=7),  # current particelle count
            _FakeResult(rowcount=2),  # history
            _FakeResult(),  # close current
            _FakeResult(rowcount=4),  # insert current
        ],
        existing_batch=existing_batch,
    )
    logs: list[str] = []

    result = service.finalize_shapefile_import(
        db,
        created_by=9,
        source_srid=3003,
        staging_table="cat_stage",
        batch_id=batch_id,
        filename="import.zip",
        log_callback=logs.append,
        cleanup_staging=False,
    )

    assert result["status"] == "completed"
    assert result["report"]["seed"] is True
    assert result["report"]["records_history_written"] == 2
    assert result["report"]["records_inserted_current"] == 4
    assert result["report"]["fast_path_empty_db"] is False
    assert existing_batch.filename == "import.zip"
    assert existing_batch.righe_totali == 20
    assert existing_batch.righe_importate == 4
    assert existing_batch.status == "completed"
    assert existing_batch.completed_at is not None
    assert db.refreshes == [(existing_batch, ["report_json"])]
    assert db.commits == 1
    assert dropped == []
    assert any("ST_Transform" in sql for sql, _ in db.executed)
    assert applied and "SET LOCAL jit = off" in applied[0]
    assert any("SCD2 [3/4]" in msg for msg in logs)
