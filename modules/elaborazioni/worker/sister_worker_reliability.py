from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
from typing import Any, Callable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catasto import (
    CatastoBatch,
    CatastoBatchStatus,
    CatastoCaptchaLog,
    CatastoDocument,
    CatastoVisuraRequest,
    CatastoVisuraRequestStatus,
)
from sister_exceptions import SisterRequestCorrelationError
from sister_worker_files import build_document_path, build_request_artifact_dir, document_values, sha256_file


logger = logging.getLogger(__name__)

ResetRequestCallback = Callable[[UUID, str, datetime | None, str | None, UUID | None], None]
SessionFactory = Callable[[], Session]
RefreshBatchCounts = Callable[[Session, CatastoBatch], None]
PersistAdeStatus = Callable[..., object]
ParseHistoricalPdf = Callable[[Path], dict[str, Any]]
ClassifyTerminalStatus = Callable[[str], str]

ACTIVE_REQUEST_STATUSES = frozenset(
    {
        CatastoVisuraRequestStatus.PROCESSING.value,
        CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value,
    }
)
OPEN_REQUEST_STATUSES = frozenset(
    {
        CatastoVisuraRequestStatus.PENDING.value,
        *ACTIVE_REQUEST_STATUSES,
    }
)
ACTIVE_REMOTE_STATES = frozenset({"submitted", "pending", "ready"})


@dataclass(slots=True)
class ClaimedRequestSelection:
    request_id: UUID | None
    wait_reason: str | None = None
    wait_seconds: int | None = None
    execution_token: UUID | None = None

    def resolved_wait_seconds(self, fallback: int) -> int:
        return self.wait_seconds if self.wait_seconds is not None else fallback


@dataclass(slots=True)
class PreparedSisterRequest:
    request: CatastoVisuraRequest
    execution_token: UUID


@dataclass(frozen=True, slots=True)
class SisterRemoteStateUpdate:
    remote_id: str | None
    remote_url: str | None
    state: str
    credential_id: UUID | None = None


@dataclass(slots=True)
class _ResultContext:
    db: Session
    batch: CatastoBatch
    request: CatastoVisuraRequest
    codice_fiscale: str
    result: Any
    terminal_status: str


@dataclass(slots=True)
class _ClaimScan:
    has_deferred_requests: bool = False
    next_retry_seconds: int | None = None
    has_waiting_captcha: bool = False

    def record_deferred(self, seconds: int) -> None:
        self.has_deferred_requests = True
        self.next_retry_seconds = (
            seconds if self.next_retry_seconds is None else min(self.next_retry_seconds, seconds)
        )

    def selection(self) -> ClaimedRequestSelection:
        if self.has_waiting_captcha:
            return ClaimedRequestSelection(request_id=None, wait_reason="WAIT")
        if self.has_deferred_requests:
            return ClaimedRequestSelection(
                request_id=None,
                wait_reason="RETRY_LATER",
                wait_seconds=self.next_retry_seconds,
            )
        return ClaimedRequestSelection(request_id=None)


@dataclass(slots=True)
class SisterRequestRetryCoordinator:
    lock: asyncio.Lock
    deferred_requests: dict[UUID, datetime]
    reset_request: ResetRequestCallback
    recoverable_retry_seconds: int

    async def defer(
        self,
        request_id: UUID,
        execution_token: UUID | None,
        seconds: int,
        operation: str,
        error_code: str,
    ) -> None:
        retry_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        async with self.lock:
            self.deferred_requests[request_id] = retry_at
        self.reset_request(request_id, operation, retry_at, error_code, execution_token)

    async def defer_recoverable(
        self,
        request_id: UUID,
        execution_token: UUID | None,
        exc: Exception,
        username: str,
    ) -> None:
        operation, error_code = recoverable_retry_metadata(exc, username)
        await self.defer(request_id, execution_token, self.recoverable_retry_seconds, operation, error_code)


