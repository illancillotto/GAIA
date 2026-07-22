from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
import re
import signal
import traceback
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.capacitas import (
    CapacitasAnagraficaHistoryImportJob,
    CapacitasInCassSyncJob,
    CapacitasParticelleSyncJob,
    CapacitasTerreniSyncJob,
)
from app.models.catasto import (
    CatastoBatch,
    CatastoBatchKind,
    CatastoBatchStatus,
    CatastoCaptchaLog,
    CatastoCredential,
    CatastoDistrettoExportJob,
    CatastoElaborazioniMassiveJob,
    CatastoElaborazioniMassiveJobStatus,
    CatastoConnectionTest,
    CatastoConnectionTestStatus,
    CatastoDocument,
    CatastoVisuraRequest,
    CatastoVisuraRequestStatus,
)
from app.models.wc_sync_job import WCSyncJob
from app.modules.utenze.services.import_service import (
    prepare_registry_import_jobs_for_recovery,
    run_registry_bulk_import_job_by_id,
)
from app.services.elaborazioni_capacitas_anagrafica_history import (
    expire_stale_anagrafica_history_jobs,
    prepare_anagrafica_history_jobs_for_recovery,
)
from app.services.elaborazioni_capacitas_particelle_sync import (
    expire_stale_particelle_sync_jobs,
    prepare_particelle_sync_jobs_for_recovery,
)
from app.services.elaborazioni_capacitas_runtime import (
    run_anagrafica_history_job_by_id,
    run_incass_job_by_id,
    run_particelle_job_by_id,
    run_terreni_job_by_id,
)
from app.services.elaborazioni_capacitas_terreni import (
    expire_stale_terreni_sync_jobs,
    prepare_terreni_sync_jobs_for_recovery,
)
from app.services.elaborazioni_capacitas_incass import (
    expire_stale_incass_sync_jobs,
    prepare_incass_sync_jobs_for_recovery,
)
from app.services.elaborazioni_batches import (
    RELEASE_REQUESTED_MESSAGE,
    RELEASE_REQUESTED_OPERATION,
)
from app.modules.catasto.services.ade_status_scan import ADE_SCAN_PURPOSE, persist_ade_status_scan_result
from app.modules.catasto.services.ade_wfs import execute_ade_sync_run, prepare_ade_sync_runs_for_recovery
from app.modules.catasto.services.ade_historical_visura_parser import parse_historical_visura_pdf
from app.modules.catasto.routes.anagrafica import (
    prepare_bulk_search_jobs_for_recovery,
    prepare_distretto_export_jobs_for_recovery,
    run_bulk_search_job_by_id,
    run_distretto_export_job_by_id,
)
from autodoc_sync import AUTODOC_SYNC_ENTITY, run_autodoc_sync_job_by_id
from anti_captcha_client import AntiCaptchaClient
from browser_session import BrowserSession, BrowserSessionConfig
from sister_exceptions import SisterServerError
from llm_captcha_solver import LLMCaptchaSolver
from credential_vault import WorkerCredentialVault
from reporting import write_batch_report
from runtime_policy import classify_terminal_status
from visura_flow import ManualCaptchaDecision, VisuraFlowResult, execute_visura_flow


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://gaia_app:change_me@postgres:5432/gaia")
CREDENTIAL_MASTER_KEY = os.environ["CREDENTIAL_MASTER_KEY"]
def env_value(primary: str, legacy: str, default: str) -> str:
    return os.getenv(primary, os.getenv(legacy, default))


POLL_INTERVAL_SEC = int(env_value("ELABORAZIONI_POLL_INTERVAL_SEC", "CATASTO_POLL_INTERVAL_SEC", "3"))
CAPTCHA_MANUAL_TIMEOUT_SEC = int(os.getenv("CAPTCHA_MANUAL_TIMEOUT_SEC", "300"))
ANTI_CAPTCHA_API_KEY = os.getenv("ANTI_CAPTCHA_API_KEY", "").strip()
ANTI_CAPTCHA_POLL_INTERVAL_SEC = int(os.getenv("ANTI_CAPTCHA_POLL_INTERVAL_SEC", "3"))
ANTI_CAPTCHA_TIMEOUT_SEC = int(os.getenv("ANTI_CAPTCHA_TIMEOUT_SEC", "120"))
CAPTCHA_LLM_AGENT_CMD = os.getenv("CAPTCHA_LLM_AGENT_CMD", "agent").strip()
CAPTCHA_LLM_ENABLED = os.getenv("CAPTCHA_LLM_ENABLED", "true").lower() != "false"
CAPTCHA_LLM_ATTEMPTS = int(os.getenv("CAPTCHA_LLM_ATTEMPTS", "3"))
CAPTCHA_EXTERNAL_ATTEMPTS = int(os.getenv("CAPTCHA_EXTERNAL_ATTEMPTS", "3"))
BETWEEN_VISURE_DELAY_SEC = int(os.getenv("BETWEEN_VISURE_DELAY_SEC", "5"))
SESSION_TIMEOUT_SEC = int(os.getenv("SESSION_TIMEOUT_SEC", "1680"))
CREDENTIAL_LOCK_COOLDOWN_SEC = int(os.getenv("ELABORAZIONI_CREDENTIAL_LOCK_COOLDOWN_SEC", "300"))
REQUEST_RETRY_DEFER_SEC = int(os.getenv("ELABORAZIONI_REQUEST_RETRY_DEFER_SEC", "45"))
SISTER_SERVER_ERROR_BASE_COOLDOWN_SEC = int(os.getenv("ELABORAZIONI_SISTER_500_COOLDOWN_SEC", "90"))
SISTER_SERVER_ERROR_MAX_COOLDOWN_SEC = int(os.getenv("ELABORAZIONI_SISTER_500_MAX_COOLDOWN_SEC", "300"))
SISTER_SERVER_ERROR_GLOBAL_PAUSE_SEC = int(os.getenv("ELABORAZIONI_SISTER_500_GLOBAL_PAUSE_SEC", "45"))
OPERATION_WINDOW_ENABLED = os.getenv("ELABORAZIONI_OPERATION_WINDOW_ENABLED", "false").lower() == "true"
OPERATION_WINDOW_START_HOUR = int(os.getenv("ELABORAZIONI_OPERATION_START_HOUR", "0"))
OPERATION_WINDOW_END_HOUR = int(os.getenv("ELABORAZIONI_OPERATION_END_HOUR", "23"))
OPERATION_WINDOW_TIMEZONE = os.getenv("ELABORAZIONI_OPERATION_TIMEZONE", "Europe/Rome").strip() or "Europe/Rome"
DOCUMENT_STORAGE_PATH = Path(env_value("ELABORAZIONI_DOCUMENT_STORAGE_PATH", "CATASTO_DOCUMENT_STORAGE_PATH", "/data/catasto/documents"))
CAPTCHA_STORAGE_PATH = Path(env_value("ELABORAZIONI_CAPTCHA_STORAGE_PATH", "CATASTO_CAPTCHA_STORAGE_PATH", "/data/catasto/captcha"))
DEBUG_ARTIFACTS_PATH = Path(env_value("ELABORAZIONI_DEBUG_ARTIFACTS_PATH", "CATASTO_DEBUG_ARTIFACTS_PATH", "/data/catasto/debug"))
REPORT_STORAGE_PATH = Path(env_value("ELABORAZIONI_REPORT_STORAGE_PATH", "CATASTO_REPORT_STORAGE_PATH", "/data/catasto/reports"))
HEADLESS = env_value("ELABORAZIONI_HEADLESS", "CATASTO_HEADLESS", "true").lower() != "false"
DEBUG_BROWSER = env_value("ELABORAZIONI_DEBUG_BROWSER", "CATASTO_DEBUG_BROWSER", "false").lower() == "true"
WORKER_JOB_FAMILIES_ENV = os.getenv("ELABORAZIONI_WORKER_FAMILIES", "all").strip()

