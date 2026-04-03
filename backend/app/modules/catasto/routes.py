from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_admin_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.shared.http_shared import build_document_response, build_zip_response
from app.schemas.catasto import (
    CatastoComuneResponse,
    CatastoComuneUpsertRequest,
    CatastoDocumentBulkDownloadRequest,
    CatastoDocumentResponse,
)
from app.services.catasto_comuni import (
    CatastoComuneConflictError,
    CatastoComuneNotFoundError,
    create_catasto_comune,
    list_catasto_comuni,
    update_catasto_comune,
)
from app.services.catasto_documents import (
    CatastoDocumentNotFoundError,
    get_document_for_user,
    list_documents_by_ids_for_user,
    list_documents_for_user,
)

router = APIRouter(prefix="/catasto", tags=["catasto"])


@router.get("/comuni", response_model=list[CatastoComuneResponse])
def comuni(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    search: Annotated[str | None, Query()] = None,
) -> list[CatastoComuneResponse]:
    return [CatastoComuneResponse.model_validate(item) for item in list_catasto_comuni(db, search=search)]


@router.post("/comuni", response_model=CatastoComuneResponse, status_code=status.HTTP_201_CREATED)
def create_comune(
    payload: CatastoComuneUpsertRequest,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoComuneResponse:
    try:
        comune = create_catasto_comune(db, payload)
    except CatastoComuneConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CatastoComuneResponse.model_validate(comune)


@router.put("/comuni/{comune_id}", response_model=CatastoComuneResponse)
def update_comune(
    comune_id: int,
    payload: CatastoComuneUpsertRequest,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoComuneResponse:
    try:
        comune = update_catasto_comune(db, comune_id, payload)
    except CatastoComuneNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CatastoComuneConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CatastoComuneResponse.model_validate(comune)


@router.get("/documents", response_model=list[CatastoDocumentResponse])
def list_documents(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    search: Annotated[str | None, Query(alias="q")] = None,
    comune: Annotated[str | None, Query()] = None,
    foglio: Annotated[str | None, Query()] = None,
    particella: Annotated[str | None, Query()] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
) -> list[CatastoDocumentResponse]:
    documents = list_documents_for_user(
        db,
        current_user.id,
        search=search,
        comune=comune,
        foglio=foglio,
        particella=particella,
        created_from=created_from,
        created_to=created_to,
    )
    return [build_document_response(db, item) for item in documents]


@router.get("/documents/search", response_model=list[CatastoDocumentResponse])
def search_documents(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query()] = None,
    comune: Annotated[str | None, Query()] = None,
    foglio: Annotated[str | None, Query()] = None,
    particella: Annotated[str | None, Query()] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
) -> list[CatastoDocumentResponse]:
    documents = list_documents_for_user(
        db,
        current_user.id,
        search=q,
        comune=comune,
        foglio=foglio,
        particella=particella,
        created_from=created_from,
        created_to=created_to,
    )
    return [build_document_response(db, item) for item in documents]


@router.post("/documents/download")
def download_selected_documents(
    payload: CatastoDocumentBulkDownloadRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    documents = list_documents_by_ids_for_user(db, current_user.id, payload.document_ids)
    if not documents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching PDF documents found")
    return build_zip_response("catasto-documents-selection.zip", documents)


@router.get("/documents/{document_id}", response_model=CatastoDocumentResponse)
def get_document(
    document_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoDocumentResponse:
    try:
        document = get_document_for_user(db, current_user.id, document_id)
    except CatastoDocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return build_document_response(db, document)


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    try:
        document = get_document_for_user(db, current_user.id, document_id)
    except CatastoDocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    filepath = Path(document.filepath)
    if not filepath.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored PDF document is missing")
    return FileResponse(filepath, media_type="application/pdf", filename=document.filename)


__all__ = ["router"]
