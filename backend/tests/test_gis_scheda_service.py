from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Self
from uuid import uuid4

import pytest
from app.modules.gis.models import GisSchedaTerritoriale
from app.modules.gis.scheda_territoriale import router as sheet_router
from app.modules.gis.scheda_territoriale import service
from app.modules.gis.schemas import GisSchedaTerritorialeCreate
from fastapi import BackgroundTasks, HTTPException


class _Scalars:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def all(self) -> list[object]:
        return self.rows


class _Session:
    def __init__(
        self,
        *,
        parcel: object = None,
        sheet: object = None,
        user: object = None,
        completed: list | None = None,
    ) -> None:
        self.parcel = parcel
        self.sheet = sheet
        self.user = user
        self.completed = completed or []
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.commits = 0
        self.rollbacks = 0

    def get(self, model: type, identifier: object) -> object | None:
        name = model.__name__
        if name == "CatParticella":
            return self.parcel
        if name == "ApplicationUser":
            return self.user
        if (
            name == "GisSchedaTerritoriale"
            and self.sheet
            and self.sheet.id == identifier
        ):
            return self.sheet
        return None

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        if self.sheet is None and self.added:
            self.sheet = self.added[0]
            self.sheet.id = self.sheet.id or uuid4()

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, value: object) -> None:
        if getattr(value, "requested_at", None) is None:
            value.requested_at = datetime.now(UTC)
        if getattr(value, "updated_at", None) is None:
            value.updated_at = datetime.now(UTC)

    def rollback(self) -> None:
        self.rollbacks += 1

    def scalars(self, statement: object) -> _Scalars:
        del statement
        return _Scalars(self.completed)

    def delete(self, value: object) -> None:
        self.deleted.append(value)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        del args


