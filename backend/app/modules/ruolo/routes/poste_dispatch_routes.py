"""Posta Online drafts for reminders. The operator presses INVIA on Poste, never GAIA."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo.poste_dispatch_schemas import (
    PosteDispatchCandidate,
    PosteDispatchCandidateList,
    PosteDispatchItemOut,
    PosteDispatchJobOut,
    PosteDispatchJobRequest,
    PosteDispatchLotCreate,
    PosteDispatchLotDetail,
    PosteDispatchLotList,
    PosteDispatchRecipientUpdate,
)
from app.modules.ruolo.services import poste_dispatch as service
from app.modules.ruolo.services import poste_dispatch_views as views
from app.modules.ruolo.services.poste_dispatch_state import DispatchConflict, DispatchNotFound

MANAGE = "ruolo.tributi.manage_status"
router = APIRouter(
    prefix="/tributi/poste-dispatch",
    tags=["ruolo-tributi"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)


def _command(db: Session, action):
    try:
        result = action()
        db.commit()
    except DispatchNotFound as exc:
        db.rollback()
        raise HTTPException(404, detail=str(exc)) from exc
    except (DispatchConflict, ValueError) as exc:
        db.rollback()
        raise HTTPException(409, detail=str(exc)) from exc
    return result


@router.get("/candidates", response_model=PosteDispatchCandidateList)
def list_candidates(
    q: str | None = None, page: int = 1, page_size: int = 50, db: Session = Depends(get_db)
):
    rows, total = service.list_candidates(db, q=q, page=page, page_size=page_size)
    items = [
        PosteDispatchCandidate(
            batch_item_id=item.id,
            batch_title=title,
            display_name=item.display_name,
            codice_fiscale=item.codice_fiscale,
            notice_number=(item.payload_json or {}).get("notice_number"),
            years=item.years_json or [],
            created_at=item.created_at,
        )
        for item, title in rows
    ]
    return PosteDispatchCandidateList(items=items, total=total, page=page, page_size=page_size)


@router.get("/lots", response_model=PosteDispatchLotList)
def list_lots(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    items, total = views.list_lots(db, page=page, page_size=page_size)
    return PosteDispatchLotList(items=items, total=total, page=page, page_size=page_size)


@router.post("/lots", response_model=PosteDispatchLotDetail)
def create_lot(
    payload: PosteDispatchLotCreate,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section(MANAGE)),
):
    lot = _command(
        db,
        lambda: service.create_lot(
            db, title=payload.title, batch_item_ids=payload.batch_item_ids, actor_id=current_user.id
        ),
    )
    return views.lot_detail(db, lot.id)


@router.get("/lots/{lot_id}", response_model=PosteDispatchLotDetail)
def get_lot(lot_id: UUID, db: Session = Depends(get_db)):
    try:
        return views.lot_detail(db, lot_id)
    except DispatchNotFound as exc:
        raise HTTPException(404, detail=str(exc)) from exc


@router.post("/lots/{lot_id}/jobs", response_model=PosteDispatchJobOut)
def request_job(
    lot_id: UUID,
    payload: PosteDispatchJobRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section(MANAGE)),
):
    job = _command(
        db, lambda: service.request_job(db, lot_id, payload.kind, actor_id=current_user.id)
    )
    return PosteDispatchJobOut.model_validate(job, from_attributes=True)


@router.put("/lots/{lot_id}/items/{item_id}/recipient", response_model=PosteDispatchItemOut)
def update_recipient(
    lot_id: UUID,
    item_id: UUID,
    payload: PosteDispatchRecipientUpdate,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section(MANAGE)),
):
    fields = payload.model_dump()
    return _command(
        db, lambda: service.update_recipient(db, lot_id, item_id, fields, actor_id=current_user.id)
    )


@router.post("/lots/{lot_id}/items/{item_id}/manual-address", response_model=PosteDispatchItemOut)
def accept_manual_address(
    lot_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section(MANAGE)),
):
    return _command(
        db, lambda: service.accept_manual_address(db, lot_id, item_id, actor_id=current_user.id)
    )


@router.post("/lots/{lot_id}/items/{item_id}/cancel", response_model=PosteDispatchItemOut)
def cancel_item(
    lot_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section(MANAGE)),
):
    return _command(db, lambda: service.cancel_item(db, lot_id, item_id, actor_id=current_user.id))


@router.get("/lots/{lot_id}/items/{item_id}/document")
def item_document(lot_id: UUID, item_id: UUID, db: Session = Depends(get_db)):
    content = views.item_document(db, lot_id, item_id)
    if content is None:
        raise HTTPException(404, detail="PDF non più conservato: avviso spedito o annullato")
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{item_id}.pdf"',
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
        },
    )
