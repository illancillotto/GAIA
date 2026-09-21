"""Protected operational register. No endpoint sends notices or imports files."""

from contextlib import contextmanager
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo import notice_register_queries as queries
from app.modules.ruolo.notice_lifecycle_schemas import DocumentEligibility, RecordedAttempt
from app.modules.ruolo.notice_register_api_schemas import (
    AttemptView,
    AuditView,
    CandidateFilters,
    CandidateResult,
    DocumentDetail,
    DocumentSummary,
    EvidenceView,
    LinkInput,
    ManualEvidence,
    Mutation,
    MutationResult,
    Page,
    Pagination,
    ReconciliationInput,
    RegisterFilters,
)
from app.modules.ruolo.notice_register_models import NoticeDocument, NoticePosition
from app.modules.ruolo.notice_register_schemas import (
    DocumentDetails,
    EvidenceInput,
    HistoricalDocument,
    NotificationDecision,
    OperatorChange,
    PositionInput,
    RecoveryDecision,
)
from app.modules.ruolo.services import notice_register as service
from app.modules.ruolo.services.notice_attempts import record_attempt
from app.modules.ruolo.services.notice_document_eligibility import document_eligibility
from app.modules.ruolo.services.notice_reconciliation import reconcile_poste
from app.modules.ruolo.services.notice_reconciliation_undo import undo_reconciliation

router = APIRouter(
    prefix="/tributi/registro-avvisi",
    tags=["ruolo-registro-avvisi"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)
Database = Annotated[Session, Depends(get_db)]
Editor = Annotated[ApplicationUser, Depends(require_section("ruolo.tributi.manage_status"))]


def require_document(document_id: UUID, db: Database) -> NoticeDocument:
    document = db.get(NoticeDocument, document_id)
    if document is None:
        raise HTTPException(404, "Documento non trovato")
    return document


def require_position(document_id: UUID, position_id: UUID, db: Database) -> NoticePosition:
    position = db.get(NoticePosition, position_id)
    if position is None or position.document_id != document_id:
        raise HTTPException(404, "Posizione non appartenente al documento")
    return position


Document = Annotated[NoticeDocument, Depends(require_document)]
Position = Annotated[NoticePosition, Depends(require_position)]


@contextmanager
def _command(db: Session, user: ApplicationUser, payload: Mutation):
    try:
        yield OperatorChange(
            actor_id=user.id,
            reason=payload.reason,
            expected_version=payload.expected_version,
        )
        db.commit()
    except service.RegisterNotFound as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc
    except (service.RegisterConflict, IntegrityError, StaleDataError) as exc:
        db.rollback()
        raise HTTPException(
            409, "Conflitto di versione o riferimento duplicato: ricaricare il registro"
        ) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc


def _result(db: Session, document_id: UUID, resource_id: UUID) -> MutationResult:
    return MutationResult(
        document_id=document_id,
        version=db.get(NoticeDocument, document_id).version,
        resource_id=resource_id,
    )


@router.get("", response_model=Page[DocumentSummary])
def list_register(db: Database, filters: Annotated[RegisterFilters, Query()]):
    return queries.list_documents(db, filters)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document: Document, db: Database):
    return queries.document_detail(db, document)


@router.get(
    "/{document_id}/posizioni/{position_id}/candidati", response_model=Page[CandidateResult]
)
def get_candidates(position: Position, db: Database, filters: Annotated[CandidateFilters, Query()]):
    return queries.search_candidates(db, position, filters)


@router.get("/{document_id}/evidenze", response_model=Page[EvidenceView])
def get_evidence(document: Document, db: Database, pagination: Annotated[Pagination, Query()]):
    return queries.document_events(db, document.id, "evidenze", pagination)


@router.get("/{document_id}/invii", response_model=Page[AttemptView])
def get_attempts(document: Document, db: Database, pagination: Annotated[Pagination, Query()]):
    return queries.document_events(db, document.id, "invii", pagination)


@router.get("/{document_id}/ammissibilita", response_model=DocumentEligibility)
def get_eligibility(document: Document, db: Database):
    return document_eligibility(db, document)


