from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import Annotated
from uuid import UUID
import zipfile
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import and_, func, select
from sqlalchemy.orm import aliased
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.utenze.anpr.models import AnprCheckLog, AnprJobRun, AnprSyncConfig
from app.modules.ruolo.models import RuoloAvviso
from app.modules.utenze.models import AnagraficaPerson, AnagraficaSubject
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
    ElaborazioneAnprErrorSubjectItemResponse,
    ElaborazioneAnprRunItemResponse,
    ElaborazioneAnprRunRecordItemResponse,
    ElaborazioneAnprSummaryResponse,
    ElaborazioneRuntimeMetricsResponse,
    ElaborazioneCaptchaSolveRequest,
    ElaborazioneCaptchaSummaryResponse,
    ElaborazioneCredentialCreateRequest,
    ElaborazioneCredentialResponse,
    ElaborazioneCredentialStatusResponse,
    ElaborazioneCredentialTestRequest,
    ElaborazioneCredentialTestResponse,
    ElaborazioneCredentialUpdateRequest,
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
    get_runtime_metrics_for_user,
    list_batches_for_user,
    release_processing_batches_for_user,
    retry_failed_batch,
    start_batch,
    sync_batch_counters,
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
    create_credential,
    delete_credential,
    get_connection_test_for_user,
    get_credential_for_user,
    get_default_credential_for_user,
    list_credentials_for_user,
    queue_credentials_connection_test,
    update_credential,
)
from app.services.catasto_documents import list_documents_for_batch

router = APIRouter(prefix="/elaborazioni", tags=["elaborazioni"])


def _build_anpr_run_records(db: Session, run: AnprJobRun) -> list[ElaborazioneAnprRunRecordItemResponse]:
    completed_at = run.completed_at or run.started_at
    if completed_at < run.started_at:
        completed_at = run.started_at

    rows = db.execute(
        select(
            AnprCheckLog.subject_id,
            AnagraficaPerson.cognome,
            AnagraficaPerson.nome,
            AnagraficaPerson.codice_fiscale,
            AnagraficaPerson.data_nascita,
            AnprCheckLog.call_type,
            AnprCheckLog.esito,
            AnprCheckLog.error_detail,
            AnprCheckLog.created_at,
        )
        .join(AnagraficaSubject, AnagraficaSubject.id == AnprCheckLog.subject_id)
        .join(AnagraficaPerson, AnagraficaPerson.subject_id == AnagraficaSubject.id)
        .where(AnagraficaSubject.subject_type == "person")
        .where(AnprCheckLog.triggered_by == run.triggered_by)
        .where(AnprCheckLog.created_at >= run.started_at)
        .where(AnprCheckLog.created_at <= completed_at)
        .order_by(AnprCheckLog.created_at.desc(), AnprCheckLog.subject_id.asc())
    ).all()

    aggregated: dict[str, ElaborazioneAnprRunRecordItemResponse] = {}
    for subject_id, cognome, nome, codice_fiscale, data_nascita, call_type, esito, error_detail, created_at in rows:
        key = str(subject_id)
        item = aggregated.get(key)
        if item is None:
            aggregated[key] = ElaborazioneAnprRunRecordItemResponse(
                id=f"{run.id}:{key}",
                subject_id=key,
                display_name=f"{(cognome or '').strip()} {(nome or '').strip()}".strip() or codice_fiscale,
                codice_fiscale=codice_fiscale,
                data_nascita=data_nascita,
                last_event_at=created_at,
                final_esito=esito,
                error_detail=error_detail,
                calls_made=1,
                call_types=[call_type],
            )
            continue

        item.calls_made += 1
        if call_type not in item.call_types:
            item.call_types.append(call_type)

    return list(aggregated.values())


