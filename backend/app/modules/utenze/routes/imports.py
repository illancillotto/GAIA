import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_admin_user, require_module
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.utenze.models import (
    AnagraficaImportJob,
    AnagraficaSubject,
    AnagraficaVisuraRoutingAnomaly,
)
from app.modules.utenze.routes.support import (
    _build_subject_list_item,
    _build_subjects_query,
    _job_progress,
    _require_registry_import_job_for_mutation,
    _serialize_import_job,
    _serialize_visura_routing_anomaly,
    get_anagrafica_import_service,
)
from app.modules.utenze.schemas import (
    AnagraficaImportJobResponse,
    AnagraficaImportPreviewRequest,
    AnagraficaImportPreviewResponse,
    AnagraficaImportRunResponse,
    AnagraficaModuleStatusResponse,
    AnagraficaSubjectListResponse,
    AnagraficaVisuraRoutingAnomalyListResponse,
    AnagraficaVisuraRoutingAnomalyResponse,
    RegistryImportJobDeletedResponse,
)
from app.modules.utenze.services.import_service import (
    AnagraficaImportPreviewService,
    create_import_snapshot,
    delete_registry_import_job,
    finalize_stuck_registry_import_job,
    preview_import,
    queue_resume_registry_bulk_import_job,
    registry_job_completed_subject_ids,
    start_registry_bulk_import_job,
)
from app.services.nas_connector import NasConnectorError

router = APIRouter(tags=["utenze"])
RequireUtenzeModule = Depends(require_module("utenze"))


# Preserve reviewed legacy callable layout for the merge-base LOC ratchet.
# fmt: off
@router.get("", response_model=AnagraficaModuleStatusResponse)
def get_anagrafica_module_status(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
) -> AnagraficaModuleStatusResponse:
    return {
        "module": "utenze",
        "enabled": True,
        "message": "GAIA Utenze module is enabled for the current user.",
        "username": current_user.username,
    }