@dataclass(slots=True)
class SisterRequestClaimCoordinator:
    claim_lock: asyncio.Lock
    shared_state_lock: asyncio.Lock
    deferred_requests: dict[UUID, datetime]
    claimed_request_ids: set[UUID]

    async def claim_next(
        self,
        repository: "SisterRequestRepository",
        batch_id: UUID,
        credential_id: UUID,
    ) -> ClaimedRequestSelection:
        async with self.claim_lock:
            async with self.shared_state_lock:
                deferred_snapshot = dict(self.deferred_requests)
                claimed_snapshot = set(self.claimed_request_ids)
            selection = repository.claim_next(
                batch_id,
                deferred_snapshot,
                claimed_snapshot,
                credential_id,
            )
            if selection.request_id is not None:
                async with self.shared_state_lock:
                    self.claimed_request_ids.add(selection.request_id)
                    self.deferred_requests.pop(selection.request_id, None)
            return selection

    async def release(self, request_id: UUID | None) -> None:
        if request_id is None:
            return
        async with self.shared_state_lock:
            self.claimed_request_ids.discard(request_id)


@dataclass(slots=True)
class SisterRequestRepository:
    session_factory: SessionFactory
    refresh_batch_counts: RefreshBatchCounts
    persist_ade_status: PersistAdeStatus
    parse_historical_pdf: ParseHistoricalPdf
    classify_terminal_status: ClassifyTerminalStatus
    to_user_message: Callable[[str], str]
    artifact_root: Path
    document_root: Path
    ade_scan_purpose: str
    release_requested_message: str
    release_requested_operation: str
    max_attempts: int
    retry_defer_seconds: int

    def fail_unavailable_pinned_requests(
        self,
        batch_id: UUID,
        active_credential_ids: set[UUID],
    ) -> int:
        with self.session_factory() as db:
            batch = db.get(CatastoBatch, batch_id)
            if batch is None or batch.status != CatastoBatchStatus.PROCESSING.value:
                return 0
            failed = 0
            for request in self._batch_requests(db, batch_id):
                if str(request.sister_remote_state or "").lower() not in ACTIVE_REMOTE_STATES:
                    continue
                if request.sister_credential_id in active_credential_ids:
                    continue
                self._mark_request_failed(
                    request,
                    "La credenziale SISTER della richiesta remota non e' piu' disponibile",
                    "Ripresa SISTER impossibile: credenziale non disponibile",
                )
                request.sister_remote_state = "orphaned"
                request.last_error_code = "sister_credential_unavailable"
                failed += 1
            if failed:
                batch.current_operation = f"{failed} richieste remote senza credenziale disponibile"
                self.refresh_batch_counts(db, batch)
                db.commit()
            return failed

    def fail_batch(self, batch_id: UUID, message: str) -> None:
        user_message = self.to_user_message(message)
        with self.session_factory() as db:
            batch = db.get(CatastoBatch, batch_id)
            if batch is None or batch.status == CatastoBatchStatus.CANCELLED.value:
                return
            requests = self._batch_requests(db, batch_id)
            for request in requests:
                if request.status not in OPEN_REQUEST_STATUSES:
                    continue
                self._persist_blocked_ade(db, request, user_message)
                self._mark_request_failed(request, user_message, "Failed before visura execution")
            batch.status = CatastoBatchStatus.FAILED.value
            batch.current_operation = user_message
            batch.completed_at = datetime.now(timezone.utc)
            self.refresh_batch_counts(db, batch)
            db.commit()

    def fail_request(
        self,
        batch_id: UUID,
        request_id: UUID,
        message: str,
        execution_token: UUID | None = None,
    ) -> None:
        user_message = self.to_user_message(message)
        with self.session_factory() as db:
            batch = db.get(CatastoBatch, batch_id)
            request = db.get(CatastoVisuraRequest, request_id)
            if not self._claim_is_active(batch, request, execution_token):
                return
            assert batch is not None and request is not None
            self._persist_blocked_ade(db, request, user_message)
            self._mark_request_failed(request, user_message, "Richiesta fallita, batch in prosecuzione")
            batch.current_operation = f"Errore riga {request.row_index}, prosecuzione batch"
            self.refresh_batch_counts(db, batch)
            db.commit()

    def reset_for_retry(
        self,
        request_id: UUID,
        operation: str,
        retry_at: datetime | None = None,
        error_code: str | None = None,
        execution_token: UUID | None = None,
    ) -> None:
        with self.session_factory() as db:
            request = db.get(CatastoVisuraRequest, request_id)
            batch = db.get(CatastoBatch, request.batch_id) if request is not None else None
            if batch is None or batch.status != CatastoBatchStatus.PROCESSING.value:
                return
            assert request is not None
            if request.error_message == self.release_requested_message:
                self._preserve_release_request(request)
                db.commit()
                return
            if request.status != CatastoVisuraRequestStatus.PROCESSING.value:
                return
            if execution_token is not None and request.execution_token != execution_token:
                return
            request.status = CatastoVisuraRequestStatus.PENDING.value
            request.current_operation = operation
            request.retry_not_before = retry_at
            request.last_error_code = error_code
            request.execution_token = None
            db.commit()

    def claim_next(
        self,
        batch_id: UUID,
        deferred_requests: dict[UUID, datetime] | None = None,
        claimed_request_ids: set[UUID] | None = None,
        credential_id: UUID | None = None,
    ) -> ClaimedRequestSelection:
        deferred_requests = deferred_requests if deferred_requests is not None else {}
        claimed_request_ids = claimed_request_ids if claimed_request_ids is not None else set()
        with self.session_factory() as db:
            requests = self._claimable_requests(db, batch_id)
            now = datetime.now(timezone.utc)
            scan = _ClaimScan()
            for request in requests:
                if request.id in claimed_request_ids:
                    continue
                if _is_pinned_to_other_credential(request, credential_id):
                    continue
                seconds = _future_retry_seconds(deferred_requests.get(request.id) or request.retry_not_before, now)
                if seconds is not None:
                    scan.record_deferred(seconds)
                    continue
                selection = self._claim_request(db, request, now)
                if selection is not None:
                    return selection
                if request.status == CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value:
                    scan.has_waiting_captcha = True
            return scan.selection()

    def prepare_execution(self, batch_id: UUID, request_id: UUID) -> PreparedSisterRequest | None:
        with self.session_factory() as db:
            request = db.get(CatastoVisuraRequest, request_id)
            batch = db.get(CatastoBatch, batch_id)
            if request is None or batch is None:
                return None
            if self._resolve_awaiting_captcha(db, batch, request):
                return None
            if request.status == CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value:
                return None
            if request.status != CatastoVisuraRequestStatus.PROCESSING.value:
                request.status = CatastoVisuraRequestStatus.PROCESSING.value
                request.current_operation = "Presa in carico dal worker"
                request.attempts += 1
            request.execution_token = request.execution_token or uuid4()
            self._set_batch_processing_operation(batch, request)
            artifact_dir = build_request_artifact_dir(self.artifact_root, batch_id, request.id)
            artifact_dir.mkdir(parents=True, exist_ok=True)
            request.artifact_dir = str(artifact_dir)
            db.commit()
            db.refresh(request)
            execution_token = request.execution_token
            db.expunge(request)
            assert execution_token is not None
            return PreparedSisterRequest(request=request, execution_token=execution_token)

    def set_operation(self, request_id: UUID, operation: str, execution_token: UUID | None = None) -> None:
        with self.session_factory() as db:
            request = db.get(CatastoVisuraRequest, request_id)
            if not _request_accepts_update(request, execution_token):
                return
            assert request is not None
            request.current_operation = operation
            db.commit()

    def set_remote_state(
        self,
        request_id: UUID,
        execution_token: UUID | None,
        update: SisterRemoteStateUpdate,
    ) -> None:
        with self.session_factory() as db:
            request = db.get(CatastoVisuraRequest, request_id)
            if not _request_accepts_update(request, execution_token, require_token=True):
                return
            assert request is not None
            if update.remote_id:
                request.sister_remote_request_id = update.remote_id
            if update.remote_url:
                request.sister_remote_request_url = update.remote_url
            if update.credential_id is not None:
                request.sister_credential_id = update.credential_id
            request.sister_remote_state = update.state
            db.commit()

    def set_correlation_baseline(
        self,
        request_id: UUID,
        execution_token: UUID | None,
        baseline_keys: list[str],
    ) -> None:
        with self.session_factory() as db:
            request = db.get(CatastoVisuraRequest, request_id)
            if not _request_accepts_update(request, execution_token, require_token=True):
                return
            assert request is not None
            if request.sister_remote_state not in {"submitted", "pending", "ready"}:
                request.sister_credential_id = None
                request.sister_remote_request_id = None
                request.sister_remote_request_url = None
                request.sister_remote_state = None
            request.sister_remote_baseline_keys = baseline_keys
            db.commit()

    def persist_flow_result(
        self,
        batch_id: UUID,
        request_id: UUID,
        codice_fiscale: str,
        result: Any,
        execution_token: UUID | None = None,
    ) -> None:
        with self.session_factory() as db:
            batch = db.scalar(select(CatastoBatch).where(CatastoBatch.id == batch_id).with_for_update())
            request = db.scalar(
                select(CatastoVisuraRequest).where(CatastoVisuraRequest.id == request_id).with_for_update()
            )
            if not self._claim_is_active(batch, request, execution_token):
                _discard_result_file(result)
                logger.info("Risultato SISTER scartato per richiesta %s: claim non piu' valido", request_id)
                return
            assert batch is not None and request is not None
            self._apply_result_metadata(request, result)
            if result.status == "queued_sister":
                # La richiesta è stata messa in coda da SISTER — salva la correlazione
                # remota e reimposta lo stato in pending così il worker la riprende.
                # Il sister_remote_state è già "pending" (aggiornato dai callbacks).
                request.status = CatastoVisuraRequestStatus.PENDING.value
                request.current_operation = "In coda SISTER — riprova in corso"
                request.last_error_code = None
                request.error_message = None
                request.execution_token = None
                request.retry_not_before = None
                request.captcha_manual_solution = None
                request.captcha_skip_requested = False
                self._log_captcha_attempt(db, request_id, result)
                self.refresh_batch_counts(db, batch)
                db.commit()
                logger.info(
                    "Richiesta %s batch %s messa in coda SISTER (queued_sister) — sarà ripresa",
                    request_id, batch_id,
                )
                return
            terminal_status = self.classify_terminal_status(result.status)
            if terminal_status == "non_evadibile":
                self._persist_non_evadibile(db, batch, request, result)
            else:
                self._persist_terminal_result(
                    _ResultContext(db, batch, request, codice_fiscale, result, terminal_status)
                )
                request.execution_token = None
                request.retry_not_before = None
            request.captcha_manual_solution = None
            request.captcha_skip_requested = False
            self._log_captcha_attempt(db, request_id, result)
            self.refresh_batch_counts(db, batch)
            db.commit()
        logger.info("Risultato persistito per richiesta %s batch %s status=%s", request_id, batch_id, result.status)

    def create_document(
        self,
        db: Session,
        request: CatastoVisuraRequest,
        codice_fiscale: str,
        file_path: Path,
        file_size: int,
    ) -> CatastoDocument:
        document = db.scalar(select(CatastoDocument).where(CatastoDocument.request_id == request.id))
        sha256 = sha256_file(file_path)
        if document is None:
            document = CatastoDocument(**document_values(request, codice_fiscale, file_path, file_size, sha256))
            db.add(document)
            db.flush()
            return document
        document.filename = file_path.name
        document.filepath = str(file_path)
        document.file_size = file_size
        document.sha256 = sha256
        return document

    def build_document_path(self, codice_fiscale: str, request: CatastoVisuraRequest) -> Path:
        return build_document_path(self.document_root, codice_fiscale, request)

    @staticmethod
    def _batch_requests(db: Session, batch_id: UUID) -> list[CatastoVisuraRequest]:
        return list(db.scalars(select(CatastoVisuraRequest).where(CatastoVisuraRequest.batch_id == batch_id)).all())

    @staticmethod
    def _claimable_requests(db: Session, batch_id: UUID) -> list[CatastoVisuraRequest]:
        return list(
            db.scalars(
                select(CatastoVisuraRequest)
                .where(
                    CatastoVisuraRequest.batch_id == batch_id,
                    CatastoVisuraRequest.status.in_(
                        [CatastoVisuraRequestStatus.PENDING.value, CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value]
                    ),
                )
                .order_by(CatastoVisuraRequest.row_index.asc())
                .with_for_update(skip_locked=True)
            ).all()
        )

    def _claim_request(
        self,
        db: Session,
        request: CatastoVisuraRequest,
        now: datetime,
    ) -> ClaimedRequestSelection | None:
        if request.status == CatastoVisuraRequestStatus.PENDING.value:
            if request.attempts >= self.max_attempts:
                self._mark_retry_exhausted(request, now)
                db.commit()
                return None
            request.status = CatastoVisuraRequestStatus.PROCESSING.value
            request.current_operation = "Presa in carico dal worker"
            request.attempts += 1
        elif not _captcha_can_resume(request):
            return None
        request.execution_token = uuid4()
        request.retry_not_before = None
        db.commit()
        return ClaimedRequestSelection(request_id=request.id, execution_token=request.execution_token)

    def _resolve_awaiting_captcha(
        self,
        db: Session,
        batch: CatastoBatch,
        request: CatastoVisuraRequest,
    ) -> bool:
        if request.status != CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value:
            return False
        if request.captcha_manual_solution:
            request.status = CatastoVisuraRequestStatus.PROCESSING.value
            request.current_operation = "Ripresa con CAPTCHA manuale"
            return False
        if is_expired(request.captcha_expires_at):
            self._finish_captcha_wait(batch, request, CatastoVisuraRequestStatus.FAILED.value)
            self.refresh_batch_counts(db, batch)
            db.commit()
            return True
        if request.captcha_skip_requested:
            self._finish_captcha_wait(batch, request, CatastoVisuraRequestStatus.SKIPPED.value)
            self.refresh_batch_counts(db, batch)
            db.commit()
            return True
        return False

    @staticmethod
    def _finish_captcha_wait(batch: CatastoBatch, request: CatastoVisuraRequest, status: str) -> None:
        request.status = status
        request.processed_at = datetime.now(timezone.utc)
        if status == CatastoVisuraRequestStatus.FAILED.value:
            request.current_operation = "Timeout CAPTCHA manuale"
            request.error_message = "Tempo massimo CAPTCHA manuale superato"
            batch.current_operation = f"Timeout CAPTCHA manuale sulla riga {request.row_index}"
            return
        request.current_operation = "Saltata dall'utente"
        request.error_message = "Saltata dall'utente dopo richiesta CAPTCHA"
        batch.current_operation = f"Saltata riga {request.row_index}"

    @staticmethod
    def _set_batch_processing_operation(batch: CatastoBatch, request: CatastoVisuraRequest) -> None:
        if request.search_mode == "soggetto":
            batch.current_operation = f"Lavorazione {request.subject_kind or 'SOGGETTO'} {request.subject_id or '-'}"
            return
        batch.current_operation = f"Lavorazione {request.comune} Fg.{request.foglio} Part.{request.particella}"

    @staticmethod
    def _claim_is_active(
        batch: CatastoBatch | None,
        request: CatastoVisuraRequest | None,
        execution_token: UUID | None,
    ) -> bool:
        return bool(
            batch is not None
            and request is not None
            and batch.status == CatastoBatchStatus.PROCESSING.value
            and request.status in ACTIVE_REQUEST_STATUSES
            and (execution_token is None or request.execution_token == execution_token)
        )

    def _persist_blocked_ade(self, db: Session, request: CatastoVisuraRequest, message: str) -> None:
        if request.purpose != self.ade_scan_purpose or request.target_ruolo_particella_id is None:
            return
        self.persist_ade_status(
            db,
            ruolo_particella_id=request.target_ruolo_particella_id,
            request_id=request.id,
            status="failed",
            classification="blocked",
            payload={"classification": "blocked", "message": message},
            error=message,
        )

    @staticmethod
    def _mark_request_failed(request: CatastoVisuraRequest, message: str, operation: str) -> None:
        request.status = CatastoVisuraRequestStatus.FAILED.value
        request.current_operation = operation
        request.error_message = message
        request.processed_at = datetime.now(timezone.utc)
        request.captcha_manual_solution = None
        request.captcha_skip_requested = False
        request.execution_token = None
        request.retry_not_before = None

    def _preserve_release_request(self, request: CatastoVisuraRequest) -> None:
        request.status = CatastoVisuraRequestStatus.SKIPPED.value
        request.current_operation = self.release_requested_operation
        request.processed_at = request.processed_at or datetime.now(timezone.utc)

    def _mark_retry_exhausted(self, request: CatastoVisuraRequest, now: datetime) -> None:
        request.status = CatastoVisuraRequestStatus.FAILED.value
        request.current_operation = "Retry SISTER esauriti"
        request.error_message = f"Numero massimo di tentativi SISTER raggiunto ({self.max_attempts})"
        request.last_error_code = "retry_exhausted"
        request.processed_at = now
        request.retry_not_before = None
        request.execution_token = None

    @staticmethod
    def _apply_result_metadata(request: CatastoVisuraRequest, result: Any) -> None:
        if result.captcha_image_path:
            request.captcha_image_path = str(result.captcha_image_path)
        if result.remote_request_id:
            request.sister_remote_request_id = result.remote_request_id
        if result.remote_request_url:
            request.sister_remote_request_url = result.remote_request_url

    def _persist_non_evadibile(
        self, db: Session, batch: CatastoBatch, request: CatastoVisuraRequest, result: Any
    ) -> None:
        attempts = request.attempts or 0
        if attempts < 3:
            request.status = CatastoVisuraRequestStatus.PENDING.value
            request.current_operation = f"Non evadibile (tentativo {attempts}), in coda per nuovo tentativo"
            request.error_message = None
            request.retry_not_before = datetime.now(timezone.utc) + timedelta(seconds=self.retry_defer_seconds)
            batch.current_operation = f"Non evadibile riga {request.row_index}, nuovo tentativo"
        else:
            self._persist_terminal_non_evadibile(db, batch, request, result)
        request.sister_remote_state = "deleted"
        request.last_error_code = "non_evadibile"
        request.execution_token = None

    def _persist_terminal_non_evadibile(
        self, db: Session, batch: CatastoBatch, request: CatastoVisuraRequest, result: Any
    ) -> None:
        request.status = CatastoVisuraRequestStatus.FAILED.value
        request.current_operation = "Non evadibile dopo 3 tentativi"
        request.error_message = result.error_message or "Richiesta non evadibile da SISTER"
        request.processed_at = datetime.now(timezone.utc)
        batch.current_operation = f"Non evadibile riga {request.row_index}"
        if request.purpose == self.ade_scan_purpose and request.target_ruolo_particella_id is not None:
            self.persist_ade_status(
                db,
                ruolo_particella_id=request.target_ruolo_particella_id,
                request_id=request.id,
                status="failed",
                classification="non_evadibile",
                error=result.error_message,
            )

    def _persist_terminal_result(self, context: _ResultContext) -> None:
        if context.request.purpose == self.ade_scan_purpose:
            self._persist_ade_result(context)
        elif _has_completed_document(context):
            self._persist_completed_result(
                context.db,
                context.batch,
                context.request,
                context.codice_fiscale,
                context.result,
            )
        elif context.terminal_status == "skipped":
            self._persist_skipped_result(context.batch, context.request, context.result)
        elif context.terminal_status == "not_found":
            self._persist_not_found_result(context.batch, context.request, context.result)
        else:
            self._persist_failed_result(context.batch, context.request, context.result)

    def _persist_ade_result(self, context: _ResultContext) -> None:
        document, payload, classification = self._prepare_ade_payload(
            context.db,
            context.request,
            context.codice_fiscale,
            context.result,
            context.terminal_status,
        )
        if context.request.target_ruolo_particella_id is not None:
            self.persist_ade_status(
                context.db,
                ruolo_particella_id=context.request.target_ruolo_particella_id,
                request_id=context.request.id,
                status=context.terminal_status,
                classification=classification,
                document_id=document.id if document is not None else None,
                payload=payload,
                error=context.result.error_message,
            )
        context.request.status = (
            CatastoVisuraRequestStatus.COMPLETED.value
            if context.terminal_status in {"completed", "not_found"}
            else CatastoVisuraRequestStatus.FAILED.value
        )
        context.request.current_operation = (
            "Visura storica AdE acquisita"
            if context.request.status == CatastoVisuraRequestStatus.COMPLETED.value
            else "Visura storica AdE fallita"
        )
        context.request.error_message = context.result.error_message
        context.request.processed_at = datetime.now(timezone.utc)
        context.batch.current_operation = (
            f"Visura storica AdE riga {context.request.row_index}: "
            f"{classification or context.terminal_status}"
        )

    def _prepare_ade_payload(
        self,
        db: Session,
        request: CatastoVisuraRequest,
        codice_fiscale: str,
        result: Any,
        terminal_status: str,
    ) -> tuple[CatastoDocument | None, Any, str | None]:
        payload = result.ade_status_payload
        if terminal_status != "completed" or result.file_path is None or result.file_size is None:
            classification = str(payload.get("classification") or "unknown") if isinstance(payload, dict) else None
            return None, payload, classification
        document = self.create_document(db, request, codice_fiscale, result.file_path, result.file_size)
        request.document_id = document.id
        payload = self._parse_ade_document(request, result.file_path, document)
        classification = str(payload.get("classification") or "unknown") if isinstance(payload, dict) else "unknown"
        return document, payload, classification

    def _parse_ade_document(
        self, request: CatastoVisuraRequest, file_path: Path, document: CatastoDocument
    ) -> dict[str, Any]:
        try:
            payload = self.parse_historical_pdf(file_path)
            payload["document_id"] = str(document.id)
            payload["document_path"] = str(file_path)
            return payload
        except Exception as exc:
            logger.exception("Parsing visura storica AdE fallito per richiesta %s", request.id)
            return {
                "source": "ade_historical_synthetic_pdf",
                "classification": "parse_failed",
                "document_id": str(document.id),
                "document_path": str(file_path),
                "error": str(exc),
            }

    def _persist_completed_result(
        self,
        db: Session,
        batch: CatastoBatch,
        request: CatastoVisuraRequest,
        codice_fiscale: str,
        result: Any,
    ) -> None:
        document = self.create_document(db, request, codice_fiscale, result.file_path, result.file_size)
        request.document_id = document.id
        request.status = CatastoVisuraRequestStatus.COMPLETED.value
        request.current_operation = "PDF scaricato"
        request.sister_remote_state = "downloaded"
        request.last_error_code = None
        request.processed_at = datetime.now(timezone.utc)
        batch.current_operation = f"Completata riga {request.row_index}"

    @staticmethod
    def _persist_skipped_result(batch: CatastoBatch, request: CatastoVisuraRequest, result: Any) -> None:
        request.status = CatastoVisuraRequestStatus.SKIPPED.value
        request.current_operation = "Saltata"
        request.last_error_code = None
        request.error_message = result.error_message
        request.processed_at = datetime.now(timezone.utc)
        batch.current_operation = f"Saltata riga {request.row_index}"

    @staticmethod
    def _persist_not_found_result(batch: CatastoBatch, request: CatastoVisuraRequest, result: Any) -> None:
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

    @staticmethod
    def _persist_failed_result(batch: CatastoBatch, request: CatastoVisuraRequest, result: Any) -> None:
        request.status = CatastoVisuraRequestStatus.FAILED.value
        request.current_operation = "Fallita"
        request.error_message = result.error_message or "Visura flow failed"
        request.last_error_code = "flow_failed"
        request.processed_at = datetime.now(timezone.utc)
        batch.current_operation = f"Fallita riga {request.row_index}"

    @staticmethod
    def _log_captcha_attempt(db: Session, request_id: UUID, result: Any) -> None:
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


