"""Admin classification surface used by Communications; no transport side effects."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin_user, require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.utenze.contact_models import AnagraficaElectronicContact as Contact
from app.modules.utenze.contact_schemas import ContactClassification
from app.modules.utenze.services import electronic_contacts as service

router = APIRouter(
    prefix="/admin/subjects",
    dependencies=[
        Depends(require_admin_user),
        Depends(require_module("ruolo")),
        Depends(require_section("ruolo.tributi.view")),
    ],
)


@router.get("/{subject_id}/contacts")
def contacts(subject_id: UUID, db: Session = Depends(get_db)):
    values = db.scalars(
        select(Contact).where(Contact.subject_id == subject_id).order_by(Contact.address)
    )
    return {
        "resolved": service.contact_values(db, subject_id),
        "items": [service.public_contact(value) for value in values],
    }


@router.put("/{subject_id}/contacts")
def classify(
    subject_id: UUID,
    payload: ContactClassification,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_admin_user),
):
    try:
        value = service.classify(db, subject_id, payload, user.id)
        db.commit()
        return service.public_contact(value)
    except service.ContactMissing as exc:
        db.rollback()
        raise HTTPException(404, detail=str(exc)) from exc
    except (service.ContactConflict, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(
            409, detail="Classificazione non applicabile o modificata: ricaricare"
        ) from exc
