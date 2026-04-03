from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.shared.http_shared import (
    build_batch_detail_response,
    build_connection_test_response,
    build_connection_test_signature,
    build_request_state_map,
    build_zip_response,
    get_websocket_token,
    websocket_db_session,
)
from app.schemas.elaborazioni import (
    ElaborazioneBatchDetailResponse,
    ElaborazioneBatchResponse,
    ElaborazioneCaptchaSolveRequest,
    ElaborazioneCaptchaSummaryResponse,
    ElaborazioneCredentialResponse,
    ElaborazioneCredentialStatusResponse,
    ElaborazioneCredentialTestResponse,
    ElaborazioneCredentialUpsertRequest,
    ElaborazioneOperationResponse,
    ElaborazioneRichiestaCreateRequest,
    ElaborazioneRichiestaResponse,
)
from app.services.auth import get_current_user_from_token
from app.services.elaborazioni_batches import (
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
from app.services.elaborazioni_captcha import (
    ElaborazioneCaptchaConflictError,
    ElaborazioneCaptchaRequestNotFoundError,
    get_captcha_request_for_user,
    get_manual_captcha_summary_for_user,
    list_pending_captcha_requests,
    skip_captcha_request,
    submit_manual_captcha_solution,
)
from app.services.elaborazioni_credentials import (
    ElaborazioneConnectionTestNotFoundError,
    ElaborazioneCredentialConfigurationError,
    ElaborazioneCredentialNotFoundError,
    delete_credentials,
    get_connection_test_for_user,
    get_credentials_for_user,
    queue_credentials_connection_test,
    upsert_credentials,
)
from app.services.catasto_documents import list_documents_for_batch

router = APIRouter(prefix="/elaborazioni", tags=["elaborazioni"])


@router.post("/credentials", response_model=ElaborazioneCredentialResponse)
def save_credentials(
    payload: ElaborazioneCredentialUpsertRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneCredentialResponse:
    try:
        credential = upsert_credentials(db, current_user.id, payload)
    except ElaborazioneCredentialConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return ElaborazioneCredentialResponse.model_validate(credential)


@router.get("/credentials", response_model=ElaborazioneCredentialStatusResponse)
def get_credentials(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneCredentialStatusResponse:
    credential = get_credentials_for_user(db, current_user.id)
    return ElaborazioneCredentialStatusResponse(
        configured=credential is not None,
        credential=ElaborazioneCredentialResponse.model_validate(credential) if credential is not None else None,
    )


@router.post("/credentials/test", response_model=ElaborazioneCredentialTestResponse, status_code=status.HTTP_202_ACCEPTED)
def test_credentials(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    payload: ElaborazioneCredentialUpsertRequest | None = None,
) -> ElaborazioneCredentialTestResponse:
    try:
        connection_test = queue_credentials_connection_test(db, current_user.id, payload)
    except (ElaborazioneCredentialConfigurationError, ElaborazioneCredentialNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return build_connection_test_response(db, connection_test)


@router.get("/credentials/test/{test_id}", response_model=ElaborazioneCredentialTestResponse)
def get_test_credentials_status(
    test_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneCredentialTestResponse:
    try:
        connection_test = get_connection_test_for_user(db, current_user.id, test_id)
    except ElaborazioneConnectionTestNotFoundError as exc:
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


@router.delete("/credentials", response_model=ElaborazioneOperationResponse)
def remove_credentials(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneOperationResponse:
    deleted = delete_credentials(db, current_user.id)
    return ElaborazioneOperationResponse(message="Credentials deleted" if deleted else "No credentials stored")


@router.post("/batches", response_model=ElaborazioneBatchDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    file: Annotated[UploadFile, File()],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    name: Annotated[str | None, Form()] = None,
) -> ElaborazioneBatchDetailResponse:
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


@router.get("/batches", response_model=list[ElaborazioneBatchResponse])
def list_batches(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[ElaborazioneBatchResponse]:
    return [ElaborazioneBatchResponse.model_validate(item) for item in list_batches_for_user(db, current_user.id, status=status_filter)]


@router.get("/batches/{batch_id}", response_model=ElaborazioneBatchDetailResponse)
def get_batch(
    batch_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneBatchDetailResponse:
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
):
    try:
        batch = get_batch_for_user(db, current_user.id, batch_id)
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    documents = list_documents_for_batch(db, current_user.id, batch_id)
    if not documents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No PDF documents available for this batch")

    batch_label = (batch.name or str(batch.id)).replace("/", "-").replace("\\", "-").strip()
    return build_zip_response(f"{batch_label or batch.id}.zip", documents)


@router.post("/batches/{batch_id}/start", response_model=ElaborazioneBatchResponse)
def start_batch_route(
    batch_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneBatchResponse:
    try:
        batch = start_batch(db, current_user.id, batch_id)
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (BatchConflictError, ElaborazioneCredentialConfigurationError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ElaborazioneBatchResponse.model_validate(batch)


@router.post("/batches/{batch_id}/cancel", response_model=ElaborazioneBatchResponse)
def cancel_batch_route(
    batch_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneBatchResponse:
    try:
        batch = cancel_batch(db, current_user.id, batch_id)
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BatchConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ElaborazioneBatchResponse.model_validate(batch)


@router.post("/batches/{batch_id}/retry-failed", response_model=ElaborazioneBatchResponse)
def retry_failed_batch_route(
    batch_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneBatchResponse:
    try:
        batch = retry_failed_batch(db, current_user.id, batch_id)
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BatchConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ElaborazioneBatchResponse.model_validate(batch)


@router.post("/requests", response_model=ElaborazioneBatchDetailResponse, status_code=status.HTTP_201_CREATED)
def create_single_visura(
    payload: ElaborazioneRichiestaCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneBatchDetailResponse:
    try:
        batch = create_single_visura_batch(db, current_user.id, payload)
    except BatchValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.to_detail()) from exc
    except (BatchConflictError, ElaborazioneCredentialConfigurationError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return build_batch_detail_response(batch, get_batch_requests(db, batch.id))


@router.get("/requests/{request_id}", response_model=ElaborazioneRichiestaResponse)
def get_single_visura(
    request_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneRichiestaResponse:
    try:
        request = get_request_for_user(db, current_user.id, request_id)
    except RequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ElaborazioneRichiestaResponse.model_validate(request)


@router.get("/captcha/pending", response_model=list[ElaborazioneRichiestaResponse])
def pending_captcha_requests(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ElaborazioneRichiestaResponse]:
    requests = list_pending_captcha_requests(db, current_user.id)
    return [ElaborazioneRichiestaResponse.model_validate(item) for item in requests]


@router.get("/captcha/summary", response_model=ElaborazioneCaptchaSummaryResponse)
def captcha_summary(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneCaptchaSummaryResponse:
    return ElaborazioneCaptchaSummaryResponse(**get_manual_captcha_summary_for_user(db, current_user.id))


@router.get("/captcha/{request_id}/image")
def captcha_image(
    request_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    try:
        request = get_captcha_request_for_user(db, current_user.id, request_id)
    except ElaborazioneCaptchaRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if not request.captcha_image_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No CAPTCHA image stored for request")
    if not Path(request.captcha_image_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored CAPTCHA image is missing")
    return FileResponse(request.captcha_image_path, media_type="image/png")


@router.post("/captcha/{request_id}/solve", response_model=ElaborazioneRichiestaResponse)
def solve_captcha(
    request_id: UUID,
    payload: ElaborazioneCaptchaSolveRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneRichiestaResponse:
    try:
        request = submit_manual_captcha_solution(db, current_user.id, request_id, payload.text)
    except ElaborazioneCaptchaRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ElaborazioneCaptchaConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ElaborazioneRichiestaResponse.model_validate(request)


@router.post("/captcha/{request_id}/skip", response_model=ElaborazioneRichiestaResponse)
def skip_captcha(
    request_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneRichiestaResponse:
    try:
        request = skip_captcha_request(db, current_user.id, request_id)
    except ElaborazioneCaptchaRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ElaborazioneCaptchaConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ElaborazioneRichiestaResponse.model_validate(request)


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
                                "image_url": f"{websocket.url.path.rsplit('/ws/', 1)[0]}/captcha/{request.id}/image",
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


__all__ = ["router"]
