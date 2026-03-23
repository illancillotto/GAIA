from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.jobs.sync import run_live_sync_job, run_scheduled_live_sync_cycle
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.sync_run import SyncRun
from app.services.nas_connector import NasConnectorError


class FlakyNasClient:
    def __init__(self, failures_before_success: int) -> None:
        self.failures_before_success = failures_before_success
        self.commands: list[str] = []

    def run_command(self, command: str) -> str:
        self.commands.append(command)
        if self.failures_before_success > 0:
            self.failures_before_success -= 1
            raise NasConnectorError("temporary ssh failure")

        mapping = {
            "getent passwd": "mrossi:x:1001:100:Mario Rossi:/var/services/homes/mrossi:/sbin/nologin\n",
            "getent group": "amministrazione:x:2001:mrossi\n",
            "ls /volume1": "contabilita\n",
            "synoacltool -get /volume1/contabilita": "allow: group:amministrazione:read,write\n",
        }
        return mapping[command]


def test_run_live_sync_job_retries_and_then_succeeds(monkeypatch) -> None:
    monkeypatch.setattr("app.jobs.sync.settings.sync_live_max_attempts", 3)
    monkeypatch.setattr("app.jobs.sync.settings.sync_live_retry_delay_seconds", 0)
    monkeypatch.setattr("app.services.sync.settings.nas_passwd_command", "getent passwd")
    monkeypatch.setattr("app.services.sync.settings.nas_group_command", "getent group")
    monkeypatch.setattr("app.services.sync.settings.nas_shares_command", "ls /volume1")
    monkeypatch.setattr(
        "app.services.sync.settings.nas_acl_command_template",
        "synoacltool -get /volume1/{share}",
    )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    sleep_calls: list[float] = []
    try:
        db.add(
            ApplicationUser(
                username="reviewer",
                email="reviewer@example.local",
                password_hash=hash_password("secret123"),
                role=ApplicationUserRole.ADMIN.value,
                is_active=True,
            )
        )
        db.commit()

        result = run_live_sync_job(
            db,
            client=FlakyNasClient(failures_before_success=1),
            sleep_fn=lambda seconds: sleep_calls.append(seconds),
        )
    finally:
        db.close()

    assert result.attempts_used == 2
    assert result.sync_result.persisted_users == 1
    assert sleep_calls == [0]
    assert db.query(SyncRun).count() == 1
    sync_run = db.query(SyncRun).one()
    assert sync_run.status == "succeeded"
    assert sync_run.trigger_type == "job"
    assert sync_run.attempts_used == 2
    assert sync_run.duration_ms is not None
    assert sync_run.started_at <= sync_run.completed_at


def test_run_live_sync_job_raises_after_max_attempts(monkeypatch) -> None:
    monkeypatch.setattr("app.jobs.sync.settings.sync_live_max_attempts", 2)
    monkeypatch.setattr("app.jobs.sync.settings.sync_live_retry_delay_seconds", 0)
    monkeypatch.setattr("app.services.sync.settings.nas_passwd_command", "getent passwd")
    monkeypatch.setattr("app.services.sync.settings.nas_group_command", "getent group")
    monkeypatch.setattr("app.services.sync.settings.nas_shares_command", "ls /volume1")
    monkeypatch.setattr(
        "app.services.sync.settings.nas_acl_command_template",
        "synoacltool -get /volume1/{share}",
    )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        db.add(
            ApplicationUser(
                username="reviewer",
                email="reviewer@example.local",
                password_hash=hash_password("secret123"),
                role=ApplicationUserRole.ADMIN.value,
                is_active=True,
            )
        )
        db.commit()

        try:
            run_live_sync_job(
                db,
                client=FlakyNasClient(failures_before_success=5),
                sleep_fn=lambda seconds: None,
            )
        except NasConnectorError as exc:
            assert str(exc) == "temporary ssh failure"
            assert db.query(SyncRun).count() == 1
            sync_run = db.query(SyncRun).one()
            assert sync_run.status == "failed"
            assert sync_run.attempts_used == 2
            assert sync_run.started_at <= sync_run.completed_at
        else:
            raise AssertionError("Expected NasConnectorError after max retry attempts")
    finally:
        db.close()


def test_run_scheduled_live_sync_cycle_sets_scheduler_metadata(monkeypatch) -> None:
    monkeypatch.setattr("app.jobs.sync.settings.sync_live_max_attempts", 1)
    monkeypatch.setattr("app.jobs.sync.settings.sync_live_retry_delay_seconds", 0)
    monkeypatch.setattr("app.services.sync.settings.nas_passwd_command", "getent passwd")
    monkeypatch.setattr("app.services.sync.settings.nas_group_command", "getent group")
    monkeypatch.setattr("app.services.sync.settings.nas_shares_command", "ls /volume1")
    monkeypatch.setattr(
        "app.services.sync.settings.nas_acl_command_template",
        "synoacltool -get /volume1/{share}",
    )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        db.add(
            ApplicationUser(
                username="reviewer",
                email="reviewer@example.local",
                password_hash=hash_password("secret123"),
                role=ApplicationUserRole.ADMIN.value,
                is_active=True,
            )
        )
        db.commit()

        result = run_scheduled_live_sync_cycle(db, client=FlakyNasClient(failures_before_success=0))
        sync_run = db.query(SyncRun).one()
    finally:
        db.close()

    assert result.attempts_used == 1
    assert sync_run.trigger_type == "scheduled"
    assert sync_run.initiated_by == "system"
    assert sync_run.source_label == "scheduler:ssh"
    assert sync_run.started_at <= sync_run.completed_at
