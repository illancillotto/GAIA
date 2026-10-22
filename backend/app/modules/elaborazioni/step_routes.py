from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section, require_super_admin_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.elaborazioni.step import credentials, jobs, queries
from app.modules.elaborazioni.step.models import StepSyncJob
from app.modules.elaborazioni.step.schemas import (
    StepAvvisoLinkOut,
    StepContribuenteDetail,
    StepContribuentiPage,
    StepCredentialCreate,
    StepCredentialOut,
    StepCredentialUpdate,
    StepLinkAnomaliesPage,
    StepOverviewOut,
    StepSyncJobCreate,
    StepSyncJobOut,
)

router = APIRouter(prefix="/elaborazioni/step", tags=["elaborazioni-step"])

Database = Annotated[Session, Depends(get_db)]
SuperAdmin = Annotated[ApplicationUser, Depends(require_super_admin_user)]
_read_dependencies = [
    Depends(require_module("ruolo")),
    Depends(require_section("ruolo.tributi.view")),
]


def _job_or_404(db: Session, job_id: int) -> StepSyncJob:
    job = db.get(StepSyncJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job STEP non trovato")
    return job


def _conflict(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/credentials", response_model=list[StepCredentialOut])
def list_step_credentials(_: SuperAdmin, db: Database) -> list[StepCredentialOut]:
    return credentials.list_credentials(db)


@router.post("/credentials", response_model=StepCredentialOut, status_code=status.HTTP_201_CREATED)
def create_step_credential(
    payload: StepCredentialCreate, _: SuperAdmin, db: Database
) -> StepCredentialOut:
    return credentials.create_credential(db, payload)


@router.patch("/credentials/{credential_id}", response_model=StepCredentialOut)
def update_step_credential(
    credential_id: int, payload: StepCredentialUpdate, _: SuperAdmin, db: Database
) -> StepCredentialOut:
    credential = credentials.update_credential(db, credential_id, payload)
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Credenziale STEP non trovata"
        )
    return credential


@router.delete("/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_step_credential(credential_id: int, _: SuperAdmin, db: Database) -> None:
    if not credentials.delete_credential(db, credential_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Credenziale STEP non trovata"
        )


@router.post(
    "/credentials/{credential_id}/test",
    response_model=StepSyncJobOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def test_step_credential(
    credential_id: int, current_user: SuperAdmin, db: Database
) -> StepSyncJobOut:
    try:
        job = jobs.create_credential_test_job(
            db, credential_id, requested_by_user_id=current_user.id
        )
    except jobs.StepJobConflict as exc:
        raise _conflict(exc) from exc
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Credenziale STEP non trovata"
        )
    return StepSyncJobOut.model_validate(job)


@router.get("/jobs", response_model=list[StepSyncJobOut])
def list_step_jobs(_: SuperAdmin, db: Database) -> list[StepSyncJobOut]:
    return [StepSyncJobOut.model_validate(job) for job in jobs.list_jobs(db)]


@router.post("/jobs", response_model=StepSyncJobOut, status_code=status.HTTP_202_ACCEPTED)
def create_step_job(
    payload: StepSyncJobCreate, current_user: SuperAdmin, db: Database
) -> StepSyncJobOut:
    if payload.mode in jobs.BROWSER_MODES and not credentials.has_available_credential(
        db, payload.credential_id
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nessuna credenziale STEP attiva",
        )
    try:
        job = jobs.create_job(db, payload, requested_by_user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except jobs.StepJobConflict as exc:
        raise _conflict(exc) from exc
    return StepSyncJobOut.model_validate(job)


@router.get("/jobs/{job_id}", response_model=StepSyncJobOut)
def get_step_job(job_id: int, _: SuperAdmin, db: Database) -> StepSyncJobOut:
    return StepSyncJobOut.model_validate(_job_or_404(db, job_id))


@router.post("/jobs/{job_id}/cancel", response_model=StepSyncJobOut)
def cancel_step_job(job_id: int, _: SuperAdmin, db: Database) -> StepSyncJobOut:
    try:
        return StepSyncJobOut.model_validate(jobs.cancel_job(db, _job_or_404(db, job_id)))
    except jobs.StepJobConflict as exc:
        raise _conflict(exc) from exc


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_step_job(job_id: int, _: SuperAdmin, db: Database) -> None:
    try:
        jobs.delete_job(db, _job_or_404(db, job_id))
    except jobs.StepJobConflict as exc:
        raise _conflict(exc) from exc


@router.get("/overview", response_model=StepOverviewOut, dependencies=_read_dependencies)
def step_overview(db: Database) -> StepOverviewOut:
    return queries.overview(db)


@router.get("/contribuenti", response_model=StepContribuentiPage, dependencies=_read_dependencies)
def list_step_contribuenti(
    db: Database,
    q: Annotated[str | None, Query(max_length=120)] = None,
    only_residuo: bool = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> StepContribuentiPage:
    return queries.list_contribuenti(
        db, q=q, only_residuo=only_residuo, page=page, page_size=page_size
    )


@router.get(
    "/contribuenti/{contribuente_id}",
    response_model=StepContribuenteDetail,
    dependencies=_read_dependencies,
)
def get_step_contribuente(contribuente_id: uuid.UUID, db: Database) -> StepContribuenteDetail:
    detail = queries.contribuente_detail(db, contribuente_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contribuente STEP non trovato"
        )
    return detail


@router.get("/documenti/{documento_id}/pdf", dependencies=_read_dependencies)
def download_step_pdf(documento_id: uuid.UUID, db: Database) -> FileResponse:
    found = queries.documento_pdf(db, documento_id)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="PDF STEP non disponibile"
        )
    documento, path = found
    return FileResponse(
        path, media_type="application/pdf", filename=documento.pdf_original_filename or path.name
    )


@router.get("/ruolo-links", response_model=StepLinkAnomaliesPage, dependencies=_read_dependencies)
def list_step_link_anomalies(
    db: Database,
    link_status: Annotated[
        str | None, Query(alias="status", pattern="^(linked|not_found|ambiguous|unrecognized)$")
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> StepLinkAnomaliesPage:
    return queries.link_anomalies(db, status=link_status, page=page, page_size=page_size)


@router.get(
    "/ruolo-avvisi/{avviso_id}",
    response_model=list[StepAvvisoLinkOut],
    dependencies=_read_dependencies,
)
def list_step_links_for_avviso(avviso_id: uuid.UUID, db: Database) -> list[StepAvvisoLinkOut]:
    return queries.links_for_avviso(db, avviso_id)
