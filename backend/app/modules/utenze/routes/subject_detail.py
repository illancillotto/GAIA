import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.utenze.models import (
    AnagraficaAuditLog,
    AnagraficaCompany,
    AnagraficaDocument,
    AnagraficaPerson,
    AnagraficaPersonSnapshot,
)
from app.modules.utenze.routes.support import (
    _build_catasto_correlations,
    _build_document_response,
    _require_subject_exists,
    _should_skip_document,
)
from app.modules.utenze.schemas import (
    AnagraficaAuditLogResponse,
    AnagraficaCompanyResponse,
    AnagraficaPersonResponse,
    AnagraficaPersonSnapshotResponse,
    AnagraficaSubjectDetailResponse,
)


# Preserve reviewed legacy callable layout for the merge-base LOC ratchet.
# fmt: off
def _build_subject_detail(db: Session, subject_id: uuid.UUID) -> AnagraficaSubjectDetailResponse:
    subject = _require_subject_exists(db, subject_id)
    person = db.get(AnagraficaPerson, subject_id)
    company = db.get(AnagraficaCompany, subject_id)
    documents = db.scalars(
        select(AnagraficaDocument)
        .where(AnagraficaDocument.subject_id == subject_id)
        .order_by(AnagraficaDocument.created_at.desc())
    ).all()
    documents = [item for item in documents if not _should_skip_document(item)]
    audit_entries = db.scalars(
        select(AnagraficaAuditLog)
        .where(AnagraficaAuditLog.subject_id == subject_id)
        .order_by(AnagraficaAuditLog.changed_at.desc())
    ).all()
    person_snapshots = db.scalars(
        select(AnagraficaPersonSnapshot)
        .where(AnagraficaPersonSnapshot.subject_id == subject_id)
        .order_by(AnagraficaPersonSnapshot.collected_at.desc())
    ).all()
    person_response = None
    company_response = None
    if person is not None:
        person_response = AnagraficaPersonResponse.model_validate(
                {
                    "subject_id": str(person.subject_id),
                    "cognome": person.cognome,
                    "nome": person.nome,
                    "codice_fiscale": person.codice_fiscale,
                    "data_nascita": person.data_nascita,
                    "comune_nascita": person.comune_nascita,
                    "indirizzo": person.indirizzo,
                    "comune_residenza": person.comune_residenza,
                    "cap": person.cap,
                    "email": person.email,
                    "telefono": person.telefono,
                    "note": person.note,
                    "anpr_id": person.anpr_id,
                    "stato_anpr": person.stato_anpr,
                    "data_decesso": person.data_decesso,
                    "luogo_decesso_comune": person.luogo_decesso_comune,
                    "created_at": person.created_at,
                    "updated_at": person.updated_at,
                }
            )
    if company is not None:
        company_response = AnagraficaCompanyResponse.model_validate(
            {
                "subject_id": str(company.subject_id),
                "ragione_sociale": company.ragione_sociale,
                "partita_iva": company.partita_iva,
                "codice_fiscale": company.codice_fiscale,
                "forma_giuridica": company.forma_giuridica,
                "sede_legale": company.sede_legale,
                "comune_sede": company.comune_sede,
                "cap": company.cap,
                "email_pec": company.email_pec,
                "telefono": company.telefono,
                "note": company.note,
                "created_at": company.created_at,
                "updated_at": company.updated_at,
            }
        )
    catasto_documents = _build_catasto_correlations(db, person)
    return AnagraficaSubjectDetailResponse(
        id=str(subject.id),
        subject_type=subject.subject_type,
        status=subject.status,
        source_system=subject.source_system,
        source_external_id=subject.source_external_id,
        source_name_raw=subject.source_name_raw,
        nas_folder_path=subject.nas_folder_path,
        nas_folder_letter=subject.nas_folder_letter,
        requires_review=subject.requires_review,
        imported_at=subject.imported_at,
        created_at=subject.created_at,
        updated_at=subject.updated_at,
        person=person_response,
        person_snapshots=[
            AnagraficaPersonSnapshotResponse.model_validate(
                {
                    "id": str(item.id),
                    "subject_id": str(item.subject_id),
                    "is_capacitas_history": item.is_capacitas_history,
                    "source_system": item.source_system,
                    "source_ref": item.source_ref,
                    "cognome": item.cognome,
                    "nome": item.nome,
                    "codice_fiscale": item.codice_fiscale,
                    "data_nascita": item.data_nascita,
                    "comune_nascita": item.comune_nascita,
                    "indirizzo": item.indirizzo,
                    "comune_residenza": item.comune_residenza,
                    "cap": item.cap,
                    "email": item.email,
                    "telefono": item.telefono,
                    "note": item.note,
                    "valid_from": item.valid_from,
                    "collected_at": item.collected_at,
                }
            )
            for item in person_snapshots
        ],
        company=company_response,
        documents=[_build_document_response(item) for item in documents],
        audit_log=[
            AnagraficaAuditLogResponse.model_validate(
                {
                    "id": str(item.id),
                    "subject_id": str(item.subject_id),
                    "changed_by_user_id": item.changed_by_user_id,
                    "action": item.action,
                    "diff_json": item.diff_json,
                    "changed_at": item.changed_at,
                }
            )
            for item in audit_entries
        ],
        catasto_documents=catasto_documents,
    )
# fmt: on
