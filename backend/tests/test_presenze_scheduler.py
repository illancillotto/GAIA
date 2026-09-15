from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.presenze.models import PresenzeCredential
from app.modules.presenze.scheduler import _run_job_wrapper, register_inaz_scheduler
from app.modules.presenze.services.auto_sync import trigger_auto_sync_job

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _create_user(username: str) -> ApplicationUser:
    db = TestingSessionLocal()
    try:
        user = ApplicationUser(
            username=username,
            email=f"{username}@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
            module_accessi=True,
            module_presenze=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


@pytest.mark.anyio
async def test_register_inaz_scheduler_adds_job(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")

    class FakeDb:
        def close(self) -> None:
            return None

    def fake_get_db():
        db = FakeDb()
        yield db

    await register_inaz_scheduler(scheduler, fake_get_db)

    job = scheduler.get_job("presenze_auto_sync")
    assert job is not None
    assert job.id == "presenze_auto_sync"


def test_run_job_wrapper_closes_plain_db_object(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    class FakeDb:
        def close(self) -> None:
            events.append("closed")

    def fake_get_db():
        return FakeDb()

    monkeypatch.setattr(
        "app.modules.presenze.scheduler.trigger_auto_sync_job",
        lambda db: events.append("triggered"),
    )

    _run_job_wrapper(fake_get_db)

    assert events == ["triggered", "closed"]


def test_run_job_wrapper_consumes_generator_and_swallows_job_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class FakeDb:
        def close(self) -> None:
            events.append("closed")

    def fake_get_db():
        db = FakeDb()
        yield db
        events.append("generator_exhausted")

    def _boom(db) -> None:
        events.append("triggered")
        raise RuntimeError("scheduler failure")

    monkeypatch.setattr("app.modules.presenze.scheduler.trigger_auto_sync_job", _boom)

    _run_job_wrapper(fake_get_db)

    assert events == ["triggered", "closed", "generator_exhausted"]


def test_trigger_auto_sync_job_creates_pending_job(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _create_user("presenze_scheduler_user")
    db: Session = TestingSessionLocal()
    try:
        credential = PresenzeCredential(
            application_user_id=user.id,
            label="Auto",
            username="auto.scheduler",
            password_encrypted="encrypted",
            active=True,
        )
        db.add(credential)
        db.commit()
        db.refresh(credential)

        config_response = SimpleNamespace(
            id=1,
            job_enabled=True,
            credential_id=credential.id,
            collaborator_limit=None,
            updated_at=None,
            updated_by_user_id=user.id,
        )
        monkeypatch.setattr(
            "app.modules.presenze.services.auto_sync.get_auto_sync_config",
            lambda db: config_response,
        )
        monkeypatch.setattr(
            "app.modules.presenze.services.auto_sync._reconcile_and_has_open_sync_job",
            lambda db: (False, False),
        )

        job = trigger_auto_sync_job(db)

        assert job is not None
        assert job.status == "pending"
        assert job.worker_pid is None
        assert job.params_json["trigger"] == "auto"
    finally:
        db.close()


def test_punch_reminder_scheduler_registers_dynamic_watcher() -> None:
    from app.modules.presenze.scheduler import register_punch_reminder_scheduler

    scheduler = AsyncIOScheduler(timezone="UTC")
    register_punch_reminder_scheduler(scheduler, lambda: None)
    job = scheduler.get_job("presenze_whatsapp_punch_reminders")
    assert job is not None
    assert job.max_instances == 1


def test_reminder_due_matches_the_configured_rome_minute() -> None:
    from app.modules.presenze.scheduler import _reminder_is_due
    from app.modules.presenze.services.whatsapp_config import environment_whatsapp_config

    config = environment_whatsapp_config()
    scheduled = datetime(2026, 9, 15, 7, 30, tzinfo=UTC)
    assert _reminder_is_due(config, scheduled) is True
    assert _reminder_is_due(config, scheduled.replace(minute=31)) is False


def test_punch_reminder_wrapper_runs_job_only_with_a_sender(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.modules.presenze import scheduler as presenze_scheduler

    events: list[str] = []

    class FakeDb:
        def close(self) -> None:
            events.append("closed")

    config = SimpleNamespace(provider="", reminder_cron="30 9 * * 1-5")
    monkeypatch.setattr(presenze_scheduler, "load_whatsapp_config", lambda db: config)
    presenze_scheduler._run_punch_reminder_wrapper(FakeDb)
    config.provider = "dry_run"
    monkeypatch.setattr(presenze_scheduler, "_reminder_is_due", lambda config: True)
    monkeypatch.setattr(presenze_scheduler, "build_whatsapp_sender", lambda config: None)
    presenze_scheduler._run_punch_reminder_wrapper(FakeDb)
    monkeypatch.setattr(presenze_scheduler, "build_whatsapp_sender", lambda config: "sender")
    monkeypatch.setattr(
        presenze_scheduler, "build_dispatch_options_from_settings", lambda config: "options"
    )
    monkeypatch.setattr(
        presenze_scheduler,
        "run_punch_reminder_job",
        lambda db, sender, options, config: events.append(f"{sender}:{options}"),
    )
    presenze_scheduler._run_punch_reminder_wrapper(FakeDb)
    assert events == ["closed", "closed", "sender:options", "closed"]


def test_run_job_wrapper_tolerates_db_without_close(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    monkeypatch.setattr(
        "app.modules.presenze.scheduler.trigger_auto_sync_job",
        lambda db: events.append("triggered"),
    )

    _run_job_wrapper(lambda: object())

    assert events == ["triggered"]


@pytest.mark.anyio
async def test_register_presenze_scheduler_adds_sync_and_reminder_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.modules.presenze.scheduler import register_presenze_scheduler

    scheduler = AsyncIOScheduler(timezone="UTC")

    await register_presenze_scheduler(scheduler, lambda: None)

    assert {job.id for job in scheduler.get_jobs()} == {
        "presenze_auto_sync",
        "presenze_whatsapp_punch_reminders",
    }
