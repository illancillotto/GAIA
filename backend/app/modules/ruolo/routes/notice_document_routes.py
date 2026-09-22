"""Authenticated draft previews and audited final batch downloads."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo.services.notice_draft_review import DraftReviewBlocked
from app.modules.ruolo.services.notice_export import export_batch
from app.modules.ruolo.services.notice_preview import PreviewUnavailable, preview_item
from app.modules.ruolo.services.notice_revision import (
    GenerationRevisionChanged,
    RevisionProtocolUnavailable,
)

router = APIRouter(
    prefix="/tributi/solleciti/batches",
    tags=["ruolo-tributi"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)


def _download(content, filename, media_type):
    return Response(
        content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{batch_id}/items/{item_id}/preview")
def preview_reminder_item(batch_id: UUID, item_id: UUID, db: Session = Depends(get_db)):
    try:
        content = preview_item(db.get_bind(), batch_id, item_id)
    except LookupError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except DraftReviewBlocked as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    except PreviewUnavailable as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    return _download(content, f"bozza-{item_id}.pdf", "application/pdf")


@router.post("/{batch_id}/export")
def export_reminder_batch(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section("ruolo.tributi.manage_status")),
):
    try:
        content = export_batch(db.get_bind(), batch_id, current_user.id)
    except (DraftReviewBlocked, GenerationRevisionChanged) as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    except RevisionProtocolUnavailable as exc:
        raise HTTPException(503, detail="Protocollo di export non disponibile") from exc
    return _download(content, f"solleciti-{batch_id}-v1.zip", "application/zip")
