from __future__ import annotations


NON_RETRYABLE_REQUEST_STATUSES = {"skipped", "not_found", "completed"}


def can_retry_request_status(status: str) -> bool:
    return status not in NON_RETRYABLE_REQUEST_STATUSES


def classify_terminal_status(flow_status: str) -> str:
    normalized = (flow_status or "").strip().lower()
    if normalized in {"completed", "failed", "skipped", "not_found"}:
        return normalized
    return "failed"
