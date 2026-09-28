"""Durable remote recovery budget, independent from local execution attempts."""

from datetime import datetime, timedelta, timezone

from app.models.catasto import CatastoVisuraRequest
from app.modules.elaborazioni.sister_recovery_contract import (
    RECOVERY_WINDOW,
    REMOTE_STATES,
    is_remote_recovery,
    recovery_stop_reason,
)

POLL_DELAY = timedelta(minutes=5)


def remote_poll_delay(request: CatastoVisuraRequest, now: datetime) -> timedelta:
    submitted = request.sister_first_submitted_at
    if submitted is None:
        return POLL_DELAY
    submitted = submitted.replace(tzinfo=submitted.tzinfo or timezone.utc)  # noqa: UP017 - Python 3.10.
    age = max((now - submitted).total_seconds(), 0)
    remaining = max((submitted + RECOVERY_WINDOW - now).total_seconds(), 0)
    if remaining <= 3600:
        seconds = min(300, remaining)
    else:
        seconds = min(300 * 2 ** min(int(age // 3600), 2), 1200)
    return timedelta(seconds=seconds)


def record_first_submission(request: CatastoVisuraRequest, state: str) -> None:
    # Never manufacture a fresh budget for legacy remote requests or renew it.
    if state in REMOTE_STATES and not is_remote_recovery(request):
        request.sister_first_submitted_at = request.sister_first_submitted_at or datetime.now(
            timezone.utc  # noqa: UP017 - Production worker runs Python 3.10.
        )


def stop_remote_recovery(request: CatastoVisuraRequest, reason: str, now: datetime) -> None:
    request.status = "failed"
    request.current_operation = reason
    request.error_message = _with_previous_error(request, reason)
    request.last_error_code = "sister_recovery_review_required"
    request.processed_at = now
    request.retry_not_before = None
    request.execution_token = None


def allow_execution(request: CatastoVisuraRequest, now: datetime, max_attempts: int) -> bool:
    reason = recovery_stop_reason(request, now)
    if reason:
        stop_remote_recovery(request, reason, now)
        return False
    if (
        is_remote_recovery(request)
        or request.status != "pending"
        or request.attempts < max_attempts
    ):
        return True
    request.status = "failed"
    request.current_operation = "Retry SISTER esauriti"
    request.error_message = _with_previous_error(
        request, f"Numero massimo di tentativi SISTER raggiunto ({max_attempts})"
    )
    request.last_error_code = "retry_exhausted"
    request.processed_at = now
    request.retry_not_before = None
    request.execution_token = None
    return False


def queue_remote_poll(request: CatastoVisuraRequest) -> None:
    request.status = "pending"
    request.current_operation = "In coda SISTER, prossimo recupero differito"
    request.last_error_code = None
    request.error_message = None
    request.execution_token = None
    now = datetime.now(timezone.utc)  # noqa: UP017 - Python 3.10.
    request.retry_not_before = now + remote_poll_delay(request, now)
    request.captcha_manual_solution = None
    request.captcha_skip_requested = False


def _with_previous_error(request: CatastoVisuraRequest, message: str) -> str:
    if request.error_message:
        return f"{message}. Ultimo errore ({request.last_error_code or 'sister'}): {request.error_message}"
    return message
