import mimetypes
import secrets
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module
from app.core.config import settings
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.utenze.models import (
    AnagraficaClassificationSource,
    AnagraficaDocument,
)
from app.modules.utenze.routes.support import (
    _apply_document_content_classification,
    _build_document_response,
    _create_subject_audit,
    _ensure_document_available_locally,
)
from app.modules.utenze.schemas import (
    AnagraficaDocumentContentClassifyRequest,
    AnagraficaDocumentUpdateRequest,
    AnagraficaPreviewDocumentResponse,
    AnagraficaResetRequest,
    AnagraficaResetResponse,
)
from app.modules.utenze.services.content_classification_service import (
    classify_document_content_file,
    classify_document_content_text,
)
from app.modules.utenze.services.import_service import (
    reset_anagrafica_data,
)

router = APIRouter(tags=["utenze"])
RequireUtenzeModule = Depends(require_module("utenze"))


# Preserve reviewed legacy callable layout for the merge-base LOC ratchet.
# fmt: off
@router.patch("/documents/{document_id}", response_model=AnagraficaPreviewDocumentResponse)
def patch_document(
    document_id: uuid.UUID,
    payload: AnagraficaDocumentUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaPreviewDocumentResponse:
    document = db.get(AnagraficaDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if payload.doc_type is not None:
        document.doc_type = payload.doc_type
        document.classification_source = AnagraficaClassificationSource.MANUAL.value
    if payload.notes is not None:
        document.notes = payload.notes
    db.add(document)
    _create_subject_audit(
        db,
        document.subject_id,
        current_user.id,
        "document_updated",
        {"document_id": str(document.id), "doc_type": document.doc_type, "notes": document.notes},
    )
    db.commit()
    db.refresh(document)
    return _build_document_response(document)

@router.post("/documents/{document_id}/content-classification", response_model=AnagraficaPreviewDocumentResponse)
def classify_document_content(
    document_id: uuid.UUID,
    payload: AnagraficaDocumentContentClassifyRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaPreviewDocumentResponse:
    document = db.get(AnagraficaDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if payload.text is not None:
        result = classify_document_content_text(payload.text, source="provided_text")
    else:
        local_path = _ensure_document_available_locally(db, document)
        result = classify_document_content_file(local_path, filename=document.filename)

    _apply_document_content_classification(document, result)
    db.add(document)
    _create_subject_audit(
        db,
        document.subject_id,
        current_user.id,
        "document_content_classified",
        {
            "document_id": str(document.id),
            "status": document.content_classification_status,
            "category": document.content_category,
            "source": document.content_classification_source,
        },
    )
    db.commit()
    db.refresh(document)
    return _build_document_response(document)

@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
    delete_password: Annotated[str | None, Header(alias="X-GAIA-Delete-Password")] = None,
) -> None:
    expected_password = (settings.utenze_delete_password or settings.anagrafica_delete_password or "").strip()
    if expected_password:
        provided_password = (delete_password or "").strip()
        if not provided_password or not secrets.compare_digest(provided_password, expected_password):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password di cancellazione non valida")

    document = db.get(AnagraficaDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    subject_id = document.subject_id
    db.delete(document)
    _create_subject_audit(
        db,
        subject_id,
        current_user.id,
        "document_deleted",
        {"document_id": str(document_id)},
    )
    db.commit()

@router.get("/documents/{document_id}/download")
def download_document(
    document_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    document = db.get(AnagraficaDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    local_path = _ensure_document_available_locally(db, document)

    media_type = document.mime_type or mimetypes.guess_type(document.filename)[0] or "application/octet-stream"
    return FileResponse(
        path=local_path,
        media_type=media_type,
        filename=document.filename,
    )

@router.post("/reset", response_model=AnagraficaResetResponse)
def post_reset_anagrafica(
    payload: AnagraficaResetRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaResetResponse:
    confirm_text = payload.confirm.strip().upper()
    if confirm_text not in {"RESET UTENZE", "RESET ANAGRAFICA"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Conferma non valida. Usa esattamente 'RESET UTENZE'.",
        )

    result = reset_anagrafica_data(db)
    return AnagraficaResetResponse(
        cleared_subject_links=result.cleared_subject_links,
        deleted_documents=result.deleted_documents,
        deleted_audit_logs=result.deleted_audit_logs,
        deleted_import_jobs=result.deleted_import_jobs,
        deleted_import_job_items=result.deleted_import_job_items,
        deleted_storage_files=result.deleted_storage_files,
    )
# fmt: on
