from __future__ import annotations

from typing import Annotated
import json
from urllib.parse import quote
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
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
    RuoloTributiPaymentImportJobListResponse,
    RuoloTributiPaymentImportJobResponse,
    RuoloTributiPaymentImportUnmatchedItem,
    RuoloTributiPaymentImportUnmatchedResponse,
    RuoloTributiPaymentResponse,
    RuoloTributiPostaOnlineImportJobListResponse,
    RuoloTributiPostaOnlineImportJobResponse,
    RuoloTributiRegisteredMailListResponse,
    RuoloTributiRegisteredMailResponse,
    RuoloTributiReminderBatchCreateRequest,
    RuoloTributiReminderBatchItemResponse,
    RuoloTributiReminderBatchListResponse,
    RuoloTributiReminderBatchResponse,
    RuoloTributiReminderCandidateAvviso,
    RuoloTributiReminderCandidateListResponse,
    RuoloTributiReminderCandidateResponse,
    RuoloTributiReminderCreateRequest,
    RuoloTributiReminderResponse,
    RuoloTributiSummaryResponse,
    RuoloTributiYearManagerListResponse,
    RuoloTributiYearManagerResponse,
    RuoloTributiYearManagerUpsertRequest,
)
from app.modules.ruolo.services.tributi_reminder_service import DOCX_MEDIA_TYPE, PDF_MEDIA_TYPE

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


def _payment_import_job_to_response(job) -> RuoloTributiPaymentImportJobResponse:
    return RuoloTributiPaymentImportJobResponse.model_validate(job)


def _posta_online_import_job_to_response(job) -> RuoloTributiPostaOnlineImportJobResponse:
    return RuoloTributiPostaOnlineImportJobResponse.model_validate(job)


def _registered_mail_to_response(mail) -> RuoloTributiRegisteredMailResponse:
    return RuoloTributiRegisteredMailResponse.model_validate(mail)


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


def _candidate_to_response(candidate: dict) -> RuoloTributiReminderCandidateResponse:
    return RuoloTributiReminderCandidateResponse(
        codice_fiscale=candidate["codice_fiscale"],
        display_name=candidate["display_name"],
        comune=candidate["comune"],
        years=candidate["years"],
        avvisi_count=candidate["avvisi_count"],
        due_amount=candidate["due_amount"],
        paid_amount=candidate["paid_amount"],
        saldo_amount=candidate["saldo_amount"],
        subject_id=candidate["subject_id"],
        nas_folder_path=candidate["nas_folder_path"],
        has_nas_folder=candidate["has_nas_folder"],
        annuality_managers=candidate["annuality_managers"],
        avvisi=[RuoloTributiReminderCandidateAvviso(**avviso) for avviso in candidate["avvisi"]],
    )


def _batch_item_to_response(item) -> RuoloTributiReminderBatchItemResponse:
    download_url = (
        f"/ruolo/tributi/solleciti/items/{item.id}/download"
        if item.generated_document_path
        else None
    )
    return RuoloTributiReminderBatchItemResponse(
        id=item.id,
        batch_id=item.batch_id,
        subject_id=item.subject_id,
        codice_fiscale=item.codice_fiscale,
        display_name=item.display_name,
        comune_key=item.comune_key,
        years_json=item.years_json,
        avviso_ids_json=item.avviso_ids_json,
        due_amount=float(item.due_amount) if item.due_amount is not None else None,
        paid_amount=float(item.paid_amount),
        saldo_amount=float(item.saldo_amount) if item.saldo_amount is not None else None,
        nas_folder_path=item.nas_folder_path,
        generated_document_path=item.generated_document_path,
        status=item.status,
        error_detail=item.error_detail,
        payload_json=item.payload_json,
        created_at=item.created_at,
        updated_at=item.updated_at,
        download_url=download_url,
    )


