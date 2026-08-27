from __future__ import annotations

from typing import Any

from sister_exceptions import SisterInvalidDocumentError, SisterRequestCorrelationError


def recoverable_retry_metadata(exc: Exception, username: str) -> tuple[str, str]:
    if isinstance(exc, SisterRequestCorrelationError):
        return "Correlazione SISTER non sicura, retry differito", "sister_correlation_error"
    if isinstance(exc, SisterInvalidDocumentError):
        return "PDF SISTER difforme o non valido, retry differito", "sister_invalid_document"
    return f"Sessione/timeout su {username}, retry differito", "session_recovery"


def clear_remote_request_metadata(request: Any, *, clear_baseline: bool = False) -> None:
    request.sister_credential_id = None
    request.sister_remote_request_id = None
    request.sister_remote_request_url = None
    request.sister_remote_state = None
    if clear_baseline:
        request.sister_remote_baseline_keys = None


__all__ = ["clear_remote_request_metadata", "recoverable_retry_metadata"]
