from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_super_admin_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.elaborazioni.posta_online.schemas import (
    PostaOnlineCredentialCreate,
    PostaOnlineCredentialOut,
    PostaOnlineCredentialTestJobCreateRequest,
    PostaOnlineCredentialUpdate,
    PostaOnlineRegisteredMailSyncJobCreateRequest,
    PostaOnlineRegisteredMailSyncJobOut,
)
from app.services.elaborazioni_posta_online import (
    create_credential,
    create_credential_test_job,
    create_registered_mail_sync_job,
    delete_credential,
    delete_registered_mail_sync_job,
    expire_stale_registered_mail_sync_jobs,
    get_credential,
    get_registered_mail_sync_job,
    list_credentials,
    list_registered_mail_sync_jobs,
    pick_credential,
    serialize_registered_mail_sync_job,
    update_credential,
)

router = APIRouter(prefix="/elaborazioni/posta-online", tags=["elaborazioni-posta-online"])


@router.post("/credentials", response_model=PostaOnlineCredentialOut, status_code=status.HTTP_201_CREATED)
def create_posta_online_credential(
    payload: PostaOnlineCredentialCreate,
    _: Annotated[ApplicationUser, Depends(require_super_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PostaOnlineCredentialOut:
    return create_credential(db, payload)


@router.get("/credentials", response_model=list[PostaOnlineCredentialOut])
def list_posta_online_credentials(
    _: Annotated[ApplicationUser, Depends(require_super_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[PostaOnlineCredentialOut]:
    return list_credentials(db)


@router.get("/credentials/{credential_id}", response_model=PostaOnlineCredentialOut)
def get_posta_online_credential(
    credential_id: int,
    _: Annotated[ApplicationUser, Depends(require_super_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PostaOnlineCredentialOut:
    credential = get_credential(db, credential_id)
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credenziale Poste Online non trovata")
    return PostaOnlineCredentialOut.model_validate(credential)


@router.patch("/credentials/{credential_id}", response_model=PostaOnlineCredentialOut)
def update_posta_online_credential(
    credential_id: int,
    payload: PostaOnlineCredentialUpdate,
    _: Annotated[ApplicationUser, Depends(require_super_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PostaOnlineCredentialOut:
    try:
        credential = update_credential(db, credential_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credenziale Poste Online non trovata")
    return credential


@router.delete("/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_posta_online_credential(
    credential_id: int,
    _: Annotated[ApplicationUser, Depends(require_super_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    if not delete_credential(db, credential_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credenziale Poste Online non trovata")


@router.post("/credentials/{credential_id}/test", response_model=PostaOnlineRegisteredMailSyncJobOut, status_code=status.HTTP_202_ACCEPTED)
def create_posta_online_credential_test_job(
    credential_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_super_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    payload: PostaOnlineCredentialTestJobCreateRequest = Body(default_factory=PostaOnlineCredentialTestJobCreateRequest),
) -> PostaOnlineRegisteredMailSyncJobOut:
    job = create_credential_test_job(db, credential_id=credential_id, requested_by_user_id=current_user.id, payload=payload)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credenziale Poste Online non trovata")
    return serialize_registered_mail_sync_job(job)


@router.post("/raccomandate/jobs", response_model=PostaOnlineRegisteredMailSyncJobOut, status_code=status.HTTP_202_ACCEPTED)
def create_posta_online_registered_mail_job(
    payload: PostaOnlineRegisteredMailSyncJobCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PostaOnlineRegisteredMailSyncJobOut:
    expire_stale_registered_mail_sync_jobs(db)
    if payload.credential_id is not None:
        try:
            pick_credential(db, payload.credential_id)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    job = create_registered_mail_sync_job(db, requested_by_user_id=current_user.id, payload=payload)
    return serialize_registered_mail_sync_job(job)


@router.get("/raccomandate/jobs", response_model=list[PostaOnlineRegisteredMailSyncJobOut])
def list_posta_online_registered_mail_jobs(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[PostaOnlineRegisteredMailSyncJobOut]:
    expire_stale_registered_mail_sync_jobs(db)
    return [serialize_registered_mail_sync_job(job) for job in list_registered_mail_sync_jobs(db)]


@router.get("/raccomandate/jobs/{job_id}", response_model=PostaOnlineRegisteredMailSyncJobOut)
def get_posta_online_registered_mail_job(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PostaOnlineRegisteredMailSyncJobOut:
    expire_stale_registered_mail_sync_jobs(db)
    job = get_registered_mail_sync_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job Poste Online non trovato")
    return serialize_registered_mail_sync_job(job)


@router.delete("/raccomandate/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_posta_online_registered_mail_job(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    expire_stale_registered_mail_sync_jobs(db)
    job = get_registered_mail_sync_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job Poste Online non trovato")
    if job.status not in {"succeeded", "completed_with_errors", "failed", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Il job puo essere eliminato solo quando e terminato")
    delete_registered_mail_sync_job(db, job)


@router.post("/raccomandate/jobs/{job_id}/run", response_model=PostaOnlineRegisteredMailSyncJobOut)
def enqueue_posta_online_registered_mail_job(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PostaOnlineRegisteredMailSyncJobOut:
    expire_stale_registered_mail_sync_jobs(db)
    job = get_registered_mail_sync_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job Poste Online non trovato")
    job.status = "pending"
    job.started_at = None
    job.completed_at = None
    job.error_detail = None
    db.commit()
    db.refresh(job)
    return serialize_registered_mail_sync_job(job)
