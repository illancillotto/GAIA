"""Prevent campaign retries from replacing unresolved SISTER requests."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoRuoloAutoSyncItem, CatastoVisuraRequest
from app.modules.elaborazioni.sister_manual_retry import BatchConflictError

REVIEW_MESSAGE = (
    "Retry AutoSync bloccato: precedente richiesta SISTER da verificare. "
    "Recuperare la richiesta originale senza creare un nuovo invio."
)


def requires_original_request(request: CatastoVisuraRequest) -> bool:
    return any(
        (
            request.last_error_code == "sister_recovery_review_required",
            request.sister_remote_state,
            request.sister_remote_request_id,
            request.sister_remote_request_url,
            request.sister_first_submitted_at,
            request.attempts,
            request.execution_token,
            request.document_id,
        )
    )


def unsubmitted_stale_batches(db: Session, batches: list) -> list:
    safe = []
    for batch in batches:
        requests = list(
            db.scalars(
                select(CatastoVisuraRequest)
                .where(CatastoVisuraRequest.batch_id == batch.id)
                .order_by(CatastoVisuraRequest.row_index.asc())
                .with_for_update()
                .execution_options(populate_existing=True)
            ).all()
        )
        if not any(
            requires_original_request(request)
            or request.status in {"processing", "awaiting_captcha"}
            for request in requests
        ):
            safe.append((batch, requests))
    return safe


def replacement_is_unsafe(db: Session, item) -> bool:
    if item.linked_request_id is None:
        return bool(item.attempt_count)
    request = db.scalar(
        select(CatastoVisuraRequest)
        .where(CatastoVisuraRequest.id == item.linked_request_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if request is None or request.status in {"pending", "processing", "awaiting_captcha"}:
        return True
    if request.status in {"completed", "not_found"}:
        return False
    return requires_original_request(request) or bool(item.attempt_count)


def guard_campaign_items(db: Session, items: list, *, manual: bool = False) -> list:
    blocked = [item for item in items if replacement_is_unsafe(db, item)]
    # Preflight the whole selection before modifying any item.
    if blocked and manual:
        raise BatchConflictError(REVIEW_MESSAGE + " Nessun elemento rimesso in coda.")
    for item in blocked:
        item.status = "blocked_runtime" if isinstance(item, CatastoRuoloAutoSyncItem) else "failed"
        item.retry_after = None
        item.last_error_message = item.last_error_message or REVIEW_MESSAGE
    if blocked:
        db.flush()
    return [item for item in items if item not in blocked]
