"""Authenticated operator API; commands only persist work, never perform network I/O."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser

from . import outbox, registry, ruolo_source, store
from .models import (
    CommunicationAccount,
    CommunicationEvent,
    CommunicationJob,
    CommunicationMessage,
    CommunicationReceipt,
    CommunicationTemplate,
)
from .policy import Conflict, Missing, sha256
from .schemas import (
    Approval,
    CandidateFilters,
    Channel,
    MessageChange,
    MessageCreate,
    Rendered,
    VersionCommand,
)
from .source_preview import router as source_preview_router

MANAGE = "ruolo.tributi.manage_status"
router = APIRouter(
    prefix="/communications",
    tags=["communications"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)

router.include_router(source_preview_router)


def command(db, action):
    try:
        result = action()
        db.commit()
        return result
    except Missing as exc:
        db.rollback()
        raise HTTPException(404, detail=str(exc)) from exc
    except (Conflict, IntegrityError) as exc:
        db.rollback()
        detail = (
            str(exc) if isinstance(exc, Conflict) else "Risorsa già prenotata o comando concorrente"
        )
        raise HTTPException(409, detail=detail) from exc


def _resource(db, identity):
    try:
        return store.message(db, identity)
    except Missing as exc:
        raise HTTPException(404, detail=str(exc)) from exc


@router.get("/accounts")
def accounts(
    db: Session = Depends(get_db), user: ApplicationUser = Depends(require_section(MANAGE))
):
    values = db.scalars(select(CommunicationAccount).order_by(CommunicationAccount.priority))
    keys = {"id", "name", "channel", "provider", "sender", "display_name", "paused", "max_bytes"}
    return [
        {key: value for key, value in store.public_model(account).items() if key in keys}
        for account in values
        if registry.allowed(account, account.channel, user.id)
    ]


@router.get("/templates")
def templates(db: Session = Depends(get_db)):
    return [
        store.public_model(value)
        for value in db.scalars(
            select(CommunicationTemplate)
            .where(CommunicationTemplate.status == "approved")
            .order_by(CommunicationTemplate.code, CommunicationTemplate.version.desc())
        )
    ]


@router.get("/ruolo/candidates")
def candidates(filters: Annotated[CandidateFilters, Query()], db: Session = Depends(get_db)):
    return ruolo_source.list_candidates(
        db,
        channel=filters.channel,
        page=filters.page,
        page_size=filters.page_size,
        filters=filters.model_dump(),
    )


@router.get("/ruolo/candidates/{identity}/eligibility")
def eligibility(identity: UUID, db: Session = Depends(get_db)):
    _, document, _, fingerprint = command(db, lambda: ruolo_source.inspect(db, identity))
    return {
        "eligible": True,
        "document_id": document.id,
        "source_digest": fingerprint,
        "authorizes_dispatch": False,
    }


@router.get("/messages")
def messages(
    channel: Channel | None = None,
    state: str | None = None,
    account_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = select(CommunicationMessage)
    for key, value in (("channel", channel), ("state", state), ("account_id", account_id)):
        if value:
            query = query.where(getattr(CommunicationMessage, key) == value)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(CommunicationMessage.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return {"items": [store.public_model(value) for value in rows], "total": total}


@router.post("/messages", status_code=201)
def create(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_section(MANAGE)),
):
    value = command(db, lambda: outbox.create(db, payload, user.id))
    return store.detail(db, value)


@router.get("/messages/{identity}")
def message(identity: UUID, db: Session = Depends(get_db)):
    return store.detail(db, _resource(db, identity))


@router.patch("/messages/{identity}")
def update(
    identity: UUID,
    payload: MessageChange,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_section(MANAGE)),
):
    value = command(db, lambda: outbox.update(db, identity, payload, user.id))
    return store.detail(db, value)


@router.post("/messages/{identity}/validate")
def validate(
    identity: UUID,
    payload: VersionCommand,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_section(MANAGE)),
):
    return store.detail(db, command(db, lambda: outbox.validate(db, identity, payload, user.id)))


@router.post("/messages/{identity}/approve")
def approve(
    identity: UUID,
    payload: Approval,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_section(MANAGE)),
):
    return store.detail(db, command(db, lambda: outbox.approve(db, identity, payload, user.id)))


@router.post("/messages/{identity}/dispatch", status_code=202)
def dispatch(
    identity: UUID,
    payload: VersionCommand,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_section(MANAGE)),
):
    return store.public_model(
        command(db, lambda: outbox.dispatch(db, identity, payload, user.id)), omit=("lease_token",)
    )


@router.post("/messages/{identity}/cancel")
def cancel(
    identity: UUID,
    payload: VersionCommand,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_section(MANAGE)),
):
    return store.detail(db, command(db, lambda: outbox.cancel(db, identity, payload, user.id)))


@router.get("/messages/{identity}/attachments")
def attachments(identity: UUID, db: Session = Depends(get_db)):
    _resource(db, identity)
    return [
        store.public_model(value, omit=("content",)) for value in store.attachments(db, identity)
    ]


@router.post("/messages/{identity}/attachments", status_code=201)
async def add_attachment(
    identity: UUID,
    upload: UploadFile,
    expected_version: Annotated[int, Form(ge=1)],
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_section(MANAGE)),
):
    content = await upload.read(32 * 1024 * 1024 + 1)
    value = command(
        db, lambda: outbox.add_attachment(db, identity, expected_version, content, user.id)
    )
    return store.detail(db, value)


@router.get("/messages/{identity}/attachments/{attachment_id}/preview")
def preview(
    identity: UUID,
    attachment_id: UUID,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_section("ruolo.tributi.view")),
):
    value = _resource(db, identity)
    part = next(
        (part for part in store.attachments(db, identity) if part.id == attachment_id), None
    )
    if part is None:
        raise HTTPException(404, detail="Allegato non trovato")
    if sha256(part.content) != part.sha256:
        raise HTTPException(409, detail="Integrità PDF non verificata")
    review = command(db, lambda: outbox.start_review(db, value, part, user.id))
    return Response(
        part.content,
        media_type=part.mime_type,
        headers={
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'inline; filename="{part.id}.pdf"',
            "X-Communication-Review": str(review.id),
            "X-Content-SHA256": part.sha256,
            "Access-Control-Expose-Headers": "X-Communication-Review, X-Content-SHA256",
        },
    )


@router.post("/messages/{identity}/attachments/{attachment_id}/rendered")
def rendered(
    identity: UUID,
    attachment_id: UUID,
    payload: Rendered,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_section(MANAGE)),
):
    command(db, lambda: outbox.rendered(db, identity, attachment_id, payload, user.id))
    return {"recorded": True}


@router.get("/messages/{identity}/events")
def events(identity: UUID, db: Session = Depends(get_db)):
    _resource(db, identity)
    return [
        store.public_model(value)
        for value in db.scalars(
            select(CommunicationEvent)
            .where(CommunicationEvent.aggregate_id == identity)
            .order_by(CommunicationEvent.created_at)
        )
    ]


@router.get("/messages/{identity}/receipts")
def receipts(identity: UUID, db: Session = Depends(get_db)):
    _resource(db, identity)
    return [
        store.public_model(value, omit=("original",))
        for value in db.scalars(
            select(CommunicationReceipt).where(CommunicationReceipt.message_id == identity)
        )
    ]


@router.get("/messages/{identity}/receipts/{receipt_id}/original")
def original_receipt(identity: UUID, receipt_id: UUID, db: Session = Depends(get_db)):
    _resource(db, identity)
    value = db.get(CommunicationReceipt, receipt_id)
    if value is None or value.message_id != identity:
        raise HTTPException(404, detail="Ricevuta non trovata")
    return Response(
        value.original,
        media_type="message/rfc822",
        headers={
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'attachment; filename="{receipt_id}.eml"',
        },
    )


@router.get("/jobs")
def jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(CommunicationJob)
        .order_by(CommunicationJob.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [store.public_model(value, omit=("lease_token",)) for value in rows]


@router.get("/jobs/{identity}")
def job(identity: UUID, db: Session = Depends(get_db)):
    value = db.get(CommunicationJob, identity)
    if value is None:
        raise HTTPException(404, detail="Job non trovato")
    return store.public_model(value, omit=("lease_token",))
