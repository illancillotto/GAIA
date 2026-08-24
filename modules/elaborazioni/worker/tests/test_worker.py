from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import sys
import types
import uuid

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


WORKER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = next((path for path in WORKER_ROOT.parents if (path / "backend").exists()), WORKER_ROOT.parents[-1])
BACKEND_ROOT = REPO_ROOT / "backend"

for path in (WORKER_ROOT, REPO_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ.setdefault("CREDENTIAL_MASTER_KEY", "WnCjZ2L63B1kIh_2mDkk8j5M6Bf0dzxN3Qv8QbQwB0A=")
os.environ.setdefault("DATABASE_URL", "sqlite:///./.pytest-worker.db")

_STUBBED_MODULE_NAMES: set[str] = set()


def _stub_module(name: str, **attrs: object) -> None:
    if name in sys.modules:
        return
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    _STUBBED_MODULE_NAMES.add(name)


playwright_module = types.ModuleType("playwright")
playwright_async_api = types.ModuleType("playwright.async_api")
playwright_async_api.Browser = object
playwright_async_api.BrowserContext = object
playwright_async_api.Download = object
playwright_async_api.Page = object
playwright_async_api.Playwright = object
playwright_async_api.TimeoutError = TimeoutError


async def _unsupported_async_playwright():
    raise RuntimeError("async_playwright non disponibile nel test stub")


playwright_async_api.async_playwright = _unsupported_async_playwright
playwright_module.async_api = playwright_async_api
sys.modules.setdefault("playwright", playwright_module)
sys.modules.setdefault("playwright.async_api", playwright_async_api)

_stub_module("pypdf", PdfReader=object, PdfWriter=object)
_stub_module("anti_captcha_client", AntiCaptchaClient=object)
_stub_module(
    "autodoc_sync",
    AUTODOC_SYNC_ENTITY="autodoc_vehicle_details",
    run_autodoc_sync_job_by_id=lambda *_args, **_kwargs: None,
)
_stub_module("browser_session", BrowserSession=object, BrowserSessionConfig=object)
_stub_module("llm_captcha_solver", LLMCaptchaSolver=object)
_stub_module("credential_vault", WorkerCredentialVault=object)
_stub_module("runtime_policy", classify_terminal_status=lambda status: status)


class _ManualCaptchaDecision:
    def __init__(self, text: str | None = None, skip: bool = False) -> None:
        self.text = text
        self.skip = skip


class _VisuraFlowResult:
    def __init__(self) -> None:
        self.status = "completed"
        self.error_message = None
        self.captcha_image_path = None
        self.captcha_method = None
        self.last_ocr_text = None
        self.file_path = self.file_size = None
        self.ade_status_payload = None
        self.remote_request_id = self.remote_request_url = None


class _VisuraFlowCallbacks:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)


async def _unsupported_execute_visura_flow(*_args, **_kwargs):
    raise RuntimeError("execute_visura_flow non disponibile nel test stub")


_stub_module(
    "visura_flow",
    ManualCaptchaDecision=_ManualCaptchaDecision,
    VisuraFlowCallbacks=_VisuraFlowCallbacks,
    VisuraFlowResult=_VisuraFlowResult,
    execute_visura_flow=_unsupported_execute_visura_flow,
)
_stub_module(
    "sister_exceptions",
    SisterInvalidDocumentError=type("SisterInvalidDocumentError", (RuntimeError,), {}),
    SisterRequestCorrelationError=type("SisterRequestCorrelationError", (RuntimeError,), {}),
    SisterServerError=type("SisterServerError", (RuntimeError,), {}),
)
_stub_module(
    "reporting",
    write_batch_report=lambda _batch, _requests, target_dir: (
        Path(target_dir) / "report.json",
        Path(target_dir) / "report.md",
    ),
)
_stub_module(
    "app.modules.utenze.services.import_service",
    prepare_registry_import_jobs_for_recovery=lambda _db: [],
    run_registry_bulk_import_job_by_id=lambda _job_id: None,
)
_stub_module(
    "app.services.elaborazioni_capacitas_anagrafica_history",
    expire_stale_anagrafica_history_jobs=lambda _db: None,
    prepare_anagrafica_history_jobs_for_recovery=lambda _db: [],
)
_stub_module(
    "app.services.elaborazioni_capacitas_particelle_sync",
    expire_stale_particelle_sync_jobs=lambda _db: None,
    prepare_particelle_sync_jobs_for_recovery=lambda _db: [],
)
_stub_module(
    "app.services.elaborazioni_capacitas_runtime",
    run_anagrafica_history_job_by_id=lambda _job_id: None,
    run_incass_job_by_id=lambda _job_id: None,
    run_particelle_job_by_id=lambda _job_id: None,
    run_terreni_job_by_id=lambda _job_id: None,
)
_stub_module("app.services.elaborazioni_capacitas", has_available_credential=lambda _db, _credential_id=None: True)
_stub_module(
    "app.services.elaborazioni_capacitas_incass",
    expire_stale_incass_sync_jobs=lambda _db: None,
    prepare_incass_sync_jobs_for_recovery=lambda _db: [],
)
_stub_module(
    "app.services.elaborazioni_capacitas_terreni",
    expire_stale_terreni_sync_jobs=lambda _db: None,
    prepare_terreni_sync_jobs_for_recovery=lambda _db: [],
)
_stub_module(
    "app.modules.catasto.services.ade_status_scan",
    ADE_SCAN_PURPOSE="ade_status_scan",
    persist_ade_status_scan_result=lambda *args, **kwargs: None,
)
_stub_module(
    "app.modules.catasto.services.ade_wfs",
    execute_ade_sync_run=lambda _db, _run_id: None,
    prepare_ade_sync_runs_for_recovery=lambda _db: 0,
)
_stub_module(
    "app.modules.catasto.services.ade_historical_visura_parser",
    parse_historical_visura_pdf=lambda _path: {"classification": "unknown"},
)
_stub_module(
    "app.modules.catasto.routes.anagrafica",
    prepare_bulk_search_jobs_for_recovery=lambda _db: 0,
    prepare_distretto_export_jobs_for_recovery=lambda _db: 0,
    run_bulk_search_job_by_id=lambda _job_id: None,
    run_distretto_export_job_by_id=lambda _job_id: None,
)

import worker as worker_module
from sister_exceptions import SisterRequestCorrelationError
from sister_captcha_wait import SisterCaptchaClaim

for _module_name in (
    "app.services.elaborazioni_capacitas",
    "app.services.elaborazioni_capacitas_anagrafica_history",
    "app.services.elaborazioni_capacitas_incass",
    "app.services.elaborazioni_capacitas_particelle_sync",
    "app.services.elaborazioni_capacitas_runtime",
    "app.services.elaborazioni_capacitas_terreni",
):
    if _module_name in _STUBBED_MODULE_NAMES:
        sys.modules.pop(_module_name, None)

from app.core.database import Base
from app.models.application_user import ApplicationUser
from app.models.capacitas import (
    CapacitasAnagraficaHistoryImportJob,
    CapacitasCredential,
    CapacitasInCassSyncJob,
    CapacitasParticelleSyncJob,
    CapacitasTerreniSyncJob,
)
from app.models.posta_online import PostaOnlineCredential, PostaOnlineRegisteredMailSyncJob
from app.services.catasto_credentials import get_credential_fernet
import posta_online_sync
from app.models.catasto import (
    CatastoBatch,
    CatastoBatchStatus,
    CatastoCaptchaLog,
    CatastoDocument,
    CatastoVisuraRequest,
    CatastoVisuraRequestStatus,
)


CatastoWorker = worker_module.CatastoWorker


@pytest.fixture()
def worker_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "worker-tests.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    ApplicationUser.__table__.create(bind=engine)
    CapacitasCredential.__table__.create(bind=engine)
    CapacitasAnagraficaHistoryImportJob.__table__.create(bind=engine)
    CapacitasInCassSyncJob.__table__.create(bind=engine)
    CapacitasTerreniSyncJob.__table__.create(bind=engine)
    CapacitasParticelleSyncJob.__table__.create(bind=engine)
    PostaOnlineRegisteredMailSyncJob.__table__.create(bind=engine)
    _create_catasto_worker_tables(engine)

    monkeypatch.setattr(worker_module, "SessionLocal", SessionLocal)
    monkeypatch.setattr(worker_module, "expire_stale_anagrafica_history_jobs", lambda _db: None)
    monkeypatch.setattr(worker_module, "expire_stale_incass_sync_jobs", lambda _db: None)
    monkeypatch.setattr(worker_module, "expire_stale_terreni_sync_jobs", lambda _db: None)
    monkeypatch.setattr(worker_module, "expire_stale_particelle_sync_jobs", lambda _db: None)
    monkeypatch.setattr(worker_module, "expire_stale_registered_mail_sync_jobs", lambda _db: None)
    monkeypatch.setattr(
        worker_module.CatastoWorker,
        "_build_batch_report_dir",
        lambda _self, batch: tmp_path / "reports" / str(batch.user_id) / str(batch.id),
    )

    worker = CatastoWorker.__new__(CatastoWorker)
    worker.state = types.SimpleNamespace(stop_requested=False)
    monkeypatch.setattr(worker_module, "write_batch_report", lambda _batch, _requests, target_dir: _fake_reports(target_dir))
    yield worker, SessionLocal, tmp_path


def _create_catasto_worker_tables(engine) -> None:
    CatastoBatch.__table__.create(bind=engine)
    CatastoDocument.__table__.create(bind=engine)
    CatastoVisuraRequest.__table__.create(bind=engine)
    CatastoCaptchaLog.__table__.create(bind=engine)


