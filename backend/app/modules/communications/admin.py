"""Administration has separate RBAC from composition; secrets never enter HTTP."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.utenze.routes.electronic_contacts import router as contact_router

from . import queue, registry, store
from .models import (
    CommunicationAccount,
    CommunicationJob,
    CommunicationMessage,
    CommunicationReceipt,
    CommunicationTemplate,
)
from .policy import transport_enabled
from .router import command
from .schemas import AccountChange, AccountInput, Pause, TemplateInput

router = APIRouter(
    prefix="/communications",
    tags=["communications-admin"],
    dependencies=[Depends(require_admin_user)],
)

router.include_router(contact_router)


@router.get("/admin/accounts")
def accounts(db: Session = Depends(get_db)):
    return [store.public_model(value) for value in db.scalars(select(CommunicationAccount))]


@router.post("/accounts", status_code=201)
def create_account(
    payload: AccountInput,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_admin_user),
):
    return store.public_model(command(db, lambda: registry.save_account(db, payload, user.id)))


@router.patch("/accounts/{identity}")
def update_account(
    identity: UUID,
    payload: AccountChange,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_admin_user),
):
    return store.public_model(
        command(db, lambda: registry.save_account(db, payload, user.id, identity))
    )


@router.post("/accounts/{identity}/test", status_code=202)
def test_account(
    identity: UUID,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_admin_user),
):
    return store.public_model(
        command(db, lambda: registry.request_account_job(db, identity, "test", user.id)),
        omit=("lease_token",),
    )


@router.post("/accounts/{identity}/reconcile", status_code=202)
def reconcile_account(
    identity: UUID,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_admin_user),
):
    def action():
        account = registry.account(db, identity)
        return registry.request_account_job(db, identity, f"reconcile_{account.channel}", user.id)

    return store.public_model(command(db, action), omit=("lease_token",))


@router.post("/accounts/{identity}/pause")
def pause_account(
    identity: UUID,
    payload: Pause,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_admin_user),
):
    def action():
        account = registry.account(db, identity)
        account.paused = payload.paused
        store.event(db, identity, "account_paused", actor_id=user.id, paused=payload.paused)
        return account

    return store.public_model(command(db, action))


@router.get("/admin/templates")
def templates(db: Session = Depends(get_db)):
    return [
        store.public_model(value)
        for value in db.scalars(
            select(CommunicationTemplate).order_by(
                CommunicationTemplate.code, CommunicationTemplate.version.desc()
            )
        )
    ]


@router.post("/templates", status_code=201)
def create_template(
    payload: TemplateInput,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_admin_user),
):
    return store.public_model(command(db, lambda: registry.create_template(db, payload, user.id)))


@router.post("/templates/{identity}/approve")
def approve_template(
    identity: UUID,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_admin_user),
):
    return store.public_model(command(db, lambda: registry.approve_template(db, identity, user.id)))


@router.post("/admin/pause")
def pause(
    payload: Pause,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_admin_user),
):
    def action():
        control = queue.control(db)
        control.paused = payload.paused
        store.event(db, UUID(int=0), "global_paused", actor_id=user.id, paused=payload.paused)
        return {"paused": control.paused}

    return command(db, action)


@router.get("/admin/monitor")
def monitor(db: Session = Depends(get_db)):
    control = queue.control(db)
    counts = dict(
        db.execute(
            select(CommunicationJob.state, func.count()).group_by(CommunicationJob.state)
        ).all()
    )
    return {
        "paused": control.paused,
        "transport_enabled": transport_enabled(),
        "worker_seen_at": control.worker_seen_at,
        "queues": counts,
        "uncertain": db.scalar(
            select(func.count())
            .select_from(CommunicationMessage)
            .where(CommunicationMessage.state == "uncertain")
        ),
        "unmatched_receipts": db.scalar(
            select(func.count())
            .select_from(CommunicationReceipt)
            .where(CommunicationReceipt.classification == "unmatched")
        ),
    }


@router.get("/admin/unmatched-receipts")
def unmatched(db: Session = Depends(get_db)):
    return [
        store.public_model(value, omit=("original",))
        for value in db.scalars(
            select(CommunicationReceipt)
            .where(CommunicationReceipt.classification == "unmatched")
            .order_by(CommunicationReceipt.created_at.desc())
            .limit(100)
        )
    ]