def _sheet(status: str = "queued", requester: int = 4) -> GisSchedaTerritoriale:
    return GisSchedaTerritoriale(
        id=uuid4(),
        particella_id=uuid4(),
        requested_by_user_id=requester,
        status=status,
        source_snapshot_json={"status": "pending"},
        requested_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_request_get_and_download_enforce_ownership_and_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(id=4, role="viewer")
    db = _Session(parcel=object())
    created = service.request_sheet(db, user, uuid4())  # type: ignore[arg-type]
    assert created.status == "queued"
    assert created.source_snapshot_json == {"status": "pending"}
    assert [item.event_type for item in db.added if hasattr(item, "event_type")] == [
        "scheda_territoriale.requested"
    ]

    with pytest.raises(HTTPException) as missing:
        service.request_sheet(_Session(), user, uuid4())  # type: ignore[arg-type]
    assert missing.value.status_code == 404

    sheet = _sheet()
    db = _Session(sheet=sheet)
    assert service.get_sheet(db, user, sheet.id) is sheet  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as denied:
        service.get_sheet(db, SimpleNamespace(id=7, role="viewer"), sheet.id)  # type: ignore[arg-type]
    assert denied.value.status_code == 403
    monkeypatch.setattr(service.services, "is_gis_admin", lambda user: True)
    assert service.get_sheet(db, SimpleNamespace(id=7), sheet.id) is sheet  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as absent:
        service.get_sheet(_Session(), user, uuid4())  # type: ignore[arg-type]
    assert absent.value.status_code == 404

    with pytest.raises(HTTPException) as pending:
        service.download_sheet(db, user, sheet.id)  # type: ignore[arg-type]
    assert pending.value.status_code == 409
    sheet.status, sheet.artifact_path = "completed", "/sheet.pdf"
    monkeypatch.setattr(service.artifact_storage, "read_artifact", lambda path: b"pdf")
    content, filename = service.download_sheet(db, user, sheet.id)  # type: ignore[arg-type]
    assert content == b"pdf" and str(sheet.particella_id) in filename
    monkeypatch.setattr(
        service.artifact_storage,
        "read_artifact",
        lambda path: (_ for _ in ()).throw(FileNotFoundError()),
    )
    with pytest.raises(HTTPException) as missing_pdf:
        service.download_sheet(db, user, sheet.id)  # type: ignore[arg-type]
    assert missing_pdf.value.status_code == 404


def test_generation_completes_with_snapshot_audit_artifact_and_retention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sheet = _sheet()
    db = _Session(sheet=sheet, user=SimpleNamespace(id=4))
    published: list[tuple[bytes, str]] = []
    monkeypatch.setattr(
        service,
        "collect_sheet_snapshot",
        lambda *args: {"parcel": {"id": "1"}, "excluded_layers": [{"title": "denied"}]},
    )
    monkeypatch.setattr(service, "render_pdf", lambda snapshot: b"pdf-content")
    monkeypatch.setattr(
        service.artifact_storage,
        "publish_artifact",
        lambda source, destination: published.append(
            (source.read_bytes(), destination)
        ),
    )
    monkeypatch.setattr(service, "prune_completed_sheets", lambda db, count: 0)

    service.run_generation(sheet.id, lambda: db)

    assert sheet.status == "completed"
    assert sheet.source_snapshot_json["excluded_layers"] == [{"title": "denied"}]
    assert sheet.checksum_sha256
    assert published[0][0] == b"pdf-content"
    assert any(
        getattr(item, "event_type", "") == "scheda_territoriale.completed"
        for item in db.added
    )


def test_generation_failure_keeps_snapshot_and_audits_every_failure_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sheet = _sheet()
    db = _Session(sheet=sheet, user=SimpleNamespace(id=4))
    monkeypatch.setattr(
        service,
        "collect_sheet_snapshot",
        lambda *args: (_ for _ in ()).throw(RuntimeError("collection down")),
    )
    service.run_generation(sheet.id, lambda: db)
    assert sheet.status == "failed"
    assert sheet.source_snapshot_json["status"] == "failed_before_collection"
    assert any(
        getattr(item, "event_type", "") == "scheda_territoriale.failed"
        for item in db.added
    )

    sheet = _sheet()
    sheet.source_snapshot_json = {"parcel": {"id": "1"}}
    db = _Session(sheet=sheet, user=SimpleNamespace(id=4))
    monkeypatch.setattr(
        service, "collect_sheet_snapshot", lambda *args: {"parcel": {"id": "1"}}
    )
    monkeypatch.setattr(
        service,
        "render_pdf",
        lambda snapshot: (_ for _ in ()).throw(RuntimeError("chromium down")),
    )
    service.run_generation(sheet.id, lambda: db)
    assert sheet.source_snapshot_json == {"parcel": {"id": "1"}}
    assert sheet.error_message == "chromium down"

    service.run_generation(uuid4(), lambda: _Session())

    missing_user = _sheet()
    db = _Session(sheet=missing_user)
    service.run_generation(missing_user.id, lambda: db)
    assert missing_user.error_message == "Utente richiedente non disponibile"


def test_retention_deletes_old_records_and_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    keep, old, missing_path = (
        _sheet("completed"),
        _sheet("completed"),
        _sheet("completed"),
    )
    keep.artifact_path = "/keep.pdf"
    old.artifact_path = "/old.pdf"
    db = _Session(completed=[keep, old, missing_path])
    deleted_paths: list[str] = []
    monkeypatch.setattr(
        service.artifact_storage,
        "delete_artifact",
        lambda path: deleted_paths.append(path) or True,
    )
    assert service.prune_completed_sheets(db, 1) == 2
    assert deleted_paths == ["/old.pdf"]
    assert db.deleted == [old, missing_path]
    assert db.commits == 1
    assert service.prune_completed_sheets(_Session(completed=[keep]), 1) == 0


def test_migration_upgrade_and_downgrade_are_reversible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = (
        Path(__file__).parents[1]
        / "alembic/versions/20260901_0900_gis_schede_territoriali.py"
    )
    spec = importlib.util.spec_from_file_location("gis_sheet_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    statements: list[str] = []
    monkeypatch.setattr(module.op, "execute", statements.append)
    module.upgrade()
    module.downgrade()
    assert "CREATE TABLE gis_schede_territoriali" in statements[0]
    assert statements[-1] == "DROP TABLE IF EXISTS gis_schede_territoriali"


def test_sheet_router_starts_reads_and_downloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sheet = _sheet("completed")
    user = SimpleNamespace(id=4)
    monkeypatch.setattr(
        sheet_router.service, "request_sheet", lambda db, user, parcel_id: sheet
    )
    monkeypatch.setattr(sheet_router.service, "run_generation", lambda sheet_id: None)
    monkeypatch.setattr(
        sheet_router.service, "get_sheet", lambda db, user, sheet_id: sheet
    )
    monkeypatch.setattr(
        sheet_router.service,
        "download_sheet",
        lambda db, user, sheet_id: (b"pdf", "sheet.pdf"),
    )
    tasks = BackgroundTasks()
    created = sheet_router.create_sheet(
        GisSchedaTerritorialeCreate(particella_id=sheet.particella_id),
        tasks,
        user,  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
    )
    assert created.id == sheet.id and len(tasks.tasks) == 1
    assert created.model_dump(by_alias=True)["source_snapshot"] == {
        "status": "pending"
    }
    assert "source_snapshot_json" not in created.model_dump(by_alias=True)
    assert sheet_router.get_sheet(sheet.id, user, SimpleNamespace()).id == sheet.id  # type: ignore[arg-type]
    response = sheet_router.download_sheet(sheet.id, user, SimpleNamespace())  # type: ignore[arg-type]
    assert response.body == b"pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="sheet.pdf"'