def _fake_reports(target_dir: Path) -> tuple[Path, Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / "report.json"
    md_path = target_dir / "report.md"
    json_path.write_text("{}", encoding="utf-8")
    md_path.write_text("# report\n", encoding="utf-8")
    return json_path, md_path


def _seed_batch(session_factory, *, request_statuses: list[str]) -> tuple[int, uuid.UUID, list[uuid.UUID]]:
    with session_factory() as db:
        user = ApplicationUser(
            username="worker-test",
            email="worker-test@example.local",
            password_hash="hash",
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.flush()

        batch = CatastoBatch(
            user_id=user.id,
            name="batch-test",
            status=CatastoBatchStatus.PROCESSING.value,
            total_items=len(request_statuses),
        )
        db.add(batch)
        db.flush()

        request_ids: list[uuid.UUID] = []
        for index, status in enumerate(request_statuses, start=1):
            request = CatastoVisuraRequest(
                batch_id=batch.id,
                user_id=user.id,
                row_index=index,
                search_mode="immobile",
                comune="ORISTANO",
                catasto="Terreni",
                foglio=str(index),
                particella=str(index),
                tipo_visura="Sintetica",
                status=status,
            )
            db.add(request)
            db.flush()
            request_ids.append(request.id)

        db.commit()
        return user.id, batch.id, request_ids


def test_recoverable_credential_error_detects_locked_session_markers() -> None:
    errors = (RuntimeError("SISTER_SESSION_LOCKED"), RuntimeError("Timeout 60000ms exceeded"),
              RuntimeError("Utente SISTER bloccato sul portale Agenzia delle Entrate."), RuntimeError("Credenziali SISTER rifiutate: Autenticazione fallita."),
              TimeoutError("poll scaduto"), worker_module.SisterInvalidDocumentError("file HTML"),
              SisterRequestCorrelationError("baseline non disponibile"))
    assert all(map(CatastoWorker._is_recoverable_credential_error, errors))


def test_recoverable_credential_error_rejects_generic_request_failures() -> None:
    assert not CatastoWorker._is_recoverable_credential_error(RuntimeError("CAPTCHA manuale rifiutato"))
    assert not CatastoWorker._is_recoverable_credential_error(RuntimeError("Particella non trovata"))


def test_sister_server_error_cooldown_uses_progressive_backoff() -> None:
    assert CatastoWorker._compute_sister_server_error_cooldown(1) == worker_module.SISTER_SERVER_ERROR_BASE_COOLDOWN_SEC
    assert CatastoWorker._compute_sister_server_error_cooldown(2) == min(
        worker_module.SISTER_SERVER_ERROR_BASE_COOLDOWN_SEC * 2,
        worker_module.SISTER_SERVER_ERROR_MAX_COOLDOWN_SEC,
    )
    assert CatastoWorker._compute_sister_server_error_cooldown(3) == min(
        worker_module.SISTER_SERVER_ERROR_BASE_COOLDOWN_SEC * 4,
        worker_module.SISTER_SERVER_ERROR_MAX_COOLDOWN_SEC,
    )


def test_sister_server_error_cooldown_is_capped() -> None:
    assert CatastoWorker._compute_sister_server_error_cooldown(99) == worker_module.SISTER_SERVER_ERROR_MAX_COOLDOWN_SEC


def test_operating_window_allows_processing_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_module, "OPERATION_WINDOW_ENABLED", False)
    assert CatastoWorker._is_within_operating_window(datetime(2026, 5, 21, 2, 0, tzinfo=timezone.utc))


def test_operating_window_blocks_processing_outside_daily_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_module, "OPERATION_WINDOW_ENABLED", True)
    monkeypatch.setattr(worker_module, "OPERATION_WINDOW_START_HOUR", 8)
    monkeypatch.setattr(worker_module, "OPERATION_WINDOW_END_HOUR", 18)
    monkeypatch.setattr(worker_module, "OPERATION_WINDOW_TIMEZONE", "Europe/Rome")

    early_morning_utc = datetime(2026, 5, 21, 4, 30, tzinfo=timezone.utc)  # 06:30 Europe/Rome
    assert not CatastoWorker._is_within_operating_window(early_morning_utc)

    resume_at = CatastoWorker._next_operating_resume_at(early_morning_utc)
    assert resume_at is not None
    assert resume_at.astimezone(timezone.utc).hour == 6


def test_operating_window_supports_overnight_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_module, "OPERATION_WINDOW_ENABLED", True)
    monkeypatch.setattr(worker_module, "OPERATION_WINDOW_START_HOUR", 22)
    monkeypatch.setattr(worker_module, "OPERATION_WINDOW_END_HOUR", 5)
    monkeypatch.setattr(worker_module, "OPERATION_WINDOW_TIMEZONE", "Europe/Rome")

    overnight_utc = datetime(2026, 5, 21, 1, 30, tzinfo=timezone.utc)  # 03:30 Europe/Rome
    day_utc = datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc)  # 12:00 Europe/Rome
    assert CatastoWorker._is_within_operating_window(overnight_utc)
    assert not CatastoWorker._is_within_operating_window(day_utc)


def test_incass_autosync_window_supports_evening_to_morning_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_module, "INCASS_AUTOSYNC_WINDOW_ENABLED", True)
    monkeypatch.setattr(worker_module, "INCASS_AUTOSYNC_START_HOUR", 20)
    monkeypatch.setattr(worker_module, "INCASS_AUTOSYNC_END_HOUR", 6)
    monkeypatch.setattr(worker_module, "INCASS_AUTOSYNC_TIMEZONE", "Europe/Rome")

    assert not CatastoWorker._is_within_incass_autosync_window(datetime(2026, 1, 1, 18, 59, tzinfo=timezone.utc))
    assert CatastoWorker._is_within_incass_autosync_window(datetime(2026, 1, 1, 19, 0, tzinfo=timezone.utc))
    assert CatastoWorker._is_within_incass_autosync_window(datetime(2026, 1, 2, 4, 59, tzinfo=timezone.utc))
    assert not CatastoWorker._is_within_incass_autosync_window(datetime(2026, 1, 2, 5, 0, tzinfo=timezone.utc))
    assert CatastoWorker._incass_autosync_window_label() == "20:00-06:00 Europe/Rome"

    monkeypatch.setattr(worker_module, "INCASS_AUTOSYNC_TIMEZONE", "Invalid/Timezone")
    assert CatastoWorker._is_within_incass_autosync_window(datetime(2026, 1, 1, 19, 0, tzinfo=timezone.utc))

    monkeypatch.setattr(worker_module, "INCASS_AUTOSYNC_TIMEZONE", "UTC")
    monkeypatch.setattr(worker_module, "INCASS_AUTOSYNC_START_HOUR", 8)
    monkeypatch.setattr(worker_module, "INCASS_AUTOSYNC_END_HOUR", 18)
    assert CatastoWorker._is_within_incass_autosync_window(datetime(2026, 1, 1, 12, 0))
    assert not CatastoWorker._is_within_incass_autosync_window(datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc))

    monkeypatch.setattr(worker_module, "INCASS_AUTOSYNC_END_HOUR", 8)
    assert CatastoWorker._is_within_incass_autosync_window(datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc))


def test_incass_autosync_window_allows_processing_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_module, "INCASS_AUTOSYNC_WINDOW_ENABLED", False)
    assert CatastoWorker._is_within_incass_autosync_window(datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc))


def test_parse_job_families_expands_aliases() -> None:
    assert CatastoWorker._parse_job_families("visure,autodoc") == {
        "connection_tests",
        "visure_batches",
        "ade_sync",
        "bulk_search",
        "autodoc",
    }


def test_parse_job_families_rejects_unknown_values() -> None:
    with pytest.raises(ValueError):
        CatastoWorker._parse_job_families("visure,unknown-family")


