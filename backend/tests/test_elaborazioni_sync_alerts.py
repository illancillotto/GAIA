from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.core.database import get_db
from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.models.capacitas import CapacitasParticelleSyncJob
from app.models.catasto import CatastoBatch, CatastoRuoloAutoSyncConfig
from app.models.wc_sync_job import WCSyncJob
from app.modules.elaborazioni.router import router as module_router
from app.modules.elaborazioni.sync_alerts import SYNC_SOURCES, collect_sync_alerts
from app.modules.presenze.models import (
    PresenzeAutoSyncConfig,
    PresenzeCredential,
    PresenzeSyncJob,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            ApplicationUser(
                id=1,
                username="admin",
                email="admin@example.test",
                password_hash="unused",
                role="admin",
            )
        )
        session.commit()
        yield session
    engine.dispose()


def job_values(model, now, status):
    values = {"status": status}
    if hasattr(model, "created_at"):
        values["created_at"] = now
    if hasattr(model, "started_at"):
        values["started_at"] = now
    if model is PresenzeSyncJob:
        values.update(requested_by_user_id=1, period_start=date.today(), period_end=date.today())
    if model is CatastoBatch:
        values.update(user_id=1, total_items=1, batch_kind="manual_batch")
    if model.__name__ == "SyncJob":
        values["requested_by_user_id"] = 1
    if model.__name__ == "AnprJobRun":
        values.update(
            run_date=date.today(),
            ruolo_year=date.today().year,
            batch_size=10,
            hard_daily_limit=100,
            configured_daily_limit=100,
        )
    if model.__name__ == "CatAdeSyncRun":
        values["request_bbox_json"] = {}
    if model is WCSyncJob:
        values["entity"] = "reports"
    return values


@pytest.mark.parametrize("source", SYNC_SOURCES, ids=lambda source: source.key)
def test_every_dashboard_source_reports_latest_failure_and_clears_on_recovery(db, source):
    now = datetime.now(UTC)
    values = job_values(source.model, now - timedelta(hours=1), "failed")
    if source.key == "autosync":
        values["batch_kind"] = "perpetual_sync"
    if source.key == "autodoc":
        values["entity"] = "autodoc_vehicle_details"
    db.add(source.model(**values))
    db.commit()
    alerts = collect_sync_alerts(db)
    assert len(alerts) == 1
    assert alerts[0].service == source.title
    assert alerts[0].id.startswith(f"{source.key}:job:")
    values.update({source.clock: now, "status": "completed"})
    db.add(source.model(**values))
    db.commit()
    assert collect_sync_alerts(db) == []


@pytest.mark.parametrize("status", ["error", "cancelled", "partial", "completed_with_errors"])
def test_interrupted_and_partial_outcomes_are_alerts(db, status):
    db.add(CapacitasParticelleSyncJob(status=status, error_detail="SECRET password cookie"))
    db.commit()
    alerts = collect_sync_alerts(db)
    assert len(alerts) == 1
    assert "SECRET" not in alerts[0].model_dump_json()


@pytest.mark.parametrize("status", ["pending", "running", "queued", "completed", "skipped"])
def test_normal_waiting_active_successful_and_skipped_jobs_do_not_alert(db, status):
    db.add(CapacitasParticelleSyncJob(status=status))
    db.commit()
    assert collect_sync_alerts(db) == []


def test_no_history_no_alerts_and_monitoring_never_writes(db):
    statements = []
    event.listen(db.bind, "before_cursor_execute", lambda *args: statements.append(args[2]))
    assert collect_sync_alerts(db) == []
    assert statements
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)


def test_independent_whitecompany_entities_and_autodoc_do_not_hide_each_other(db):
    now = datetime.now(UTC)
    db.add_all(
        [
            WCSyncJob(entity="reports", status="failed", started_at=now - timedelta(hours=2)),
            WCSyncJob(entity="vehicles", status="completed", started_at=now),
            WCSyncJob(entity="autodoc_vehicle_details", status="error", started_at=now),
        ]
    )
    db.commit()
    assert {alert.service for alert in collect_sync_alerts(db)} == {"WhiteCompany", "AUTODOC mezzi"}


