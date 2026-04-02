from __future__ import annotations

import asyncio
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Annotated
from uuid import UUID
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect, WebSocketException, status
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_admin_user
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoCredential, CatastoVisuraRequest
from app.schemas.catasto import (
    CatastoBatchDetailResponse,
    CatastoBatchResponse,
    CatastoCaptchaSolveRequest,
    CatastoCaptchaSummaryResponse,
    CatastoComuneResponse,
    CatastoComuneUpsertRequest,
    CatastoCredentialResponse,
    CatastoCredentialStatusResponse,
    CatastoCredentialTestResponse,
    CatastoCredentialUpsertRequest,
    CatastoDocumentBulkDownloadRequest,
    CatastoDocumentResponse,
    CatastoOperationResponse,
    CatastoSingleVisuraCreateRequest,
    CatastoVisuraRequestResponse,
)
from app.services.auth import get_current_user_from_token
from app.services.catasto_batches import (
    BatchConflictError,
    BatchNotFoundError,
    BatchValidationError,
    RequestNotFoundError,
    cancel_batch,
    create_batch_from_upload,
    create_single_visura_batch,
    get_batch_for_user,
    get_batch_requests,
    get_request_for_user,
    list_batches_for_user,
    retry_failed_batch,
    start_batch,
)
from app.services.catasto_captcha import (
    CatastoCaptchaConflictError,
    CatastoCaptchaRequestNotFoundError,
    get_manual_captcha_summary_for_user,
    get_captcha_request_for_user,
    list_pending_captcha_requests,
    skip_captcha_request,
    submit_manual_captcha_solution,
)
from app.services.catasto_comuni import (
    CatastoComuneConflictError,
    CatastoComuneNotFoundError,
    create_catasto_comune,
    list_catasto_comuni,
    update_catasto_comune,
)
from app.services.catasto_credentials import (
    CatastoConnectionTestNotFoundError,
    CatastoCredentialConfigurationError,
    CatastoCredentialNotFoundError,
    delete_credentials,
    get_connection_test_for_user,
    get_credentials_for_user,
    queue_credentials_connection_test,
    upsert_credentials,
)
from app.services.catasto_documents import (
    CatastoDocumentNotFoundError,
    get_document_for_user,
    list_documents_by_ids_for_user,
    list_documents_for_batch,
    list_documents_for_user,
)

router = APIRouter(prefix="/catasto", tags=["catasto"])


def build_batch_detail_response(batch: object, requests: list[object]) -> CatastoBatchDetailResponse:
    payload = CatastoBatchResponse.model_validate(batch).model_dump()
    payload["requests"] = [CatastoVisuraRequestResponse.model_validate(item) for item in requests]
    return CatastoBatchDetailResponse(**payload)


def build_document_response(db: Session, document: object) -> CatastoDocumentResponse:
    payload = CatastoDocumentResponse.model_validate(document).model_dump()
    batch_id = None

    if payload["request_id"] is not None:
        batch_id = db.scalar(
            select(CatastoVisuraRequest.batch_id).where(CatastoVisuraRequest.id == payload["request_id"]),
        )

    payload["batch_id"] = batch_id
    return CatastoDocumentResponse(**payload)


def build_connection_test_response(db: Session, connection_test: object) -> CatastoCredentialTestResponse:
    verified_at = None
    if getattr(connection_test, "credential_id", None) is not None:
        credential = db.get(CatastoCredential, connection_test.credential_id)
        verified_at = credential.verified_at if credential is not None else None

    success: bool | None
    if connection_test.status == "completed":
        success = True
    elif connection_test.status == "failed":
        success = False
    else:
        success = None

    return CatastoCredentialTestResponse(
        id=connection_test.id,
        status=connection_test.status,
        success=success,
        mode=connection_test.mode,
        reachable=connection_test.reachable,
        authenticated=connection_test.authenticated,
        message=connection_test.message,
        verified_at=verified_at,
        created_at=connection_test.created_at,
        started_at=connection_test.started_at,
        completed_at=connection_test.completed_at,
    )