def test_next_capacitas_job_waits_when_credential_is_unavailable(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker, SessionLocal, _ = worker_db
    monkeypatch.setattr(
        worker_module.CatastoWorker,
        "_is_within_incass_autosync_window",
        staticmethod(lambda _now=None: True),
    )
    monkeypatch.setattr(worker_module, "has_available_credential", lambda _db, _credential_id=None: False)
    with SessionLocal() as db:
        job = CapacitasInCassSyncJob(
            requested_by_user_id=None,
            credential_id=9,
            status="pending",
            mode="subjects_sync",
            payload_json={"subject_ids": [str(uuid.uuid4())]},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    assert worker._next_capacitas_job() is None

    with SessionLocal() as db:
        refreshed = db.get(CapacitasInCassSyncJob, job_id)
        assert refreshed is not None
        assert refreshed.status == "pending"
        assert refreshed.started_at is None
        assert refreshed.error_detail == "In attesa di una credenziale Capacitas disponibile"


def test_next_capacitas_job_claims_when_credential_is_available(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker, SessionLocal, _ = worker_db
    seen_credential_ids: list[int | None] = []
    monkeypatch.setattr(
        worker_module.CatastoWorker,
        "_is_within_incass_autosync_window",
        staticmethod(lambda _now=None: True),
    )

    def fake_has_available_credential(_db, credential_id=None):
        seen_credential_ids.append(credential_id)
        return True

    monkeypatch.setattr(worker_module, "has_available_credential", fake_has_available_credential)
    with SessionLocal() as db:
        job = CapacitasInCassSyncJob(
            requested_by_user_id=None,
            credential_id=9,
            status="queued_resume",
            mode="subjects_sync",
            payload_json={"credential_id": 4, "subject_ids": [str(uuid.uuid4())]},
            error_detail="In attesa di una credenziale Capacitas disponibile",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    assert worker._next_capacitas_job() == ("incass", job_id)

    with SessionLocal() as db:
        refreshed = db.get(CapacitasInCassSyncJob, job_id)
        assert refreshed is not None
        assert refreshed.status == "processing"
        assert refreshed.started_at is not None
        assert refreshed.error_detail is None
    assert seen_credential_ids == [4]


def test_next_capacitas_job_skips_incass_autosync_outside_window(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker, SessionLocal, _ = worker_db
    monkeypatch.setattr(
        worker_module.CatastoWorker,
        "_is_within_incass_autosync_window",
        staticmethod(lambda _now=None: False),
    )
    monkeypatch.setattr(worker_module, "has_available_credential", lambda _db, _credential_id=None: True)

    with SessionLocal() as db:
        job = CapacitasInCassSyncJob(
            requested_by_user_id=None,
            credential_id=9,
            status="pending",
            mode="subjects_sync",
            payload_json={"subject_ids": [str(uuid.uuid4())]},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    assert worker._next_capacitas_job() is None

    with SessionLocal() as db:
        refreshed = db.get(CapacitasInCassSyncJob, job_id)
        assert refreshed is not None
        assert refreshed.status == "pending"
        assert refreshed.started_at is None
        assert refreshed.error_detail == "Autosync inCASS in pausa fuori finestra oraria 20:00-06:00 Europe/Rome"


def test_next_capacitas_job_claims_manual_incass_job_outside_autosync_window(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker, SessionLocal, _ = worker_db
    monkeypatch.setattr(
        worker_module.CatastoWorker,
        "_is_within_incass_autosync_window",
        staticmethod(lambda _now=None: False),
    )
    monkeypatch.setattr(worker_module, "has_available_credential", lambda _db, _credential_id=None: True)

    with SessionLocal() as db:
        job = CapacitasInCassSyncJob(
            requested_by_user_id=1,
            credential_id=9,
            status="pending",
            mode="subjects_sync",
            payload_json={"subject_ids": [str(uuid.uuid4())]},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    assert worker._next_capacitas_job() == ("incass", job_id)

    with SessionLocal() as db:
        refreshed = db.get(CapacitasInCassSyncJob, job_id)
        assert refreshed is not None
        assert refreshed.status == "processing"
        assert refreshed.started_at is not None
        assert refreshed.error_detail is None


def test_next_posta_online_job_waits_when_credential_is_unavailable(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker, SessionLocal, _ = worker_db
    monkeypatch.setattr(worker_module, "has_available_posta_online_credential", lambda _db, _credential_id=None: False)
    with SessionLocal() as db:
        job = PostaOnlineRegisteredMailSyncJob(
            requested_by_user_id=None,
            credential_id=8,
            status="pending",
            mode="registered_mails",
            payload_json={"credential_id": 8, "annualita": [2022, 2023]},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    assert worker._next_posta_online_job_id() is None

    with SessionLocal() as db:
        refreshed = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        assert refreshed is not None
        assert refreshed.status == "pending"
        assert refreshed.started_at is None
        assert refreshed.error_detail == "In attesa di una credenziale Poste Online disponibile"


def test_next_posta_online_job_claims_when_credential_is_available(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker, SessionLocal, _ = worker_db
    seen_credential_ids: list[int | None] = []

    def fake_has_available_credential(_db, credential_id=None):
        seen_credential_ids.append(credential_id)
        return True

    monkeypatch.setattr(worker_module, "has_available_posta_online_credential", fake_has_available_credential)
    with SessionLocal() as db:
        job = PostaOnlineRegisteredMailSyncJob(
            requested_by_user_id=None,
            credential_id=8,
            status="queued_resume",
            mode="registered_mails",
            payload_json={"credential_id": 4, "annualita": [2022, 2023]},
            error_detail="In attesa di una credenziale Poste Online disponibile",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    assert worker._next_posta_online_job_id() == job_id

    with SessionLocal() as db:
        refreshed = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        assert refreshed is not None
        assert refreshed.status == "processing"
        assert refreshed.started_at is not None
        assert refreshed.error_detail is None
    assert seen_credential_ids == [4]


def test_next_posta_online_credential_test_job_bypasses_availability_check(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker, SessionLocal, _ = worker_db
    calls: list[int | None] = []

    def fake_has_available_credential(_db, credential_id=None):
        calls.append(credential_id)
        return False

    monkeypatch.setattr(worker_module, "has_available_posta_online_credential", fake_has_available_credential)
    with SessionLocal() as db:
        job = PostaOnlineRegisteredMailSyncJob(
            requested_by_user_id=None,
            credential_id=8,
            status="pending",
            mode="credential_test",
            payload_json={"credential_id": 8},
            error_detail="In attesa di una credenziale Poste Online disponibile",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    assert worker._next_posta_online_job_id() == job_id

    with SessionLocal() as db:
        refreshed = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        assert refreshed is not None
        assert refreshed.status == "processing"
        assert refreshed.started_at is not None
        assert refreshed.error_detail is None
    assert calls == []


def test_process_posta_online_job_delegates_to_worker_runner(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker, SessionLocal, _ = worker_db
    calls: list[dict[str, object]] = []

    async def fake_runner(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(worker_module, "run_posta_online_job_by_id", fake_runner)

    asyncio.run(worker._process_posta_online_job(123))

    assert calls == [{"job_id": 123, "session_factory": SessionLocal, "headless": worker_module.HEADLESS}]


def test_posta_online_sync_runner_uses_worker_client_and_persists_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "posta-online-sync.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    ApplicationUser.__table__.create(bind=engine)
    PostaOnlineCredential.__table__.create(bind=engine)
    PostaOnlineRegisteredMailSyncJob.__table__.create(bind=engine)

    generated_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr("app.services.catasto_credentials.settings.credential_master_key", generated_key)
    monkeypatch.setattr("app.core.config.settings.credential_master_key", generated_key)
    get_credential_fernet.cache_clear()
    encrypted_password = get_credential_fernet().encrypt(b"secret").decode("utf-8")

    with SessionLocal() as db:
        credential = PostaOnlineCredential(
            label="Poste",
            username="poste-user",
            password_encrypted=encrypted_password,
            min_delay_ms=1111,
            max_delay_ms=2222,
        )
        db.add(credential)
        db.flush()
        job = PostaOnlineRegisteredMailSyncJob(
            credential_id=credential.id,
            requested_by_user_id=None,
            status="processing",
            mode="registered_mails",
            payload_json={
                "credential_id": credential.id,
                "annualita": [2022, 2023],
                "max_pages": 2,
                "max_details": 3,
                "include_contacts": True,
                "include_details": True,
                "continue_on_error": True,
            },
        )
        db.add(job)
        db.commit()
        job_id = job.id

    calls: list[dict[str, object]] = []

    class FakeClient:
        def __init__(self, config) -> None:
            self.config = config

        async def __aenter__(self):
            calls.append({"event": "enter", "min_delay_ms": self.config.min_delay_ms, "max_delay_ms": self.config.max_delay_ms})
            return self

        async def __aexit__(self, *_exc_info: object) -> None:
            calls.append({"event": "exit"})

        async def login(self, username: str, password: str) -> None:
            calls.append({"event": "login", "username": username, "password": password})

        async def scrape_registered_mails(self, **_kwargs):
            calls.append({"event": "scrape"})
            return {
                "details": [{"idInvio": "11280322", "html": "<html></html>"}],
                "contacts": [{"id": "C1"}],
                "errors": [],
                "archive_ids": ["11280322"],
            }

    class FakeImportJob:
        id = uuid.uuid4()
        records_total = 1
        records_imported = 1
        records_matched = 1
        records_ambiguous = 0
        records_unmatched = 0
        records_errors = 0

    imported_payloads: list[dict[str, object]] = []

    def fake_import(db, **kwargs):
        imported_payloads.append(kwargs)
        return FakeImportJob()

    monkeypatch.setattr(posta_online_sync, "_import_tributi_registered_mails", fake_import)

    asyncio.run(
        posta_online_sync.run_posta_online_registered_mail_job_by_id(
            job_id=job_id,
            session_factory=SessionLocal,
            headless=True,
            _client_class=FakeClient,
        )
    )

    assert calls == [
        {"event": "enter", "min_delay_ms": 1111, "max_delay_ms": 2222},
        {"event": "login", "username": "poste-user", "password": "secret"},
        {"event": "scrape"},
        {"event": "exit"},
    ]
    assert imported_payloads[0]["filename"] == f"posta-online-worker-job-{job_id}.json"
    assert imported_payloads[0]["annualita"] == [2022, 2023]
    with SessionLocal() as db:
        refreshed = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        credential = db.scalar(select(PostaOnlineCredential))
        assert refreshed is not None
        assert refreshed.status == "succeeded"
        assert refreshed.result_json["details_scraped"] == 1
        assert refreshed.result_json["records_matched"] == 1
        assert credential is not None
        assert credential.last_used_at is not None


def test_posta_online_sync_runner_reuses_completed_scrape_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "posta-online-resume.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    ApplicationUser.__table__.create(bind=engine)
    PostaOnlineCredential.__table__.create(bind=engine)
    PostaOnlineRegisteredMailSyncJob.__table__.create(bind=engine)

    generated_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr("app.services.catasto_credentials.settings.credential_master_key", generated_key)
    monkeypatch.setattr("app.core.config.settings.credential_master_key", generated_key)
    monkeypatch.setattr(posta_online_sync, "POSTA_ONLINE_RESUME_STORAGE_PATH", tmp_path / "resume")
    get_credential_fernet.cache_clear()
    encrypted_password = get_credential_fernet().encrypt(b"secret").decode("utf-8")

    checkpoint_payload = {
        "details": [{"idInvio": "11280322", "html": "<html>checkpoint</html>"}],
        "contacts": [],
        "errors": [],
        "archive_ids": ["11280322"],
        "completed_scopes": ["archive", "detail:11280322"],
    }

    with SessionLocal() as db:
        credential = PostaOnlineCredential(
            label="Poste",
            username="poste-user",
            password_encrypted=encrypted_password,
            active=False,
        )
        db.add(credential)
        db.flush()
        job = PostaOnlineRegisteredMailSyncJob(
            credential_id=credential.id,
            requested_by_user_id=None,
            status="processing",
            mode="registered_mails",
            payload_json={"credential_id": credential.id, "annualita": [2022, 2023]},
        )
        db.add(job)
        db.flush()
        checkpoint_path = posta_online_sync._resume_checkpoint_path(job.id)
        posta_online_sync.write_debug_payload(checkpoint_path, checkpoint_payload)
        job.result_json = {
            "resume_state": {
                "stage": "scraped",
                "path": str(checkpoint_path),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        }
        db.commit()
        job_id = job.id
        credential_id = credential.id

    class UnexpectedClient:
        def __init__(self, _config) -> None:
            raise AssertionError("Il checkpoint completo non deve riaprire Poste Online")

    class FakeImportJob:
        id = uuid.uuid4()
        records_total = 1
        records_imported = 1
        records_matched = 1
        records_ambiguous = 0
        records_unmatched = 0
        records_errors = 0

    imported_payloads: list[dict[str, object]] = []

    def fake_import(_db, **kwargs):
        imported_payloads.append(kwargs)
        return FakeImportJob()

    monkeypatch.setattr(posta_online_sync, "_import_tributi_registered_mails", fake_import)

    asyncio.run(
        posta_online_sync.run_posta_online_registered_mail_job_by_id(
            job_id=job_id,
            session_factory=SessionLocal,
            headless=True,
            _client_class=UnexpectedClient,
        )
    )

    assert json.loads(imported_payloads[0]["content"].decode("utf-8")) == checkpoint_payload
    assert not checkpoint_path.exists()
    with SessionLocal() as db:
        refreshed = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        credential = db.get(PostaOnlineCredential, credential_id)
        assert refreshed is not None
        assert refreshed.status == "succeeded"
        assert refreshed.result_json["resumed_from_checkpoint"] is True
        assert credential is not None
        assert credential.last_used_at is not None


def test_posta_online_sync_runner_resumes_partial_scrape_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "posta-online-partial-resume.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    ApplicationUser.__table__.create(bind=engine)
    PostaOnlineCredential.__table__.create(bind=engine)
    PostaOnlineRegisteredMailSyncJob.__table__.create(bind=engine)

    generated_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr("app.services.catasto_credentials.settings.credential_master_key", generated_key)
    monkeypatch.setattr("app.core.config.settings.credential_master_key", generated_key)
    monkeypatch.setattr(posta_online_sync, "POSTA_ONLINE_RESUME_STORAGE_PATH", tmp_path / "resume")
    get_credential_fernet.cache_clear()
    encrypted_password = get_credential_fernet().encrypt(b"secret").decode("utf-8")

    checkpoint_payload = {
        "details": [{"idInvio": "A", "html": "<html>A</html>"}],
        "contacts": [{"id": "C1"}],
        "errors": [],
        "archive_ids": ["A", "B"],
        "completed_scopes": ["contacts", "archive", "detail:A"],
    }

    with SessionLocal() as db:
        credential = PostaOnlineCredential(label="Poste", username="poste-user", password_encrypted=encrypted_password)
        db.add(credential)
        db.flush()
        job = PostaOnlineRegisteredMailSyncJob(
            credential_id=credential.id,
            status="processing",
            mode="registered_mails",
            payload_json={"credential_id": credential.id, "annualita": [2022, 2023]},
        )
        db.add(job)
        db.flush()
        checkpoint_path = posta_online_sync._resume_checkpoint_path(job.id)
        posta_online_sync.write_debug_payload(checkpoint_path, checkpoint_payload)
        job.result_json = {"resume_state": {"stage": "scraping", "path": str(checkpoint_path)}}
        db.commit()
        job_id = job.id
        credential_id = credential.id

    calls: list[dict[str, object]] = []

    class ResumeClient:
        def __init__(self, _config) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc_info: object) -> None:
            return None

        async def login(self, username: str, password: str) -> None:
            calls.append({"event": "login", "username": username, "password": password})

        async def scrape_registered_mails(self, **kwargs) -> dict[str, object]:
            calls.append({"event": "scrape", "resume_payload": kwargs["resume_payload"]})
            await kwargs["progress_callback"]({**checkpoint_payload, "details": [*checkpoint_payload["details"], {"idInvio": "B", "html": "<html>B</html>"}]})
            return {**checkpoint_payload, "details": [*checkpoint_payload["details"], {"idInvio": "B", "html": "<html>B</html>"}]}

    class FakeImportJob:
        id = uuid.uuid4()
        records_total = 2
        records_imported = 2
        records_matched = 2
        records_ambiguous = 0
        records_unmatched = 0
        records_errors = 0

    monkeypatch.setattr(posta_online_sync, "_import_tributi_registered_mails", lambda _db, **_kwargs: FakeImportJob())

    asyncio.run(
        posta_online_sync.run_posta_online_registered_mail_job_by_id(
            job_id=job_id,
            session_factory=SessionLocal,
            headless=True,
            _client_class=ResumeClient,
        )
    )

    assert calls[0] == {"event": "login", "username": "poste-user", "password": "secret"}
    assert calls[1]["resume_payload"] == checkpoint_payload
    with SessionLocal() as db:
        refreshed = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        credential = db.get(PostaOnlineCredential, credential_id)
        assert refreshed is not None
        assert refreshed.status == "succeeded"
        assert refreshed.result_json["resumed_from_checkpoint"] is True
        assert credential is not None
        assert credential.last_used_at is not None


def test_posta_online_sync_preserves_resume_state_after_scrape_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "posta-online-resume-failure.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    PostaOnlineCredential.__table__.create(bind=engine)
    PostaOnlineRegisteredMailSyncJob.__table__.create(bind=engine)

    generated_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr("app.services.catasto_credentials.settings.credential_master_key", generated_key)
    monkeypatch.setattr("app.core.config.settings.credential_master_key", generated_key)
    monkeypatch.setattr(posta_online_sync, "POSTA_ONLINE_RESUME_STORAGE_PATH", tmp_path / "resume")
    get_credential_fernet.cache_clear()
    encrypted_password = get_credential_fernet().encrypt(b"secret").decode("utf-8")

    with SessionLocal() as db:
        credential = PostaOnlineCredential(label="Poste", username="poste-user", password_encrypted=encrypted_password)
        db.add(credential)
        db.flush()
        job = PostaOnlineRegisteredMailSyncJob(
            credential_id=credential.id,
            status="processing",
            mode="registered_mails",
            payload_json={"credential_id": credential.id, "annualita": [2022, 2023]},
        )
        db.add(job)
        db.flush()
        checkpoint_path = posta_online_sync._resume_checkpoint_path(job.id)
        posta_online_sync.write_debug_payload(checkpoint_path, {"archive_ids": ["A"]})
        job.result_json = {"resume_state": {"stage": "scraping", "path": str(checkpoint_path)}}
        db.commit()
        job_id = job.id

    class FailingResumeClient:
        def __init__(self, _config) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc_info: object) -> None:
            return None

        async def login(self, _username: str, _password: str) -> None:
            return None

        async def scrape_registered_mails(self, **_kwargs) -> dict[str, object]:
            raise RuntimeError("resume scrape boom")

    asyncio.run(
        posta_online_sync.run_posta_online_registered_mail_job_by_id(
            job_id=job_id,
            session_factory=SessionLocal,
            headless=True,
            _client_class=FailingResumeClient,
        )
    )

    with SessionLocal() as db:
        refreshed = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        assert refreshed is not None
        assert refreshed.status == "failed"
        assert refreshed.result_json["error"] == "resume scrape boom"
        assert refreshed.result_json["resume_state"]["stage"] == "scraping"


def test_posta_online_resume_checkpoint_helper_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "posta-online-resume-helpers.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    PostaOnlineRegisteredMailSyncJob.__table__.create(bind=engine)
    monkeypatch.setattr(posta_online_sync, "POSTA_ONLINE_RESUME_STORAGE_PATH", tmp_path / "resume")

    assert posta_online_sync._result_resume_state({"resume_state": {"stage": "bad"}}) is None
    assert posta_online_sync._load_resume_checkpoint(session_factory=SessionLocal, job_id=999) == (None, None)

    with SessionLocal() as db:
        missing_file_job = PostaOnlineRegisteredMailSyncJob(
            status="processing",
            mode="registered_mails",
            result_json={"resume_state": {"stage": "scraping", "path": str(tmp_path / "missing.json")}},
        )
        unreadable_job = PostaOnlineRegisteredMailSyncJob(status="processing", mode="registered_mails")
        invalid_payload_job = PostaOnlineRegisteredMailSyncJob(status="processing", mode="registered_mails")
        db.add_all([missing_file_job, unreadable_job, invalid_payload_job])
        db.flush()
        unreadable_dir = tmp_path / "unreadable"
        unreadable_dir.mkdir()
        unreadable_job.result_json = {"resume_state": {"stage": "scraping", "path": str(unreadable_dir)}}
        invalid_payload_path = tmp_path / "invalid.json"
        invalid_payload_path.write_text("[]", encoding="utf-8")
        invalid_payload_job.result_json = {"resume_state": {"stage": "scraping", "path": str(invalid_payload_path)}}
        db.commit()
        missing_file_job_id = missing_file_job.id
        unreadable_job_id = unreadable_job.id
        invalid_payload_job_id = invalid_payload_job.id

    assert posta_online_sync._load_resume_checkpoint(session_factory=SessionLocal, job_id=missing_file_job_id) == (None, None)
    assert posta_online_sync._load_resume_checkpoint(session_factory=SessionLocal, job_id=unreadable_job_id) == (None, None)
    assert posta_online_sync._load_resume_checkpoint(session_factory=SessionLocal, job_id=invalid_payload_job_id) == (None, None)

    posta_online_sync._write_resume_checkpoint(
        session_factory=SessionLocal,
        job_id=999,
        scrape_payload={"archive_ids": []},
        stage="scraping",
        started_at=datetime.now(timezone.utc),
    )

    class CommitFailJob:
        result_json: dict[str, object] = {}

    class CommitFailSession:
        def __enter__(self):
            return self

        def __exit__(self, *_exc_info: object) -> None:
            return None

        def get(self, *_args: object) -> CommitFailJob:
            return CommitFailJob()

        def commit(self) -> None:
            raise RuntimeError("commit boom")

        def rollback(self) -> None:
            self.rolled_back = True

    posta_online_sync._write_resume_checkpoint(
        session_factory=lambda: CommitFailSession(),
        job_id=123,
        scrape_payload={"archive_ids": []},
        stage="scraping",
        started_at=datetime.now(timezone.utc),
    )

    class UnlinkFailPath:
        def unlink(self) -> None:
            raise OSError("unlink boom")

    monkeypatch.setattr(posta_online_sync, "_resume_checkpoint_path", lambda _job_id: UnlinkFailPath())
    posta_online_sync._delete_resume_checkpoint(123)


def test_posta_online_credential_test_runner_logs_in_without_scraping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "posta-online-credential-test.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    PostaOnlineCredential.__table__.create(bind=engine)
    PostaOnlineRegisteredMailSyncJob.__table__.create(bind=engine)

    generated_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr("app.services.catasto_credentials.settings.credential_master_key", generated_key)
    monkeypatch.setattr("app.core.config.settings.credential_master_key", generated_key)
    get_credential_fernet.cache_clear()
    encrypted_password = get_credential_fernet().encrypt(b"secret").decode("utf-8")

    with SessionLocal() as db:
        credential = PostaOnlineCredential(
            label="Poste",
            username="poste-user",
            password_encrypted=encrypted_password,
            min_delay_ms=1234,
            max_delay_ms=2345,
        )
        db.add(credential)
        db.flush()
        job = PostaOnlineRegisteredMailSyncJob(
            credential_id=credential.id,
            requested_by_user_id=None,
            status="processing",
            mode="credential_test",
            payload_json={"credential_id": credential.id, "min_delay_ms": 2000, "max_delay_ms": 3000},
        )
        db.add(job)
        db.commit()
        job_id = job.id

    calls: list[dict[str, object]] = []

    class FakeClient:
        def __init__(self, config) -> None:
            self.config = config

        async def __aenter__(self):
            calls.append({"event": "enter", "min_delay_ms": self.config.min_delay_ms, "max_delay_ms": self.config.max_delay_ms})
            return self

        async def __aexit__(self, *_exc_info: object) -> None:
            calls.append({"event": "exit"})

        async def login(self, username: str, password: str) -> None:
            calls.append({"event": "login", "username": username, "password": password})

        async def scrape_registered_mails(self, **_kwargs):
            raise AssertionError("Il test credenziale non deve eseguire lo scraping")

    asyncio.run(
        posta_online_sync.run_posta_online_credential_test_job_by_id(
            job_id=job_id,
            session_factory=SessionLocal,
            headless=True,
            _client_class=FakeClient,
        )
    )

    assert calls == [
        {"event": "enter", "min_delay_ms": 2000, "max_delay_ms": 3000},
        {"event": "login", "username": "poste-user", "password": "secret"},
        {"event": "exit"},
    ]
    with SessionLocal() as db:
        refreshed = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        credential = db.get(PostaOnlineCredential, 1)
        assert refreshed is not None
        assert refreshed.status == "succeeded"
        assert refreshed.result_json["ok"] is True
        assert credential is not None
        assert credential.last_used_at is not None


def test_posta_online_sync_dispatcher_handles_modes_and_missing_jobs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "posta-online-dispatcher.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    PostaOnlineRegisteredMailSyncJob.__table__.create(bind=engine)

    asyncio.run(
        posta_online_sync.run_posta_online_job_by_id(
            job_id=999,
            session_factory=SessionLocal,
            headless=True,
        )
    )

    with SessionLocal() as db:
        credential_test = PostaOnlineRegisteredMailSyncJob(status="processing", mode="credential_test", payload_json={})
        registered = PostaOnlineRegisteredMailSyncJob(status="processing", mode="registered_mails", payload_json={})
        db.add_all([credential_test, registered])
        db.commit()
        credential_test_id = credential_test.id
        registered_id = registered.id

    calls: list[tuple[str, int, bool]] = []

    async def fake_credential_test_runner(**kwargs):
        calls.append(("credential_test", kwargs["job_id"], kwargs["headless"]))

    async def fake_registered_runner(**kwargs):
        calls.append(("registered_mails", kwargs["job_id"], kwargs["headless"]))

    monkeypatch.setattr(posta_online_sync, "run_posta_online_credential_test_job_by_id", fake_credential_test_runner)
    monkeypatch.setattr(posta_online_sync, "run_posta_online_registered_mail_job_by_id", fake_registered_runner)

    asyncio.run(
        posta_online_sync.run_posta_online_job_by_id(
            job_id=credential_test_id,
            session_factory=SessionLocal,
            headless=False,
        )
    )
    asyncio.run(
        posta_online_sync.run_posta_online_job_by_id(
            job_id=registered_id,
            session_factory=SessionLocal,
            headless=True,
        )
    )

    assert calls == [
        ("credential_test", credential_test_id, False),
        ("registered_mails", registered_id, True),
    ]


def test_posta_online_credential_test_runner_failure_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "posta-online-credential-test-failures.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    PostaOnlineCredential.__table__.create(bind=engine)
    PostaOnlineRegisteredMailSyncJob.__table__.create(bind=engine)

    asyncio.run(
        posta_online_sync.run_posta_online_credential_test_job_by_id(
            job_id=999,
            session_factory=SessionLocal,
            headless=True,
        )
    )

    with SessionLocal() as db:
        missing_credential_job = PostaOnlineRegisteredMailSyncJob(
            credential_id=999,
            status="processing",
            mode="credential_test",
            payload_json={"credential_id": 999},
        )
        db.add(missing_credential_job)
        db.commit()
        missing_credential_job_id = missing_credential_job.id

    asyncio.run(
        posta_online_sync.run_posta_online_credential_test_job_by_id(
            job_id=missing_credential_job_id,
            session_factory=SessionLocal,
            headless=True,
        )
    )
    with SessionLocal() as db:
        refreshed = db.get(PostaOnlineRegisteredMailSyncJob, missing_credential_job_id)
        assert refreshed is not None
        assert refreshed.status == "failed"
        assert refreshed.result_json["ok"] is False
        assert refreshed.error_detail == "Credenziale Poste Online non trovata"

    generated_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr("app.services.catasto_credentials.settings.credential_master_key", generated_key)
    monkeypatch.setattr("app.core.config.settings.credential_master_key", generated_key)
    monkeypatch.setattr(posta_online_sync, "POSTA_ONLINE_RESUME_STORAGE_PATH", tmp_path / "resume")
    get_credential_fernet.cache_clear()
    encrypted_password = get_credential_fernet().encrypt(b"secret").decode("utf-8")

    with SessionLocal() as db:
        credential = PostaOnlineCredential(
            label="Poste",
            username="poste-user",
            password_encrypted=encrypted_password,
        )
        db.add(credential)
        db.flush()
        job = PostaOnlineRegisteredMailSyncJob(
            credential_id=credential.id,
            status="processing",
            mode="credential_test",
            payload_json={"credential_id": credential.id},
        )
        db.add(job)
        db.commit()
        job_id = job.id
        credential_id = credential.id

    class FailingClient:
        def __init__(self, _config) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc_info: object) -> None:
            return None

        async def login(self, _username: str, _password: str) -> None:
            raise RuntimeError("login boom")

    asyncio.run(
        posta_online_sync.run_posta_online_credential_test_job_by_id(
            job_id=job_id,
            session_factory=SessionLocal,
            headless=True,
            _client_class=FailingClient,
        )
    )

    with SessionLocal() as db:
        refreshed = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        credential = db.get(PostaOnlineCredential, credential_id)
        assert refreshed is not None
        assert refreshed.status == "failed"
        assert refreshed.result_json["error"] == "login boom"
        assert credential is not None
        assert credential.last_error == "login boom"


def test_posta_online_registered_runner_missing_failure_and_persist_helpers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "posta-online-registered-failures.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    PostaOnlineCredential.__table__.create(bind=engine)
    PostaOnlineRegisteredMailSyncJob.__table__.create(bind=engine)

    asyncio.run(
        posta_online_sync.run_posta_online_registered_mail_job_by_id(
            job_id=999,
            session_factory=SessionLocal,
            headless=True,
        )
    )

    generated_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr("app.services.catasto_credentials.settings.credential_master_key", generated_key)
    monkeypatch.setattr("app.core.config.settings.credential_master_key", generated_key)
    monkeypatch.setattr(posta_online_sync, "POSTA_ONLINE_RESUME_STORAGE_PATH", tmp_path / "resume")
    get_credential_fernet.cache_clear()
    encrypted_password = get_credential_fernet().encrypt(b"secret").decode("utf-8")

    with SessionLocal() as db:
        credential = PostaOnlineCredential(
            label="Poste",
            username="poste-user",
            password_encrypted=encrypted_password,
        )
        db.add(credential)
        db.flush()
        failing_job = PostaOnlineRegisteredMailSyncJob(
            credential_id=credential.id,
            status="processing",
            mode="registered_mails",
            payload_json={"credential_id": credential.id, "annualita": [2022, 2023]},
        )
        completed_with_errors_job = PostaOnlineRegisteredMailSyncJob(
            credential_id=credential.id,
            status="processing",
            mode="registered_mails",
            payload_json={"credential_id": credential.id, "annualita": [2022, 2023]},
        )
        persist_failing_job = PostaOnlineRegisteredMailSyncJob(
            credential_id=credential.id,
            status="processing",
            mode="registered_mails",
            payload_json={"credential_id": credential.id, "annualita": [2022, 2023]},
        )
        db.add_all([failing_job, completed_with_errors_job, persist_failing_job])
        db.commit()
        failing_job_id = failing_job.id
        completed_with_errors_job_id = completed_with_errors_job.id
        persist_failing_job_id = persist_failing_job.id
        credential_id = credential.id

    class FailingClient:
        def __init__(self, _config) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc_info: object) -> None:
            return None

        async def login(self, _username: str, _password: str) -> None:
            raise RuntimeError("scrape login boom")

    asyncio.run(
        posta_online_sync.run_posta_online_registered_mail_job_by_id(
            job_id=failing_job_id,
            session_factory=SessionLocal,
            headless=True,
            _client_class=FailingClient,
        )
    )
    with SessionLocal() as db:
        refreshed = db.get(PostaOnlineRegisteredMailSyncJob, failing_job_id)
        credential = db.get(PostaOnlineCredential, credential_id)
        assert refreshed is not None
        assert refreshed.status == "failed"
        assert refreshed.result_json["error"] == "scrape login boom"
        assert credential is not None
        assert credential.last_error == "scrape login boom"

    class SuccessfulClient:
        def __init__(self, _config) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc_info: object) -> None:
            return None

        async def login(self, _username: str, _password: str) -> None:
            return None

        async def scrape_registered_mails(self, **_kwargs) -> dict[str, object]:
            return {"details": [], "contacts": [], "archive_ids": []}

    original_persist_scrape_payload = posta_online_sync._persist_scrape_payload
    monkeypatch.setattr(posta_online_sync, "_persist_scrape_payload", lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("persist boom")))
    asyncio.run(
        posta_online_sync.run_posta_online_registered_mail_job_by_id(
            job_id=persist_failing_job_id,
            session_factory=SessionLocal,
            headless=True,
            _client_class=SuccessfulClient,
        )
    )
    with SessionLocal() as db:
        refreshed = db.get(PostaOnlineRegisteredMailSyncJob, persist_failing_job_id)
        credential = db.get(PostaOnlineCredential, credential_id)
        assert refreshed is not None
        assert refreshed.status == "failed"
        assert refreshed.result_json["error"] == "persist boom"
        assert refreshed.result_json["resume_state"]["stage"] == "scraped"
        assert Path(refreshed.result_json["resume_state"]["path"]).exists()
        assert credential is not None
        assert credential.last_error == "scrape login boom"
    monkeypatch.setattr(posta_online_sync, "_persist_scrape_payload", original_persist_scrape_payload)

    class FakeImportJob:
        id = uuid.uuid4()
        records_total = 2
        records_imported = 1
        records_matched = 0
        records_ambiguous = 1
        records_unmatched = 0
        records_errors = 1

    original_import_wrapper = posta_online_sync._import_tributi_registered_mails
    monkeypatch.setattr(posta_online_sync, "_import_tributi_registered_mails", lambda _db, **_kwargs: FakeImportJob())
    result = posta_online_sync._persist_scrape_payload(
        session_factory=SessionLocal,
        job_id=completed_with_errors_job_id,
        credential_id=credential_id,
        requested_payload={"annualita": [2022, 2023]},
        scrape_payload={"errors": [{"scope": "detail", "error": "boom"}], "archive_ids": ["1"]},
        started_at=datetime.now(timezone.utc),
    )
    assert result["records_errors"] == 1
    with SessionLocal() as db:
        refreshed = db.get(PostaOnlineRegisteredMailSyncJob, completed_with_errors_job_id)
        assert refreshed is not None
        assert refreshed.status == "completed_with_errors"
        assert refreshed.error_detail == "Job completato con errori o anomalie"

    with pytest.raises(RuntimeError, match="non trovato durante persistenza"):
        posta_online_sync._persist_scrape_payload(
            session_factory=SessionLocal,
            job_id=999,
            credential_id=credential_id,
            requested_payload={},
            scrape_payload={},
            started_at=datetime.now(timezone.utc),
        )

    debug_path = tmp_path / "debug" / "payload.json"
    posta_online_sync.write_debug_payload(debug_path, {"ok": True})
    assert json.loads(debug_path.read_text(encoding="utf-8")) == {"ok": True}

    from app.modules.ruolo import tributi_repositories

    monkeypatch.setattr(tributi_repositories, "import_posta_online_registered_mails", lambda _db, **kwargs: kwargs)
    assert original_import_wrapper(None, filename="x")["filename"] == "x"


def test_next_request_id_claims_pending_request_and_marks_processing(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(SessionLocal, request_statuses=[CatastoVisuraRequestStatus.PENDING.value])

    selection = worker._request_repository().claim_next(batch_id)

    assert (selection.request_id, selection.wait_reason) == (request_ids[0], None)
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == CatastoVisuraRequestStatus.PROCESSING.value
        assert request.current_operation == "Presa in carico dal worker"
        assert request.attempts == 1
        assert selection.execution_token == request.execution_token is not None


def test_next_request_id_stops_after_maximum_attempts(worker_db, monkeypatch: pytest.MonkeyPatch) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(SessionLocal, request_statuses=[CatastoVisuraRequestStatus.PENDING.value])
    monkeypatch.setattr(worker_module, "MAX_REQUEST_ATTEMPTS", 3)
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.attempts = 3
        db.commit()

    selection = worker._request_repository().claim_next(batch_id)

    assert selection.request_id is None
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == CatastoVisuraRequestStatus.FAILED.value
        assert request.last_error_code == "retry_exhausted"


def test_next_request_id_uses_persisted_retry_deadline(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(SessionLocal, request_statuses=[CatastoVisuraRequestStatus.PENDING.value])
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.retry_not_before = datetime.now(timezone.utc) + timedelta(seconds=90)
        db.commit()

    selection = worker._request_repository().claim_next(batch_id)

    assert selection.request_id is None
    assert selection.wait_reason == "RETRY_LATER"
    assert selection.wait_seconds is not None
    assert 1 <= selection.wait_seconds <= 90


def test_next_request_id_skips_claimed_request_and_uses_next_pending(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.PENDING.value,
            CatastoVisuraRequestStatus.PENDING.value,
        ],
    )

    selection = worker._request_repository().claim_next(batch_id, claimed_request_ids={request_ids[0]})

    assert selection.request_id == request_ids[1]
    with SessionLocal() as db:
        first = db.get(CatastoVisuraRequest, request_ids[0])
        second = db.get(CatastoVisuraRequest, request_ids[1])
        assert first is not None and second is not None
        assert first.status == CatastoVisuraRequestStatus.PENDING.value
        assert second.status == CatastoVisuraRequestStatus.PROCESSING.value


def test_next_request_id_resumes_remote_request_only_with_its_sister_credential(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PENDING.value],
    )
    pinned_credential_id = uuid.uuid4()
    other_credential_id = uuid.uuid4()
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.sister_credential_id = pinned_credential_id
        request.sister_remote_state = "submitted"
        db.commit()

    wrong_credential = worker._request_repository().claim_next(
        batch_id,
        credential_id=other_credential_id,
    )
    matching_credential = worker._request_repository().claim_next(
        batch_id,
        credential_id=pinned_credential_id,
    )

    assert wrong_credential.request_id is None
    assert matching_credential.request_id == request_ids[0]


def test_next_request_id_returns_retry_later_for_deferred_requests(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(SessionLocal, request_statuses=[CatastoVisuraRequestStatus.PENDING.value])
    deferred_until = datetime.now(timezone.utc) + timedelta(seconds=120)

    selection = worker._request_repository().claim_next(batch_id, deferred_requests={request_ids[0]: deferred_until})

    assert selection.request_id is None
    assert selection.wait_reason == "RETRY_LATER"
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == CatastoVisuraRequestStatus.PENDING.value


def test_next_request_id_returns_wait_for_unresolved_captcha(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(SessionLocal, request_statuses=[CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value])
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.captcha_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        db.commit()

    selection = worker._request_repository().claim_next(batch_id)

    assert selection.request_id is None
    assert selection.wait_reason == "WAIT"


def test_next_request_id_reclaims_captcha_request_when_solution_present(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(SessionLocal, request_statuses=[CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value])
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.captcha_manual_solution = "ABCDE"
        db.commit()

    selection = worker._request_repository().claim_next(batch_id)

    assert selection.request_id == request_ids[0]
    assert selection.wait_reason is None


def test_manual_captcha_wait_is_fenced_and_exposes_current_decision(worker_db) -> None:
    worker, SessionLocal, tmp_path = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    request_id = request_ids[0]
    token = uuid.uuid4()
    deadline = datetime.now(timezone.utc) + timedelta(minutes=5)
    image_path = tmp_path / "captcha.png"
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_id)
        assert request is not None
        request.execution_token = token
        db.commit()

    repository = worker._captcha_wait_repository()
    assert repository.begin(batch_id, request_id, token, image_path, deadline) is True
    waiting = repository.state(batch_id, request_id, token)
    assert waiting.active is True
    assert waiting.solution is None
    assert waiting.skip_requested is False

    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_id)
        assert request is not None
        request.captcha_manual_solution = "ABCDE"
        db.commit()

    solved = repository.state(batch_id, request_id, token)
    assert solved.active is True
    assert solved.solution == "ABCDE"


def test_manual_captcha_wait_cannot_resurrect_cancelled_claim(worker_db) -> None:
    worker, SessionLocal, tmp_path = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.SKIPPED.value],
    )
    request_id = request_ids[0]
    stale_token = uuid.uuid4()
    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        batch.status = CatastoBatchStatus.CANCELLED.value
        db.commit()

    decision = asyncio.run(
        worker._wait_for_manual_captcha(
            SisterCaptchaClaim(batch_id, request_id, stale_token),
            tmp_path / "stale.png",
        )
    )

    assert decision.skip is True
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_id)
        assert request is not None
        assert request.status == CatastoVisuraRequestStatus.SKIPPED.value
        assert request.captcha_image_path is None


def test_manual_captcha_wait_stops_after_claim_is_cancelled(worker_db) -> None:
    worker, SessionLocal, tmp_path = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    request_id = request_ids[0]
    token = uuid.uuid4()
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_id)
        assert request is not None
        request.execution_token = token
        db.commit()

    repository = worker._captcha_wait_repository()
    original_state = repository.state
    state_reads = 0

    def cancel_before_state_read(current_batch_id, current_request_id, current_token):
        nonlocal state_reads
        state_reads += 1
        with SessionLocal() as db:
            batch = db.get(CatastoBatch, batch_id)
            request = db.get(CatastoVisuraRequest, request_id)
            assert batch is not None and request is not None
            batch.status = CatastoBatchStatus.CANCELLED.value
            request.status = CatastoVisuraRequestStatus.SKIPPED.value
            request.execution_token = None
            db.commit()
        return original_state(current_batch_id, current_request_id, current_token)

    wait_repository = types.SimpleNamespace(begin=repository.begin, state=cancel_before_state_read)
    worker._captcha_wait_repository = lambda: wait_repository
    decision = asyncio.run(
        worker._wait_for_manual_captcha(
            SisterCaptchaClaim(batch_id, request_id, token),
            tmp_path / "captcha.png",
        )
    )

    assert decision.skip is True
    assert state_reads == 1


def test_batch_has_open_requests_reflects_terminal_state(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.COMPLETED.value,
            CatastoVisuraRequestStatus.NOT_FOUND.value,
        ],
    )

    assert worker._batch_has_open_requests(batch_id) is False

    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.status = CatastoVisuraRequestStatus.PROCESSING.value
        db.commit()

    assert worker._batch_has_open_requests(batch_id) is True


def test_finalize_batch_keeps_processing_when_pending_requests_remain(worker_db) -> None:
    worker, SessionLocal, tmp_path = worker_db
    _, batch_id, _ = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.COMPLETED.value,
            CatastoVisuraRequestStatus.PENDING.value,
        ],
    )

    worker._finalize_batch(batch_id)

    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        assert batch.status == CatastoBatchStatus.PROCESSING.value
        assert batch.report_json_path is not None
        assert batch.report_md_path is not None
        assert Path(batch.report_json_path).exists()
        assert Path(batch.report_md_path).exists()


def test_finalize_batch_marks_completed_for_not_found_and_skipped(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, _ = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.COMPLETED.value,
            CatastoVisuraRequestStatus.NOT_FOUND.value,
            CatastoVisuraRequestStatus.SKIPPED.value,
        ],
    )

    worker._finalize_batch(batch_id)

    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        assert batch.status == CatastoBatchStatus.COMPLETED.value
        assert batch.completed_items == 1
        assert batch.not_found_items == 1
        assert batch.skipped_items == 1


def test_finalize_batch_does_not_overwrite_cancellation(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, _ = _seed_batch(SessionLocal, request_statuses=[CatastoVisuraRequestStatus.SKIPPED.value])
    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        batch.status = CatastoBatchStatus.CANCELLED.value
        batch.current_operation = "Cancelled by user"
        db.commit()

    worker._finalize_batch(batch_id)

    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        assert batch.status == CatastoBatchStatus.CANCELLED.value
        assert batch.current_operation == "Cancelled by user"


def test_persist_flow_result_discards_stale_cancelled_claim(worker_db) -> None:
    worker, SessionLocal, tmp_path = worker_db
    _, batch_id, request_ids = _seed_batch(SessionLocal, request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value])
    stale_token = uuid.uuid4()
    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert batch is not None and request is not None
        batch.status = CatastoBatchStatus.CANCELLED.value
        request.status = CatastoVisuraRequestStatus.SKIPPED.value
        request.execution_token = None
        db.commit()

    pdf_path = tmp_path / "stale.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    result = _VisuraFlowResult()
    result.file_path = pdf_path
    result.file_size = pdf_path.stat().st_size

    worker._request_repository().persist_flow_result(
        batch_id,
        request_ids[0],
        "USER",
        result,
        stale_token,
    )
    worker._request_repository().persist_flow_result(
        batch_id,
        request_ids[0],
        "USER",
        _VisuraFlowResult(),
        stale_token,
    )

    assert not pdf_path.exists()
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == CatastoVisuraRequestStatus.SKIPPED.value
        assert request.document_id is None


def test_stale_claim_cannot_reset_or_fail_new_execution(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.PROCESSING.value,
            CatastoVisuraRequestStatus.PROCESSING.value,
        ],
    )
    stale_token = uuid.uuid4()
    current_tokens = [uuid.uuid4(), uuid.uuid4()]
    with SessionLocal() as db:
        for request_id, current_token in zip(request_ids, current_tokens, strict=True):
            request = db.get(CatastoVisuraRequest, request_id)
            assert request is not None
            request.execution_token = current_token
        db.commit()

    worker._request_repository().reset_for_retry(
        request_ids[0],
        "retry obsoleto",
        datetime.now(timezone.utc) + timedelta(seconds=30),
        "stale_retry",
        stale_token,
    )
    worker._request_repository().fail_request(batch_id, request_ids[1], "errore obsoleto", stale_token)

    with SessionLocal() as db:
        first = db.get(CatastoVisuraRequest, request_ids[0])
        second = db.get(CatastoVisuraRequest, request_ids[1])
        assert first is not None and second is not None
        assert first.status == CatastoVisuraRequestStatus.PROCESSING.value
        assert first.execution_token == current_tokens[0]
        assert first.retry_not_before is None
        assert second.status == CatastoVisuraRequestStatus.PROCESSING.value
        assert second.execution_token == current_tokens[1]
        assert second.error_message is None


def test_new_correlation_baseline_clears_deleted_remote_identity(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, _, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.PROCESSING.value,
            CatastoVisuraRequestStatus.PROCESSING.value,
        ],
    )
    execution_tokens = [uuid.uuid4(), uuid.uuid4()]
    with SessionLocal() as db:
        deleted = db.get(CatastoVisuraRequest, request_ids[0])
        active = db.get(CatastoVisuraRequest, request_ids[1])
        assert deleted is not None and active is not None
        deleted.execution_token = execution_tokens[0]
        deleted.sister_remote_request_id = "OLD-1"
        deleted.sister_remote_request_url = "https://sister/old"
        deleted.sister_remote_state = "deleted"
        deleted.sister_credential_id = uuid.uuid4()
        active.execution_token = execution_tokens[1]
        active.sister_remote_request_id = "ACTIVE-2"
        active.sister_remote_request_url = "https://sister/active"
        active.sister_remote_state = "pending"
        active.sister_credential_id = uuid.uuid4()
        active_credential_id = active.sister_credential_id
        db.commit()

    worker._request_repository().set_correlation_baseline(request_ids[0], execution_tokens[0], ["BASE-NEW"])
    worker._request_repository().set_correlation_baseline(request_ids[1], execution_tokens[1], ["BASE-ACTIVE"])

    with SessionLocal() as db:
        deleted = db.get(CatastoVisuraRequest, request_ids[0])
        active = db.get(CatastoVisuraRequest, request_ids[1])
        assert deleted is not None and active is not None
        assert deleted.sister_remote_request_id is None
        assert deleted.sister_remote_request_url is None
        assert deleted.sister_remote_state is None
        assert deleted.sister_credential_id is None
        assert deleted.sister_remote_baseline_keys == ["BASE-NEW"]
        assert active.sister_remote_request_id == "ACTIVE-2"
        assert active.sister_remote_request_url == "https://sister/active"
        assert active.sister_remote_state == "pending"
        assert active.sister_credential_id == active_credential_id
        assert active.sister_remote_baseline_keys == ["BASE-ACTIVE"]


def test_document_paths_are_unique_per_request_and_execution(worker_db, monkeypatch: pytest.MonkeyPatch) -> None:
    worker, SessionLocal, tmp_path = worker_db
    monkeypatch.setattr(worker_module, "DOCUMENT_STORAGE_PATH", tmp_path / "documents")
    _, _, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value, CatastoVisuraRequestStatus.PROCESSING.value],
    )
    with SessionLocal() as db:
        first = db.get(CatastoVisuraRequest, request_ids[0])
        second = db.get(CatastoVisuraRequest, request_ids[1])
        assert first is not None and second is not None
        first.execution_token = uuid.uuid4()
        second.execution_token = uuid.uuid4()
        first_path = worker._request_repository().build_document_path("USER", first)
        second_path = worker._request_repository().build_document_path("USER", second)

    assert first_path != second_path
    assert str(request_ids[0]) in str(first_path)
    assert str(request_ids[1]) in str(second_path)


