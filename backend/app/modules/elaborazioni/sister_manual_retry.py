"""Fail-closed preflight for an operator retry; never renew a remote budget."""

from datetime import datetime

from app.models.catasto import CatastoVisuraRequest
from app.modules.elaborazioni.sister_recovery_contract import (
    is_remote_recovery,
    recovery_stop_reason,
)


class BatchConflictError(Exception):
    pass


def queue_request(
    request: CatastoVisuraRequest, operation: str, *, preserve_error: bool = False
) -> None:
    request.status = "pending"
    request.current_operation = operation
    request.error_message = request.error_message if preserve_error else None
    request.processed_at = None
    request.document_id = None
    request.captcha_manual_solution = None
    request.captcha_skip_requested = False
    request.captcha_requested_at = None
    request.captcha_expires_at = None
    request.captcha_image_path = None
    request.execution_token = None
    request.retry_not_before = None
    request.last_error_code = request.last_error_code if preserve_error else None


def retry_failed_requests(requests: list[CatastoVisuraRequest], now: datetime) -> None:
    failed = [request for request in requests if request.status == "failed"]
    if not failed:
        raise BatchConflictError("No failed requests available for retry")
    if conflict := manual_retry_conflict(failed, now):
        raise BatchConflictError(conflict)
    for request in failed:
        queue_request(request, "Queued for retry", preserve_error=True)


def manual_retry_conflict(requests: list[CatastoVisuraRequest], now: datetime) -> str | None:
    for request in requests:
        if request.status != "failed":
            continue
        reason = _request_retry_conflict(request, now)
        if reason:
            return f"Retry bloccato alla riga {request.row_index}: {reason}. Nessuna richiesta rimessa in coda."
    return None


def _request_retry_conflict(request: CatastoVisuraRequest, now: datetime) -> str | None:
    if request.execution_token or request.document_id:
        return "esecuzione o documento gia presente, verifica manuale necessaria"
    reason = recovery_stop_reason(request, now)
    if reason:
        return reason
    if is_remote_recovery(request):
        if not request.sister_remote_request_id or not request.sister_credential_id:
            return "ID remoto o credenziale SISTER mancanti, recupero non sicuro"
        return None
    if any(
        (
            request.sister_remote_state,
            request.sister_remote_request_id,
            request.sister_remote_request_url,
            request.sister_first_submitted_at,
            request.attempts,
        )
    ):
        return "precedente tentativo SISTER da verificare prima di autorizzare un nuovo invio"
    return None