def build_zip_response(filename: str, documents: list[object]) -> StreamingResponse:
    archive_buffer = BytesIO()
    with zipfile.ZipFile(archive_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for document in documents:
            filepath = Path(document.filepath)
            if not filepath.exists():
                continue
            archive.write(filepath, arcname=document.filename)

    archive_buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(archive_buffer, media_type="application/zip", headers=headers)


@contextmanager
def websocket_db_session(websocket: WebSocket) -> Generator[Session, None, None]:
    override = getattr(websocket.app, "dependency_overrides", {}).get(get_db)
    if override is None:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
        return

    generator = override()
    db = next(generator)
    try:
        yield db
    finally:
        try:
            next(generator)
        except StopIteration:
            pass


def get_websocket_token(websocket: WebSocket) -> str:
    token = websocket.query_params.get("token")
    if token:
        return token

    authorization = websocket.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", maxsplit=1)[1]

    raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")


def build_request_state_map(requests: list[object]) -> dict[str, dict[str, object]]:
    state_map: dict[str, dict[str, object]] = {}
    for request in requests:
        state_map[str(request.id)] = {
            "status": request.status,
            "current_operation": request.current_operation,
            "document_id": str(request.document_id) if request.document_id else None,
            "captcha_image_path": request.captcha_image_path,
            "captcha_requested_at": request.captcha_requested_at.isoformat() if request.captcha_requested_at else None,
        }
    return state_map


def build_connection_test_signature(connection_test: object) -> tuple[object, ...]:
    return (
        connection_test.status,
        connection_test.mode,
        connection_test.reachable,
        connection_test.authenticated,
        connection_test.message,
        connection_test.started_at.isoformat() if connection_test.started_at else None,
        connection_test.completed_at.isoformat() if connection_test.completed_at else None,
    )


@router.post("/credentials", response_model=CatastoCredentialResponse)
def save_credentials(
    payload: CatastoCredentialUpsertRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoCredentialResponse:
    try:
        credential = upsert_credentials(db, current_user.id, payload)
    except CatastoCredentialConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return CatastoCredentialResponse.model_validate(credential)


@router.get("/credentials", response_model=CatastoCredentialStatusResponse)
def get_credentials(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoCredentialStatusResponse:
    credential = get_credentials_for_user(db, current_user.id)
    return CatastoCredentialStatusResponse(
        configured=credential is not None,
        credential=CatastoCredentialResponse.model_validate(credential) if credential is not None else None,
    )


@router.post("/credentials/test", response_model=CatastoCredentialTestResponse, status_code=status.HTTP_202_ACCEPTED)
def test_credentials(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    payload: CatastoCredentialUpsertRequest | None = None,
) -> CatastoCredentialTestResponse:
    try:
        connection_test = queue_credentials_connection_test(db, current_user.id, payload)
    except (CatastoCredentialConfigurationError, CatastoCredentialNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return build_connection_test_response(db, connection_test)


@router.get("/credentials/test/{test_id}", response_model=CatastoCredentialTestResponse)
def get_test_credentials_status(
    test_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoCredentialTestResponse:
    try:
        connection_test = get_connection_test_for_user(db, current_user.id, test_id)
    except CatastoConnectionTestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return build_connection_test_response(db, connection_test)


@router.websocket("/ws/credentials-test/{test_id}")
async def credentials_test_websocket(websocket: WebSocket, test_id: UUID) -> None:
    try:
        token = get_websocket_token(websocket)
        with websocket_db_session(websocket) as db:
            current_user = get_current_user_from_token(db, token)
            user_id = current_user.id
            get_connection_test_for_user(db, user_id, test_id)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    last_signature: tuple[object, ...] | None = None

    try:
        while True:
            with websocket_db_session(websocket) as db:
                connection_test = get_connection_test_for_user(db, user_id, test_id)
                response = build_connection_test_response(db, connection_test)

            signature = build_connection_test_signature(connection_test)
            if signature != last_signature:
                await websocket.send_json({"type": "credentials_test", "test": response.model_dump(mode="json")})
                last_signature = signature

            if response.status in {"completed", "failed"}:
                return

            await asyncio.sleep(settings.catasto_websocket_poll_seconds)
    except WebSocketDisconnect:
        return


@router.delete("/credentials", response_model=CatastoOperationResponse)
def remove_credentials(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoOperationResponse:
    deleted = delete_credentials(db, current_user.id)
    return CatastoOperationResponse(message="Credentials deleted" if deleted else "No credentials stored")


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


@router.post("/batches", response_model=CatastoBatchDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    file: Annotated[UploadFile, File()],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    name: Annotated[str | None, Form()] = None,
) -> CatastoBatchDetailResponse:
    try:
        batch = create_batch_from_upload(
            db=db,
            user_id=current_user.id,
            filename=file.filename or "visure.csv",
            content=await file.read(),
            name=name,
        )
    except BatchValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.to_detail()) from exc
    return build_batch_detail_response(batch, get_batch_requests(db, batch.id))


@router.get("/batches", response_model=list[CatastoBatchResponse])
def list_batches(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[CatastoBatchResponse]:
    return [CatastoBatchResponse.model_validate(item) for item in list_batches_for_user(db, current_user.id, status=status_filter)]


@router.get("/batches/{batch_id}", response_model=CatastoBatchDetailResponse)
def get_batch(
    batch_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoBatchDetailResponse:
    try:
        batch = get_batch_for_user(db, current_user.id, batch_id)
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return build_batch_detail_response(batch, get_batch_requests(db, batch.id))


@router.get("/batches/{batch_id}/download")
def download_batch_documents(
    batch_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    try:
        batch = get_batch_for_user(db, current_user.id, batch_id)
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    documents = list_documents_for_batch(db, current_user.id, batch_id)
    if not documents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No PDF documents available for this batch")

    batch_label = (batch.name or str(batch.id)).replace("/", "-").replace("\\", "-").strip()
    return build_zip_response(f"{batch_label or batch.id}.zip", documents)


@router.post("/batches/{batch_id}/start", response_model=CatastoBatchResponse)
def start_batch_route(
    batch_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoBatchResponse:
    try:
        batch = start_batch(db, current_user.id, batch_id)
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (BatchConflictError, CatastoCredentialConfigurationError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CatastoBatchResponse.model_validate(batch)


@router.post("/batches/{batch_id}/cancel", response_model=CatastoBatchResponse)
def cancel_batch_route(
    batch_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoBatchResponse:
    try:
        batch = cancel_batch(db, current_user.id, batch_id)
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BatchConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CatastoBatchResponse.model_validate(batch)


@router.post("/batches/{batch_id}/retry-failed", response_model=CatastoBatchResponse)
def retry_failed_batch_route(
    batch_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoBatchResponse:
    try:
        batch = retry_failed_batch(db, current_user.id, batch_id)
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BatchConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CatastoBatchResponse.model_validate(batch)


@router.post("/visure", response_model=CatastoBatchDetailResponse, status_code=status.HTTP_201_CREATED)
def create_single_visura(
    payload: CatastoSingleVisuraCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoBatchDetailResponse:
    try:
        batch = create_single_visura_batch(db, current_user.id, payload)
    except BatchValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.to_detail()) from exc
    except (BatchConflictError, CatastoCredentialConfigurationError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return build_batch_detail_response(batch, get_batch_requests(db, batch.id))


@router.get("/visure/{request_id}", response_model=CatastoVisuraRequestResponse)
def get_single_visura(
    request_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoVisuraRequestResponse:
    try:
        request = get_request_for_user(db, current_user.id, request_id)
    except RequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CatastoVisuraRequestResponse.model_validate(request)


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


@router.get("/captcha/pending", response_model=list[CatastoVisuraRequestResponse])
def pending_captcha_requests(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CatastoVisuraRequestResponse]:
    requests = list_pending_captcha_requests(db, current_user.id)
    return [CatastoVisuraRequestResponse.model_validate(item) for item in requests]


@router.get("/captcha/summary", response_model=CatastoCaptchaSummaryResponse)
def captcha_summary(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoCaptchaSummaryResponse:
    return CatastoCaptchaSummaryResponse(**get_manual_captcha_summary_for_user(db, current_user.id))


@router.get("/captcha/{request_id}/image")
def captcha_image(
    request_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    try:
        request = get_captcha_request_for_user(db, current_user.id, request_id)
    except CatastoCaptchaRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if not request.captcha_image_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No CAPTCHA image stored for request")
    if not Path(request.captcha_image_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored CAPTCHA image is missing")
    return FileResponse(request.captcha_image_path, media_type="image/png")


@router.post("/captcha/{request_id}/solve", response_model=CatastoVisuraRequestResponse)
def solve_captcha(
    request_id: UUID,
    payload: CatastoCaptchaSolveRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoVisuraRequestResponse:
    try:
        request = submit_manual_captcha_solution(db, current_user.id, request_id, payload.text)
    except CatastoCaptchaRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CatastoCaptchaConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CatastoVisuraRequestResponse.model_validate(request)


@router.post("/captcha/{request_id}/skip", response_model=CatastoVisuraRequestResponse)
def skip_captcha(
    request_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CatastoVisuraRequestResponse:
    try:
        request = skip_captcha_request(db, current_user.id, request_id)
    except CatastoCaptchaRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CatastoCaptchaConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CatastoVisuraRequestResponse.model_validate(request)


@router.websocket("/ws/{batch_id}")
async def batch_updates_websocket(websocket: WebSocket, batch_id: UUID) -> None:
    try:
        token = get_websocket_token(websocket)
        with websocket_db_session(websocket) as db:
            current_user = get_current_user_from_token(db, token)
            user_id = current_user.id
            get_batch_for_user(db, user_id, batch_id)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    last_batch_signature: tuple[object, ...] | None = None
    last_request_state: dict[str, dict[str, object]] = {}
    terminal_sent = False

    try:
        while True:
            with websocket_db_session(websocket) as db:
                batch = get_batch_for_user(db, user_id, batch_id)
                requests = get_batch_requests(db, batch.id)

            batch_signature = (
                batch.status,
                batch.completed_items,
                batch.failed_items,
                batch.skipped_items,
                batch.current_operation,
            )
            request_state = build_request_state_map(requests)

            if batch_signature != last_batch_signature or request_state != last_request_state:
                await websocket.send_json(
                    {
                        "type": "progress",
                        "status": batch.status,
                        "completed": batch.completed_items,
                        "failed": batch.failed_items,
                        "skipped": batch.skipped_items,
                        "total": batch.total_items,
                        "current": batch.current_operation,
                    }
                )

                for request in requests:
                    previous = last_request_state.get(str(request.id))
                    current = request_state[str(request.id)]
                    if previous == current:
                        continue

                    if request.status == "awaiting_captcha" and request.captcha_image_path:
                        await websocket.send_json(
                            {
                                "type": "captcha_needed",
                                "request_id": str(request.id),
                                "image_url": f"/catasto/captcha/{request.id}/image",
                            }
                        )
                    elif request.status == "completed" and request.document_id:
                        await websocket.send_json(
                            {
                                "type": "visura_completed",
                                "request_id": str(request.id),
                                "document_id": str(request.document_id),
                            }
                        )

                if batch.status in {"completed", "failed", "cancelled"} and not terminal_sent:
                    await websocket.send_json(
                        {
                            "type": "batch_completed",
                            "status": batch.status,
                            "ok": batch.completed_items,
                            "failed": batch.failed_items,
                            "skipped": batch.skipped_items,
                        }
                    )
                    terminal_sent = True

                last_batch_signature = batch_signature
                last_request_state = request_state

            if terminal_sent:
                return

            await asyncio.sleep(settings.catasto_websocket_poll_seconds)
    except WebSocketDisconnect:
        return


__all__ = [
    "router",
    "build_batch_detail_response",
    "build_document_response",
    "build_connection_test_response",
    "build_zip_response",
    "websocket_db_session",
    "get_websocket_token",
]