def test_retry_coordinator_persists_deadline_and_fencing_token() -> None:
    from sister_worker_reliability import (
        ClaimedRequestSelection,
        SisterRequestClaimCoordinator,
        SisterRequestRetryCoordinator,
        recoverable_retry_metadata,
    )

    calls: list[tuple[object, ...]] = []
    deferred: dict[uuid.UUID, datetime] = {}
    request_id = uuid.uuid4()
    execution_token = uuid.uuid4()
    coordinator = SisterRequestRetryCoordinator(
        asyncio.Lock(),
        deferred,
        lambda *args: calls.append(args),
        30,
    )

    asyncio.run(coordinator.defer(request_id, execution_token, 30, "retry", "temporary"))

    assert request_id in deferred
    assert deferred[request_id] > datetime.now(timezone.utc)
    assert calls[0][0:2] == (request_id, "retry")
    assert calls[0][3:] == ("temporary", execution_token)
    asyncio.run(
        coordinator.defer_recoverable(
            request_id,
            execution_token,
            SisterRequestCorrelationError("ambigua"),
            "USER",
        )
    )
    assert calls[-1][1] == "Correlazione SISTER non sicura, retry differito"
    assert calls[-1][3] == "sister_correlation_error"
    assert ClaimedRequestSelection(None).resolved_wait_seconds(7) == 7
    assert ClaimedRequestSelection(None, wait_seconds=3).resolved_wait_seconds(7) == 3

    class _Repository:
        selections = [ClaimedRequestSelection(request_id), ClaimedRequestSelection(None)]

        def claim_next(self, *_args):
            return self.selections.pop(0)

    coordinator = SisterRequestClaimCoordinator(asyncio.Lock(), asyncio.Lock(), deferred, set())
    claimed = asyncio.run(coordinator.claim_next(_Repository(), uuid.uuid4(), uuid.uuid4()))
    empty = asyncio.run(coordinator.claim_next(_Repository(), uuid.uuid4(), uuid.uuid4()))
    asyncio.run(coordinator.release(None))
    asyncio.run(coordinator.release(request_id))

    assert claimed.request_id == request_id
    assert empty.request_id is None
    assert request_id not in coordinator.claimed_request_ids
    assert request_id not in deferred
    assert recoverable_retry_metadata(
        SisterRequestCorrelationError("ambigua"), "USER"
    ) == ("Correlazione SISTER non sicura, retry differito", "sister_correlation_error")
    assert recoverable_retry_metadata(RuntimeError("timeout"), "USER") == (
        "Sessione/timeout su USER, retry differito",
        "session_recovery",
    )