def test_latest_means_created_not_updated_and_ties_are_deterministic(db):
    now = datetime.now(UTC)
    db.add_all(
        [
            CapacitasParticelleSyncJob(id=1, status="failed", created_at=now, updated_at=now),
            CapacitasParticelleSyncJob(id=2, status="completed", created_at=now, updated_at=now),
            CapacitasParticelleSyncJob(
                id=3,
                status="failed",
                created_at=now - timedelta(days=1),
                updated_at=now + timedelta(hours=1),
            ),
        ]
    )
    db.commit()
    assert collect_sync_alerts(db) == []


def test_sister_manual_autosync_and_other_owners_are_independent(db):
    now = datetime.now(UTC)
    db.add(
        ApplicationUser(id=2, username="other", email="other@example.test", password_hash="unused")
    )
    db.add_all(
        [
            CatastoBatch(
                user_id=1, total_items=1, batch_kind="manual_batch", status="failed", created_at=now
            ),
            CatastoBatch(
                user_id=1,
                total_items=1,
                batch_kind="perpetual_sync",
                status="running",
                created_at=now,
            ),
            CatastoBatch(
                user_id=2,
                total_items=1,
                batch_kind="perpetual_sync",
                status="failed",
                created_at=now,
            ),
        ]
    )
    db.commit()
    assert {alert.service for alert in collect_sync_alerts(db)} == {
        "SISTER visure",
        "SISTER autosync",
    }


@pytest.mark.parametrize("active", [False, True])
def test_enabled_inaz_schedule_requires_an_active_credential(db, active):
    db.add(
        PresenzeCredential(
            id=1,
            application_user_id=1,
            label="INAZ",
            username="private-login",
            password_encrypted="SECRET",
            active=active,
        )
    )
    db.add(PresenzeAutoSyncConfig(job_enabled=True, credential_id=1))
    db.commit()
    alerts = collect_sync_alerts(db)
    assert len(alerts) == int(not active)
    assert "SECRET" not in str(alerts)
    assert "private-login" not in str(alerts)


def test_missing_inaz_credential_alerts_only_when_schedule_enabled(db):
    config = PresenzeAutoSyncConfig(job_enabled=True)
    db.add(config)
    db.commit()
    assert collect_sync_alerts(db)[0].id == "presenze:credential:1:None"
    config.job_enabled = False
    db.commit()
    assert collect_sync_alerts(db) == []


def test_sister_planner_error_even_if_automatically_disabled_and_clears_after_recovery(db):
    config = CatastoRuoloAutoSyncConfig(
        user_id=1,
        enabled=False,
        last_error_message="SECRET auth error",
    )
    db.add(config)
    db.commit()
    alert = collect_sync_alerts(db)[0]
    assert alert.service == "SISTER autosync"
    assert "SECRET" not in alert.model_dump_json()
    config.last_error_message = ""
    db.commit()
    assert collect_sync_alerts(db) == []


def test_expired_inaz_worker_lease_reports_loss_without_changing_jobs(db):
    now = datetime.now(UTC)
    db.add_all(
        [
            PresenzeSyncJob(
                **job_values(PresenzeSyncJob, now, "running"),
                lease_expires_at=now - timedelta(minutes=1),
            ),
            PresenzeSyncJob(
                **job_values(PresenzeSyncJob, now, "running"),
                lease_expires_at=now + timedelta(minutes=5),
            ),
            PresenzeSyncJob(**job_values(PresenzeSyncJob, now, "pending")),
        ]
    )
    db.commit()
    alerts = collect_sync_alerts(db)
    assert len(alerts) == 1
    assert alerts[0].id.startswith("presenze:lease:")
    assert db.query(PresenzeSyncJob).filter_by(status="running").count() == 2


@pytest.mark.parametrize(
    "role,active,expected",
    [
        ("admin", True, 200),
        ("super_admin", True, 200),
        ("operator", True, 403),
        ("viewer", True, 403),
        ("admin", False, 403),
    ],
)
def test_endpoint_permissions_use_real_role_and_active_user_dependencies(
    db, role, active, expected
):
    app = FastAPI()
    app.include_router(module_router)
    user = db.get(ApplicationUser, 1)
    user.role, user.is_active = role, active
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        response = client.get("/elaborazioni/sync-alerts")
    assert response.status_code == expected
    if expected == 200:
        assert response.json() == []


def test_endpoint_requires_authentication():
    app = FastAPI()
    app.include_router(module_router)
    with TestClient(app) as client:
        assert client.get("/elaborazioni/sync-alerts").status_code == 401