def _batch_to_response(batch, items: list | None = None) -> RuoloTributiReminderBatchResponse:
    return RuoloTributiReminderBatchResponse(
        id=batch.id,
        title=batch.title,
        status=batch.status,
        template_path=batch.template_path,
        filters_json=batch.filters_json,
        items_total=batch.items_total,
        items_generated=batch.items_generated,
        items_failed=batch.items_failed,
        generated_by=batch.generated_by,
        generated_at=batch.generated_at,
        notes=batch.notes,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        items=[_batch_item_to_response(item) for item in (items or [])],
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
        annuality_manager_key=item["annuality_manager_key"],
        annuality_manager_label=item["annuality_manager_label"],
        calculation_policy=item["calculation_policy"],
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
        mailing_delivery=item["mailing_delivery"],
        registered_mails=[_registered_mail_to_response(mail) for mail in item["registered_mails"]],
        payments=[_payment_to_response(payment) for payment in item["payments"]],
        notes=[_note_to_response(note) for note in item["notes"]],
    )


@router.get("/year-managers", response_model=RuoloTributiYearManagerListResponse)
def list_year_managers(db: Session = Depends(get_db)) -> RuoloTributiYearManagerListResponse:
    managers = repo.list_year_managers(db)
    db.commit()
    return RuoloTributiYearManagerListResponse(
        items=[RuoloTributiYearManagerResponse.model_validate(manager) for manager in managers]
    )


@router.post(
    "/year-managers",
    response_model=RuoloTributiYearManagerResponse,
    dependencies=[Depends(require_section("ruolo.tributi.manage_status"))],
)
def create_year_manager(
    payload: RuoloTributiYearManagerUpsertRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section("ruolo.tributi.manage_status")),
) -> RuoloTributiYearManagerResponse:
    try:
        manager = repo.upsert_year_manager(
            db,
            manager_key=payload.manager_key,
            manager_label=payload.manager_label,
            year_from=payload.year_from,
            year_to=payload.year_to,
            calculation_policy=payload.calculation_policy,
            is_active=payload.is_active,
            notes=payload.notes,
            updated_by=current_user.id,
        )
        db.commit()
        db.refresh(manager)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return RuoloTributiYearManagerResponse.model_validate(manager)


@router.put(
    "/year-managers/{manager_id}",
    response_model=RuoloTributiYearManagerResponse,
    dependencies=[Depends(require_section("ruolo.tributi.manage_status"))],
)
def update_year_manager(
    manager_id: uuid.UUID,
    payload: RuoloTributiYearManagerUpsertRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section("ruolo.tributi.manage_status")),
) -> RuoloTributiYearManagerResponse:
    try:
        manager = repo.upsert_year_manager(
            db,
            manager_id=manager_id,
            manager_key=payload.manager_key,
            manager_label=payload.manager_label,
            year_from=payload.year_from,
            year_to=payload.year_to,
            calculation_policy=payload.calculation_policy,
            is_active=payload.is_active,
            notes=payload.notes,
            updated_by=current_user.id,
        )
        db.commit()
        db.refresh(manager)
    except ValueError as exc:
        db.rollback()
        if str(exc) == "Gestore annualita non trovato":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return RuoloTributiYearManagerResponse.model_validate(manager)