def test_request_repository_fails_active_batch_and_preserves_terminal_items(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.PENDING.value,
            CatastoVisuraRequestStatus.COMPLETED.value,
            CatastoVisuraRequestStatus.PROCESSING.value,
        ],
    )
    ade_calls: list[dict[str, object]] = []
    monkeypatch.setattr(worker_module, "persist_ade_status_scan_result", lambda _db, **kwargs: ade_calls.append(kwargs))
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.purpose = worker_module.ADE_SCAN_PURPOSE
        request.target_ruolo_particella_id = uuid.uuid4()
        request.execution_token = uuid.uuid4()
        request.retry_not_before = datetime.now(timezone.utc)
        db.commit()

    worker._request_repository().fail_batch(batch_id, "SISTER_SESSION_LOCKED")

    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        failed = db.get(CatastoVisuraRequest, request_ids[0])
        completed = db.get(CatastoVisuraRequest, request_ids[1])
        assert batch is not None and failed is not None and completed is not None
        assert batch.status == CatastoBatchStatus.FAILED.value
        assert failed.status == CatastoVisuraRequestStatus.FAILED.value
        assert failed.execution_token is None and failed.retry_not_before is None
        assert completed.status == CatastoVisuraRequestStatus.COMPLETED.value
    assert ade_calls[0]["classification"] == "blocked"

    worker._request_repository().fail_batch(uuid.uuid4(), "ignored")
    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        batch.status = CatastoBatchStatus.CANCELLED.value
        db.commit()
    worker._request_repository().fail_batch(batch_id, "ignored")