def is_expired(deadline: datetime | None) -> bool:
    if deadline is None:
        return False
    now = datetime.now(timezone.utc)
    if deadline.tzinfo is None:
        return deadline <= now.replace(tzinfo=None)
    return deadline <= now


def is_recoverable_credential_error(exc: Exception, invalid_document_error: type[Exception]) -> bool:
    message = str(exc).lower()
    markers = (
        "sister_session_locked",
        "gia' in sessione",
        "già in sessione",
        "utente sister bloccato",
        "error_locked.jsp",
        "login timeout", "timeout 60000ms exceeded",
        "credenziali sister rifiutate", "autenticazione fallita",
    )
    return (
        isinstance(exc, (TimeoutError, invalid_document_error, SisterRequestCorrelationError))
        or type(exc).__name__ == "TimeoutError"
        or any(marker in message for marker in markers)
    )


def recoverable_retry_metadata(exc: Exception, username: str) -> tuple[str, str]:
    if isinstance(exc, SisterRequestCorrelationError):
        return "Correlazione SISTER non sicura, retry differito", "sister_correlation_error"
    return f"Sessione/timeout su {username}, retry differito", "session_recovery"


def _future_retry_seconds(deadline: datetime | None, now: datetime) -> int | None:
    if deadline is None:
        return None
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if deadline <= now:
        return None
    return max(int((deadline - now).total_seconds()), 1)


def _captcha_can_resume(request: CatastoVisuraRequest) -> bool:
    return bool(request.captcha_skip_requested or request.captcha_manual_solution or is_expired(request.captcha_expires_at))


def _has_completed_document(context: _ResultContext) -> bool:
    return bool(
        context.terminal_status == "completed"
        and context.result.file_path is not None
        and context.result.file_size is not None
    )


def _request_accepts_update(
    request: CatastoVisuraRequest | None,
    execution_token: UUID | None,
    *,
    require_token: bool = False,
) -> bool:
    return bool(
        request is not None
        and request.status in ACTIVE_REQUEST_STATUSES
        and (not require_token or execution_token is not None and request.execution_token == execution_token)
        and (execution_token is None or request.execution_token == execution_token)
    )


def _is_pinned_to_other_credential(
    request: CatastoVisuraRequest,
    credential_id: UUID | None,
) -> bool:
    return bool(
        credential_id is not None
        and request.sister_credential_id is not None
        and request.sister_credential_id != credential_id
        and str(request.sister_remote_state or "").lower() in ACTIVE_REMOTE_STATES
    )


def _discard_result_file(result: Any) -> None:
    if result.file_path is not None:
        result.file_path.unlink(missing_ok=True)
