"""Persisted retry timing for the authorized Poste campaign controller.

This policy never submits a document. A due retry queues reconciliation first;
manual holds and completed reconciliations with unresolved items stay protected.
"""

import random
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem
from app.modules.ruolo.services.poste_dispatch_accounts import checked_job
from app.modules.ruolo.services.poste_dispatch_state import (
    DRAFT_STATUSES,
    DispatchConflict,
    record_event,
    transition,
)

DELAYS_SECONDS = (120, 300, 600, 1200, 1800)
RECOVERY_DELAYS_SECONDS = (15, 30, 60)
LOGIN_REDIRECT_DELAYS_SECONDS = (60, 120, 300)
ACTIVE_STATUSES = {"pending", "queued_resume", "processing"}
_ARCHIVE_DETAIL_FORBIDDEN = re.compile(r"Poste Online detail:(\d+) HTTP 403")
_RECOVERY_ERROR = re.compile(
    r"timeout|timed out|oops|due bozze consecutive non create|net::err_|connection|socket"
)
_ATTENTION = (
    "otp",
    "autenticazione interattiva",
    "postebusiness",
    "autorizzazione nell'app",
    "credenziali errate",
    "credenziali non valide",
    "password errata",
    "password non corretta",
    "username o password",
    "account bloccato",
    "utenza bloccata",
    "troppi tentativi",
    "captcha",
    "accesso non riuscito",
    "mancato accesso",
)
_TEMPORARY = (
    "timeout",
    "timed out",
    "net::err_",
    "connection",
    "socket",
    "oops",
    "non raggiunto dopo login",
    "login poste online non completato",
    "due bozze consecutive non create",
)


def temporary_error(message: str | None) -> bool:
    text = (message or "").lower()
    if any(marker in text for marker in _ATTENTION):
        return False
    return (
        any(marker in text for marker in _TEMPORARY)
        or bool(re.search(r"http (?:429|5\d\d)\b", text))
        or bool(_ARCHIVE_DETAIL_FORBIDDEN.fullmatch(message or ""))
    )


def _aware(value: str | datetime) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def _automatic_hold(config: dict, job) -> bool:
    reason = config.get("reason", "")
    previous_error = job.payload_json.get("campaign_retry", {}).get("error")
    return reason in (
        job.error_detail,
        previous_error,
        "Credential absent or disabled; other campaign accounts may continue",
    )


def _retry_delays(error: str | None) -> tuple[int, ...]:
    text = (error or "").lower()
    if re.search(r"http 429\b", text):
        return DELAYS_SECONDS
    if text.startswith("archivio poste online non raggiunto dopo login:"):
        return LOGIN_REDIRECT_DELAYS_SECONDS
    if _ARCHIVE_DETAIL_FORBIDDEN.fullmatch(error or "") or _RECOVERY_ERROR.search(text):
        return RECOVERY_DELAYS_SECONDS
    return DELAYS_SECONDS