def test_request_repository_fails_remote_requests_without_their_pinned_credential(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.PENDING.value,
            CatastoVisuraRequestStatus.PENDING.value,
            CatastoVisuraRequestStatus.PENDING.value,
        ],
    )
    available_credential_id = uuid.uuid4()
    with SessionLocal() as db:
        orphaned = db.get(CatastoVisuraRequest, request_ids[0])
        available = db.get(CatastoVisuraRequest, request_ids[1])
        assert orphaned is not None and available is not None
        orphaned.sister_remote_state = "submitted"
        orphaned.sister_credential_id = uuid.uuid4()
        available.sister_remote_state = "pending"
        available.sister_credential_id = available_credential_id
        db.commit()

    repository = worker._request_repository()
    assert repository.fail_unavailable_pinned_requests(uuid.uuid4(), {available_credential_id}) == 0
    assert repository.fail_unavailable_pinned_requests(batch_id, {available_credential_id}) == 1
    assert repository.fail_unavailable_pinned_requests(batch_id, {available_credential_id}) == 0

    with SessionLocal() as db:
        orphaned = db.get(CatastoVisuraRequest, request_ids[0])
        available = db.get(CatastoVisuraRequest, request_ids[1])
        unsubmitted = db.get(CatastoVisuraRequest, request_ids[2])
        batch = db.get(CatastoBatch, batch_id)
        assert orphaned is not None and available is not None and unsubmitted is not None and batch is not None
        assert orphaned.status == CatastoVisuraRequestStatus.FAILED.value
        assert orphaned.sister_remote_state == "orphaned"
        assert orphaned.last_error_code == "sister_credential_unavailable"
        assert available.status == CatastoVisuraRequestStatus.PENDING.value
        assert unsubmitted.status == CatastoVisuraRequestStatus.PENDING.value
        batch.status = CatastoBatchStatus.CANCELLED.value
        db.commit()

    assert repository.fail_unavailable_pinned_requests(batch_id, {available_credential_id}) == 0


