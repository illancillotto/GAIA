from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import sys
import types
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


WORKER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = next((path for path in WORKER_ROOT.parents if (path / "backend").exists()), WORKER_ROOT.parents[-1])
BACKEND_ROOT = REPO_ROOT / "backend"

for path in (WORKER_ROOT, REPO_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ.setdefault("CREDENTIAL_MASTER_KEY", "WnCjZ2L63B1kIh_2mDkk8j5M6Bf0dzxN3Qv8QbQwB0A=")
os.environ.setdefault("DATABASE_URL", "sqlite:///./.pytest-worker.db")


def _stub_module(name: str, **attrs: object) -> None:
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules.setdefault(name, module)


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

_stub_module("pypdf", PdfReader=object)
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
        self.file_path = None
        self.file_size = None
        self.ade_status_payload = None


async def _unsupported_execute_visura_flow(*_args, **_kwargs):
    raise RuntimeError("execute_visura_flow non disponibile nel test stub")


_stub_module(
    "visura_flow",
    ManualCaptchaDecision=_ManualCaptchaDecision,
    VisuraFlowResult=_VisuraFlowResult,
    execute_visura_flow=_unsupported_execute_visura_flow,
)
_stub_module("sister_exceptions", SisterServerError=type("SisterServerError", (RuntimeError,), {}))
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
    run_bulk_search_job_by_id=lambda _job_id: None,
)

import worker as worker_module
from app.core.database import Base
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoBatch, CatastoBatchStatus, CatastoDocument, CatastoVisuraRequest, CatastoVisuraRequestStatus


CatastoWorker = worker_module.CatastoWorker


@pytest.fixture()
def worker_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "worker-tests.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    ApplicationUser.__table__.create(bind=engine)
    CatastoBatch.__table__.create(bind=engine)
    CatastoDocument.__table__.create(bind=engine)
    CatastoVisuraRequest.__table__.create(bind=engine)

    monkeypatch.setattr(worker_module, "SessionLocal", SessionLocal)
    monkeypatch.setattr(
        worker_module.CatastoWorker,
        "_build_batch_report_dir",
        lambda _self, batch: tmp_path / "reports" / str(batch.user_id) / str(batch.id),
    )

    worker = CatastoWorker.__new__(CatastoWorker)
    worker.state = types.SimpleNamespace(stop_requested=False)
    monkeypatch.setattr(worker_module, "write_batch_report", lambda _batch, _requests, target_dir: _fake_reports(target_dir))
    yield worker, SessionLocal, tmp_path


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
    assert CatastoWorker._is_recoverable_credential_error(RuntimeError("SISTER_SESSION_LOCKED"))
    assert CatastoWorker._is_recoverable_credential_error(RuntimeError("Timeout 60000ms exceeded"))
    assert CatastoWorker._is_recoverable_credential_error(
        RuntimeError("Utente SISTER bloccato sul portale Agenzia delle Entrate.")
    )


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
        worker_module.SISTER_SERVER_ERROR_BASE_COOLDOWN_SEC * 3,
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


def test_next_request_id_claims_pending_request_and_marks_processing(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(SessionLocal, request_statuses=[CatastoVisuraRequestStatus.PENDING.value])

    selection = worker._next_request_id(batch_id)

    assert selection.request_id == request_ids[0]
    assert selection.wait_reason is None
    with SessionLocal() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        assert request.status == CatastoVisuraRequestStatus.PROCESSING.value
        assert request.current_operation == "Presa in carico dal worker"
        assert request.attempts == 1


def test_next_request_id_skips_claimed_request_and_uses_next_pending(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        SessionLocal,
        request_statuses=[
            CatastoVisuraRequestStatus.PENDING.value,
            CatastoVisuraRequestStatus.PENDING.value,
        ],
    )

    selection = worker._next_request_id(batch_id, claimed_request_ids={request_ids[0]})

    assert selection.request_id == request_ids[1]
    with SessionLocal() as db:
        first = db.get(CatastoVisuraRequest, request_ids[0])
        second = db.get(CatastoVisuraRequest, request_ids[1])
        assert first is not None and second is not None
        assert first.status == CatastoVisuraRequestStatus.PENDING.value
        assert second.status == CatastoVisuraRequestStatus.PROCESSING.value


def test_next_request_id_returns_retry_later_for_deferred_requests(worker_db) -> None:
    worker, SessionLocal, _ = worker_db
    _, batch_id, request_ids = _seed_batch(SessionLocal, request_statuses=[CatastoVisuraRequestStatus.PENDING.value])
    deferred_until = datetime.now(timezone.utc) + timedelta(seconds=120)

    selection = worker._next_request_id(batch_id, deferred_requests={request_ids[0]: deferred_until})

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

    selection = worker._next_request_id(batch_id)

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

    selection = worker._next_request_id(batch_id)

    assert selection.request_id == request_ids[0]
    assert selection.wait_reason is None


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