def _schedule(config: dict, job, now: datetime, jitter) -> None:
    previous = config.get("retry") or job.payload_json.get("campaign_retry", {})
    attempt = previous.get("attempt", 0) + 1
    delays = _retry_delays(job.error_detail)
    base = delays[min(attempt, len(delays)) - 1]
    seconds = base + jitter(0, base // 5)
    # Failed-at anchors the cooldown. A controller restart must not postpone it.
    failed_at = _aware(job.completed_at) if job.completed_at else now
    config["retry"] = {
        "attempt": attempt,
        "failure_job_id": job.id,
        "next_at_utc": (failed_at + timedelta(seconds=seconds)).isoformat(),
        "delay_seconds": seconds,
        "error": job.error_detail,
        "action": "reconcile",
        "lot_id": job.payload_json["lot_id"],
    }


def _account_outcome(config: dict, job) -> str:
    """Resolve operator holds and terminal results before calculating a deadline."""
    if job is None or job.status in ACTIVE_STATUSES:
        return "hold" if config.get("state") != "running" else "normal"
    if config.get("state") == "paused" and not _automatic_hold(config, job):
        return "hold"
    if job.status == "succeeded":
        config.pop("retry", None)
        config["state"] = "running"
        return "normal"
    if job.status != "failed" or not temporary_error(job.error_detail):
        return "hold" if config.get("state") != "running" else "normal"
    return "eligible"


def retry_gate(config: dict, job, now: datetime, *, jitter=None) -> str:
    """Return normal/wait/retry/hold; the caller persists config atomically."""
    outcome = _account_outcome(config, job)
    if outcome != "eligible":
        return outcome
    if config.get("retry", {}).get("failure_job_id") != job.id:
        _schedule(config, job, now, jitter or random.randint)
    config.update(state="retry_wait", reason=job.error_detail)
    if now < _aware(config["retry"]["next_at_utc"]):
        return "wait"
    return "retry"


def retry_credential(db, credential, job, lot, *, actor_id: int) -> bool:
    """Re-enable only failure-counter deactivation; preserve failure history."""
    if credential is None:
        return False
    if credential.active:
        return True
    if not (
        credential.consecutive_failures >= 5
        and credential.last_error == (job.error_detail or "")[:1000]
        and temporary_error(job.error_detail)
    ):
        return False
    credential.active = True
    record_event(
        db,
        lot,
        None,
        "credential_transient_retry_enabled",
        actor_id=actor_id,
        job_id=job.id,
        detail={"failures_preserved": credential.consecutive_failures, "success_claimed": False},
    )
    return True


def _hold_forbidden_archive_detail(db, config: dict, job, lot, *, actor_id: int) -> bool:
    """Quarantine exactly one identifiable submitted item, retaining both unique keys."""
    match = _ARCHIVE_DETAIL_FORBIDDEN.fullmatch(job.error_detail or "")
    if match is None:
        return True
    checked = checked_job(db, lot.id, job.id)
    if checked.mode != "poste_dispatch_reconcile" or checked.requested_by_user_id != actor_id:
        raise DispatchConflict("Job o operatore del dettaglio Archivio non coerente")
    items = list(
        db.scalars(
            select(PosteDispatchItem)
            .where(
                PosteDispatchItem.lot_id == lot.id,
                PosteDispatchItem.poste_draft_id == match[1],
                PosteDispatchItem.active_key.is_not(None),
            )
            .with_for_update()
        )
    )
    if len(items) != 1 or items[0].status not in DRAFT_STATUSES - {"cancel_requested"}:
        config.update(
            state="paused",
            reason="HTTP 403 Archivio: caso non attribuibile o protetto, verificare manualmente",
        )
        return False
    item = items[0]
    review = {
        "reason": job.error_detail[:1000],
        "review_type": "archive_detail_unavailable",
        "archive_shipment_id": match[1],
        "operational_hold": True,
        "no_automatic_retry": True,
        "pdf_and_recipient_preserved": True,
        "previous_review": item.address_review,
    }
    item.address_review, item.error_detail = review, review["reason"]
    transition(
        db,
        item,
        "address_review",
        "archive_detail_unavailable",
        actor_id=actor_id,
        job_id=job.id,
        detail=review,
    )
    return True


def queue_retry(db, config: dict, job, credential, *, actor_id: int):
    """Reconcile on the same account, never re-submit an uncertain document."""
    from uuid import UUID

    from app.modules.ruolo.services import poste_dispatch
    from app.modules.ruolo.services.poste_dispatch_state import get_lot

    lot = get_lot(db, UUID(config["retry"]["lot_id"]), lock=True)
    if not retry_credential(db, credential, job, lot, actor_id=actor_id):
        config.update(state="paused", reason="Credential disabled manually or unavailable")
        return None
    if not _hold_forbidden_archive_detail(db, config, job, lot, actor_id=actor_id):
        return None
    queued = poste_dispatch.request_job(db, lot.id, "reconcile", actor_id=actor_id)
    queued.payload_json = {**queued.payload_json, "campaign_retry": dict(config["retry"])}
    record_event(
        db,
        lot,
        None,
        "transient_retry_queued",
        actor_id=actor_id,
        job_id=queued.id,
        detail={**config["retry"], "previous_job_preserved": True, "send_action": False},
    )
    config.update(state="running", resume_after_job_id=queued.id)
    config["retry"]["queued_job_id"] = queued.id
    return queued