def test_request_repository_fails_only_current_execution(worker_db, monkeypatch: pytest.MonkeyPatch) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    token = uuid.uuid4()
    ade_calls: list[dict[str, object]] = []
    monkeypatch.setattr(worker_module, "persist_ade_status_scan_result", lambda _db, **kwargs: ade_calls.append(kwargs))
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.execution_token = token
        request.purpose = worker_module.ADE_SCAN_PURPOSE
        request.target_ruolo_particella_id = uuid.uuid4()
        db.commit()

    repository = worker._request_repository()
    repository.fail_request(batch_id, request_ids[0], "stale", uuid.uuid4())
    repository.fail_request(batch_id, request_ids[0], "fatal", token)

    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == CatastoVisuraRequestStatus.FAILED.value
        assert request.error_message == "fatal"
        assert request.execution_token is None
    assert ade_calls[-1]["classification"] == "blocked"


def test_request_repository_reset_for_retry_handles_release_and_guards(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.PROCESSING.value,
            CatastoVisuraRequestStatus.PROCESSING.value,
            CatastoVisuraRequestStatus.COMPLETED.value,
        ],
    )
    tokens = [uuid.uuid4(), uuid.uuid4()]
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=20)
    with SessionLocal() as db:
        first = db.get(CatastoVisuraRequest, request_ids[0])
        released = db.get(CatastoVisuraRequest, request_ids[1])
        assert first is not None and released is not None
        first.execution_token = tokens[0]
        released.execution_token = tokens[1]
        released.error_message = worker_module.RELEASE_REQUESTED_MESSAGE
        db.commit()

    repository = worker._request_repository()
    repository.reset_for_retry(request_ids[0], "stale", retry_at, "stale", uuid.uuid4())
    repository.reset_for_retry(request_ids[2], "terminal")
    repository.reset_for_retry(request_ids[1], "ignored", execution_token=tokens[1])
    repository.reset_for_retry(request_ids[0], "retry", retry_at, "temporary", tokens[0])
    repository.reset_for_retry(uuid.uuid4(), "missing")

    with SessionLocal() as db:
        first = db.get(CatastoVisuraRequest, request_ids[0])
        released = db.get(CatastoVisuraRequest, request_ids[1])
        assert first is not None and released is not None
        assert first.status == CatastoVisuraRequestStatus.PENDING.value
        assert first.retry_not_before == retry_at.replace(tzinfo=None)
        assert first.last_error_code == "temporary"
        assert released.status == CatastoVisuraRequestStatus.SKIPPED.value
        assert released.current_operation == worker_module.RELEASE_REQUESTED_OPERATION

    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        first = db.get(CatastoVisuraRequest, request_ids[0])
        assert batch is not None and first is not None
        batch.status = CatastoBatchStatus.CANCELLED.value
        first.status = CatastoVisuraRequestStatus.PROCESSING.value
        db.commit()
    repository.reset_for_retry(request_ids[0], "cancelled")


@pytest.mark.parametrize(
    ("captcha_mode", "expected_status", "expected_operation"),
    [
        ("manual", CatastoVisuraRequestStatus.PROCESSING.value, "Ripresa con CAPTCHA manuale"),
        ("expired", CatastoVisuraRequestStatus.FAILED.value, "Timeout CAPTCHA manuale"),
        ("skip", CatastoVisuraRequestStatus.SKIPPED.value, "Saltata dall'utente"),
    ],
)
def test_prepare_execution_resolves_captcha_states(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    captcha_mode: str,
    expected_status: str,
    expected_operation: str,
) -> None:
    worker, SessionLocal, _ = worker_db
    monkeypatch.setattr(worker_module, "DEBUG_ARTIFACTS_PATH", tmp_path / "debug")
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value],
    )
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.captcha_manual_solution = "1234" if captcha_mode == "manual" else None
        request.captcha_skip_requested = captcha_mode == "skip"
        request.captcha_expires_at = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
            if captcha_mode == "expired"
            else datetime.now(timezone.utc) + timedelta(minutes=5)
        )
        db.commit()

    prepared = worker._request_repository().prepare_execution(batch_id, request_ids[0])

    assert (prepared is not None) == (captcha_mode == "manual")
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == expected_status
        assert request.current_operation == expected_operation


