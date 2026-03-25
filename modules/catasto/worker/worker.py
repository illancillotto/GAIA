from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
import re
import signal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.catasto import (
    CatastoBatch,
    CatastoBatchStatus,
    CatastoCaptchaLog,
    CatastoCredential,
    CatastoConnectionTest,
    CatastoConnectionTestStatus,
    CatastoDocument,
    CatastoVisuraRequest,
    CatastoVisuraRequestStatus,
)
from browser_session import BrowserSession, BrowserSessionConfig
from captcha_solver import CaptchaSolver
from credential_vault import WorkerCredentialVault
from visura_flow import ManualCaptchaDecision, VisuraFlowResult, execute_visura_flow


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://naap_app:change_me@postgres:5432/naap")
CREDENTIAL_MASTER_KEY = os.environ["CREDENTIAL_MASTER_KEY"]
POLL_INTERVAL_SEC = int(os.getenv("CATASTO_POLL_INTERVAL_SEC", "3"))
CAPTCHA_MAX_OCR_ATTEMPTS = int(os.getenv("CAPTCHA_MAX_OCR_ATTEMPTS", "3"))
CAPTCHA_MANUAL_TIMEOUT_SEC = int(os.getenv("CAPTCHA_MANUAL_TIMEOUT_SEC", "300"))
BETWEEN_VISURE_DELAY_SEC = int(os.getenv("BETWEEN_VISURE_DELAY_SEC", "5"))
SESSION_TIMEOUT_SEC = int(os.getenv("SESSION_TIMEOUT_SEC", "1680"))
DOCUMENT_STORAGE_PATH = Path(os.getenv("CATASTO_DOCUMENT_STORAGE_PATH", "/data/catasto/documents"))
CAPTCHA_STORAGE_PATH = Path(os.getenv("CATASTO_CAPTCHA_STORAGE_PATH", "/data/catasto/captcha"))
DEBUG_ARTIFACTS_PATH = Path(os.getenv("CATASTO_DEBUG_ARTIFACTS_PATH", "/data/catasto/debug"))
HEADLESS = os.getenv("CATASTO_HEADLESS", "true").lower() != "false"
DEBUG_BROWSER = os.getenv("CATASTO_DEBUG_BROWSER", "false").lower() == "true"

