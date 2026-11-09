"""Plan a final, read-only portal pass per account and preserve its independent evidence."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.models.posta_online import PostaOnlineCredential, PostaOnlineRegisteredMailSyncJob
from app.modules.ruolo.poste_dispatch_models import (
    PosteDispatchEvent,
    PosteDispatchItem,
    PosteDispatchLot,
)
from app.modules.ruolo.services.poste_dispatch_accounts import checked_job
from app.modules.ruolo.services.poste_dispatch_recipient import shipment_name
from app.modules.ruolo.services.poste_dispatch_state import (
    DRAFT_STATUSES,
    DispatchConflict,
    DispatchNotFound,
)
from app.services.elaborazioni_posta_online import ACTIVE_JOB_STATUSES

MODE = "poste_dispatch_final_check"
REQUEST_KIND = "final_check_requested"
SNAPSHOT_KIND = "final_check_account_snapshot"


class SnapshotDraft(BaseModel):
    name: str
    draft_id: str | None
    status: str


class AccountRead(BaseModel):
    started_at: AwareDatetime
    checked_at: AwareDatetime
    drafts: list[SnapshotDraft]
    archive: dict[str, list[str]]


def account_key(username: str | None) -> str:
    return (username or "").strip().casefold()


def get_check(db: Session, check_id: UUID) -> PosteDispatchEvent:
    check = db.get(PosteDispatchEvent, check_id)
    if check is None or check.kind != REQUEST_KIND:
        raise DispatchNotFound("Verifica finale Poste non trovata")
    return check


def _account_plan(credential, lots) -> dict:
    bound = next((lot for lot in lots if lot.credential_id == credential.id), None)
    reason = None
    if not account_key(credential.username):
        reason = "invalid_username"
    elif not credential.active:
        reason = "credential_inactive"
    elif bound is None:
        reason = "no_bound_lot"
    elif bound.poste_username != credential.username:
        reason = "account_changed"
    return {
        "credential_id": credential.id,
        "poste_username": credential.username,
        "lot_id": str(bound.id) if bound else None,
        "job_id": None,
        "unavailable_reason": reason,
    }


def _plans(db: Session, lots) -> list[dict]:
    plans = {}
    for credential in db.scalars(select(PostaOnlineCredential).order_by(PostaOnlineCredential.id)):
        plan = _account_plan(credential, lots)
        key = account_key(credential.username)
        previous = plans.get(key)
        if previous is None or previous["unavailable_reason"] is not None:
            plans[key] = plan
    known = set(plans)
    for lot in lots:
        key = account_key(lot.poste_username)
        if key not in known:
            plans[key] = {
                "credential_id": lot.credential_id,
                "poste_username": lot.poste_username,
                "lot_id": str(lot.id),
                "job_id": None,
                "unavailable_reason": "credential_missing",
            }
    return list(plans.values())


def _expected_items(db: Session, lots) -> list[dict]:
    accounts = {lot.id: lot.poste_username for lot in lots}
    items = db.scalars(
        select(PosteDispatchItem).where(PosteDispatchItem.status.in_((*DRAFT_STATUSES, "sent")))
    )
    return [
        {
            "item_id": str(item.id),
            "notice_name": " ".join(
                shipment_name(item.notice_number).upper().split()
            ),
            "poste_username": accounts[item.lot_id],
            "status": item.status,
        }
        for item in items
    ]


def start_check(db: Session, *, actor_id: int) -> PosteDispatchEvent:
    # The first lot is a common transaction lock: two requests cannot queue parallel checks.
    anchor = db.scalar(
        select(PosteDispatchLot)
        .order_by(PosteDispatchLot.created_at, PosteDispatchLot.id)
        .limit(1)
        .with_for_update()
    )
    if anchor is None:
        raise DispatchConflict("Nessun lotto Poste da verificare")
    if db.scalar(
        select(PostaOnlineRegisteredMailSyncJob.id)
        .where(PostaOnlineRegisteredMailSyncJob.status.in_(ACTIVE_JOB_STATUSES))
        .limit(1)
    ):
        raise DispatchConflict(
            "Attendere la conclusione o la sospensione definitiva dei job Poste prima della verifica finale"
        )
    lots = list(db.scalars(select(PosteDispatchLot).order_by(PosteDispatchLot.created_at.desc())))
    check = PosteDispatchEvent(
        id=uuid4(),
        lot_id=anchor.id,
        kind=REQUEST_KIND,
        actor_id=actor_id,
        actor_username=db.scalar(
            select(ApplicationUser.username).where(ApplicationUser.id == actor_id)
        ),
        created_at=datetime.now(UTC),
    )
    plans = _plans(db, lots)
    for plan in plans:
        if plan["unavailable_reason"] is None:
            _queue_account(db, check, plan)
    check.detail = {
        "accounts": plans,
        "expected_items": _expected_items(db, lots),
        "lot_ids": [str(lot.id) for lot in lots],
    }
    db.add(check)
    db.flush()
    return check


def _queue_account(db: Session, check: PosteDispatchEvent, plan: dict) -> None:
    job = PostaOnlineRegisteredMailSyncJob(
        credential_id=plan["credential_id"],
        requested_by_user_id=check.actor_id,
        mode=MODE,
        status="pending",
        payload_json={
            "lot_id": plan["lot_id"],
            "poste_username": plan["poste_username"],
            "final_check_id": str(check.id),
        },
    )
    db.add(job)
    db.flush()
    plan["job_id"] = job.id


def record_account_snapshot(db: Session, lot_id: UUID, *, job_id: int, snapshot: dict) -> None:
    job = checked_job(db, lot_id, job_id)
    if job.mode != MODE:
        raise DispatchConflict("Job diverso dalla verifica finale")
    check = get_check(db, UUID(job.payload_json["final_check_id"]))
    plan = next((p for p in check.detail["accounts"] if p["job_id"] == job_id), None)
    if plan is None or plan["credential_id"] != job.credential_id:
        raise DispatchConflict("Account fuori dalla verifica finale richiesta")
    validated = AccountRead.model_validate(snapshot).model_dump(mode="json")
    db.add(
        PosteDispatchEvent(
            lot_id=lot_id,
            kind=SNAPSHOT_KIND,
            job_id=job_id,
            actor_id=check.actor_id,
            actor_username=check.actor_username,
            detail={
                "final_check_id": str(check.id),
                "poste_username": plan["poste_username"],
                **validated,
            },
        )
    )
    db.flush()