def test_prepare_execution_claims_pending_subject_and_handles_missing(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker, SessionLocal, tmp_path = worker_db
    monkeypatch_root = tmp_path / "debug"
    monkeypatch.setattr(worker_module, "DEBUG_ARTIFACTS_PATH", monkeypatch_root)
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PENDING.value],
    )
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.search_mode = "soggetto"
        request.subject_kind = "PF"
        request.subject_id = "ABC"
        db.commit()

    repository = worker._request_repository()
    assert repository.prepare_execution(uuid.uuid4(), uuid.uuid4()) is None
    prepared = repository.prepare_execution(batch_id, request_ids[0])

    assert prepared is not None
    assert prepared.request.execution_token == prepared.execution_token
    assert prepared.request.artifact_dir is not None
    assert Path(prepared.request.artifact_dir).is_dir()
    with SessionLocal() as db:
        batch = db.get(CatastoBatch, batch_id)
        assert batch is not None
        assert batch.current_operation == "Lavorazione PF ABC"


def test_prepare_execution_keeps_unresolved_captcha_waiting(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker, SessionLocal, tmp_path = worker_db
    monkeypatch.setattr(worker_module, "DEBUG_ARTIFACTS_PATH", tmp_path / "debug")
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value],
    )
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.captcha_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        db.commit()

    prepared = worker._request_repository().prepare_execution(batch_id, request_ids[0])

    assert prepared is None
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value


def test_request_repository_fences_operation_and_remote_updates(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, _, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    token = uuid.uuid4()
    credential_id = uuid.uuid4()
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.execution_token = token
        request.sister_remote_request_id = "OLD"
        request.sister_remote_request_url = "https://old"
        request.sister_remote_state = "deleted"
        db.commit()

    repository = worker._request_repository()
    repository.set_operation(uuid.uuid4(), "missing", token)
    repository.set_operation(request_ids[0], "stale", uuid.uuid4())
    repository.set_operation(request_ids[0], "running", token)
    repository.set_remote_state(
        request_ids[0], None, worker_module.SisterRemoteStateUpdate("NO-TOKEN", None, "pending")
    )
    repository.set_remote_state(
        request_ids[0], uuid.uuid4(), worker_module.SisterRemoteStateUpdate("STALE", None, "pending")
    )
    repository.set_remote_state(
        request_ids[0], token, worker_module.SisterRemoteStateUpdate(None, None, "ready")
    )
    repository.set_remote_state(
        request_ids[0],
        token,
        worker_module.SisterRemoteStateUpdate("NEW", "https://new", "submitted", credential_id),
    )
    repository.set_correlation_baseline(request_ids[0], uuid.uuid4(), ["STALE"])
    repository.set_correlation_baseline(request_ids[0], token, ["BASE"])

    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.current_operation == "running"
        assert request.sister_remote_request_id == "NEW"
        assert request.sister_remote_request_url == "https://new"
        assert request.sister_remote_state == "submitted"
        assert request.sister_credential_id == credential_id
        assert request.sister_remote_baseline_keys == ["BASE"]


def test_request_repository_persists_completed_document_idempotently(worker_db, tmp_path: Path) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    token = uuid.uuid4()
    pdf_path = tmp_path / "first.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\nfirst")
    result = _VisuraFlowResult()
    result.file_path = pdf_path
    result.file_size = pdf_path.stat().st_size
    result.remote_request_id = "REMOTE-1"
    result.remote_request_url = "https://sister/1"
    result.captcha_image_path = tmp_path / "captcha_manual.png"
    result.captcha_method = "manual"
    result.last_ocr_text = "1234"
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.execution_token = token
        db.commit()

    repository = worker._request_repository()
    repository.persist_flow_result(batch_id, request_ids[0], "USER", result, token)

    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        document = db.scalar(select(CatastoDocument).where(CatastoDocument.request_id == request_ids[0]))
        log = db.scalar(select(CatastoCaptchaLog).where(CatastoCaptchaLog.request_id == request_ids[0]))
        assert request is not None and document is not None and log is not None
        document_id = document.id
        assert request.status == CatastoVisuraRequestStatus.COMPLETED.value
        assert document.sha256 is not None and len(document.sha256) == 64
        assert log.manual_text == "1234"
        request.status = CatastoVisuraRequestStatus.PROCESSING.value
        request.execution_token = token
        db.commit()

    second_path = tmp_path / "second.pdf"
    second_path.write_bytes(b"%PDF-1.4\nsecond")
    result.file_path = second_path
    result.file_size = second_path.stat().st_size
    result.captcha_image_path = None
    repository.persist_flow_result(batch_id, request_ids[0], "USER", result, token)

    with SessionLocal() as db:
        documents = list(db.scalars(select(CatastoDocument).where(CatastoDocument.request_id == request_ids[0])))
        assert len(documents) == 1
        assert documents[0].id == document_id
        assert documents[0].filename == "second.pdf"


def test_request_repository_infers_captcha_log_method(worker_db, tmp_path: Path) -> None:
    worker, SessionLocal, _ = worker_db
    _, _, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    repository = worker._request_repository()
    for filename, expected_method in (("captcha_manual.png", "manual"), ("captcha.png", "ocr")):
        result = _VisuraFlowResult()
        result.captcha_image_path = tmp_path / filename
        result.last_ocr_text = "9876"
        with SessionLocal() as db:
            repository._log_captcha_attempt(db, request_ids[0], result)
            db.commit()
            log = db.scalar(
                select(CatastoCaptchaLog)
                .where(
                    CatastoCaptchaLog.request_id == request_ids[0],
                    CatastoCaptchaLog.method == expected_method,
                )
            )
            assert log is not None
            assert log.method == expected_method


@pytest.mark.parametrize(
    ("status", "expected_status", "expected_error_code"),
    [
        ("skipped", CatastoVisuraRequestStatus.SKIPPED.value, None),
        ("not_found", CatastoVisuraRequestStatus.NOT_FOUND.value, None),
        ("failed", CatastoVisuraRequestStatus.FAILED.value, "flow_failed"),
    ],
)
def test_request_repository_persists_terminal_statuses(
    worker_db,
    status: str,
    expected_status: str,
    expected_error_code: str | None,
) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    result = _VisuraFlowResult()
    result.status = status
    result.error_message = "detail" if status != "failed" else None

    worker._request_repository().persist_flow_result(batch_id, request_ids[0], "USER", result)

    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == expected_status
        assert request.last_error_code == expected_error_code


@pytest.mark.parametrize(("attempts", "is_ade"), [(1, True), (3, True), (3, False)])
def test_request_repository_persists_non_evadibile_retry_and_terminal(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
    attempts: int,
    is_ade: bool,
) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    ade_calls: list[dict[str, object]] = []
    monkeypatch.setattr(worker_module, "persist_ade_status_scan_result", lambda _db, **kwargs: ade_calls.append(kwargs))
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.attempts = attempts
        if is_ade:
            request.purpose = worker_module.ADE_SCAN_PURPOSE
            request.target_ruolo_particella_id = uuid.uuid4()
        db.commit()
    result = _VisuraFlowResult()
    result.status = "non_evadibile"
    result.error_message = "not possible"

    worker._request_repository().persist_flow_result(batch_id, request_ids[0], "USER", result)

    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.sister_remote_state == "deleted"
        assert request.last_error_code == "non_evadibile"
        if attempts < 3:
            assert request.status == CatastoVisuraRequestStatus.PENDING.value
            assert request.retry_not_before is not None
            assert not ade_calls
        else:
            assert request.status == CatastoVisuraRequestStatus.FAILED.value
            if is_ade:
                assert ade_calls[0]["classification"] == "non_evadibile"
            else:
                assert not ade_calls


@pytest.mark.parametrize("parse_fails", [False, True])
def test_request_repository_persists_ade_document_payload(
    worker_db,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    parse_fails: bool,
) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    ade_calls: list[dict[str, object]] = []
    monkeypatch.setattr(worker_module, "persist_ade_status_scan_result", lambda _db, **kwargs: ade_calls.append(kwargs))
    monkeypatch.setattr(
        worker_module,
        "parse_historical_visura_pdf",
        (lambda _path: (_ for _ in ()).throw(ValueError("parse boom")))
        if parse_fails
        else (lambda _path: {"classification": "active"}),
    )
    pdf_path = tmp_path / "ade.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\nade")
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.purpose = worker_module.ADE_SCAN_PURPOSE
        request.target_ruolo_particella_id = uuid.uuid4()
        db.commit()
    result = _VisuraFlowResult()
    result.file_path = pdf_path
    result.file_size = pdf_path.stat().st_size

    worker._request_repository().persist_flow_result(batch_id, request_ids[0], "USER", result)

    expected = "parse_failed" if parse_fails else "active"
    assert ade_calls[0]["classification"] == expected
    assert ade_calls[0]["document_id"] is not None


def test_request_repository_persists_ade_payload_without_document(worker_db, monkeypatch: pytest.MonkeyPatch) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.PROCESSING.value,
            CatastoVisuraRequestStatus.PROCESSING.value,
        ],
    )
    ade_calls: list[dict[str, object]] = []
    monkeypatch.setattr(worker_module, "persist_ade_status_scan_result", lambda _db, **kwargs: ade_calls.append(kwargs))
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.purpose = worker_module.ADE_SCAN_PURPOSE
        request.target_ruolo_particella_id = uuid.uuid4()
        no_target = db.get(CatastoVisuraRequest, request_ids[1])
        assert no_target is not None
        no_target.purpose = worker_module.ADE_SCAN_PURPOSE
        db.commit()
    result = _VisuraFlowResult()
    result.status = "not_found"
    result.ade_status_payload = {"classification": "missing"}

    worker._request_repository().persist_flow_result(batch_id, request_ids[0], "USER", result)
    worker._request_repository().persist_flow_result(batch_id, request_ids[1], "USER", result)

    assert ade_calls[0]["classification"] == "missing"
    assert ade_calls[0]["document_id"] is None
    assert len(ade_calls) == 1


def test_document_path_builders_cover_subject_and_immobile_fallbacks(worker_db, tmp_path: Path) -> None:
    from sister_worker_reliability import _future_retry_seconds, build_document_path, is_expired, sha256_file

    _, SessionLocal, _ = worker_db
    _, _, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.subalterno = "7"
        immobile_path = build_document_path(tmp_path, "", request)
        request.search_mode = "soggetto"
        request.subject_kind = None
        request.subject_id = None
        request.request_type = None
        subject_path = build_document_path(tmp_path, "USER", request)

    assert immobile_path.name == "ORISTANO_1_1_7.pdf"
    assert subject_path.name == "SOGGETTO_UNKNOWN_ATTUALITA.pdf"
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"abc")
    assert sha256_file(payload) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert not is_expired(None)
    assert is_expired(datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1))
    assert not is_expired(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=30))
    assert not is_expired(datetime.now(timezone.utc) + timedelta(seconds=30))
    now = datetime.now(timezone.utc)
    assert _future_retry_seconds(now - timedelta(seconds=1), now) is None