logging.basicConfig(
    level=os.getenv("CATASTO_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@dataclass(slots=True)
class WorkerState:
    stop_requested: bool = False


class CatastoWorker:
    def __init__(self) -> None:
        self.state = WorkerState()
        self.vault = WorkerCredentialVault(CREDENTIAL_MASTER_KEY)
        self.captcha_solver = CaptchaSolver()
        DEBUG_ARTIFACTS_PATH.mkdir(parents=True, exist_ok=True)

    async def run(self) -> None:
        self._install_signal_handlers()
        self._recover_stuck_requests()
        logger.info("Worker Catasto avviato")

        while not self.state.stop_requested:
            connection_test_id = self._next_connection_test_id()
            if connection_test_id is not None:
                logger.info("Elaborazione test connessione SISTER %s", connection_test_id)
                await self._process_connection_test(connection_test_id)
                continue

            batch_id = self._next_batch_id()
            if batch_id is None:
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue
            logger.info("Batch %s prelevato dalla coda di lavorazione", batch_id)
            await self._process_batch(batch_id)

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for signame in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(signame, self._request_stop)

    def _request_stop(self) -> None:
        self.state.stop_requested = True

    def _recover_stuck_requests(self) -> None:
        with SessionLocal() as db:
            stuck_connection_tests = db.scalars(
                select(CatastoConnectionTest).where(
                    CatastoConnectionTest.status == CatastoConnectionTestStatus.PROCESSING.value,
                )
            ).all()
            for connection_test in stuck_connection_tests:
                connection_test.status = CatastoConnectionTestStatus.PENDING.value
                connection_test.message = "Recuperato dopo riavvio worker"

            stuck_requests = db.scalars(
                select(CatastoVisuraRequest).where(
                    CatastoVisuraRequest.status == CatastoVisuraRequestStatus.PROCESSING.value,
                )
            ).all()
            for request in stuck_requests:
                request.status = CatastoVisuraRequestStatus.PENDING.value
                request.current_operation = "Recuperato dopo riavvio worker"
            db.commit()

    def _next_connection_test_id(self):
        with SessionLocal() as db:
            connection_test = db.scalar(
                select(CatastoConnectionTest)
                .where(CatastoConnectionTest.status == CatastoConnectionTestStatus.PENDING.value)
                .order_by(CatastoConnectionTest.created_at.asc())
            )
            return connection_test.id if connection_test is not None else None

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
            credential = db.scalar(select(CatastoCredential).where(CatastoCredential.user_id == batch.user_id))
            if credential is None:
                batch.status = CatastoBatchStatus.FAILED.value
                batch.current_operation = "Credenziali SISTER mancanti"
                db.commit()
                return
            password = self.vault.decrypt(credential.sister_password_encrypted)
            logger.info("Batch %s preso in carico per utente %s", batch_id, batch.user_id)

        browser = BrowserSession(
            BrowserSessionConfig(
                headless=HEADLESS,
                session_timeout_sec=SESSION_TIMEOUT_SEC,
                debug_pause=DEBUG_BROWSER,
                debug_artifacts_path=DEBUG_ARTIFACTS_PATH,
            )
        )
        await browser.start()
        try:
            self._set_batch_operation(batch_id, "Autenticazione SISTER in corso")
            logger.info("Batch %s autenticazione SISTER in corso", batch_id)
            await browser.ensure_authenticated(credential.sister_username, password)
            self._set_batch_operation(batch_id, "Autenticazione SISTER completata")
            logger.info("Batch %s autenticato su SISTER", batch_id)
            while not self.state.stop_requested:
                next_request = self._next_request_id(batch_id)
                if next_request == "WAIT":
                    self._set_batch_operation(batch_id, "In attesa di input CAPTCHA manuale")
                    logger.info("Batch %s in attesa di input CAPTCHA manuale", batch_id)
                    await asyncio.sleep(2)
                    continue
                if next_request is None:
                    self._finalize_batch(batch_id)
                    return
                await self._process_request(browser, credential, batch_id, next_request)
                if self.state.stop_requested:
                    return
                await asyncio.sleep(BETWEEN_VISURE_DELAY_SEC)
        except Exception as exc:
            logger.exception("Batch %s fallito prima del completamento", batch_id)
            self._fail_batch(batch_id, str(exc))
        finally:
            await browser.stop()

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

    def _next_request_id(self, batch_id):
        with SessionLocal() as db:
            requests = db.scalars(
                select(CatastoVisuraRequest)
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
                .order_by(CatastoVisuraRequest.row_index.asc())
            ).all()

            for request in requests:
                if request.status in {
                    CatastoVisuraRequestStatus.PENDING.value,
                    CatastoVisuraRequestStatus.PROCESSING.value,
                }:
                    return request.id
                if request.status == CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value:
                    if request.captcha_skip_requested or request.captcha_manual_solution:
                        return request.id
                    if request.captcha_expires_at and request.captcha_expires_at <= datetime.now(timezone.utc):
                        return request.id

            if any(request.status == CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value for request in requests):
                return "WAIT"
            return None

    async def _process_request(self, browser: BrowserSession, credential: CatastoCredential, batch_id, request_id) -> None:
        with SessionLocal() as db:
            request = db.get(CatastoVisuraRequest, request_id)
            batch = db.get(CatastoBatch, batch_id)
            if request is None or batch is None:
                return
            logger.info(
                "Elaborazione richiesta %s del batch %s riga=%s comune=%s foglio=%s particella=%s",
                request_id,
                batch_id,
                request.row_index,
                request.comune,
                request.foglio,
                request.particella,
            )

            if request.status == CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value and request.captcha_manual_solution:
                request.status = CatastoVisuraRequestStatus.PROCESSING.value
                request.current_operation = "Ripresa con CAPTCHA manuale"
            elif (
                request.status == CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value
                and request.captcha_expires_at
                and request.captcha_expires_at <= datetime.now(timezone.utc)
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
            db.commit()

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

        result = await execute_visura_flow(
            browser=browser,
            request=request,
            document_path=self._build_document_path(credential.sister_username, request),
            captcha_dir=CAPTCHA_STORAGE_PATH / str(batch_id),
            captcha_solver=self.captcha_solver,
            max_ocr_attempts=CAPTCHA_MAX_OCR_ATTEMPTS,
            get_manual_captcha_decision=lambda image_path: self._wait_for_manual_captcha(batch_id, request_id, image_path),
            update_operation=lambda operation: self._set_request_operation(request_id, operation),
        )
        logger.info(
            "Richiesta %s completata con status=%s errore=%s",
            request_id,
            result.status,
            result.error_message,
        )
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

    def _persist_flow_result(self, batch_id, request_id, codice_fiscale: str, result: VisuraFlowResult) -> None:
        with SessionLocal() as db:
            batch = db.get(CatastoBatch, batch_id)
            request = db.get(CatastoVisuraRequest, request_id)
            if batch is None or request is None:
                return

            if result.captcha_image_path:
                request.captcha_image_path = str(result.captcha_image_path)

            if result.status == "completed" and result.file_path is not None and result.file_size is not None:
                document = CatastoDocument(
                    user_id=request.user_id,
                    request_id=request.id,
                    comune=request.comune,
                    foglio=request.foglio,
                    particella=request.particella,
                    subalterno=request.subalterno,
                    catasto=request.catasto,
                    tipo_visura=request.tipo_visura,
                    filename=result.file_path.name,
                    filepath=str(result.file_path),
                    file_size=result.file_size,
                    codice_fiscale=codice_fiscale,
                )
                db.add(document)
                db.flush()
                request.document_id = document.id
                request.status = CatastoVisuraRequestStatus.COMPLETED.value
                request.current_operation = "PDF scaricato"
                request.processed_at = datetime.now(timezone.utc)
                batch.current_operation = f"Completata riga {request.row_index}"
            elif result.status == "skipped":
                request.status = CatastoVisuraRequestStatus.SKIPPED.value
                request.current_operation = "Saltata"
                request.error_message = result.error_message
                request.processed_at = datetime.now(timezone.utc)
                batch.current_operation = f"Saltata riga {request.row_index}"
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
            elif any(item.status == CatastoVisuraRequestStatus.PENDING.value for item in requests):
                batch.status = CatastoBatchStatus.PROCESSING.value
            else:
                batch.status = CatastoBatchStatus.FAILED.value if batch.failed_items else CatastoBatchStatus.COMPLETED.value
            batch.completed_at = datetime.now(timezone.utc)
            batch.current_operation = "Batch terminato"
            db.commit()

    def _refresh_batch_counts(self, db: Session, batch: CatastoBatch) -> None:
        requests = db.scalars(
            select(CatastoVisuraRequest).where(CatastoVisuraRequest.batch_id == batch.id),
        ).all()
        batch.total_items = len(requests)
        batch.completed_items = sum(1 for item in requests if item.status == CatastoVisuraRequestStatus.COMPLETED.value)
        batch.failed_items = sum(1 for item in requests if item.status == CatastoVisuraRequestStatus.FAILED.value)
        batch.skipped_items = sum(1 for item in requests if item.status == CatastoVisuraRequestStatus.SKIPPED.value)

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
        method = "manual" if result.captcha_image_path.name.endswith("_manual.png") else "ocr"
        db.add(
            CatastoCaptchaLog(
                request_id=request_id,
                image_path=str(result.captcha_image_path),
                ocr_text=result.last_ocr_text if method == "ocr" else None,
                manual_text=result.last_ocr_text if method == "manual" else None,
                is_correct=result.status == "completed",
                method=method,
            )
        )

    def _build_document_path(self, codice_fiscale: str, request: CatastoVisuraRequest) -> Path:
        comune_component = self._slugify(request.comune)
        year_component = datetime.now(timezone.utc).strftime("%Y")
        filename = f"{codice_fiscale}_{request.foglio}_{request.particella}"
        if request.subalterno:
            filename += f"_{request.subalterno}"
        filename += ".pdf"
        return DOCUMENT_STORAGE_PATH / year_component / comune_component / filename

    @staticmethod
    def _slugify(value: str) -> str:
        value = value.upper().strip()
        return re.sub(r"[^A-Z0-9]+", "_", value).strip("_")

    @staticmethod
    def _to_user_message(message: str) -> str:
        if "Utente SISTER bloccato sul portale Agenzia delle Entrate" in message:
            return (
                "Utente SISTER bloccato sul portale Agenzia delle Entrate. "
                "Verificare se esiste gia' una sessione attiva su un'altra postazione o browser. "
                "indirizzo link: https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp"
            )
        if "gia' in sessione" in message or "già in sessione" in message or "error_locked.jsp" in message:
            return (
                "Utente SISTER bloccato sul portale Agenzia delle Entrate. "
                "Verificare se esiste gia' una sessione attiva su un'altra postazione o browser. "
                "indirizzo link: https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp"
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