@router.get("/visure-routing-anomalies", response_model=AnagraficaVisuraRoutingAnomalyListResponse)
def list_visura_routing_anomalies(
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
    resolved: bool | None = Query(default=None),
    search: str | None = Query(default=None, min_length=2, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> AnagraficaVisuraRoutingAnomalyListResponse:
    filters = []
    if resolved is True:
        filters.append(AnagraficaVisuraRoutingAnomaly.resolved_at.is_not(None))
    elif resolved is False:
        filters.append(AnagraficaVisuraRoutingAnomaly.resolved_at.is_(None))

    normalized_search = (search or "").strip()
    if normalized_search:
        pattern = f"%{normalized_search}%"
        filters.append(
            or_(
                AnagraficaVisuraRoutingAnomaly.filename.ilike(pattern),
                AnagraficaVisuraRoutingAnomaly.identifier.ilike(pattern),
                AnagraficaVisuraRoutingAnomaly.source_path.ilike(pattern),
                AnagraficaVisuraRoutingAnomaly.reason.ilike(pattern),
            )
        )

    base_statement = select(AnagraficaVisuraRoutingAnomaly)
    if filters:
        base_statement = base_statement.where(*filters)

    total = db.scalar(select(func.count()).select_from(base_statement.subquery())) or 0
    unresolved = db.scalar(
        select(func.count()).select_from(AnagraficaVisuraRoutingAnomaly).where(AnagraficaVisuraRoutingAnomaly.resolved_at.is_(None))
    ) or 0
    resolved_count = db.scalar(
        select(func.count()).select_from(AnagraficaVisuraRoutingAnomaly).where(AnagraficaVisuraRoutingAnomaly.resolved_at.is_not(None))
    ) or 0

    items = db.scalars(
        base_statement.order_by(
            AnagraficaVisuraRoutingAnomaly.resolved_at.is_not(None).asc(),
            AnagraficaVisuraRoutingAnomaly.updated_at.desc(),
            AnagraficaVisuraRoutingAnomaly.created_at.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return AnagraficaVisuraRoutingAnomalyListResponse(
        items=[_serialize_visura_routing_anomaly(item) for item in items],
        total=total,
        unresolved=unresolved,
        resolved=resolved_count,
        page=page,
        page_size=page_size,
    )

@router.post("/visure-routing-anomalies/{anomaly_id}/resolve", response_model=AnagraficaVisuraRoutingAnomalyResponse)
def resolve_visura_routing_anomaly(
    anomaly_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaVisuraRoutingAnomalyResponse:
    anomaly = db.get(AnagraficaVisuraRoutingAnomaly, anomaly_id)
    if anomaly is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anomalia visura non trovata")
    anomaly.resolved_at = datetime.now(UTC)
    db.add(anomaly)
    db.commit()
    db.refresh(anomaly)
    return _serialize_visura_routing_anomaly(anomaly)

@router.post("/import/preview", response_model=AnagraficaImportPreviewResponse)
def post_import_preview(
    payload: AnagraficaImportPreviewRequest,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    service: Annotated[AnagraficaImportPreviewService, Depends(get_anagrafica_import_service)],
) -> AnagraficaImportPreviewResponse:
    try:
        return AnagraficaImportPreviewResponse.model_validate(preview_import(payload.letter, service=service))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except NasConnectorError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

@router.post("/import/run", response_model=AnagraficaImportRunResponse, status_code=status.HTTP_202_ACCEPTED)
def post_import_run(
    payload: AnagraficaImportPreviewRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AnagraficaImportPreviewService, Depends(get_anagrafica_import_service)],
) -> AnagraficaImportRunResponse:
    try:
        result = create_import_snapshot(db, current_user=current_user, letter=payload.letter, service=service)
        return AnagraficaImportRunResponse.model_validate(
            {
                "job_id": str(result.job_id),
                "letter": result.letter,
                "status": result.status,
                "total_folders": result.total_folders,
                "imported_ok": result.imported_ok,
                "imported_errors": result.imported_errors,
                "warning_count": result.warning_count,
                "pending_items": 0,
                "running_items": 0,
                "completed_items": result.imported_ok,
                "failed_items": result.imported_errors,
                "created_subjects": 0,
                "updated_subjects": 0,
                "created_documents": 0,
                "updated_documents": 0,
                "generated_at": result.generated_at,
                "completed_at": result.completed_at,
                "log_json": result.log_json,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except NasConnectorError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

@router.post("/import/run-from-subjects", response_model=AnagraficaImportRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def post_import_run_from_subjects(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaImportRunResponse:
    try:
        job_id = start_registry_bulk_import_job(db, current_user)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    job = db.get(AnagraficaImportJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Impossibile creare il job di aggiornamento utenze")

    progress = _job_progress(db, job_id)
    generated_at = job.created_at

    return AnagraficaImportRunResponse.model_validate(
        {
            "job_id": str(job_id),
            "letter": "REGISTRY",
            "status": job.status,
            "total_folders": job.total_folders,
            "imported_ok": job.imported_ok,
            "imported_errors": job.imported_errors,
            "warning_count": job.warning_count,
            "pending_items": progress["pending_items"],
            "running_items": progress["running_items"],
            "completed_items": progress["completed_items"],
            "failed_items": progress["failed_items"],
            "created_subjects": 0,
            "updated_subjects": 0,
            "created_documents": 0,
            "updated_documents": 0,
            "generated_at": generated_at,
            "completed_at": job.completed_at,
            "log_json": job.log_json,
        }
    )

@router.get("/import/jobs", response_model=list[AnagraficaImportJobResponse])
def get_import_jobs(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> list[AnagraficaImportJobResponse]:
    jobs = db.scalars(select(AnagraficaImportJob).order_by(AnagraficaImportJob.created_at.desc())).all()
    return [_serialize_import_job(db, job) for job in jobs]

@router.get("/import/jobs/{job_id}", response_model=AnagraficaImportJobResponse)
def get_import_job(
    job_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaImportJobResponse:
    job = db.get(AnagraficaImportJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    return _serialize_import_job(db, job)

@router.post("/import/jobs/{job_id}/abort-registry", response_model=AnagraficaImportJobResponse)
def post_abort_registry_import_job(
    job_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaImportJobResponse:
    """Chiude job REGISTRY bloccati: marca gli item `processing` come falliti e ricalcola lo stato del job."""
    _require_registry_import_job_for_mutation(db, job_id, current_user)
    updated = finalize_stuck_registry_import_job(db, job_id, refresh=True)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job non trovato")
    return _serialize_import_job(db, updated)

@router.post("/import/jobs/{job_id}/resume-registry", response_model=AnagraficaImportRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def post_resume_registry_import_job(
    job_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaImportRunResponse:
    """Riprende un job REGISTRY: interrompe eventuali item bloccati in processing, poi elabora solo i soggetti non ancora completati."""
    _require_registry_import_job_for_mutation(db, job_id, current_user)

    total_subjects = int(db.scalar(select(func.count()).select_from(AnagraficaSubject)) or 0)
    completed_ids = registry_job_completed_subject_ids(db, job_id)
    if total_subjects == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nessun soggetto in anagrafica: impossibile riprendere il job.",
        )
    if len(completed_ids) >= total_subjects:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tutti i soggetti risultano già elaborati con esito positivo per questo job.",
        )

    job = queue_resume_registry_bulk_import_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job non trovato")

    progress = _job_progress(db, job_id)
    generated_at = job.created_at

    return AnagraficaImportRunResponse.model_validate(
        {
            "job_id": str(job_id),
            "letter": "REGISTRY",
            "status": job.status,
            "total_folders": job.total_folders,
            "imported_ok": job.imported_ok,
            "imported_errors": job.imported_errors,
            "warning_count": job.warning_count,
            "pending_items": progress["pending_items"],
            "running_items": progress["running_items"],
            "completed_items": progress["completed_items"],
            "failed_items": progress["failed_items"],
            "created_subjects": 0,
            "updated_subjects": 0,
            "created_documents": 0,
            "updated_documents": 0,
            "generated_at": generated_at,
            "completed_at": job.completed_at,
            "log_json": job.log_json,
        }
    )

@router.delete("/import/jobs/{job_id}", response_model=RegistryImportJobDeletedResponse)
def delete_registry_import_job_route(
    job_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> RegistryImportJobDeletedResponse:
    """Elimina dal database un job REGISTRY e tutti i relativi item (storico / job bloccati)."""
    _require_registry_import_job_for_mutation(db, job_id, current_user)
    deleted = delete_registry_import_job(db, job_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job non trovato")
    return RegistryImportJobDeletedResponse(deleted=True)

@router.post("/import/jobs/{job_id}/resume", response_model=AnagraficaImportRunResponse, status_code=status.HTTP_202_ACCEPTED)
def post_resume_import_job(
    job_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaImportRunResponse:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Resume import Anagrafica temporaneamente sospeso. Usare solo la preview.",
    )


@router.get("/subjects", response_model=AnagraficaSubjectListResponse)
def get_subjects(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    search: str | None = Query(default=None),
    subject_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    letter: str | None = Query(default=None),
    requires_review: bool | None = Query(default=None),
) -> AnagraficaSubjectListResponse:
    query = _build_subjects_query(search, subject_type, status_filter, letter, requires_review)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    subjects = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return AnagraficaSubjectListResponse(
        items=[_build_subject_list_item(db, subject) for subject in subjects],
        total=total,
        page=page,
        page_size=page_size,
    )
# fmt: on
