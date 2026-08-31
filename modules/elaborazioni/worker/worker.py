from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from functools import partial
import logging
import os
from pathlib import Path
import re
import signal
import traceback
from typing import cast
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
from app.models.posta_online import PostaOnlineRegisteredMailSyncJob
from app.models.catasto import (
    CatastoBatch,
    CatastoBatchKind,
    CatastoBatchStatus,
    CatastoCredential,
    CatastoDistrettoExportJob,
    CatastoElaborazioniMassiveJob,
    CatastoElaborazioniMassiveJobStatus,
    CatastoConnectionTest,
    CatastoConnectionTestStatus,
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
from app.services.elaborazioni_capacitas import has_available_credential
from app.services.elaborazioni_capacitas_terreni import (
    expire_stale_terreni_sync_jobs,
    prepare_terreni_sync_jobs_for_recovery,
)
from app.services.elaborazioni_capacitas_incass import (
    expire_stale_incass_sync_jobs,
    prepare_incass_sync_jobs_for_recovery,
)
from app.services.elaborazioni_posta_online import (
    expire_stale_registered_mail_sync_jobs,
    has_available_credential as has_available_posta_online_credential,
    prepare_registered_mail_sync_jobs_for_recovery,
)
from app.services.elaborazioni_batches import (
    RELEASE_REQUESTED_MESSAGE,
    RELEASE_REQUESTED_OPERATION,
)
from app.modules.catasto.services.ade_status_scan import ADE_SCAN_PURPOSE, persist_ade_status_scan_result
from app.modules.catasto.services.ade_wfs import execute_ade_sync_run, prepare_ade_sync_runs_for_recovery
from app.modules.catasto.services.ade_historical_visura_parser import parse_historical_visura_pdf
from app.modules.catasto.services.ade_document_audit import audit_downloaded_document, expected_document_request_type
from app.modules.catasto.routes.anagrafica import (
    prepare_bulk_search_jobs_for_recovery,
    prepare_distretto_export_jobs_for_recovery,
    run_bulk_search_job_by_id,
    run_distretto_export_job_by_id,
)
from autodoc_sync import AUTODOC_SYNC_ENTITY, run_autodoc_sync_job_by_id
from anti_captcha_client import AntiCaptchaClient
from browser_session import BrowserSession, BrowserSessionConfig
from sister_credential_pool import (
    CredentialLeaseHeartbeat,
    CredentialRejectionContext,
    acquire_credential_lease,
    announce_expanded_credential_pool,
    batch_release_requested,
    credential_is_enabled_for_batch,
    credential_is_runnable,
    finalize_credential_pool,
    isolate_rejected_credential_runner,
    load_active_credential_pool,
    mark_batch_waiting_for_schedule,
    next_processable_batch_id,
    quarantine_rejected_credential,
    release_credential_lease,
    refresh_shared_credential_pool,
    run_dynamic_credential_pool,
    should_stop_credential_runner,
)
from sister_document_validation import reject_unexpected_document_type
from sister_exceptions import SisterInvalidDocumentError, SisterServerError
from sister_captcha_wait import SisterCaptchaClaim, SisterCaptchaWaitRepository
from sister_worker_reliability import (
    SisterRemoteStateUpdate,
    SisterRequestClaimCoordinator,
    SisterRequestRepository,
    SisterRequestRetryCoordinator,
    is_recoverable_credential_error,
)
from sister_observability import WorkerState, emit_pdf_parcel_status, instrument_sister_worker
from llm_captcha_solver import LLMCaptchaSolver
from credential_vault import WorkerCredentialVault
from reporting import write_batch_report
from runtime_policy import classify_terminal_status
from posta_online_sync import run_posta_online_job_by_id
from visura_flow import ManualCaptchaDecision, VisuraFlowCallbacks, VisuraFlowResult, execute_visura_flow


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
CAPTCHA_LLM_ATTEMPTS = int(os.getenv("CAPTCHA_LLM_ATTEMPTS", "10"))
CAPTCHA_EXTERNAL_ATTEMPTS = int(os.getenv("CAPTCHA_EXTERNAL_ATTEMPTS", "3"))
BETWEEN_VISURE_DELAY_SEC = int(os.getenv("BETWEEN_VISURE_DELAY_SEC", "5"))
SESSION_TIMEOUT_SEC = int(os.getenv("SESSION_TIMEOUT_SEC", "1680"))
CREDENTIAL_LOCK_COOLDOWN_SEC = int(os.getenv("ELABORAZIONI_CREDENTIAL_LOCK_COOLDOWN_SEC", "300"))
REQUEST_RETRY_DEFER_SEC = int(os.getenv("ELABORAZIONI_REQUEST_RETRY_DEFER_SEC", "45"))
MAX_REQUEST_ATTEMPTS = int(os.getenv("ELABORAZIONI_MAX_REQUEST_ATTEMPTS", "5"))
SISTER_SERVER_ERROR_BASE_COOLDOWN_SEC = int(os.getenv("ELABORAZIONI_SISTER_500_COOLDOWN_SEC", "90"))
INITIAL_REMOTE_POLL_ATTEMPTS = int(os.getenv("ELABORAZIONI_INITIAL_REMOTE_POLL_ATTEMPTS", "2"))
SISTER_SERVER_ERROR_MAX_COOLDOWN_SEC = int(os.getenv("ELABORAZIONI_SISTER_500_MAX_COOLDOWN_SEC", "300"))
SISTER_SERVER_ERROR_GLOBAL_PAUSE_SEC = int(os.getenv("ELABORAZIONI_SISTER_500_GLOBAL_PAUSE_SEC", "45"))
OPERATION_WINDOW_ENABLED = os.getenv("ELABORAZIONI_OPERATION_WINDOW_ENABLED", "false").lower() == "true"
OPERATION_WINDOW_START_HOUR = int(os.getenv("ELABORAZIONI_OPERATION_START_HOUR", "0"))
OPERATION_WINDOW_END_HOUR = int(os.getenv("ELABORAZIONI_OPERATION_END_HOUR", "23"))
OPERATION_WINDOW_TIMEZONE = os.getenv("ELABORAZIONI_OPERATION_TIMEZONE", "Europe/Rome").strip() or "Europe/Rome"
INCASS_AUTOSYNC_WINDOW_ENABLED = os.getenv("CAPACITAS_INCASS_AUTOSYNC_WINDOW_ENABLED", "true").lower() != "false"
INCASS_AUTOSYNC_START_HOUR = int(os.getenv("CAPACITAS_INCASS_AUTOSYNC_START_HOUR", "20"))
INCASS_AUTOSYNC_END_HOUR = int(os.getenv("CAPACITAS_INCASS_AUTOSYNC_END_HOUR", "6"))
INCASS_AUTOSYNC_TIMEZONE = os.getenv("CAPACITAS_INCASS_AUTOSYNC_TIMEZONE", "Europe/Rome").strip() or "Europe/Rome"
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
    "posta_online",
    "registry",
}
JOB_FAMILY_ALIASES = {
    "all": ALL_JOB_FAMILIES,
    "visure": {"connection_tests", "visure_batches", "ade_sync", "bulk_search"},
    "catasto": {"connection_tests", "visure_batches", "ade_sync", "bulk_search"},
    "runtime": {"capacitas", "registry"},
    "poste": {"posta_online"},
    "posta_online": {"posta_online"},
    "autodoc": {"autodoc"},
}

