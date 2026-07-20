from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloAvviso, RuoloTributiNote, RuoloTributiPayment, RuoloTributiReminder
from app.modules.ruolo.schemas import (
    RuoloTributiAvvisoDetailResponse,
    RuoloTributiAvvisoListItemResponse,
    RuoloTributiAvvisoListResponse,
    RuoloTributiAvvisoStatusResponse,
    RuoloTributiAvvisoStatusUpdateRequest,
    RuoloTributiNoteCreateRequest,
    RuoloTributiNoteResponse,
    RuoloTributiPaymentCreateRequest,
    RuoloTributiPaymentResponse,
    RuoloTributiReminderCreateRequest,
    RuoloTributiReminderResponse,
)
from app.modules.ruolo.services.tributi_reminder_service import DOCX_MEDIA_TYPE

router = APIRouter(
    prefix="/tributi",
    tags=["ruolo-tributi"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)


def _payment_to_response(payment: RuoloTributiPayment) -> RuoloTributiPaymentResponse:
    return RuoloTributiPaymentResponse(
        id=payment.id,
        avviso_id=payment.avviso_id,
        import_job_id=payment.import_job_id,
        codice_cnc_raw=payment.codice_cnc_raw,
        codice_utenza_raw=payment.codice_utenza_raw,
        anno_tributario=payment.anno_tributario,
        paid_at=payment.paid_at,
        amount=float(payment.amount),
        payment_reference=payment.payment_reference,
        payment_method=payment.payment_method,
        source=payment.source,
        status=payment.status,
        raw_payload_json=payment.raw_payload_json,
        created_by=payment.created_by,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )


def _note_to_response(note: RuoloTributiNote) -> RuoloTributiNoteResponse:
    return RuoloTributiNoteResponse(
        id=note.id,
        avviso_id=note.avviso_id,
        body=note.body,
        visibility=note.visibility,
        created_by=note.created_by,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def _reminder_to_response(reminder: RuoloTributiReminder) -> RuoloTributiReminderResponse:
    download_url = (
        f"/ruolo/tributi/reminders/{reminder.id}/download"
        if reminder.generated_document_path
        else None
    )
    return RuoloTributiReminderResponse(
        id=reminder.id,
        avviso_id=reminder.avviso_id,
        template_id=reminder.template_id,
        status=reminder.status,
        generated_document_path=reminder.generated_document_path,
        generated_at=reminder.generated_at,
        generated_by=reminder.generated_by,
        payload_json=reminder.payload_json,
        notes=reminder.notes,
        created_at=reminder.created_at,
        download_url=download_url,
    )


def _item_to_response(item: dict) -> RuoloTributiAvvisoListItemResponse:
    avviso: RuoloAvviso = item["avviso"]
    return RuoloTributiAvvisoListItemResponse(
        id=avviso.id,
        codice_cnc=avviso.codice_cnc,
        anno_tributario=avviso.anno_tributario,
        subject_id=avviso.subject_id,
        codice_fiscale_raw=avviso.codice_fiscale_raw,
        nominativo_raw=avviso.nominativo_raw,
        codice_utenza=avviso.codice_utenza,
        importo_totale_euro=float(avviso.importo_totale_euro) if avviso.importo_totale_euro is not None else None,
        paid_amount=item["paid_amount"],
        saldo_amount=item["saldo_amount"],
        payment_status=item["payment_status"],
        workflow_status=item["workflow_status"],
        last_payment_at=item["last_payment_at"],
        capacitas_url=item["capacitas_url"],
        capacitas_avviso_code=item["capacitas_avviso_code"],
        display_name=item["display_name"],
        is_linked=item["is_linked"],
        notes_count=item["notes_count"],
    )


def _detail_to_response(item: dict) -> RuoloTributiAvvisoDetailResponse:
    list_item = _item_to_response(item)
    avviso: RuoloAvviso = item["avviso"]
    return RuoloTributiAvvisoDetailResponse(
        **list_item.model_dump(),
        domicilio_raw=avviso.domicilio_raw,
        residenza_raw=avviso.residenza_raw,
        importo_totale_0648=float(avviso.importo_totale_0648) if avviso.importo_totale_0648 is not None else None,
        importo_totale_0985=float(avviso.importo_totale_0985) if avviso.importo_totale_0985 is not None else None,
        importo_totale_0668=float(avviso.importo_totale_0668) if avviso.importo_totale_0668 is not None else None,
        payments=[_payment_to_response(payment) for payment in item["payments"]],
        notes=[_note_to_response(note) for note in item["notes"]],
    )


@router.get("/avvisi", response_model=RuoloTributiAvvisoListResponse)
def list_tributi_avvisi(
    anno: int | None = None,
    subject_id: str | None = None,
    q: str | None = Query(default=None, min_length=1),
    codice_fiscale: str | None = None,
    comune: str | None = None,
    codice_utenza: str | None = None,
    unlinked: bool = False,
    payment_status: str | None = None,
    workflow_status: str | None = None,
    open_only: bool = False,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> RuoloTributiAvvisoListResponse:
    items, total = repo.list_tributi_avvisi(
        db,
        anno=anno,
        subject_id=subject_id,
        q=q,
        codice_fiscale=codice_fiscale,
        comune=comune,
        codice_utenza=codice_utenza,
        unlinked=unlinked,
        payment_status=payment_status,
        workflow_status=workflow_status,
        open_only=open_only,
        page=page,
        page_size=page_size,
    )
    return RuoloTributiAvvisoListResponse(
        items=[_item_to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/avvisi/{avviso_id}", response_model=RuoloTributiAvvisoDetailResponse)
def get_tributi_avviso(
    avviso_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> RuoloTributiAvvisoDetailResponse:
    item = repo.get_tributi_avviso(db, avviso_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avviso tributi non trovato")
    return _detail_to_response(item)


@router.post(
    "/avvisi/{avviso_id}/payments",
    response_model=RuoloTributiPaymentResponse,
    dependencies=[Depends(require_section("ruolo.tributi.manage_payments"))],
)
def create_payment(
    avviso_id: uuid.UUID,
    payload: RuoloTributiPaymentCreateRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section("ruolo.tributi.manage_payments")),
) -> RuoloTributiPaymentResponse:
    avviso = db.get(RuoloAvviso, avviso_id)
    if avviso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avviso non trovato")

    try:
        payment = repo.create_payment(
            db,
            avviso=avviso,
            amount=payload.amount,
            paid_at=payload.paid_at,
            payment_reference=payload.payment_reference,
            payment_method=payload.payment_method,
            source=payload.source,
            status=payload.status,
            raw_payload_json=payload.raw_payload_json,
            created_by=current_user.id,
        )
        db.commit()
        db.refresh(payment)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pagamento gia presente per source/reference",
        ) from exc

    return _payment_to_response(payment)


@router.patch(
    "/avvisi/{avviso_id}/status",
    response_model=RuoloTributiAvvisoStatusResponse,
    dependencies=[Depends(require_section("ruolo.tributi.manage_status"))],
)
def update_avviso_status(
    avviso_id: uuid.UUID,
    payload: RuoloTributiAvvisoStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section("ruolo.tributi.manage_status")),
) -> RuoloTributiAvvisoStatusResponse:
    avviso = db.get(RuoloAvviso, avviso_id)
    if avviso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avviso non trovato")

    try:
        status_row = repo.update_avviso_status(
            db,
            avviso=avviso,
            workflow_status=payload.workflow_status,
            capacitas_url=payload.capacitas_url,
            capacitas_avviso_code=payload.capacitas_avviso_code,
            updated_by=current_user.id,
        )
        db.commit()
        db.refresh(status_row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return RuoloTributiAvvisoStatusResponse.model_validate(status_row)


@router.post(
    "/avvisi/{avviso_id}/notes",
    response_model=RuoloTributiNoteResponse,
    dependencies=[Depends(require_section("ruolo.tributi.manage_notes"))],
)
def add_note(
    avviso_id: uuid.UUID,
    payload: RuoloTributiNoteCreateRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section("ruolo.tributi.manage_notes")),
) -> RuoloTributiNoteResponse:
    if db.get(RuoloAvviso, avviso_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avviso non trovato")

    note = repo.add_note(
        db,
        avviso_id=avviso_id,
        body=payload.body,
        visibility=payload.visibility,
        created_by=current_user.id,
    )
    db.commit()
    db.refresh(note)
    return _note_to_response(note)


@router.post(
    "/avvisi/{avviso_id}/reminders",
    response_model=RuoloTributiReminderResponse,
    dependencies=[Depends(require_section("ruolo.tributi.generate_reminders"))],
)
def create_reminder(
    avviso_id: uuid.UUID,
    payload: RuoloTributiReminderCreateRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section("ruolo.tributi.generate_reminders")),
) -> RuoloTributiReminderResponse:
    avviso = db.get(RuoloAvviso, avviso_id)
    if avviso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avviso non trovato")

    reminder = repo.create_generated_reminder(
        db,
        avviso=avviso,
        template_id=payload.template_id,
        notes=payload.notes,
        generated_by=current_user.id,
    )
    db.commit()
    db.refresh(reminder)
    return _reminder_to_response(reminder)


@router.get("/avvisi/{avviso_id}/reminders", response_model=list[RuoloTributiReminderResponse])
def list_reminders(
    avviso_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[RuoloTributiReminderResponse]:
    if db.get(RuoloAvviso, avviso_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avviso non trovato")
    return [_reminder_to_response(reminder) for reminder in repo.list_reminders(db, avviso_id)]


@router.get("/reminders/{reminder_id}/download")
def download_reminder(
    reminder_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> FileResponse:
    reminder = repo.get_reminder(db, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sollecito non trovato")
    path = repo.reminder_document_path(reminder)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento sollecito non trovato")
    return FileResponse(path, media_type=DOCX_MEDIA_TYPE, filename=path.name)