ALL_JOB_FAMILIES = {
    "connection_tests",
    "visure_batches",
    "ade_sync",
    "bulk_search",
    "autodoc",
    "capacitas",
    "registry",
}
JOB_FAMILY_ALIASES = {
    "all": ALL_JOB_FAMILIES,
    "visure": {"connection_tests", "visure_batches", "ade_sync", "bulk_search"},
    "catasto": {"connection_tests", "visure_batches", "ade_sync", "bulk_search"},
    "runtime": {"capacitas", "registry"},
    "autodoc": {"autodoc"},
}

logging.basicConfig(
    level=env_value("ELABORAZIONI_LOG_LEVEL", "CATASTO_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@dataclass(slots=True)
class WorkerState:
    stop_requested: bool = False


@dataclass(slots=True)
class ClaimedRequestSelection:
    request_id: UUID | None
    wait_reason: str | None = None


class CatastoWorker:
    def __init__(self) -> None:
        self.state = WorkerState()
        self.vault = WorkerCredentialVault(CREDENTIAL_MASTER_KEY)
        self.job_families = self._parse_job_families(WORKER_JOB_FAMILIES_ENV)
        self.anti_captcha_client = (
            AntiCaptchaClient(
                api_key=ANTI_CAPTCHA_API_KEY,
                poll_interval_sec=ANTI_CAPTCHA_POLL_INTERVAL_SEC,
                timeout_sec=ANTI_CAPTCHA_TIMEOUT_SEC,
        )
            if ANTI_CAPTCHA_API_KEY
            else None
        )
        self.llm_captcha_solver = LLMCaptchaSolver(agent_cmd=CAPTCHA_LLM_AGENT_CMD) if CAPTCHA_LLM_ENABLED else None
        DEBUG_ARTIFACTS_PATH.mkdir(parents=True, exist_ok=True)
        REPORT_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

    async def run(self) -> None:
        self._install_signal_handlers()
        self._recover_stuck_requests()
        logger.info("Worker Elaborazioni avviato con famiglie job: %s", ", ".join(sorted(self.job_families)))

        while not self.state.stop_requested:
            if self._handles_job_family("connection_tests"):
                connection_test_id = self._next_connection_test_id()
                if connection_test_id is not None:
                    logger.info("Elaborazione test connessione SISTER %s", connection_test_id)
                    await self._process_connection_test(connection_test_id)
                    continue

            if self._handles_job_family("capacitas"):
                capacitas_job = self._next_capacitas_job()
                if capacitas_job is not None:
                    job_kind, job_id = capacitas_job
                    logger.info("Job Capacitas %s %s prelevato dalla coda", job_kind, job_id)
                    await self._process_capacitas_job(job_kind, job_id)
                    continue

            if self._handles_job_family("registry"):
                registry_job_id = self._next_registry_import_job_id()
                if registry_job_id is not None:
                    logger.info("Job REGISTRY utenze %s prelevato dalla coda", registry_job_id)
                    await self._process_registry_import_job(registry_job_id)
                    continue

            if self._handles_job_family("ade_sync"):
                ade_sync_run_id = self._next_ade_sync_run_id()
                if ade_sync_run_id is not None:
                    logger.info("Run AdE %s prelevato dalla coda", ade_sync_run_id)
                    await self._process_ade_sync_run(ade_sync_run_id)
                    continue

            if self._handles_job_family("bulk_search"):
                distretto_export_job_id = self._next_distretto_export_job_id()
                if distretto_export_job_id is not None:
                    logger.info("Job export distretto catasto %s prelevato dalla coda", distretto_export_job_id)
                    await self._process_distretto_export_job(distretto_export_job_id)
                    continue

                bulk_job_id = self._next_bulk_search_job_id()
                if bulk_job_id is not None:
                    logger.info("Job catasto elaborazione massiva %s prelevato dalla coda", bulk_job_id)
                    await self._process_bulk_search_job(bulk_job_id)
                    continue

            if self._handles_job_family("autodoc"):
                autodoc_job_id = self._next_autodoc_sync_job_id()
                if autodoc_job_id is not None:
                    logger.info("Job AUTODOC %s prelevato dalla coda", autodoc_job_id)
                    await self._process_autodoc_sync_job(autodoc_job_id)
                    continue

            if self._handles_job_family("visure_batches"):
                batch_id = self._next_batch_id()
                if batch_id is not None:
                    logger.info("Batch %s prelevato dalla coda di lavorazione", batch_id)
                    await self._process_batch(batch_id)
                    continue

            await asyncio.sleep(POLL_INTERVAL_SEC)

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for signame in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(signame, self._request_stop)

    def _request_stop(self) -> None:
        self.state.stop_requested = True

    @staticmethod
    def _parse_job_families(raw_value: str) -> set[str]:
        requested = [item.strip().lower() for item in raw_value.split(",") if item.strip()]
        if not requested:
            return set(ALL_JOB_FAMILIES)

        families: set[str] = set()
        for item in requested:
            alias_members = JOB_FAMILY_ALIASES.get(item)
            if alias_members is not None:
                families.update(alias_members)
                continue
            if item in ALL_JOB_FAMILIES:
                families.add(item)
                continue
            raise ValueError(f"Famiglia job worker non riconosciuta: {item}")
        return families or set(ALL_JOB_FAMILIES)

    def _handles_job_family(self, family: str) -> bool:
        return family in self.job_families

    def _recover_stuck_requests(self) -> None:
        with SessionLocal() as db:
            if self._handles_job_family("connection_tests"):
                stuck_connection_tests = db.scalars(
                    select(CatastoConnectionTest).where(
                        CatastoConnectionTest.status == CatastoConnectionTestStatus.PROCESSING.value,
                    )
                ).all()
                for connection_test in stuck_connection_tests:
                    connection_test.status = CatastoConnectionTestStatus.PENDING.value
                    connection_test.message = "Recuperato dopo riavvio worker"

            if self._handles_job_family("visure_batches"):
                stuck_requests = db.scalars(
                    select(CatastoVisuraRequest).where(
                        CatastoVisuraRequest.status == CatastoVisuraRequestStatus.PROCESSING.value,
                    )
                ).all()
                for request in stuck_requests:
                    request.status = CatastoVisuraRequestStatus.PENDING.value
                    request.current_operation = "Recuperato dopo riavvio worker"

            history_ids: list[int] = []
            incass_ids: list[int] = []
            terreni_ids: list[int] = []
            particelle_ids: list[int] = []
            bulk_jobs = 0
            distretto_export_jobs = 0
            registry_ids: list[int] = []
            ade_sync_runs = 0

            if self._handles_job_family("capacitas"):
                history_ids = prepare_anagrafica_history_jobs_for_recovery(db)
                incass_ids = prepare_incass_sync_jobs_for_recovery(db)
                terreni_ids = prepare_terreni_sync_jobs_for_recovery(db)
                particelle_ids = prepare_particelle_sync_jobs_for_recovery(db)
            if self._handles_job_family("bulk_search"):
                bulk_jobs = prepare_bulk_search_jobs_for_recovery(db)
                distretto_export_jobs = prepare_distretto_export_jobs_for_recovery(db)
            if self._handles_job_family("registry"):
                registry_ids = prepare_registry_import_jobs_for_recovery(db)
            if self._handles_job_family("ade_sync"):
                ade_sync_runs = prepare_ade_sync_runs_for_recovery(db)
            if history_ids:
                logger.info("Recuperati %d job Capacitas storico anagrafica", len(history_ids))
            if incass_ids:
                logger.info("Recuperati %d job Capacitas inCASS", len(incass_ids))
            if terreni_ids:
                logger.info("Recuperati %d job Capacitas terreni", len(terreni_ids))
            if particelle_ids:
                logger.info("Recuperati %d job Capacitas particelle", len(particelle_ids))
            if bulk_jobs:
                logger.info("Recuperati %d job catasto elaborazione massiva", bulk_jobs)
            if distretto_export_jobs:
                logger.info("Recuperati %d job export distretto catasto", distretto_export_jobs)
            if registry_ids:
                logger.info("Recuperati %d job REGISTRY utenze", len(registry_ids))
            if ade_sync_runs:
                logger.info("Recuperati %d run AdE WFS", ade_sync_runs)
            db.commit()

    def _next_connection_test_id(self):
        with SessionLocal() as db:
            connection_test = db.scalar(
                select(CatastoConnectionTest)
                .where(CatastoConnectionTest.status == CatastoConnectionTestStatus.PENDING.value)
                .order_by(CatastoConnectionTest.created_at.asc())
            )
            return connection_test.id if connection_test is not None else None

    def _next_capacitas_job(self) -> tuple[str, int] | None:
        with SessionLocal() as db:
            expire_stale_anagrafica_history_jobs(db)
            expire_stale_incass_sync_jobs(db)
            expire_stale_terreni_sync_jobs(db)
            expire_stale_particelle_sync_jobs(db)

            for job_kind, model in (
                ("anagrafica_history", CapacitasAnagraficaHistoryImportJob),
                ("incass", CapacitasInCassSyncJob),
                ("terreni", CapacitasTerreniSyncJob),
                ("particelle", CapacitasParticelleSyncJob),
            ):
                job = db.scalar(
                    select(model)
                    .where(
                        model.status.in_(("pending", "queued_resume")),
                        model.completed_at.is_(None),
                    )
                    .order_by(model.created_at.asc())
                    .with_for_update(skip_locked=True)
                )
                if job is None:
                    continue
                job.status = "processing"
                job.started_at = datetime.now(timezone.utc)
                job.error_detail = None
                db.commit()
                return job_kind, job.id
        return None

    async def _process_capacitas_job(self, job_kind: str, job_id: int) -> None:
        if job_kind == "anagrafica_history":
            await run_anagrafica_history_job_by_id(job_id)
            return
        if job_kind == "incass":
            await run_incass_job_by_id(job_id)
            return
        if job_kind == "terreni":
            await run_terreni_job_by_id(job_id)
            return
        if job_kind == "particelle":
            await run_particelle_job_by_id(job_id)
            return
        logger.error("Tipo job Capacitas non riconosciuto: %s", job_kind)

    def _next_registry_import_job_id(self):
        from app.modules.utenze.models import AnagraficaImportJob, AnagraficaImportJobStatus

        with SessionLocal() as db:
            job = db.scalar(
                select(AnagraficaImportJob)
                .where(
                    AnagraficaImportJob.letter == "REGISTRY",
                    AnagraficaImportJob.status == AnagraficaImportJobStatus.PENDING.value,
                )
                .order_by(AnagraficaImportJob.created_at.asc())
                .with_for_update(skip_locked=True)
            )
            if job is None:
                return None
            job.status = AnagraficaImportJobStatus.RUNNING.value
            job.started_at = datetime.now(timezone.utc)
            db.commit()
            return job.id

    async def _process_registry_import_job(self, job_id) -> None:
        await asyncio.to_thread(run_registry_bulk_import_job_by_id, job_id)

    def _next_ade_sync_run_id(self) -> str | None:
        from app.models.catasto_phase1 import CatAdeSyncRun

        with SessionLocal() as db:
            run = db.scalar(
                select(CatAdeSyncRun)
                .where(CatAdeSyncRun.status == "queued")
                .order_by(CatAdeSyncRun.started_at.asc(), CatAdeSyncRun.id.asc())
            )
            return str(run.id) if run is not None else None

    async def _process_ade_sync_run(self, run_id: str) -> None:
        try:
            with SessionLocal() as db:
                execute_ade_sync_run(db, run_id)
        except Exception:
            logger.exception("Run AdE worker %s fallito", run_id)

    def _next_bulk_search_job_id(self) -> str | None:
        with SessionLocal() as db:
            job = db.scalar(
                select(CatastoElaborazioniMassiveJob)
                .where(CatastoElaborazioniMassiveJob.status == CatastoElaborazioniMassiveJobStatus.PENDING.value)
                .order_by(CatastoElaborazioniMassiveJob.created_at.asc())
                .with_for_update(skip_locked=True)
            )
            if job is None:
                return None
            job.status = CatastoElaborazioniMassiveJobStatus.PROCESSING.value
            job.started_at = datetime.now(timezone.utc)
            job.error_message = None
            db.commit()
            return str(job.id)

    async def _process_bulk_search_job(self, job_id: str) -> None:
        try:
            await run_bulk_search_job_by_id(UUID(job_id))
        except Exception:
            logger.exception("Job catasto elaborazione massiva %s fallito", job_id)

    def _next_distretto_export_job_id(self) -> str | None:
        with SessionLocal() as db:
            job = db.scalar(
                select(CatastoDistrettoExportJob)
                .where(CatastoDistrettoExportJob.status == CatastoElaborazioniMassiveJobStatus.PENDING.value)
                .order_by(CatastoDistrettoExportJob.created_at.asc())
                .with_for_update(skip_locked=True)
            )
            if job is None:
                return None
            job.status = CatastoElaborazioniMassiveJobStatus.PROCESSING.value
            job.started_at = datetime.now(timezone.utc)
            job.error_message = None
            db.commit()
            return str(job.id)

    async def _process_distretto_export_job(self, job_id: str) -> None:
        try:
            await asyncio.to_thread(run_distretto_export_job_by_id, UUID(job_id))
        except Exception:
            logger.exception("Job export distretto catasto %s fallito", job_id)

    def _next_autodoc_sync_job_id(self) -> str | None:
        with SessionLocal() as db:
            job = db.scalar(
                select(WCSyncJob)
                .where(
                    WCSyncJob.entity == AUTODOC_SYNC_ENTITY,
                    WCSyncJob.status == "queued",
                )
                .order_by(WCSyncJob.started_at.asc())
                .with_for_update(skip_locked=True)
            )
            if job is None:
                return None
            job.status = "running"
            db.commit()
            return str(job.id)

    async def _process_autodoc_sync_job(self, job_id: str) -> None:
        try:
            await run_autodoc_sync_job_by_id(SessionLocal, job_id)
        except Exception:
            logger.exception("Job AUTODOC %s fallito", job_id)

    async def _process_connection_test(self, connection_test_id) -> None:
        browser = BrowserSession(
            BrowserSessionConfig(
                headless=HEADLESS,
                session_timeout_sec=SESSION_TIMEOUT_SEC,
                debug_pause=DEBUG_BROWSER,
                debug_artifacts_path=DEBUG_ARTIFACTS_PATH,
            )
        )

        with SessionLocal() as db:
            connection_test = db.get(CatastoConnectionTest, connection_test_id)
            if connection_test is None:
                return
            connection_test.status = CatastoConnectionTestStatus.PROCESSING.value
            connection_test.started_at = datetime.now(timezone.utc)
            connection_test.message = "Test credenziali SISTER in corso"
            db.commit()

        try:
            await browser.start()
            with SessionLocal() as db:
                connection_test = db.get(CatastoConnectionTest, connection_test_id)
                if connection_test is None:
                    return
                password = self.vault.decrypt(connection_test.sister_password_encrypted)
                sister_username = connection_test.sister_username

            result = await browser.test_connection(sister_username, password)
            logger.info(
                "Test connessione SISTER %s completato: reachable=%s authenticated=%s message=%s",
                connection_test_id,
                result.reachable,
                result.authenticated,
                result.message,
            )

            with SessionLocal() as db:
                connection_test = db.get(CatastoConnectionTest, connection_test_id)
                if connection_test is None:
                    return

                connection_test.status = (
                    CatastoConnectionTestStatus.COMPLETED.value
                    if result.authenticated
                    else CatastoConnectionTestStatus.FAILED.value
                )
                connection_test.mode = "worker"
                connection_test.reachable = result.reachable
                connection_test.authenticated = result.authenticated
                connection_test.message = result.message
                connection_test.completed_at = datetime.now(timezone.utc)

                if connection_test.persist_verification and connection_test.credential_id and result.authenticated:
                    credential = db.get(CatastoCredential, connection_test.credential_id)
                    if credential is not None:
                        credential.verified_at = connection_test.completed_at

                db.commit()
        except Exception as exc:
            logger.exception("Test connessione worker %s fallito", connection_test_id)
            with SessionLocal() as db:
                connection_test = db.get(CatastoConnectionTest, connection_test_id)
                if connection_test is not None:
                    connection_test.status = CatastoConnectionTestStatus.FAILED.value
                    connection_test.mode = "worker"
                    connection_test.reachable = False
                    connection_test.authenticated = False
                    connection_test.message = f"Test connessione worker fallito: {exc}"
                    connection_test.completed_at = datetime.now(timezone.utc)
                    db.commit()
        finally:
            await browser.stop()

    def _next_batch_id(self):
        with SessionLocal() as db:
            batch = db.scalar(
                select(CatastoBatch)
                .where(CatastoBatch.status == CatastoBatchStatus.PROCESSING.value)
                .order_by(CatastoBatch.started_at.asc().nullsfirst(), CatastoBatch.created_at.asc())
            )
            return batch.id if batch is not None else None

    async def _process_batch(self, batch_id) -> None:
        with SessionLocal() as db:
            batch = db.get(CatastoBatch, batch_id)
            if batch is None:
                return
            batch.current_operation = "Batch preso in carico dal worker"
            db.commit()
            if batch.credential_id is not None:
                selected_credential = db.get(CatastoCredential, batch.credential_id)
                active_credentials = (
                    [selected_credential]
                    if selected_credential is not None and selected_credential.user_id == batch.user_id and selected_credential.active
                    else []
                )
            else:
                all_credentials = list(
                    db.scalars(
                        select(CatastoCredential)
                        .where(CatastoCredential.user_id == batch.user_id)
                        .order_by(CatastoCredential.is_default.desc(), CatastoCredential.active.desc(), CatastoCredential.updated_at.desc())
                    ).all()
                )
                active_credentials = [c for c in all_credentials if c.active]
            if not active_credentials:
                batch.status = CatastoBatchStatus.FAILED.value
                batch.current_operation = "Credenziali SISTER attive mancanti"
                db.commit()
                return
            logger.info("Batch %s preso in carico per utente %s", batch_id, batch.user_id)

        claim_lock = asyncio.Lock()
        shared_state_lock = asyncio.Lock()
        deferred_requests: dict[UUID, datetime] = {}
        claimed_request_ids: set[UUID] = set()
        credential_cooldowns: dict[UUID, datetime] = {}
        credential_server_error_counts: dict[UUID, int] = {}
        global_server_error_pause_until: datetime | None = None

        async def _restart_browser(browser: BrowserSession) -> BrowserSession:
            with contextlib.suppress(Exception):
                await browser.logout()
            with contextlib.suppress(Exception):
                await browser.stop()
            browser = self._build_browser_session()
            await browser.start()
            return browser

        async def _release_claim(request_id: UUID | None) -> None:
            if request_id is None:
                return
            async with shared_state_lock:
                claimed_request_ids.discard(request_id)

        async def _defer_request(request_id: UUID, seconds: int, operation: str) -> None:
            async with shared_state_lock:
                deferred_requests[request_id] = datetime.now(timezone.utc) + timedelta(seconds=seconds)
            self._reset_request_for_retry(request_id, operation)

        async def _next_wait_seconds() -> int:
            now = datetime.now(timezone.utc)
            async with shared_state_lock:
                deferred_times = [value for value in deferred_requests.values() if value > now]
                cooldown_times = [value for value in credential_cooldowns.values() if value > now]
            candidates = deferred_times + cooldown_times
            if not candidates:
                return 2
            retry_at = min(candidates)
            return max(int((retry_at - now).total_seconds()), 1)

        async def _register_sister_server_error(credential: CatastoCredential, request_id: UUID, exc: SisterServerError) -> tuple[int, bool]:
            nonlocal global_server_error_pause_until

            now = datetime.now(timezone.utc)
            async with shared_state_lock:
                consecutive_errors = credential_server_error_counts.get(credential.id, 0) + 1
                credential_server_error_counts[credential.id] = consecutive_errors
                cooldown_seconds = self._compute_sister_server_error_cooldown(consecutive_errors)
                credential_cooldowns[credential.id] = now + timedelta(seconds=cooldown_seconds)
                all_credentials_in_cooldown = all(
                    (credential_cooldowns.get(active_credential.id) or now) > now
                    for active_credential in active_credentials
                )
                opened_global_pause = False
                if all_credentials_in_cooldown:
                    global_server_error_pause_until = now + timedelta(seconds=SISTER_SERVER_ERROR_GLOBAL_PAUSE_SEC)
                    opened_global_pause = True

            logger.warning(
                "Batch %s richiesta %s differita per errore 500 SISTER con %s: consecutive_errors=%s cooldown=%ss global_pause=%s detail=%s",
                batch_id,
                request_id,
                credential.sister_username,
                consecutive_errors,
                cooldown_seconds,
                opened_global_pause,
                exc,
            )
            return cooldown_seconds, opened_global_pause

        async def _claim_next_request() -> ClaimedRequestSelection:
            async with claim_lock:
                async with shared_state_lock:
                    deferred_snapshot = dict(deferred_requests)
                    claimed_snapshot = set(claimed_request_ids)
                selection = self._next_request_id(batch_id, deferred_snapshot, claimed_snapshot)
                if selection.request_id is not None:
                    async with shared_state_lock:
                        claimed_request_ids.add(selection.request_id)
                        deferred_requests.pop(selection.request_id, None)
                return selection

        def _batch_release_requested() -> bool:
            with SessionLocal() as db:
                batch = db.get(CatastoBatch, batch_id)
                return batch is None or batch.status == CatastoBatchStatus.CANCELLED.value

        async def _credential_runner(credential: CatastoCredential) -> None:
            nonlocal global_server_error_pause_until
            browser = self._build_browser_session()
            password = self.vault.decrypt(credential.sister_password_encrypted)
            await browser.start()
            try:
                while not self.state.stop_requested:
                    if _batch_release_requested():
                        logger.info(
                            "Batch %s rilascio richiesto, chiusura sessione SISTER per %s",
                            batch_id,
                            credential.sister_username,
                        )
                        return
                    now = datetime.now(timezone.utc)
                    if not self._is_within_operating_window(now):
                        resume_at = self._next_operating_resume_at(now)
                        wait_seconds = max(int((resume_at - now).total_seconds()), 1) if resume_at is not None else 60
                        resume_label = resume_at.astimezone(self._operation_window_zone()).strftime("%H:%M") if resume_at is not None else "n/d"
                        self._set_batch_operation(
                            batch_id,
                            f"Batch in pausa fuori finestra operativa, ripresa automatica alle {resume_label}",
                        )
                        await asyncio.sleep(min(wait_seconds, 60))
                        continue
                    async with shared_state_lock:
                        cooldown_until = credential_cooldowns.get(credential.id)
                        global_pause_until = global_server_error_pause_until
                    if global_pause_until is not None and global_pause_until > now:
                        wait_seconds = max(int((global_pause_until - now).total_seconds()), 1)
                        self._set_batch_operation(
                            batch_id,
                            f"Portale SISTER instabile, pausa globale {wait_seconds}s prima della ripresa",
                        )
                        await asyncio.sleep(wait_seconds)
                        continue
                    if cooldown_until is not None and cooldown_until > now:
                        wait_seconds = max(int((cooldown_until - now).total_seconds()), 1)
                        self._set_batch_operation(
                            batch_id,
                            f"Credenziale {credential.sister_username} in cooldown, attesa {wait_seconds}s",
                        )
                        await asyncio.sleep(wait_seconds)
                        continue

                    selection = await _claim_next_request()
                    request_id = selection.request_id
                    if request_id is None:
                        if not self._batch_has_open_requests(batch_id):
                            return
                        if selection.wait_reason == "WAIT":
                            self._set_batch_operation(batch_id, "In attesa di input CAPTCHA manuale")
                        elif selection.wait_reason == "RETRY_LATER":
                            wait_seconds = await _next_wait_seconds()
                            self._set_batch_operation(batch_id, f"Richieste differite, attesa {wait_seconds}s")
                            await asyncio.sleep(wait_seconds)
                            continue
                        await asyncio.sleep(2)
                        continue

                    try:
                        await self._process_request(browser, credential, batch_id, request_id)
                    except SisterServerError as exc:
                        cooldown_seconds, opened_global_pause = await _register_sister_server_error(
                            credential,
                            request_id,
                            exc,
                        )
                        await _defer_request(
                            request_id,
                            max(REQUEST_RETRY_DEFER_SEC, cooldown_seconds),
                            (
                                "Portale SISTER temporaneamente non disponibile, richiesta rimessa in coda"
                                if opened_global_pause
                                else f"Errore SISTER 500 su {credential.sister_username}, retry differito"
                            ),
                        )
                        browser = await _restart_browser(browser)
                        await asyncio.sleep(5)
                    except Exception as exc:
                        if self._is_recoverable_credential_error(exc):
                            async with shared_state_lock:
                                credential_server_error_counts[credential.id] = 0
                                global_server_error_pause_until = None
                                credential_cooldowns[credential.id] = datetime.now(timezone.utc) + timedelta(
                                    seconds=CREDENTIAL_LOCK_COOLDOWN_SEC
                                )
                            logger.warning(
                                "Batch %s richiesta %s differita per errore recuperabile con %s: %s",
                                batch_id,
                                request_id,
                                credential.sister_username,
                                exc,
                            )
                            await _defer_request(
                                request_id,
                                REQUEST_RETRY_DEFER_SEC,
                                f"Sessione/timeout su {credential.sister_username}, retry differito",
                            )
                            browser = await _restart_browser(browser)
                        else:
                            async with shared_state_lock:
                                credential_server_error_counts[credential.id] = 0
                            logger.exception(
                                "Batch %s richiesta %s fallita su %s, isolamento errore e prosecuzione batch",
                                batch_id,
                                request_id,
                                credential.sister_username,
                            )
                            with SessionLocal() as db:
                                request = db.get(CatastoVisuraRequest, request_id)
                                if request is not None and request.artifact_dir:
                                    artifact_dir = Path(request.artifact_dir)
                                    self._write_request_error_artifact(artifact_dir, exc)
                                    with contextlib.suppress(Exception):
                                        await browser.capture_debug_snapshot(artifact_dir, "final-failed")
                            self._fail_request(batch_id, request_id, str(exc))
                            browser = await _restart_browser(browser)
                    else:
                        async with shared_state_lock:
                            credential_server_error_counts[credential.id] = 0
                    finally:
                        await _release_claim(request_id)

                    if self.state.stop_requested:
                        return
                    if _batch_release_requested():
                        logger.info(
                            "Batch %s arrestato dopo completamento checkpoint corrente, logout per %s",
                            batch_id,
                            credential.sister_username,
                        )
                        return
                    await asyncio.sleep(BETWEEN_VISURE_DELAY_SEC)
            finally:
                with contextlib.suppress(Exception):
                    await browser.logout()
                await browser.stop()

        pool_label = (
            f"Avvio autosync ruolo con credenziale {active_credentials[0].sister_username}"
            if len(active_credentials) == 1 and batch.batch_kind == CatastoBatchKind.RUOLO_AUTOSYNC.value
            else f"Avvio pool visure con {len(active_credentials)} credenziali"
        )
        self._set_batch_operation(batch_id, pool_label)
        try:
            await asyncio.gather(*[_credential_runner(active_credential) for active_credential in active_credentials])
            self._finalize_batch(batch_id)
        except Exception as exc:
            logger.exception("Batch %s fallito prima del completamento", batch_id)
            self._fail_batch(batch_id, str(exc))

    @staticmethod
    def _is_recoverable_credential_error(exc: Exception) -> bool:
        message = str(exc).lower()
        markers = [
            "sister_session_locked",
            "gia' in sessione",
            "già in sessione",
            "utente sister bloccato",
            "error_locked.jsp",
            "login timeout",
            "timeout 60000ms exceeded",
        ]
        return any(marker in message for marker in markers)

    @staticmethod
    def _operation_window_zone() -> ZoneInfo:
        try:
            return ZoneInfo(OPERATION_WINDOW_TIMEZONE)
        except Exception:
            return ZoneInfo("Europe/Rome")

    @staticmethod
    def _is_within_operating_window(now_utc: datetime | None = None) -> bool:
        if not OPERATION_WINDOW_ENABLED:
            return True
        now_utc = now_utc or datetime.now(timezone.utc)
        local_now = now_utc.astimezone(CatastoWorker._operation_window_zone())
        current_hour = local_now.hour
        start_hour = min(max(OPERATION_WINDOW_START_HOUR, 0), 23)
        end_hour = min(max(OPERATION_WINDOW_END_HOUR, 0), 23)
        if start_hour <= end_hour:
            return start_hour <= current_hour <= end_hour
        return current_hour >= start_hour or current_hour <= end_hour

    @staticmethod
    def _next_operating_resume_at(now_utc: datetime | None = None) -> datetime | None:
        if not OPERATION_WINDOW_ENABLED:
            return None
        now_utc = now_utc or datetime.now(timezone.utc)
        zone = CatastoWorker._operation_window_zone()
        local_now = now_utc.astimezone(zone)
        start_hour = min(max(OPERATION_WINDOW_START_HOUR, 0), 23)
        resume_local = local_now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        if resume_local <= local_now:
            resume_local = resume_local + timedelta(days=1)
        return resume_local.astimezone(timezone.utc)

    @staticmethod
    def _compute_sister_server_error_cooldown(consecutive_errors: int) -> int:
        if consecutive_errors <= 1:
            return SISTER_SERVER_ERROR_BASE_COOLDOWN_SEC
        cooldown = SISTER_SERVER_ERROR_BASE_COOLDOWN_SEC * consecutive_errors
        return min(cooldown, SISTER_SERVER_ERROR_MAX_COOLDOWN_SEC)

    @staticmethod
    def _is_expired(deadline: datetime | None) -> bool:
        if deadline is None:
            return False
        now = datetime.now(timezone.utc)
        if deadline.tzinfo is None:
            return deadline <= now.replace(tzinfo=None)
        return deadline <= now

    def _build_browser_session(self) -> BrowserSession:
        return BrowserSession(
            BrowserSessionConfig(
                headless=HEADLESS,
                session_timeout_sec=SESSION_TIMEOUT_SEC,
                debug_pause=DEBUG_BROWSER,
                debug_artifacts_path=DEBUG_ARTIFACTS_PATH,
            )
        )

    def _fail_batch(self, batch_id, message: str) -> None:
        user_message = self._to_user_message(message)
        with SessionLocal() as db:
            batch = db.get(CatastoBatch, batch_id)
            if batch is None:
                return

            requests = db.scalars(
                select(CatastoVisuraRequest).where(CatastoVisuraRequest.batch_id == batch_id),
            ).all()

            for request in requests:
                if request.status in {
                    CatastoVisuraRequestStatus.PENDING.value,
                    CatastoVisuraRequestStatus.PROCESSING.value,
                    CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value,
                }:
                    if request.purpose == ADE_SCAN_PURPOSE and request.target_ruolo_particella_id is not None:
                        persist_ade_status_scan_result(
                            db,
                            ruolo_particella_id=request.target_ruolo_particella_id,
                            request_id=request.id,
                            status="failed",
                            classification="blocked",
                            payload={"classification": "blocked", "message": user_message},
                            error=user_message,
                        )
                    request.status = CatastoVisuraRequestStatus.FAILED.value
                    request.current_operation = "Failed before visura execution"
                    request.error_message = user_message
                    request.processed_at = datetime.now(timezone.utc)
                    request.captcha_manual_solution = None
                    request.captcha_skip_requested = False

            batch.status = CatastoBatchStatus.FAILED.value
            batch.current_operation = user_message
            batch.completed_at = datetime.now(timezone.utc)
            self._refresh_batch_counts(db, batch)
            db.commit()

    def _fail_request(self, batch_id, request_id, message: str) -> None:
        user_message = self._to_user_message(message)
        with SessionLocal() as db:
            batch = db.get(CatastoBatch, batch_id)
            request = db.get(CatastoVisuraRequest, request_id)
            if batch is None or request is None:
                return

            if request.purpose == ADE_SCAN_PURPOSE and request.target_ruolo_particella_id is not None:
                persist_ade_status_scan_result(
                    db,
                    ruolo_particella_id=request.target_ruolo_particella_id,
                    request_id=request.id,
                    status="failed",
                    classification="blocked",
                    payload={"classification": "blocked", "message": user_message},
                    error=user_message,
                )

            request.status = CatastoVisuraRequestStatus.FAILED.value
            request.current_operation = "Richiesta fallita, batch in prosecuzione"
            request.error_message = user_message
            request.processed_at = datetime.now(timezone.utc)
            request.captcha_manual_solution = None
            request.captcha_skip_requested = False

            batch.current_operation = f"Errore riga {request.row_index}, prosecuzione batch"
            self._refresh_batch_counts(db, batch)
            db.commit()

    def _reset_request_for_retry(self, request_id, operation: str) -> None:
        with SessionLocal() as db:
            request = db.get(CatastoVisuraRequest, request_id)
            if request is None:
                return
            if request.error_message == RELEASE_REQUESTED_MESSAGE:
                request.status = CatastoVisuraRequestStatus.SKIPPED.value
                request.current_operation = RELEASE_REQUESTED_OPERATION
                request.processed_at = request.processed_at or datetime.now(timezone.utc)
                db.commit()
                return
            request.status = CatastoVisuraRequestStatus.PENDING.value
            request.current_operation = operation
            db.commit()

    def _next_request_id(
        self,
        batch_id,
        deferred_requests: dict[UUID, datetime] | None = None,
        claimed_request_ids: set[UUID] | None = None,
    ) -> ClaimedRequestSelection:
        deferred_requests = deferred_requests or {}
        claimed_request_ids = claimed_request_ids or set()
        with SessionLocal() as db:
            requests = db.scalars(
                select(CatastoVisuraRequest)
                .where(
                    CatastoVisuraRequest.batch_id == batch_id,
                    CatastoVisuraRequest.status.in_(
                        [
                            CatastoVisuraRequestStatus.PENDING.value,
                            CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value,
                        ]
                    ),
                )
                .order_by(CatastoVisuraRequest.row_index.asc())
                .with_for_update(skip_locked=True)
            ).all()

            now = datetime.now(timezone.utc)
            has_deferred_requests = False
            has_waiting_captcha = False
            for request in requests:
                if request.id in claimed_request_ids:
                    continue
                deferred_until = deferred_requests.get(request.id)
                if deferred_until is not None and deferred_until > now:
                    has_deferred_requests = True
                    continue
                if request.status == CatastoVisuraRequestStatus.PENDING.value:
                    request.status = CatastoVisuraRequestStatus.PROCESSING.value
                    request.current_operation = "Presa in carico dal worker"
                    request.attempts += 1
                    db.commit()
                    return ClaimedRequestSelection(request_id=request.id)
                if request.status == CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value:
                    if request.captcha_skip_requested or request.captcha_manual_solution:
                        return ClaimedRequestSelection(request_id=request.id)
                    if self._is_expired(request.captcha_expires_at):
                        return ClaimedRequestSelection(request_id=request.id)
                    has_waiting_captcha = True

            if has_waiting_captcha:
                return ClaimedRequestSelection(request_id=None, wait_reason="WAIT")
            if has_deferred_requests:
                return ClaimedRequestSelection(request_id=None, wait_reason="RETRY_LATER")
            return ClaimedRequestSelection(request_id=None)

    def _batch_has_open_requests(self, batch_id) -> bool:
        with SessionLocal() as db:
            open_request = db.scalar(
                select(CatastoVisuraRequest.id)
                .where(
                    CatastoVisuraRequest.batch_id == batch_id,
                    CatastoVisuraRequest.status.in_(
                        [
                            CatastoVisuraRequestStatus.PENDING.value,
                            CatastoVisuraRequestStatus.PROCESSING.value,
                            CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value,
                        ]
                    ),
                )
                .limit(1)
            )
            return open_request is not None

    async def _process_request(self, browser: BrowserSession, credential: CatastoCredential, batch_id, request_id) -> None:
        request_snapshot: CatastoVisuraRequest | None = None
        artifact_dir: Path | None = None
        with SessionLocal() as db:
            request = db.get(CatastoVisuraRequest, request_id)
            batch = db.get(CatastoBatch, batch_id)
            if request is None or batch is None:
                return
            logger.info(
                "Elaborazione richiesta %s del batch %s riga=%s mode=%s comune=%s foglio=%s particella=%s subject_id=%s",
                request_id,
                batch_id,
                request.row_index,
                request.search_mode,
                request.comune,
                request.foglio,
                request.particella,
                request.subject_id,
            )

            if request.status == CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value and request.captcha_manual_solution:
                request.status = CatastoVisuraRequestStatus.PROCESSING.value
                request.current_operation = "Ripresa con CAPTCHA manuale"
            elif (
                request.status == CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value
                and self._is_expired(request.captcha_expires_at)
            ):
                request.status = CatastoVisuraRequestStatus.FAILED.value
                request.current_operation = "Timeout CAPTCHA manuale"
                request.error_message = "Tempo massimo CAPTCHA manuale superato"
                request.processed_at = datetime.now(timezone.utc)
                batch.current_operation = f"Timeout CAPTCHA manuale sulla riga {request.row_index}"
                self._refresh_batch_counts(db, batch)
                db.commit()
                return
            elif request.status == CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value and request.captcha_skip_requested:
                request.status = CatastoVisuraRequestStatus.SKIPPED.value
                request.current_operation = "Saltata dall'utente"
                request.error_message = "Saltata dall'utente dopo richiesta CAPTCHA"
                request.processed_at = datetime.now(timezone.utc)
                batch.current_operation = f"Saltata riga {request.row_index}"
                self._refresh_batch_counts(db, batch)
                db.commit()
                return
            elif request.status != CatastoVisuraRequestStatus.PROCESSING.value:
                request.status = CatastoVisuraRequestStatus.PROCESSING.value
                request.current_operation = "Presa in carico dal worker"
                request.attempts += 1

            batch.current_operation = f"Lavorazione {request.comune} Fg.{request.foglio} Part.{request.particella}"
            if request.search_mode == "soggetto":
                batch.current_operation = (
                    f"Lavorazione {request.subject_kind or 'SOGGETTO'} {request.subject_id or '-'}"
                )
            artifact_dir = self._build_request_artifact_dir(batch_id, request)
            artifact_dir.mkdir(parents=True, exist_ok=True)
            request.artifact_dir = str(artifact_dir)
            db.commit()
            db.refresh(request)
            db.expunge(request)
            request_snapshot = request

        self._set_request_operation(request_id, "Autenticazione sessione SISTER")
        await browser.ensure_authenticated(
            credential.sister_username,
            self.vault.decrypt(credential.sister_password_encrypted),
        )
        self._set_request_operation(request_id, "Apertura form SISTER")

        with SessionLocal() as db:
            request = db.get(CatastoVisuraRequest, request_id)
            if request is None:
                return
            request.current_operation = "Esecuzione flusso visura"
            db.commit()

        if request_snapshot is None:
            return

        result = await execute_visura_flow(
            browser=browser,
            request=request_snapshot,
            document_path=self._build_document_path(credential.sister_username, request_snapshot),
            captcha_dir=CAPTCHA_STORAGE_PATH / str(batch_id),
            get_manual_captcha_decision=lambda image_path: self._wait_for_manual_captcha(batch_id, request_id, image_path),
            solve_llm_captcha=self._solve_llm_captcha if self.llm_captcha_solver is not None else None,
            solve_external_captcha=self._solve_external_captcha if self.anti_captcha_client is not None else None,
            max_llm_attempts=CAPTCHA_LLM_ATTEMPTS,
            max_external_attempts=CAPTCHA_EXTERNAL_ATTEMPTS,
            update_operation=lambda operation: self._set_request_operation(request_id, operation),
        )
        logger.info(
            "Richiesta %s completata con status=%s errore=%s",
            request_id,
            result.status,
            result.error_message,
        )
        if request_snapshot.artifact_dir:
            if result.status == "not_found" and request_snapshot.search_mode == "soggetto":
                await browser.capture_subject_not_found_preview(Path(request_snapshot.artifact_dir))
            await browser.capture_debug_snapshot(Path(request_snapshot.artifact_dir), f"final-{result.status}")
        self._persist_flow_result(batch_id, request_id, credential.sister_username, result)

    async def _wait_for_manual_captcha(self, batch_id, request_id, image_path: Path) -> ManualCaptchaDecision:
        deadline = datetime.now(timezone.utc) + timedelta(seconds=CAPTCHA_MANUAL_TIMEOUT_SEC)
        logger.info("Richiesta %s in attesa di CAPTCHA manuale fino a %s", request_id, deadline.isoformat())

        with SessionLocal() as db:
            request = db.get(CatastoVisuraRequest, request_id)
            batch = db.get(CatastoBatch, batch_id)
            if request is not None and batch is not None:
                request.status = CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value
                request.current_operation = "In attesa di CAPTCHA manuale"
                request.captcha_image_path = str(image_path)
                request.captcha_requested_at = datetime.now(timezone.utc)
                request.captcha_expires_at = deadline
                request.captcha_manual_solution = None
                request.captcha_skip_requested = False
                batch.current_operation = f"CAPTCHA richiesto per riga {request.row_index}"
                db.commit()

        while datetime.now(timezone.utc) < deadline and not self.state.stop_requested:
            with SessionLocal() as db:
                request = db.get(CatastoVisuraRequest, request_id)
                if request is None:
                    return ManualCaptchaDecision(text=None, skip=True)
                if request.captcha_skip_requested:
                    logger.info("Richiesta %s CAPTCHA manuale saltato dall'utente", request_id)
                    return ManualCaptchaDecision(text=None, skip=True)
                if request.captcha_manual_solution:
                    logger.info("Richiesta %s CAPTCHA manuale ricevuto", request_id)
                    return ManualCaptchaDecision(text=request.captcha_manual_solution)
            await asyncio.sleep(2)

        logger.warning("Richiesta %s timeout CAPTCHA manuale", request_id)
        return ManualCaptchaDecision(text=None, skip=False)

    async def _solve_llm_captcha(self, image_bytes: bytes) -> str | None:
        if self.llm_captcha_solver is None:
            return None
        logger.info("Invio CAPTCHA al solver LLM")
        text = await self.llm_captcha_solver.solve(image_bytes)
        logger.info("Risposta ricevuta dal solver LLM: testo_presente=%s", bool(text))
        return text

    async def _solve_external_captcha(self, image_bytes: bytes) -> str | None:
        if self.anti_captcha_client is None:
            return None
        logger.info("Invio CAPTCHA al servizio esterno Anti-Captcha")
        text = await self.anti_captcha_client.solve_image_to_text(image_bytes)
        logger.info("Risposta ricevuta da Anti-Captcha: testo_presente=%s", bool(text))
        return text

    def _persist_flow_result(self, batch_id, request_id, codice_fiscale: str, result: VisuraFlowResult) -> None:
        with SessionLocal() as db:
            batch = db.get(CatastoBatch, batch_id)
            request = db.get(CatastoVisuraRequest, request_id)
            if batch is None or request is None:
                return

            if result.captcha_image_path:
                request.captcha_image_path = str(result.captcha_image_path)

            terminal_status = classify_terminal_status(result.status)

            if terminal_status == "non_evadibile":
                attempts = request.attempts or 0
                if attempts < 3:
                    request.status = CatastoVisuraRequestStatus.PENDING.value
                    request.current_operation = f"Non evadibile (tentativo {attempts}), in coda per nuovo tentativo"
                    request.error_message = None
                    batch.current_operation = f"Non evadibile riga {request.row_index}, nuovo tentativo"
                else:
                    request.status = CatastoVisuraRequestStatus.FAILED.value
                    request.current_operation = "Non evadibile dopo 3 tentativi"
                    request.error_message = result.error_message or "Richiesta non evadibile da SISTER"
                    request.processed_at = datetime.now(timezone.utc)
                    batch.current_operation = f"Non evadibile riga {request.row_index}"
                    if request.purpose == ADE_SCAN_PURPOSE and request.target_ruolo_particella_id is not None:
                        persist_ade_status_scan_result(
                            db,
                            ruolo_particella_id=request.target_ruolo_particella_id,
                            request_id=request.id,
                            status="failed",
                            classification="non_evadibile",
                            error=result.error_message,
                        )
                request.captcha_manual_solution = None
                request.captcha_skip_requested = False
                self._log_captcha_attempt(db, request_id, result)
                self._refresh_batch_counts(db, batch)
                db.commit()
                return

            if request.purpose == ADE_SCAN_PURPOSE:
                document: CatastoDocument | None = None
                payload = result.ade_status_payload
                classification = None
                if terminal_status == "completed" and result.file_path is not None and result.file_size is not None:
                    document = self._create_document(db, request, codice_fiscale, result.file_path, result.file_size)
                    request.document_id = document.id
                    try:
                        payload = parse_historical_visura_pdf(result.file_path)
                        payload["document_id"] = str(document.id)
                        payload["document_path"] = str(result.file_path)
                    except Exception as exc:
                        logger.exception("Parsing visura storica AdE fallito per richiesta %s", request.id)
                        payload = {
                            "source": "ade_historical_synthetic_pdf",
                            "classification": "parse_failed",
                            "document_id": str(document.id),
                            "document_path": str(result.file_path),
                            "error": str(exc),
                        }
                    classification = str(payload.get("classification") or "unknown") if isinstance(payload, dict) else "unknown"
                elif isinstance(payload, dict):
                    classification = str(payload.get("classification") or "unknown")
                if request.target_ruolo_particella_id is not None:
                    persist_ade_status_scan_result(
                        db,
                        ruolo_particella_id=request.target_ruolo_particella_id,
                        request_id=request.id,
                        status=terminal_status,
                        classification=classification,
                        document_id=document.id if document is not None else None,
                        payload=payload,
                        error=result.error_message,
                    )
                request.status = (
                    CatastoVisuraRequestStatus.COMPLETED.value
                    if terminal_status in {"completed", "not_found"}
                    else CatastoVisuraRequestStatus.FAILED.value
                )
                request.current_operation = "Visura storica AdE acquisita" if request.status == "completed" else "Visura storica AdE fallita"
                request.error_message = result.error_message
                request.processed_at = datetime.now(timezone.utc)
                batch.current_operation = f"Visura storica AdE riga {request.row_index}: {classification or terminal_status}"
            elif terminal_status == "completed" and result.file_path is not None and result.file_size is not None:
                document = self._create_document(db, request, codice_fiscale, result.file_path, result.file_size)
                request.document_id = document.id
                request.status = CatastoVisuraRequestStatus.COMPLETED.value
                request.current_operation = "PDF scaricato"
                request.processed_at = datetime.now(timezone.utc)
                batch.current_operation = f"Completata riga {request.row_index}"
            elif terminal_status == "skipped":
                request.status = CatastoVisuraRequestStatus.SKIPPED.value
                request.current_operation = "Saltata"
                request.error_message = result.error_message
                request.processed_at = datetime.now(timezone.utc)
                batch.current_operation = f"Saltata riga {request.row_index}"
            elif terminal_status == "not_found":
                request.status = CatastoVisuraRequestStatus.NOT_FOUND.value
                request.current_operation = (
                    "Utente non è titolare di terreni o immobili"
                    if request.search_mode == "soggetto"
                    else "Nessuna corrispondenza"
                )
                request.error_message = result.error_message
                request.processed_at = datetime.now(timezone.utc)
                batch.current_operation = (
                    f"Utente senza titolarità catastale riga {request.row_index}"
                    if request.search_mode == "soggetto"
                    else f"Nessuna corrispondenza riga {request.row_index}"
                )
            else:
                request.status = CatastoVisuraRequestStatus.FAILED.value
                request.current_operation = "Fallita"
                request.error_message = result.error_message or "Visura flow failed"
                request.processed_at = datetime.now(timezone.utc)
                batch.current_operation = f"Fallita riga {request.row_index}"

            request.captcha_manual_solution = None
            request.captcha_skip_requested = False
            self._log_captcha_attempt(db, request_id, result)
            self._refresh_batch_counts(db, batch)
            db.commit()
        logger.info(
            "Risultato persistito per richiesta %s batch %s status=%s",
            request_id,
            batch_id,
            result.status,
        )

    def _create_document(
        self,
        db: Session,
        request: CatastoVisuraRequest,
        codice_fiscale: str,
        file_path: Path,
        file_size: int,
    ) -> CatastoDocument:
        document = CatastoDocument(
            user_id=request.user_id,
            request_id=request.id,
            search_mode=request.search_mode,
            comune=request.comune,
            foglio=request.foglio,
            particella=request.particella,
            subalterno=request.subalterno,
            catasto=request.catasto,
            tipo_visura=request.tipo_visura,
            subject_kind=request.subject_kind,
            subject_id=request.subject_id,
            request_type=request.request_type,
            intestazione=request.intestazione,
            filename=file_path.name,
            filepath=str(file_path),
            file_size=file_size,
            codice_fiscale=codice_fiscale,
        )
        db.add(document)
        db.flush()
        return document

    def _finalize_batch(self, batch_id) -> None:
        with SessionLocal() as db:
            batch = db.get(CatastoBatch, batch_id)
            if batch is None:
                return
            requests = db.scalars(
                select(CatastoVisuraRequest).where(CatastoVisuraRequest.batch_id == batch_id),
            ).all()
            self._refresh_batch_counts(db, batch)
            if all(item.status in {CatastoVisuraRequestStatus.COMPLETED.value, CatastoVisuraRequestStatus.SKIPPED.value} for item in requests):
                batch.status = CatastoBatchStatus.COMPLETED.value
            elif all(
                item.status
                in {
                    CatastoVisuraRequestStatus.COMPLETED.value,
                    CatastoVisuraRequestStatus.SKIPPED.value,
                    CatastoVisuraRequestStatus.NOT_FOUND.value,
                }
                for item in requests
            ):
                batch.status = CatastoBatchStatus.COMPLETED.value
            elif any(item.status == CatastoVisuraRequestStatus.PENDING.value for item in requests):
                batch.status = CatastoBatchStatus.PROCESSING.value
            else:
                batch.status = CatastoBatchStatus.FAILED.value if batch.failed_items else CatastoBatchStatus.COMPLETED.value
            batch.completed_at = datetime.now(timezone.utc)
            batch.current_operation = "Batch terminato"
            report_json_path, report_md_path = write_batch_report(batch, requests, self._build_batch_report_dir(batch))
            batch.report_json_path = str(report_json_path)
            batch.report_md_path = str(report_md_path)
            db.commit()

    def _refresh_batch_counts(self, db: Session, batch: CatastoBatch) -> None:
        requests = db.scalars(
            select(CatastoVisuraRequest).where(CatastoVisuraRequest.batch_id == batch.id),
        ).all()
        batch.total_items = len(requests)
        batch.completed_items = sum(1 for item in requests if item.status == CatastoVisuraRequestStatus.COMPLETED.value)
        batch.failed_items = sum(1 for item in requests if item.status == CatastoVisuraRequestStatus.FAILED.value)
        batch.skipped_items = sum(1 for item in requests if item.status == CatastoVisuraRequestStatus.SKIPPED.value)
        batch.not_found_items = sum(1 for item in requests if item.status == CatastoVisuraRequestStatus.NOT_FOUND.value)

    def _set_batch_operation(self, batch_id, operation: str) -> None:
        with SessionLocal() as db:
            batch = db.get(CatastoBatch, batch_id)
            if batch is None:
                return
            batch.current_operation = operation
            db.commit()

    def _set_request_operation(self, request_id, operation: str) -> None:
        with SessionLocal() as db:
            request = db.get(CatastoVisuraRequest, request_id)
            if request is None:
                return
            request.current_operation = operation
            db.commit()

    def _log_captcha_attempt(self, db: Session, request_id, result: VisuraFlowResult) -> None:
        if result.captcha_image_path is None:
            return
        method = result.captcha_method
        if method is None:
            method = "manual" if result.captcha_image_path.name.endswith("_manual.png") else "ocr"
        db.add(
            CatastoCaptchaLog(
                request_id=request_id,
                image_path=str(result.captcha_image_path),
                ocr_text=result.last_ocr_text if method in {"ocr", "external", "llm"} else None,
                manual_text=result.last_ocr_text if method == "manual" else None,
                is_correct=result.status == "completed",
                method=method,
            )
        )

    def _build_document_path(self, codice_fiscale: str, request: CatastoVisuraRequest) -> Path:
        if request.search_mode == "soggetto":
            kind_component = self._slugify(request.subject_kind or "SOGGETTO")
            subject_component = self._slugify(request.subject_id or "UNKNOWN")
            request_type_component = self._slugify(request.request_type or "ATTUALITA")
            filename = f"{kind_component}_{subject_component}_{request_type_component}.pdf"
            year_component = datetime.now(timezone.utc).strftime("%Y")
            return DOCUMENT_STORAGE_PATH / year_component / "soggetti" / filename

        comune_component = self._slugify(request.comune or "SCONOSCIUTO")
        year_component = datetime.now(timezone.utc).strftime("%Y")
        filename = f"{codice_fiscale}_{request.foglio}_{request.particella}"
        if request.subalterno:
            filename += f"_{request.subalterno}"
        filename += ".pdf"
        return DOCUMENT_STORAGE_PATH / year_component / comune_component / filename

    def _build_request_artifact_dir(self, batch_id, request: CatastoVisuraRequest) -> Path:
        return DEBUG_ARTIFACTS_PATH / "requests" / str(batch_id) / str(request.id)

    def _write_request_error_artifact(self, artifact_dir: Path, error: Exception) -> None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        error_path = artifact_dir / "error.txt"
        details = [
            f"timestamp={datetime.now(timezone.utc).isoformat()}",
            f"error_type={type(error).__name__}",
            f"message={str(error)}",
            "",
            traceback.format_exc(),
        ]
        error_path.write_text("\n".join(details), encoding="utf-8")

    def _build_batch_report_dir(self, batch: CatastoBatch) -> Path:
        return REPORT_STORAGE_PATH / str(batch.user_id) / str(batch.id)

    @staticmethod
    def _slugify(value: str) -> str:
        value = value.upper().strip()
        return re.sub(r"[^A-Z0-9]+", "_", value).strip("_")

    @staticmethod
    def _to_user_message(message: str) -> str:
        if "SISTER_SESSION_LOCKED" in message:
            return (
                "Utente SISTER bloccato sul portale Agenzia delle Entrate. "
                "Verificare se esiste gia' una sessione attiva su un'altra postazione o browser."
            )
        if "Utente SISTER bloccato sul portale Agenzia delle Entrate" in message:
            return (
                "Utente SISTER bloccato sul portale Agenzia delle Entrate. "
                "Verificare se esiste gia' una sessione attiva su un'altra postazione o browser."
            )
        if "gia' in sessione" in message or "già in sessione" in message or "error_locked.jsp" in message:
            return (
                "Utente SISTER bloccato sul portale Agenzia delle Entrate. "
                "Verificare se esiste gia' una sessione attiva su un'altra postazione o browser."
            )
        if "Credenziali SISTER rifiutate" in message:
            return "Le credenziali SISTER sono state rifiutate dal portale."
        return message


async def main() -> None:
    DOCUMENT_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    CAPTCHA_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    worker = CatastoWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