def _resolve_request_artifact_preview_path(artifact_dir: Path) -> Path | None:
    candidates = [
        artifact_dir / "preview-not-found.png",
        artifact_dir / "final-not_found.png",
        artifact_dir / "final-failed.png",
        artifact_dir / "final-skipped.png",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        for candidate in sorted(artifact_dir.glob(pattern)):
            if candidate.is_file():
                return candidate
    return None


def _build_missing_artifact_archive(request) -> BytesIO:
    archive_buffer = BytesIO()
    diagnostic_lines = [
        "Artifact directory missing.",
        f"request_id={request.id}",
        f"status={request.status}",
        f"artifact_dir={request.artifact_dir or '-'}",
        f"current_operation={request.current_operation or '-'}",
        f"error_message={request.error_message or '-'}",
        f"processed_at={request.processed_at.isoformat() if request.processed_at else '-'}",
    ]
    with zipfile.ZipFile(archive_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("error.txt", "\n".join(diagnostic_lines) + "\n")
    archive_buffer.seek(0)
    return archive_buffer


@router.get("/utenze-anpr/summary", response_model=ElaborazioneAnprSummaryResponse)
def get_utenze_anpr_summary(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneAnprSummaryResponse:
    config = db.get(AnprSyncConfig, 1)
    configured_daily_limit = config.max_calls_per_day if config is not None else settings.anpr_daily_call_hard_limit
    effective_daily_limit = min(configured_daily_limit, settings.anpr_daily_call_hard_limit)
    local_today = datetime.now(ZoneInfo(settings.anpr_job_timezone)).date()
    latest_run = db.execute(select(AnprJobRun).order_by(AnprJobRun.started_at.desc()).limit(1)).scalar_one_or_none()
    ruolo_year = (
        latest_run.ruolo_year
        if latest_run is not None
        else db.execute(select(func.max(RuoloAvviso.anno_tributario)).where(RuoloAvviso.subject_id.is_not(None))).scalar_one_or_none()
    )
    calls_today = db.execute(
        select(func.coalesce(func.sum(AnprJobRun.calls_used), 0)).where(AnprJobRun.run_date == local_today)
    ).scalar_one()
    recent_runs = db.execute(select(AnprJobRun).order_by(AnprJobRun.started_at.desc()).limit(10)).scalars().all()
    recent_run_records = {str(item.id): _build_anpr_run_records(db, item) for item in recent_runs}
    error_subjects: list[ElaborazioneAnprErrorSubjectItemResponse] = []
    total_error_subjects = 0

    if ruolo_year is not None:
        ruolo_subjects = (
            select(RuoloAvviso.subject_id)
            .where(
                RuoloAvviso.anno_tributario == ruolo_year,
                RuoloAvviso.subject_id.is_not(None),
            )
            .distinct()
            .subquery()
        )
        latest_error_subquery = (
            select(
                AnprCheckLog.subject_id.label("subject_id"),
                func.max(AnprCheckLog.created_at).label("latest_error_at"),
            )
            .where(AnprCheckLog.esito == "error")
            .group_by(AnprCheckLog.subject_id)
            .subquery()
        )
        latest_error_log = aliased(AnprCheckLog)
        error_base_stmt = (
            select(
                AnagraficaSubject.id,
                AnagraficaPerson.cognome,
                AnagraficaPerson.nome,
                AnagraficaPerson.codice_fiscale,
                AnagraficaPerson.data_nascita,
                AnagraficaPerson.stato_anpr,
                AnagraficaPerson.last_anpr_check_at,
                AnagraficaPerson.capacitas_deceduto,
                AnagraficaPerson.capacitas_last_check_at,
                latest_error_subquery.c.latest_error_at,
                latest_error_log.error_detail,
            )
            .join(AnagraficaPerson, AnagraficaPerson.subject_id == AnagraficaSubject.id)
            .join(ruolo_subjects, ruolo_subjects.c.subject_id == AnagraficaSubject.id)
            .outerjoin(latest_error_subquery, latest_error_subquery.c.subject_id == AnagraficaSubject.id)
            .outerjoin(
                latest_error_log,
                and_(
                    latest_error_log.subject_id == latest_error_subquery.c.subject_id,
                    latest_error_log.created_at == latest_error_subquery.c.latest_error_at,
                    latest_error_log.esito == "error",
                ),
            )
            .where(AnagraficaSubject.subject_type == "person")
            .where(AnagraficaPerson.stato_anpr == "error")
        )
        total_error_subjects = int(
            db.execute(select(func.count()).select_from(error_base_stmt.subquery())).scalar_one()
        )
        error_rows = db.execute(
            error_base_stmt.order_by(
                latest_error_subquery.c.latest_error_at.desc().nullslast(),
                AnagraficaPerson.data_nascita.asc().nullslast(),
                AnagraficaPerson.cognome.asc(),
                AnagraficaPerson.nome.asc(),
            ).limit(100)
        ).all()
        error_subjects = [
            ElaborazioneAnprErrorSubjectItemResponse(
                subject_id=str(subject_id),
                display_name=f"{(cognome or '').strip()} {(nome or '').strip()}".strip() or codice_fiscale,
                codice_fiscale=codice_fiscale,
                data_nascita=data_nascita,
                stato_anpr=stato_anpr,
                last_anpr_check_at=last_anpr_check_at,
                latest_error_at=latest_error_at,
                latest_error_detail=error_detail,
                capacitas_deceduto=capacitas_deceduto,
                capacitas_last_check_at=capacitas_last_check_at,
            )
            for (
                subject_id,
                cognome,
                nome,
                codice_fiscale,
                data_nascita,
                stato_anpr,
                last_anpr_check_at,
                capacitas_deceduto,
                capacitas_last_check_at,
                latest_error_at,
                error_detail,
            ) in error_rows
        ]

    return ElaborazioneAnprSummaryResponse(
        calls_today=int(calls_today or 0),
        configured_daily_limit=configured_daily_limit,
        hard_daily_limit=settings.anpr_daily_call_hard_limit,
        effective_daily_limit=effective_daily_limit,
        batch_size=settings.anpr_job_batch_size,
        ruolo_year=ruolo_year,
        total_error_subjects=total_error_subjects,
        error_subjects=error_subjects,
        recent_runs=[
            ElaborazioneAnprRunItemResponse(
                id=str(item.id),
                run_date=item.run_date,
                ruolo_year=item.ruolo_year,
                status=item.status,
                daily_calls_before=item.daily_calls_before,
                daily_calls_after=item.daily_calls_after,
                subjects_selected=item.subjects_selected,
                subjects_processed=item.subjects_processed,
                deceased_found=item.deceased_found,
                errors=item.errors,
                calls_used=item.calls_used,
                started_at=item.started_at,
                completed_at=item.completed_at,
                records=recent_run_records.get(str(item.id), []),
            )
            for item in recent_runs
        ],
    )


@router.post("/credentials", response_model=ElaborazioneCredentialResponse)
def save_credentials(
    payload: ElaborazioneCredentialCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneCredentialResponse:
    try:
        credential = create_credential(db, current_user.id, payload)
    except ElaborazioneCredentialConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return ElaborazioneCredentialResponse.model_validate(credential)


@router.get("/credentials", response_model=ElaborazioneCredentialStatusResponse)
def get_credentials(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneCredentialStatusResponse:
    credentials = list_credentials_for_user(db, current_user.id)
    default_credential = get_default_credential_for_user(db, current_user.id)
    return ElaborazioneCredentialStatusResponse(
        configured=bool(credentials),
        credentials=[ElaborazioneCredentialResponse.model_validate(item) for item in credentials],
        default_credential=ElaborazioneCredentialResponse.model_validate(default_credential) if default_credential is not None else None,
        credential=ElaborazioneCredentialResponse.model_validate(default_credential) if default_credential is not None else None,
    )


@router.post("/credentials/test", response_model=ElaborazioneCredentialTestResponse, status_code=status.HTTP_202_ACCEPTED)
def test_credentials(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    payload: ElaborazioneCredentialTestRequest | None = None,
) -> ElaborazioneCredentialTestResponse:
    try:
        connection_test = queue_credentials_connection_test(db, current_user.id, payload)
    except (ElaborazioneCredentialConfigurationError, ElaborazioneCredentialNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return build_connection_test_response(db, connection_test)


@router.get("/credentials/{credential_id}", response_model=ElaborazioneCredentialResponse)
def get_credential(
    credential_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneCredentialResponse:
    credential = get_credential_for_user(db, current_user.id, credential_id)
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"SISTER credential {credential_id} not found")
    return ElaborazioneCredentialResponse.model_validate(credential)


@router.patch("/credentials/{credential_id}", response_model=ElaborazioneCredentialResponse)
def patch_credential(
    credential_id: UUID,
    payload: ElaborazioneCredentialUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneCredentialResponse:
    try:
        credential = update_credential(db, current_user.id, credential_id, payload)
    except ElaborazioneCredentialConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ElaborazioneCredentialNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ElaborazioneCredentialResponse.model_validate(credential)


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
    default_credential = get_default_credential_for_user(db, current_user.id)
    deleted = delete_credential(db, current_user.id, default_credential.id) if default_credential is not None else False
    return ElaborazioneOperationResponse(message="Credentials deleted" if deleted else "No credentials stored")


@router.delete("/credentials/{credential_id}", response_model=ElaborazioneOperationResponse)
def remove_credential(
    credential_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneOperationResponse:
    deleted = delete_credential(db, current_user.id, credential_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"SISTER credential {credential_id} not found")
    return ElaborazioneOperationResponse(message="Credential deleted")


@router.post("/credentials/release", response_model=ElaborazioneOperationResponse)
def release_sister_credentials(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneOperationResponse:
    released_count, batch_ids = release_processing_batches_for_user(db, current_user.id)
    if released_count == 0:
        return ElaborazioneOperationResponse(success=True, message="Nessun batch visure in esecuzione da fermare")
    batch_list = ", ".join(str(batch_id) for batch_id in batch_ids)
    return ElaborazioneOperationResponse(
        success=True,
        message=f"Richiesta di rilascio inviata per {released_count} batch. Logout SISTER al primo checkpoint utile. Batch: {batch_list}",
    )


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.to_detail()) from exc
    return build_batch_detail_response(batch, get_batch_requests(db, batch.id))


@router.get("/batches", response_model=list[ElaborazioneBatchResponse])
def list_batches(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[ElaborazioneBatchResponse]:
    batches = list_batches_for_user(db, current_user.id, status=status_filter)
    for batch in batches:
        sync_batch_counters(db, batch)
    return [ElaborazioneBatchResponse.model_validate(item) for item in batches]


@router.get("/metrics", response_model=ElaborazioneRuntimeMetricsResponse)
def get_runtime_metrics(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneRuntimeMetricsResponse:
    return ElaborazioneRuntimeMetricsResponse(**get_runtime_metrics_for_user(db, current_user.id))


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
    requests = get_batch_requests(db, batch.id)
    sync_batch_counters(db, batch, requests)
    return build_batch_detail_response(batch, requests)


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


@router.get("/batches/{batch_id}/report.json")
def download_batch_report_json(
    batch_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    try:
        batch = get_batch_for_user(db, current_user.id, batch_id)
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if not batch.report_json_path or not Path(batch.report_json_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch JSON report not available")
    return FileResponse(batch.report_json_path, media_type="application/json")


@router.get("/batches/{batch_id}/report.md")
def download_batch_report_markdown(
    batch_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    try:
        batch = get_batch_for_user(db, current_user.id, batch_id)
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if not batch.report_md_path or not Path(batch.report_md_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch Markdown report not available")
    return FileResponse(batch.report_md_path, media_type="text/markdown")


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.to_detail()) from exc
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


@router.get("/requests/{request_id}/artifacts/download")
def download_request_artifacts(
    request_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        request = get_request_for_user(db, current_user.id, request_id)
    except RequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if not request.artifact_dir:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No artifact directory stored for request")
    artifact_dir = Path(request.artifact_dir)
    if not artifact_dir.exists():
        archive_buffer = _build_missing_artifact_archive(request)
        filename = f"request-{request.id}-artifacts-missing.zip"
        return StreamingResponse(
            archive_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    archive_buffer = BytesIO()
    with zipfile.ZipFile(archive_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in artifact_dir.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, arcname=file_path.relative_to(artifact_dir))
    archive_buffer.seek(0)
    filename = f"request-{request.id}-artifacts.zip"
    return StreamingResponse(
        archive_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/requests/{request_id}/artifacts/preview")
def get_request_artifact_preview(
    request_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    try:
        request = get_request_for_user(db, current_user.id, request_id)
    except RequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if not request.artifact_dir:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No artifact directory stored for request")
    artifact_dir = Path(request.artifact_dir)
    if not artifact_dir.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored request artifacts are missing")
    preview_path = _resolve_request_artifact_preview_path(artifact_dir)
    if preview_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No artifact preview available for request")
    return FileResponse(preview_path)


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
                sync_batch_counters(db, batch, requests)

            batch_signature = (
                batch.status,
                batch.completed_items,
                batch.failed_items,
                batch.skipped_items,
                batch.not_found_items,
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
                        "not_found": batch.not_found_items,
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
                            "not_found": batch.not_found_items,
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