@router.delete(
    "/year-managers/{manager_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_section("ruolo.tributi.manage_status"))],
)
def delete_year_manager(
    manager_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    deleted = repo.delete_year_manager(db, manager_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gestore annualita non trovato")
    db.commit()


@router.get("/solleciti/candidates", response_model=RuoloTributiReminderCandidateListResponse)
def list_reminder_candidates(
    anno_from: int | None = None,
    anno_to: int | None = None,
    q: str | None = Query(default=None, min_length=1),
    comune: str | None = None,
    codice_fiscale: list[str] | None = Query(default=None),
    manager_key: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
) -> RuoloTributiReminderCandidateListResponse:
    items, total = repo.list_reminder_candidates(
        db,
        anno_from=anno_from,
        anno_to=anno_to,
        q=q,
        comune=comune,
        codice_fiscale=codice_fiscale,
        manager_key=manager_key,
        page=page,
        page_size=page_size,
    )
    return RuoloTributiReminderCandidateListResponse(
        items=[_candidate_to_response(candidate) for candidate in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/solleciti/batches",
    response_model=RuoloTributiReminderBatchResponse,
    dependencies=[Depends(require_section("ruolo.tributi.generate_reminders"))],
)
def create_reminder_batch(
    payload: RuoloTributiReminderBatchCreateRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section("ruolo.tributi.generate_reminders")),
) -> RuoloTributiReminderBatchResponse:
    try:
        batch = repo.create_reminder_batch(
            db,
            title=payload.title,
            codice_fiscale=payload.codice_fiscale,
            filters=payload.filters,
            template_path=payload.template_path,
            notes=payload.notes,
            generated_by=current_user.id,
        )
        db.commit()
        db.refresh(batch)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _batch_to_response(batch, repo.list_reminder_batch_items(db, batch.id))


@router.get("/solleciti/batches", response_model=RuoloTributiReminderBatchListResponse)
def list_reminder_batches(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> RuoloTributiReminderBatchListResponse:
    items, total = repo.list_reminder_batches(db, page=page, page_size=page_size)
    return RuoloTributiReminderBatchListResponse(
        items=[_batch_to_response(batch) for batch in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/solleciti/batches/{batch_id}", response_model=RuoloTributiReminderBatchResponse)
def get_reminder_batch(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> RuoloTributiReminderBatchResponse:
    batch = repo.get_reminder_batch(db, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch solleciti non trovato")
    return _batch_to_response(batch, repo.list_reminder_batch_items(db, batch.id))


@router.get("/solleciti/items/{item_id}/download")
def download_reminder_batch_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Response:
    item = repo.get_reminder_batch_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sollecito batch non trovato")
    path = repo.reminder_batch_item_document_path(item)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento sollecito non trovato")
    media_type = DOCX_MEDIA_TYPE if path.suffix.lower() == ".docx" else PDF_MEDIA_TYPE
    if repo.is_remote_reminder_document_path(path):
        return _remote_document_response(path, media_type=media_type)
    return FileResponse(path, media_type=media_type, filename=path.name)


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
    manager_key: str | None = None,
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
        manager_key=manager_key,
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


@router.get("/summary", response_model=RuoloTributiSummaryResponse)
def get_tributi_summary(
    anno: int | None = None,
    subject_id: str | None = None,
    q: str | None = Query(default=None, min_length=1),
    codice_fiscale: str | None = None,
    comune: str | None = None,
    codice_utenza: str | None = None,
    unlinked: bool = False,
    payment_status: str | None = None,
    workflow_status: str | None = None,
    manager_key: str | None = None,
    open_only: bool = False,
    db: Session = Depends(get_db),
) -> RuoloTributiSummaryResponse:
    return RuoloTributiSummaryResponse(
        **repo.get_tributi_summary(
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
            manager_key=manager_key,
            open_only=open_only,
        )
    )


@router.post(
    "/import-pagamenti",
    response_model=RuoloTributiPaymentImportJobResponse,
    dependencies=[Depends(require_section("ruolo.tributi.import_payments"))],
)
async def import_tributi_payments(
    file: Annotated[UploadFile, File()],
    mapping_json: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section("ruolo.tributi.import_payments")),
) -> RuoloTributiPaymentImportJobResponse:
    mapping: dict[str, str] | None = None
    if mapping_json:
        try:
            parsed_mapping = json.loads(mapping_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="mapping_json non valido") from exc
        if not isinstance(parsed_mapping, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in parsed_mapping.items()):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="mapping_json deve essere un oggetto stringa/stringa")
        mapping = parsed_mapping

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File import pagamenti vuoto")

    job = repo.import_capacitas_payments(
        db,
        filename=file.filename,
        content=content,
        mapping=mapping,
        triggered_by=current_user.id,
    )
    db.commit()
    db.refresh(job)
    return _payment_import_job_to_response(job)


@router.get("/import-pagamenti/jobs", response_model=RuoloTributiPaymentImportJobListResponse)
def list_tributi_payment_import_jobs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> RuoloTributiPaymentImportJobListResponse:
    items, total = repo.list_payment_import_jobs(db, page=page, page_size=page_size)
    return RuoloTributiPaymentImportJobListResponse(
        items=[_payment_import_job_to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/import-pagamenti/jobs/{job_id}", response_model=RuoloTributiPaymentImportJobResponse)
def get_tributi_payment_import_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> RuoloTributiPaymentImportJobResponse:
    job = repo.get_payment_import_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job import pagamenti non trovato")
    return _payment_import_job_to_response(job)


@router.get("/import-pagamenti/jobs/{job_id}/unmatched", response_model=RuoloTributiPaymentImportUnmatchedResponse)
def list_tributi_payment_import_unmatched(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> RuoloTributiPaymentImportUnmatchedResponse:
    job = repo.get_payment_import_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job import pagamenti non trovato")
    items = repo.payment_import_unmatched_items(job)
    return RuoloTributiPaymentImportUnmatchedResponse(
        job_id=job.id,
        items=[RuoloTributiPaymentImportUnmatchedItem(**item) for item in items],
        total=len(items),
    )


@router.post(
    "/raccomandate/import-posta-online",
    response_model=RuoloTributiPostaOnlineImportJobResponse,
    dependencies=[Depends(require_section("ruolo.tributi.import_payments"))],
)
async def import_posta_online_registered_mails(
    file: Annotated[UploadFile, File()],
    annualita_json: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section("ruolo.tributi.import_payments")),
) -> RuoloTributiPostaOnlineImportJobResponse:
    annualita: list[int] | None = None
    if annualita_json:
        try:
            parsed_annualita = json.loads(annualita_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="annualita_json non valido") from exc
        if not isinstance(parsed_annualita, list):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="annualita_json deve essere una lista")
        annualita = [
            int(year)
            for year in parsed_annualita
            if isinstance(year, int) or (isinstance(year, str) and year.strip().isdigit())
        ]

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File import raccomandate vuoto")

    job = repo.import_posta_online_registered_mails(
        db,
        filename=file.filename,
        content=content,
        annualita=annualita,
        triggered_by=current_user.id,
    )
    db.commit()
    db.refresh(job)
    return _posta_online_import_job_to_response(job)


@router.get("/raccomandate/jobs", response_model=RuoloTributiPostaOnlineImportJobListResponse)
def list_posta_online_import_jobs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> RuoloTributiPostaOnlineImportJobListResponse:
    items, total = repo.list_posta_online_import_jobs(db, page=page, page_size=page_size)
    return RuoloTributiPostaOnlineImportJobListResponse(
        items=[_posta_online_import_job_to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/raccomandate/jobs/{job_id}", response_model=RuoloTributiPostaOnlineImportJobResponse)
def get_posta_online_import_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> RuoloTributiPostaOnlineImportJobResponse:
    job = repo.get_posta_online_import_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job import raccomandate non trovato")
    return _posta_online_import_job_to_response(job)


@router.get("/raccomandate", response_model=RuoloTributiRegisteredMailListResponse)
def list_registered_mails(
    avviso_id: uuid.UUID | None = None,
    import_job_id: uuid.UUID | None = None,
    match_status: str | None = None,
    recovery_status: str | None = None,
    q: str | None = Query(default=None, min_length=1),
    anomalies_only: bool = False,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
) -> RuoloTributiRegisteredMailListResponse:
    items, total = repo.list_registered_mails(
        db,
        avviso_id=avviso_id,
        import_job_id=import_job_id,
        match_status=match_status,
        recovery_status=recovery_status,
        q=q,
        anomalies_only=anomalies_only,
        page=page,
        page_size=page_size,
    )
    return RuoloTributiRegisteredMailListResponse(
        items=[_registered_mail_to_response(item) for item in items],
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
) -> Response:
    reminder = repo.get_reminder(db, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sollecito non trovato")
    path = repo.reminder_document_path(reminder)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento sollecito non trovato")
    if repo.is_remote_reminder_document_path(path):
        return _remote_document_response(path, media_type=DOCX_MEDIA_TYPE)
    return FileResponse(path, media_type=DOCX_MEDIA_TYPE, filename=path.name)


def _remote_document_response(path, *, media_type: str) -> Response:
    try:
        content = repo.read_remote_reminder_document(path)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento sollecito non trovato") from exc

    filename = path.name
    quoted_filename = quote(filename)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}"},
    )
