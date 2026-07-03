from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.catasto_phase1 import CatAdeAlignmentAuditChange, CatAdeAlignmentAuditRun, CatAdeSyncRun
from app.modules.catasto.ade_autosync_scheduler import (
    _run_catasto_ade_autosync_job,
    register_catasto_ade_autosync_scheduler,
)
from app.modules.catasto.services.ade_wfs import get_ade_alignment_audit_run_detail, list_ade_alignment_audit_runs, run_ade_autosync_job


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.mark.anyio
async def test_register_catasto_ade_autosync_scheduler_registers_job(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_cron", "0 4 * * *")
    monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_timezone", "Europe/Rome")
    monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_enabled", True)

    await register_catasto_ade_autosync_scheduler(scheduler, lambda: None)

    job = scheduler.get_job("catasto_ade_autosync")
    assert job is not None
    assert job.id == "catasto_ade_autosync"
    assert job.max_instances == 1


@pytest.mark.anyio
async def test_run_catasto_ade_autosync_job_wrapper_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        closed = False

        def close(self) -> None:
            self.closed = True

    fake_db = FakeDb()

    def fake_get_db():
        yield fake_db

    monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_enabled", False)

    called = False

    def fake_run(_db) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("app.modules.catasto.ade_autosync_scheduler.run_ade_autosync_job", fake_run)

    await _run_catasto_ade_autosync_job(fake_get_db)

    assert fake_db.closed is True
    assert called is False


def test_run_ade_autosync_job_requires_bbox_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    db = TestingSessionLocal()
    try:
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_min_lon", None)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_min_lat", 39.8)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_max_lon", 8.7)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_max_lat", 39.9)

        with pytest.raises(ValueError, match="Config autosync AdE incompleta"):
            run_ade_autosync_job(db)
    finally:
        db.close()


def test_run_ade_autosync_job_skips_when_active_run_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    db = TestingSessionLocal()
    try:
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_min_lon", 8.5)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_min_lat", 39.8)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_max_lon", 8.7)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_max_lat", 39.9)
        monkeypatch.setattr("app.modules.catasto.services.ade_wfs.has_active_ade_sync_run", lambda _db: True)

        result = run_ade_autosync_job(db)

        assert result["status"] == "skipped"
        assert result["reason"] == "active_run"
    finally:
        db.close()


def test_run_ade_autosync_job_executes_sync_and_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    db = TestingSessionLocal()
    try:
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_min_lon", 8.5)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_min_lat", 39.8)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_max_lon", 8.7)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_max_lat", 39.9)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_max_tile_km2", 4.0)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_max_tiles", 25)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_count", 1000)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_max_pages_per_tile", 20)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_geometry_threshold_m", 1.5)
        monkeypatch.setattr("app.core.config.settings.catasto_ade_autosync_allow_suppress_missing", False)
        monkeypatch.setattr(
            "app.core.config.settings.catasto_ade_autosync_categories",
            "nuove_in_ade,geometrie_variate",
        )
        monkeypatch.setattr("app.modules.catasto.services.ade_wfs.has_active_ade_sync_run", lambda _db: False)

        captured: dict[str, object] = {}

        def fake_sync(*_args, **kwargs) -> dict[str, object]:
            captured["sync_kwargs"] = kwargs
            return {"run_id": "11111111-1111-1111-1111-111111111111"}

        def fake_apply(_db, run_id: str, **kwargs) -> dict[str, object]:
            captured["apply_run_id"] = run_id
            captured["apply_kwargs"] = kwargs
            return {"run_id": run_id, "audit_run_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}

        monkeypatch.setattr("app.modules.catasto.services.ade_wfs.sync_ade_parcels_bbox", fake_sync)
        monkeypatch.setattr("app.modules.catasto.services.ade_wfs.apply_ade_alignment", fake_apply)

        result = run_ade_autosync_job(db)

        assert result["status"] == "completed"
        assert result["sync"]["run_id"] == "11111111-1111-1111-1111-111111111111"
        assert result["apply"]["audit_run_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        assert captured["apply_run_id"] == "11111111-1111-1111-1111-111111111111"
        assert captured["apply_kwargs"] == {
            "categories": ["nuove_in_ade", "geometrie_variate"],
            "geometry_threshold_m": 1.5,
            "confirm": True,
            "allow_suppress_missing": False,
            "execution_mode": "scheduler",
        }
    finally:
        db.close()


def test_alignment_audit_history_services_return_runs_and_changes() -> None:
    db = TestingSessionLocal()
    try:
        ade_run = CatAdeSyncRun(
            id=uuid4(),
            status="completed",
            progress_phase="completed",
            request_bbox_json={"min_lon": 8.58, "min_lat": 39.88, "max_lon": 8.59, "max_lat": 39.89},
            tiles=1,
            tiles_completed=1,
            features=10,
            upserted=2,
            with_geometry=2,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(ade_run)
        db.flush()

        audit_run = CatAdeAlignmentAuditRun(
            id=uuid4(),
            ade_run_id=ade_run.id,
            execution_mode="scheduler",
            status="applied",
            requested_bbox_json=ade_run.request_bbox_json,
            selected_categories_json=["nuove_in_ade"],
            geometry_threshold_m=Decimal("1.000"),
            allow_suppress_missing=False,
            counters_json={
                "inserted_new": 1,
                "updated_geometry": 0,
                "suppressed_missing": 0,
                "skipped_ambiguous": 0,
                "skipped_not_selected": 0,
                "skipped_missing_comune": 0,
            },
            warnings_json=[],
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(audit_run)
        db.flush()

        db.add(
            CatAdeAlignmentAuditChange(
                audit_run_id=audit_run.id,
                operation="insert_new",
                category="nuove_in_ade",
                national_cadastral_reference="A357000800.101",
                codice_catastale="A357",
                foglio="8",
                particella="101",
                before_state_json=None,
                after_state_json={"source_type": "ade_wfs", "suppressed": False},
            )
        )
        db.commit()

        runs = list_ade_alignment_audit_runs(db)
        detail = get_ade_alignment_audit_run_detail(db, str(audit_run.id))

        assert len(runs) == 1
        assert runs[0]["audit_run_id"] == str(audit_run.id)
        assert runs[0]["execution_mode"] == "scheduler"
        assert detail["audit_run_id"] == str(audit_run.id)
        assert detail["changes"][0]["operation"] == "insert_new"
        assert detail["changes"][0]["after_state"]["source_type"] == "ade_wfs"
    finally:
        db.close()
