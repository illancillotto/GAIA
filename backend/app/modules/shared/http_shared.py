from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from uuid import UUID
import zipfile

from fastapi import WebSocket, WebSocketException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.models.catasto import CatastoCredential, CatastoVisuraRequest
from app.schemas.catasto import (
    CatastoBatchDetailResponse,
    CatastoBatchResponse,
    CatastoCredentialTestResponse,
    CatastoDocumentResponse,
    CatastoVisuraRequestResponse,
)


def build_batch_detail_response(batch: object, requests: list[object]) -> CatastoBatchDetailResponse:
    payload = CatastoBatchResponse.model_validate(batch).model_dump()
    payload["requests"] = [CatastoVisuraRequestResponse.model_validate(item) for item in requests]
    return CatastoBatchDetailResponse(**payload)


def build_document_response(db: Session, document: object) -> CatastoDocumentResponse:
    payload = CatastoDocumentResponse.model_validate(document).model_dump()
    batch_id: UUID | None = None

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
        credential_id=getattr(connection_test, "credential_id", None),
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
            "artifact_dir": request.artifact_dir,
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