logging.basicConfig(
    level=env_value("ELABORAZIONI_LOG_LEVEL", "CATASTO_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@instrument_sister_worker
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

            if self._handles_job_family("posta_online"):
                posta_online_job_id = self._next_posta_online_job_id()
                if posta_online_job_id is not None:
                    logger.info("Job Poste Online %s prelevato dalla coda", posta_online_job_id)
                    await self._process_posta_online_job(posta_online_job_id)
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

    @staticmethod
    def _recover_visura_request(request: CatastoVisuraRequest) -> None:
        request.status = CatastoVisuraRequestStatus.PENDING.value
        request.current_operation = "Recuperato dopo riavvio worker"
        request.execution_token = None
        request.retry_not_before = None

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
                    self._recover_visura_request(request)

            history_ids: list[int] = []
            incass_ids: list[int] = []
            posta_online_ids: list[int] = []
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
            if self._handles_job_family("posta_online"):
                posta_online_ids = prepare_registered_mail_sync_jobs_for_recovery(db)
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
            if posta_online_ids:
                logger.info("Recuperati %d job Poste Online", len(posta_online_ids))
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
                jobs = db.scalars(
                    select(model)
                    .where(
                        model.status.in_(("pending", "queued_resume")),
                        model.completed_at.is_(None),
                    )
                    .order_by(model.created_at.asc())
                    .with_for_update(skip_locked=True)
                ).all()
                pending_credential_updates = False
                for job in jobs:
                    if (
                        job_kind == "incass"
                        and self._is_incass_autosync_job(job)
                        and not self._is_within_incass_autosync_window()
                    ):
                        message = (
                            "Autosync inCASS in pausa fuori finestra oraria "
                            f"{self._incass_autosync_window_label()}"
                        )
                        if job.error_detail != message:
                            job.error_detail = message
                            pending_credential_updates = True
                        continue
                    credential_id = self._capacitas_job_credential_id(job)
                    if not has_available_credential(db, credential_id):
                        message = "In attesa di una credenziale Capacitas disponibile"
                        if job.error_detail != message:
                            job.error_detail = message
                            pending_credential_updates = True
                        continue
                    job.status = "processing"
                    job.started_at = datetime.now(timezone.utc)
                    job.error_detail = None
                    db.commit()
                    return job_kind, job.id
                if pending_credential_updates:
                    db.commit()
        return None

    @staticmethod
    def _capacitas_job_credential_id(job) -> int | None:
        credential_id = getattr(job, "credential_id", None)
        payload_json = getattr(job, "payload_json", None)
        if isinstance(payload_json, dict) and payload_json.get("credential_id") is not None:
            return int(payload_json["credential_id"])
        return credential_id

    @staticmethod
    def _is_incass_autosync_job(job) -> bool:
        return getattr(job, "requested_by_user_id", None) is None

    def _next_posta_online_job_id(self) -> int | None:
        with SessionLocal() as db:
            expire_stale_registered_mail_sync_jobs(db)
            jobs = db.scalars(
                select(PostaOnlineRegisteredMailSyncJob)
                .where(
                    PostaOnlineRegisteredMailSyncJob.status.in_(("pending", "queued_resume")),
                    PostaOnlineRegisteredMailSyncJob.completed_at.is_(None),
                )
                .order_by(PostaOnlineRegisteredMailSyncJob.created_at.asc())
                .with_for_update(skip_locked=True)
            ).all()
            pending_credential_updates = False
            for job in jobs:
                credential_id = self._posta_online_job_credential_id(job)
                if job.mode != "credential_test" and not has_available_posta_online_credential(db, credential_id):
                    message = "In attesa di una credenziale Poste Online disponibile"
                    if job.error_detail != message:
                        job.error_detail = message
                        pending_credential_updates = True
                    continue
                job.status = "processing"
                job.started_at = datetime.now(timezone.utc)
                job.error_detail = None
                db.commit()
                return job.id
            if pending_credential_updates:
                db.commit()
        return None

    @staticmethod
    def _posta_online_job_credential_id(job) -> int | None:
        credential_id = getattr(job, "credential_id", None)
        payload_json = getattr(job, "payload_json", None)
        if isinstance(payload_json, dict) and payload_json.get("credential_id") is not None:
            return int(payload_json["credential_id"])
        return credential_id

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

    async def _process_posta_online_job(self, job_id: int) -> None:
        await run_posta_online_job_by_id(
            job_id=job_id,
            session_factory=SessionLocal,
            headless=HEADLESS,
        )

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
            return next_processable_batch_id(db)

    async def _process_batch(self, batch_id) -> None:
        with SessionLocal() as db:
            batch = db.get(CatastoBatch, batch_id)
            if self._batch_cannot_process(batch):
                return
            batch.current_operation = "Batch preso in carico dal worker"
            db.commit()
            credential_pool = load_active_credential_pool(db, batch)
            active_credentials = credential_pool.credentials
            if not active_credentials:
                mark_batch_waiting_for_schedule(batch, credential_pool)
                db.commit()
                return
            logger.info("Batch %s preso in carico per utente %s", batch_id, batch.user_id)

        request_repository = self._request_repository()
        request_repository.fail_unavailable_pinned_requests(batch_id, credential_pool.available_ids)
        runtime = _SisterBatchRuntime(
            self,
            batch,
            credential_pool,
            request_repository,
        )
        await runtime.run()

    @staticmethod
    def _batch_cannot_process(batch: CatastoBatch | None) -> bool:
        return batch is None or batch.status == CatastoBatchStatus.CANCELLED.value

    @staticmethod
    def _is_recoverable_credential_error(exc: Exception) -> bool:
        return is_recoverable_credential_error(exc, SisterInvalidDocumentError)

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
    def _incass_autosync_window_zone() -> ZoneInfo:
        try:
            return ZoneInfo(INCASS_AUTOSYNC_TIMEZONE)
        except Exception:
            return ZoneInfo("Europe/Rome")

    @staticmethod
    def _is_within_incass_autosync_window(now_utc: datetime | None = None) -> bool:
        if not INCASS_AUTOSYNC_WINDOW_ENABLED:
            return True
        now_utc = now_utc or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)
        local_now = now_utc.astimezone(CatastoWorker._incass_autosync_window_zone())
        current_time = local_now.time().replace(tzinfo=None)
        start_time = time(min(max(INCASS_AUTOSYNC_START_HOUR, 0), 23), 0)
        end_time = time(min(max(INCASS_AUTOSYNC_END_HOUR, 0), 23), 0)
        if start_time == end_time:
            return True
        if start_time < end_time:
            return start_time <= current_time < end_time
        return current_time >= start_time or current_time < end_time

    @staticmethod
    def _incass_autosync_window_label() -> str:
        return (
            f"{min(max(INCASS_AUTOSYNC_START_HOUR, 0), 23):02d}:00-"
            f"{min(max(INCASS_AUTOSYNC_END_HOUR, 0), 23):02d}:00 "
            f"{INCASS_AUTOSYNC_TIMEZONE}"
        )

    @staticmethod
    def _compute_sister_server_error_cooldown(consecutive_errors: int) -> int:
        if consecutive_errors <= 1:
            return SISTER_SERVER_ERROR_BASE_COOLDOWN_SEC
        cooldown = SISTER_SERVER_ERROR_BASE_COOLDOWN_SEC * (2 ** (consecutive_errors - 1))
        return min(cooldown, SISTER_SERVER_ERROR_MAX_COOLDOWN_SEC)

    def _build_browser_session(self) -> BrowserSession:
        return BrowserSession(
            BrowserSessionConfig(
                headless=HEADLESS,
                session_timeout_sec=SESSION_TIMEOUT_SEC,
                debug_pause=DEBUG_BROWSER,
                debug_artifacts_path=DEBUG_ARTIFACTS_PATH,
            )
        )

    def _request_repository(self) -> SisterRequestRepository:
        return SisterRequestRepository(
            session_factory=SessionLocal,
            refresh_batch_counts=self._refresh_batch_counts,
            persist_ade_status=persist_ade_status_scan_result,
            parse_historical_pdf=parse_historical_visura_pdf,
            classify_terminal_status=classify_terminal_status,
            to_user_message=self._to_user_message,
            artifact_root=DEBUG_ARTIFACTS_PATH,
            document_root=DOCUMENT_STORAGE_PATH,
            ade_scan_purpose=ADE_SCAN_PURPOSE,
            release_requested_message=RELEASE_REQUESTED_MESSAGE,
            release_requested_operation=RELEASE_REQUESTED_OPERATION,
            max_attempts=MAX_REQUEST_ATTEMPTS,
            retry_defer_seconds=REQUEST_RETRY_DEFER_SEC,
        )

    @staticmethod
    def _captcha_wait_repository() -> SisterCaptchaWaitRepository:
        return SisterCaptchaWaitRepository(SessionLocal)

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
        repository = self._request_repository()
        prepared = repository.prepare_execution(batch_id, request_id)
        if prepared is None:
            return
        request_snapshot = prepared.request
        execution_token = prepared.execution_token
        self._log_request_start(batch_id, request_snapshot)
        repository.set_operation(request_id, "Autenticazione sessione SISTER", execution_token)
        await browser.ensure_authenticated(
            credential.sister_username,
            self.vault.decrypt(credential.sister_password_encrypted),
        )
        repository.set_operation(request_id, "Apertura form SISTER", execution_token)
        repository.set_operation(request_id, "Esecuzione flusso visura", execution_token)
        result = await execute_visura_flow(
            browser=browser,
            request=request_snapshot,
            document_path=repository.build_document_path(credential.sister_username, request_snapshot),
            captcha_dir=CAPTCHA_STORAGE_PATH / str(batch_id),
            get_manual_captcha_decision=lambda image_path: self._wait_for_manual_captcha(
                SisterCaptchaClaim(batch_id, request_id, execution_token),
                image_path,
            ),
            solve_llm_captcha=self._solve_llm_captcha if self.llm_captcha_solver is not None else None,
            solve_external_captcha=self._solve_external_captcha if self.anti_captcha_client is not None else None,
            max_llm_attempts=CAPTCHA_LLM_ATTEMPTS,
            max_external_attempts=CAPTCHA_EXTERNAL_ATTEMPTS,
            initial_remote_poll_attempts=INITIAL_REMOTE_POLL_ATTEMPTS if INITIAL_REMOTE_POLL_ATTEMPTS > 0 else None,
            callbacks=VisuraFlowCallbacks(
                update_operation=lambda operation: repository.set_operation(request_id, operation, execution_token),
                update_remote_state=lambda remote_id, remote_url, state: repository.set_remote_state(
                    request_id,
                    execution_token,
                    SisterRemoteStateUpdate(remote_id, remote_url, state, credential.id),
                ),
                update_correlation_baseline=lambda keys: repository.set_correlation_baseline(
                    request_id,
                    execution_token,
                    keys,
                ),
            ),
        )
        logger.info(
            "Richiesta %s completata con status=%s errore=%s",
            request_id,
            result.status,
            result.error_message,
        )
        result.document_audit_payload = audit_downloaded_document(request_snapshot, result)
        emit_pdf_parcel_status(browser, result.document_audit_payload)
        reject_unexpected_document_type(result)
        if request_snapshot.artifact_dir:
            if result.status == "not_found" and request_snapshot.search_mode == "soggetto":
                await browser.capture_subject_not_found_preview(Path(request_snapshot.artifact_dir))
            await browser.capture_debug_snapshot(Path(request_snapshot.artifact_dir), f"final-{result.status}")
        repository.persist_flow_result(
            batch_id, request_id, credential.sister_username, result, execution_token
        )

    @staticmethod
    def _log_request_start(batch_id, request: CatastoVisuraRequest) -> None:
        logger.info(
            "Elaborazione richiesta %s del batch %s riga=%s mode=%s comune=%s foglio=%s particella=%s "
            "subject_id=%s tipo_visura=%s request_type=%s",
            request.id,
            batch_id,
            request.row_index,
            request.search_mode,
            request.comune,
            request.foglio,
            request.particella,
            request.subject_id,
            getattr(request, "tipo_visura", None),
            expected_document_request_type(
                getattr(request, "request_type", None),
                getattr(request, "tipo_visura", None),
            ),
        )

    async def _wait_for_manual_captcha(
        self,
        claim: SisterCaptchaClaim,
        image_path: Path,
    ) -> ManualCaptchaDecision:
        deadline = datetime.now(timezone.utc) + timedelta(seconds=CAPTCHA_MANUAL_TIMEOUT_SEC)
        logger.info("Richiesta %s in attesa di CAPTCHA manuale fino a %s", claim.request_id, deadline.isoformat())

        repository = self._captcha_wait_repository()
        if not repository.begin(claim.batch_id, claim.request_id, claim.execution_token, image_path, deadline):
            logger.info("Richiesta %s non piu attiva prima dell'attesa CAPTCHA", claim.request_id)
            return ManualCaptchaDecision(text=None, skip=True)

        while datetime.now(timezone.utc) < deadline and not self.state.stop_requested:
            wait_state = repository.state(claim.batch_id, claim.request_id, claim.execution_token)
            if not wait_state.active:
                logger.info("Richiesta %s non piu attiva durante l'attesa CAPTCHA", claim.request_id)
                return ManualCaptchaDecision(text=None, skip=True)
            if wait_state.skip_requested:
                logger.info("Richiesta %s CAPTCHA manuale saltato dall'utente", claim.request_id)
                return ManualCaptchaDecision(text=None, skip=True)
            if wait_state.solution:
                logger.info("Richiesta %s CAPTCHA manuale ricevuto", claim.request_id)
                return ManualCaptchaDecision(text=wait_state.solution)
            await asyncio.sleep(2)

        logger.warning("Richiesta %s timeout CAPTCHA manuale", claim.request_id)
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

    def _persist_flow_result(
        self,
        batch_id,
        request_id,
        codice_fiscale: str,
        result: VisuraFlowResult,
    ) -> None:
        self._request_repository().persist_flow_result(batch_id, request_id, codice_fiscale, result)

    def _finalize_batch(self, batch_id) -> None:
        with SessionLocal() as db:
            batch = db.get(CatastoBatch, batch_id)
            if self._batch_cannot_process(batch):
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


@dataclass
class _CredentialRuntimeSession:
    browser: BrowserSession | None = None
    lease_acquired: bool = False
    lease_heartbeat: CredentialLeaseHeartbeat | None = None


class _SisterBatchRuntime:
    def __init__(
        self,
        worker: CatastoWorker,
        batch: CatastoBatch,
        credential_pool,
        request_repository: SisterRequestRepository,
    ) -> None:
        self.worker = worker
        self.batch = batch
        self.batch_id = batch.id
        self.credential_pool = credential_pool
        self.request_repository = request_repository
        self.shared_state_lock = asyncio.Lock()
        self.deferred_requests: dict[UUID, datetime] = {}
        self.credential_cooldowns: dict[UUID, datetime] = {}
        self.credential_server_error_counts: dict[UUID, int] = {}
        self.global_server_error_pause_until: datetime | None = None
        self.retry_coordinator = SisterRequestRetryCoordinator(
            self.shared_state_lock,
            self.deferred_requests,
            request_repository.reset_for_retry,
            REQUEST_RETRY_DEFER_SEC,
        )
        self.claim_coordinator = SisterRequestClaimCoordinator(
            asyncio.Lock(),
            self.shared_state_lock,
            self.deferred_requests,
            set(),
        )

    async def run(self) -> None:
        active_credentials = self.credential_pool.credentials
        pool_label = (
            f"Avvio autosync ruolo con credenziale {active_credentials[0].sister_username}"
            if len(active_credentials) == 1
            and self.batch.batch_kind == CatastoBatchKind.RUOLO_AUTOSYNC.value
            else f"Avvio pool visure con {len(active_credentials)} credenziali"
        )
        self.worker._set_batch_operation(self.batch_id, pool_label)
        try:
            await run_dynamic_credential_pool(
                active_credentials,
                lambda credential: isolate_rejected_credential_runner(
                    self._credential_runner(credential)
                ),
                partial(
                    refresh_shared_credential_pool,
                    SessionLocal,
                    self.batch_id,
                    self.credential_pool,
                ),
                lambda: self.worker._batch_has_open_requests(self.batch_id),
                partial(
                    announce_expanded_credential_pool,
                    self.credential_pool,
                    self.batch_id,
                    self.request_repository,
                    self.worker._set_batch_operation,
                ),
                POLL_INTERVAL_SEC,
            )
            finalize_credential_pool(
                self.credential_pool,
                self.batch_id,
                self.worker._batch_has_open_requests(self.batch_id),
                SessionLocal,
                self.worker._finalize_batch,
            )
        except Exception as exc:
            logger.exception("Batch %s fallito prima del completamento", self.batch_id)
            self.worker._request_repository().fail_batch(self.batch_id, str(exc))

    async def _credential_runner(self, credential: CatastoCredential) -> None:
        session = _CredentialRuntimeSession()
        try:
            while not self.worker.state.stop_requested:
                readiness = await self._prepare_session(credential, session)
                if readiness == "stop":
                    return
                if readiness == "wait":
                    continue
                if await self._wait_for_runtime_window(credential):
                    continue
                outcome = await self._process_next_request(credential, session)
                if outcome == "stop":
                    return
        finally:
            await self._close_session(credential, session)

    async def _prepare_session(
        self,
        credential: CatastoCredential,
        session: _CredentialRuntimeSession,
    ) -> str:
        if session.lease_heartbeat is not None and session.lease_heartbeat.lost.is_set():
            await self._discard_lost_lease(session)
        if not credential_is_runnable(SessionLocal, credential.id, self.batch_id):
            await self._close_session(credential, session)
            if not credential_is_enabled_for_batch(SessionLocal, credential.id, self.batch_id):
                return "stop"
            self.worker._set_batch_operation(
                self.batch_id,
                f"Credenziale {credential.sister_username} fuori fascia, in attesa",
            )
            await asyncio.sleep(min(POLL_INTERVAL_SEC, 60))
            return "wait"
        if not session.lease_acquired and not self._acquire_lease(credential, session):
            await asyncio.sleep(POLL_INTERVAL_SEC)
            return "wait"
        if session.browser is None:
            session.browser = self.worker._build_browser_session()
            await session.browser.start()
        if self._should_stop(credential):
            return "stop"
        return "ready"

    def _acquire_lease(
        self,
        credential: CatastoCredential,
        session: _CredentialRuntimeSession,
    ) -> bool:
        if not acquire_credential_lease(SessionLocal, credential, self.batch_id):
            self.worker._set_batch_operation(
                self.batch_id,
                f"Credenziale {credential.sister_username} gia in uso, in attesa",
            )
            return False
        session.lease_acquired = True
        session.lease_heartbeat = CredentialLeaseHeartbeat(
            SessionLocal,
            credential,
            self.batch_id,
        )
        session.lease_heartbeat.start()
        return True

    async def _discard_lost_lease(self, session: _CredentialRuntimeSession) -> None:
        browser = cast(BrowserSession, session.browser)
        with contextlib.suppress(Exception):
            await browser.logout()
        await browser.stop()
        session.browser = None
        session.lease_acquired = False
        session.lease_heartbeat = None

    async def _close_session(
        self,
        credential: CatastoCredential,
        session: _CredentialRuntimeSession,
    ) -> None:
        if session.browser is not None:
            with contextlib.suppress(Exception):
                await session.browser.logout()
            await session.browser.stop()
            session.browser = None
        if session.lease_acquired:
            await cast(CredentialLeaseHeartbeat, session.lease_heartbeat).stop()
            release_credential_lease(SessionLocal, credential, self.batch_id)
            session.lease_acquired = False
            session.lease_heartbeat = None

    def _should_stop(self, credential: CatastoCredential) -> bool:
        return should_stop_credential_runner(
            self.worker.state.stop_requested,
            self.batch_id,
            credential.sister_username,
            lambda: batch_release_requested(SessionLocal, self.batch_id),
            lambda: self._credential_release_requested(credential.id),
        )

    def _credential_release_requested(self, credential_id: UUID) -> bool:
        if credential_is_enabled_for_batch(SessionLocal, credential_id, self.batch_id):
            return False
        self.credential_pool.reject(credential_id)
        self.request_repository.fail_unavailable_pinned_requests(
            self.batch_id,
            self.credential_pool.available_ids,
        )
        return True

    async def _wait_for_runtime_window(self, credential: CatastoCredential) -> bool:
        now = datetime.now(timezone.utc)
        if not self.worker._is_within_operating_window(now):
            await self._wait_for_operating_window(now)
            return True
        async with self.shared_state_lock:
            cooldown_until = self.credential_cooldowns.get(credential.id)
            global_pause_until = self.global_server_error_pause_until
        if global_pause_until is not None and global_pause_until > now:
            await self._wait_for_global_pause(global_pause_until, now)
            return True
        if cooldown_until is not None and cooldown_until > now:
            await self._wait_for_credential_cooldown(credential, cooldown_until, now)
            return True
        return False

    async def _wait_for_operating_window(self, now: datetime) -> None:
        resume_at = self.worker._next_operating_resume_at(now)
        wait_seconds = (
            max(int((resume_at - now).total_seconds()), 1)
            if resume_at is not None
            else 60
        )
        resume_label = (
            resume_at.astimezone(self.worker._operation_window_zone()).strftime("%H:%M")
            if resume_at is not None
            else "n/d"
        )
        self.worker._set_batch_operation(
            self.batch_id,
            f"Batch in pausa fuori finestra operativa, ripresa automatica alle {resume_label}",
        )
        await asyncio.sleep(min(wait_seconds, 60))

    async def _wait_for_global_pause(self, pause_until: datetime, now: datetime) -> None:
        wait_seconds = max(int((pause_until - now).total_seconds()), 1)
        self.worker._set_batch_operation(
            self.batch_id,
            f"Portale SISTER instabile, pausa globale {wait_seconds}s prima della ripresa",
        )
        await asyncio.sleep(wait_seconds)

    async def _wait_for_credential_cooldown(
        self,
        credential: CatastoCredential,
        cooldown_until: datetime,
        now: datetime,
    ) -> None:
        wait_seconds = max(int((cooldown_until - now).total_seconds()), 1)
        self.worker._set_batch_operation(
            self.batch_id,
            f"Credenziale {credential.sister_username} in cooldown, attesa {wait_seconds}s",
        )
        await asyncio.sleep(wait_seconds)

    async def _process_next_request(
        self,
        credential: CatastoCredential,
        session: _CredentialRuntimeSession,
    ) -> str:
        selection = await self.claim_coordinator.claim_next(
            self.request_repository,
            self.batch_id,
            credential.id,
        )
        request_id = selection.request_id
        if request_id is None:
            return await self._handle_empty_claim(selection)
        try:
            await self._execute_claimed_request(credential, session, selection)
        finally:
            await self.claim_coordinator.release(request_id)
        if self._should_stop(credential):
            return "stop"
        await asyncio.sleep(BETWEEN_VISURE_DELAY_SEC)
        return "continue"

    async def _handle_empty_claim(self, selection) -> str:
        if not self.worker._batch_has_open_requests(self.batch_id):
            return "stop"
        if selection.wait_reason == "WAIT":
            self.worker._set_batch_operation(
                self.batch_id,
                "In attesa di input CAPTCHA manuale",
            )
        elif selection.wait_reason == "RETRY_LATER":
            wait_seconds = selection.resolved_wait_seconds(await self._next_wait_seconds())
            self.worker._set_batch_operation(
                self.batch_id,
                f"Richieste differite, attesa {wait_seconds}s",
            )
            await asyncio.sleep(wait_seconds)
            return "continue"
        await asyncio.sleep(2)
        return "continue"

    async def _execute_claimed_request(
        self,
        credential: CatastoCredential,
        session: _CredentialRuntimeSession,
        selection,
    ) -> None:
        request_id = selection.request_id
        try:
            await self.worker._process_request(
                cast(BrowserSession, session.browser),
                credential,
                self.batch_id,
                request_id,
            )
        except SisterServerError as exc:
            await self._handle_sister_server_error(credential, session, selection, exc)
        except Exception as exc:
            await self._handle_request_error(credential, session, selection, exc)
        else:
            async with self.shared_state_lock:
                self.credential_server_error_counts[credential.id] = 0

    async def _handle_sister_server_error(
        self,
        credential: CatastoCredential,
        session: _CredentialRuntimeSession,
        selection,
        exc: SisterServerError,
    ) -> None:
        cooldown_seconds, opened_global_pause = await self._register_server_error(
            credential,
            selection.request_id,
            exc,
        )
        message = (
            "Portale SISTER temporaneamente non disponibile, richiesta rimessa in coda"
            if opened_global_pause
            else f"Errore SISTER 500 su {credential.sister_username}, retry differito"
        )
        await self.retry_coordinator.defer(
            selection.request_id,
            selection.execution_token,
            max(REQUEST_RETRY_DEFER_SEC, cooldown_seconds),
            message,
            "sister_server_error",
        )
        session.browser = await self._restart_browser(cast(BrowserSession, session.browser))
        await asyncio.sleep(5)

    async def _handle_request_error(
        self,
        credential: CatastoCredential,
        session: _CredentialRuntimeSession,
        selection,
        exc: Exception,
    ) -> None:
        context = CredentialRejectionContext(
            self.credential_pool,
            credential,
            self.batch_id,
            selection.request_id,
            selection.execution_token,
            self.request_repository,
            self.worker._set_batch_operation,
        )
        quarantine_rejected_credential(exc, context)
        if self.worker._is_recoverable_credential_error(exc):
            await self._defer_recoverable_error(credential, selection, exc)
        else:
            await self._fail_terminal_request(credential, session, selection, exc)
        session.browser = await self._restart_browser(cast(BrowserSession, session.browser))

    async def _defer_recoverable_error(
        self,
        credential: CatastoCredential,
        selection,
        exc: Exception,
    ) -> None:
        async with self.shared_state_lock:
            self.credential_server_error_counts[credential.id] = 0
            self.global_server_error_pause_until = None
            self.credential_cooldowns[credential.id] = datetime.now(timezone.utc) + timedelta(
                seconds=CREDENTIAL_LOCK_COOLDOWN_SEC
            )
        logger.warning(
            "Batch %s richiesta %s differita per errore recuperabile con %s: %s",
            self.batch_id,
            selection.request_id,
            credential.sister_username,
            exc,
        )
        await self.retry_coordinator.defer_recoverable(
            selection.request_id,
            selection.execution_token,
            exc,
            credential.sister_username,
        )

    async def _fail_terminal_request(
        self,
        credential: CatastoCredential,
        session: _CredentialRuntimeSession,
        selection,
        exc: Exception,
    ) -> None:
        async with self.shared_state_lock:
            self.credential_server_error_counts[credential.id] = 0
        logger.exception(
            "Batch %s richiesta %s fallita su %s, isolamento errore e prosecuzione batch",
            self.batch_id,
            selection.request_id,
            credential.sister_username,
        )
        await self._capture_terminal_error(
            cast(BrowserSession, session.browser),
            selection.request_id,
            exc,
        )
        self.request_repository.fail_request(
            self.batch_id,
            selection.request_id,
            str(exc),
            selection.execution_token,
        )

    async def _capture_terminal_error(
        self,
        browser: BrowserSession,
        request_id: UUID,
        exc: Exception,
    ) -> None:
        with SessionLocal() as db:
            request = db.get(CatastoVisuraRequest, request_id)
            if request is None or not request.artifact_dir:
                return
            artifact_dir = Path(request.artifact_dir)
            self.worker._write_request_error_artifact(artifact_dir, exc)
            with contextlib.suppress(Exception):
                await browser.capture_debug_snapshot(artifact_dir, "final-failed")

    async def _register_server_error(
        self,
        credential: CatastoCredential,
        request_id: UUID,
        exc: SisterServerError,
    ) -> tuple[int, bool]:
        now = datetime.now(timezone.utc)
        async with self.shared_state_lock:
            consecutive_errors = self.credential_server_error_counts.get(credential.id, 0) + 1
            self.credential_server_error_counts[credential.id] = consecutive_errors
            cooldown_seconds = self.worker._compute_sister_server_error_cooldown(consecutive_errors)
            self.credential_cooldowns[credential.id] = now + timedelta(seconds=cooldown_seconds)
            opened_global_pause = self._all_credentials_in_cooldown(now)
            if opened_global_pause:
                self.global_server_error_pause_until = now + timedelta(
                    seconds=SISTER_SERVER_ERROR_GLOBAL_PAUSE_SEC
                )
        logger.warning(
            "Batch %s richiesta %s differita per errore 500 SISTER con %s: consecutive_errors=%s cooldown=%ss global_pause=%s detail=%s",
            self.batch_id,
            request_id,
            credential.sister_username,
            consecutive_errors,
            cooldown_seconds,
            opened_global_pause,
            exc,
        )
        return cooldown_seconds, opened_global_pause

    def _all_credentials_in_cooldown(self, now: datetime) -> bool:
        return all(
            (self.credential_cooldowns.get(credential.id) or now) > now
            for credential in self.credential_pool.credentials
        )

    async def _next_wait_seconds(self) -> int:
        now = datetime.now(timezone.utc)
        async with self.shared_state_lock:
            candidates = [
                value
                for value in (
                    *self.deferred_requests.values(),
                    *self.credential_cooldowns.values(),
                )
                if value > now
            ]
        if not candidates:
            return 2
        return max(int((min(candidates) - now).total_seconds()), 1)

    async def _restart_browser(self, browser: BrowserSession) -> BrowserSession:
        with contextlib.suppress(Exception):
            await browser.logout()
        with contextlib.suppress(Exception):
            await browser.stop()
        browser = self.worker._build_browser_session()
        await browser.start()
        return browser


async def main() -> None:
    DOCUMENT_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    CAPTCHA_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    worker = CatastoWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
