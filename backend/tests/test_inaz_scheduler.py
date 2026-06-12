from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.inaz.models import InazCredential
from app.modules.inaz.scheduler import _run_job_wrapper, register_inaz_scheduler
from app.modules.inaz.services.auto_sync import trigger_auto_sync_job


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
            module_inaz=True,
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

    job = scheduler.get_job("inaz_auto_sync")
    assert job is not None
    assert job.id == "inaz_auto_sync"


def test_run_job_wrapper_closes_plain_db_object(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    class FakeDb:
        def close(self) -> None:
            events.append("closed")

    def fake_get_db():
        return FakeDb()

    monkeypatch.setattr("app.modules.inaz.scheduler.trigger_auto_sync_job", lambda db: events.append("triggered"))

    _run_job_wrapper(fake_get_db)

    assert events == ["triggered", "closed"]


def test_run_job_wrapper_consumes_generator_and_swallows_job_errors(monkeypatch: pytest.MonkeyPatch) -> None:
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

    monkeypatch.setattr("app.modules.inaz.scheduler.trigger_auto_sync_job", _boom)

    _run_job_wrapper(fake_get_db)

    assert events == ["triggered", "closed", "generator_exhausted"]


def test_trigger_auto_sync_job_creates_pending_job(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _create_user("inaz_scheduler_user")
    db: Session = TestingSessionLocal()
    try:
        credential = InazCredential(
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
        monkeypatch.setattr("app.modules.inaz.services.auto_sync.get_auto_sync_config", lambda db: config_response)
        monkeypatch.setattr("app.modules.inaz.services.auto_sync.has_running_sync_job", lambda db: False)
        monkeypatch.setattr("app.modules.inaz.services.auto_sync.launch_sync_worker", lambda job: 7070)

        job = trigger_auto_sync_job(db)

        assert job is not None
        assert job.status == "pending"
        assert job.worker_pid == 7070
        assert job.params_json["trigger"] == "auto"
    finally:
        db.close()
