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
        self.remote_request_id = self.remote_request_url = self.document_audit_payload = None


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
    extract_pdf_text=lambda _path: "",
    parse_historical_visura_text=lambda _text: {"classification": "unknown"},
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