@router.post("/{document_id}/invii", response_model=MutationResult, status_code=201)
def create_attempt(
    document_id: UUID, payload: Mutation[RecordedAttempt], db: Database, user: Editor
):
    with _command(db, user, payload) as change:
        attempt = record_attempt(db, document_id, payload.data, change)
        return _result(db, document_id, attempt.id)


@router.get("/{document_id}/storico", response_model=Page[AuditView])
def get_audit(document: Document, db: Database, pagination: Annotated[Pagination, Query()]):
    return queries.document_events(db, document.id, "storico", pagination)


@router.post("", response_model=MutationResult, status_code=201)
def create_document(payload: Mutation[HistoricalDocument], db: Database, user: Editor):
    with _command(db, user, payload) as change:
        document = service.create_historical_document(db, payload.data, change)
        return _result(db, document.id, document.id)


@router.put("/{document_id}", response_model=MutationResult)
def update_document(
    document_id: UUID, payload: Mutation[DocumentDetails], db: Database, user: Editor
):
    with _command(db, user, payload) as change:
        service.revise_document(db, document_id, payload.data, change)
        return _result(db, document_id, document_id)


@router.post("/{document_id}/riconciliazione", response_model=MutationResult)
def reconcile_document(
    document_id: UUID, payload: Mutation[ReconciliationInput], db: Database, user: Editor
):
    with _command(db, user, payload) as change:
        target = reconcile_poste(db, document_id, payload.data, change)
        return _result(db, target.id, document_id)


@router.post("/{document_id}/posizioni", response_model=MutationResult, status_code=201)
def create_position(
    document_id: UUID, payload: Mutation[PositionInput], db: Database, user: Editor
):
    with _command(db, user, payload) as change:
        position = service.add_position(db, document_id, payload.data, change)
        return _result(db, document_id, position.id)


@router.post("/{document_id}/riconciliazione/annulla", response_model=MutationResult)
def undo_document_reconciliation(
    document_id: UUID, payload: Mutation[ReconciliationInput], db: Database, user: Editor
):
    with _command(db, user, payload) as change:
        source = undo_reconciliation(db, document_id, payload.data, change)
        return _result(db, source.id, source.id)


@router.put("/{document_id}/posizioni/{position_id}", response_model=MutationResult)
def update_position(
    document_id: UUID,
    position_id: UUID,
    payload: Mutation[PositionInput],
    db: Database,
    user: Editor,
):
    with _command(db, user, payload) as change:
        service.revise_position(db, document_id, position_id, payload.data, change)
        return _result(db, document_id, position_id)


@router.put("/{document_id}/posizioni/{position_id}/collegamento", response_model=MutationResult)
def update_link(
    document_id: UUID,
    position_id: UUID,
    payload: Mutation[LinkInput],
    db: Database,
    user: Editor,
):
    with _command(db, user, payload) as change:
        service.link_position(db, document_id, position_id, payload.data.avviso_id, change)
        return _result(db, document_id, position_id)


@router.post("/{document_id}/evidenze", response_model=MutationResult, status_code=201)
def create_evidence(
    document_id: UUID, payload: Mutation[ManualEvidence], db: Database, user: Editor
):
    with _command(db, user, payload) as change:
        evidence = service.record_evidence(
            db,
            document_id,
            EvidenceInput(
                **payload.data.model_dump(),
                source_system="manual",
                source_key=str(uuid4()),
                original_json=payload.data.model_dump(mode="json"),
            ),
            change,
        )
        return _result(db, document_id, evidence.id)


@router.put("/{document_id}/notifica", response_model=MutationResult)
def update_notification(
    document_id: UUID,
    payload: Mutation[NotificationDecision],
    db: Database,
    user: Editor,
):
    with _command(db, user, payload) as change:
        service.assess_notification(db, document_id, payload.data, change)
        return _result(db, document_id, document_id)


@router.put("/{document_id}/posizioni/{position_id}/step", response_model=MutationResult)
def update_recovery(
    document_id: UUID,
    position_id: UUID,
    payload: Mutation[RecoveryDecision],
    db: Database,
    user: Editor,
):
    with _command(db, user, payload) as change:
        service.assess_recovery(db, document_id, position_id, payload.data, change)
        return _result(db, document_id, position_id)
