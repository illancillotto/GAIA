import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.payer_assignment_models import RuoloTributiPayerAssignment
from app.modules.ruolo.payer_assignment_schemas import (
    PayerAssignmentRequest,
    PayerAssignmentsResponse,
    PayerAssignmentView,
)
from app.modules.ruolo.services import payer_assignments as service

router = APIRouter(
    prefix="/tributi/avvisi",
    tags=["ruolo-tributi"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)
Database = Annotated[Session, Depends(get_db)]
Editor = Annotated[ApplicationUser, Depends(require_section("ruolo.tributi.manage_status"))]


def _view(db: Session, row: RuoloTributiPayerAssignment) -> PayerAssignmentView:
    payer = service.load_payer(db, row.payer_subject_id)
    return PayerAssignmentView(
        id=row.id,
        reason=row.reason,
        reason_label=service.REASON_LABELS[row.reason],
        notes=row.notes,
        payer_subject_id=row.payer_subject_id,
        payer_tax_code=payer.tax_code if payer else None,
        payer_name=payer.name if payer else None,
        payer_address=payer.address if payer else None,
        created_at=row.created_at,
        voided_at=row.voided_at,
    )


def _response(db: Session, avviso_id: uuid.UUID) -> PayerAssignmentsResponse:
    if db.get(RuoloAvviso, avviso_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avviso non trovato")
    rows = service.history(db, avviso_id)
    active = next((row for row in rows if row.voided_at is None), None)
    return PayerAssignmentsResponse(
        active=_view(db, active) if active else None, history=[_view(db, row) for row in rows]
    )


@router.get("/{avviso_id}/payer", response_model=PayerAssignmentsResponse)
def get_payer(avviso_id: uuid.UUID, db: Database) -> PayerAssignmentsResponse:
    return _response(db, avviso_id)


@router.put("/{avviso_id}/payer", response_model=PayerAssignmentsResponse)
def set_payer(
    avviso_id: uuid.UUID, payload: PayerAssignmentRequest, db: Database, current_user: Editor
) -> PayerAssignmentsResponse:
    try:
        service.assign(
            db,
            avviso_id=avviso_id,
            payer_tax_code=payload.payer_tax_code,
            reason=payload.reason,
            notes=payload.notes,
            user_id=current_user.id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    db.commit()
    return _response(db, avviso_id)


@router.delete("/{avviso_id}/payer", response_model=PayerAssignmentsResponse)
def remove_payer(
    avviso_id: uuid.UUID, db: Database, current_user: Editor
) -> PayerAssignmentsResponse:
    service.void(db, avviso_id, current_user.id)
    db.commit()
    return _response(db, avviso_id)
