from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_admin_user
from app.core.database import SessionLocal, get_db
from app.modules.elaborazioni.capacitas.client import InVoltureClient
from app.modules.elaborazioni.capacitas.models import (
    AnagraficaSearchRequest,
    CapacitasLookupOption,
    CapacitasTerreniBatchRequest,
    CapacitasTerreniBatchResponse,
    CapacitasTerreniJobCreateRequest,
    CapacitasTerreniJobOut,
    CapacitasCredentialCreate,
    CapacitasCredentialOut,
    CapacitasCredentialUpdate,
    CapacitasSearchResult,
    CapacitasTerreniSearchRequest,
    CapacitasTerreniSearchResult,
    CapacitasTerreniSyncRequest,
    CapacitasTerreniSyncResponse,
)
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
from app.models.application_user import ApplicationUser
from app.services.elaborazioni_capacitas import (
    create_credential,
    delete_credential,
    get_credential,
    list_credentials,
    mark_credential_error,
    mark_credential_used,
    pick_credential,
    test_credential,
    update_credential,
)
from app.services.elaborazioni_capacitas_terreni import (
    create_terreni_sync_job,
    get_terreni_sync_job,
    list_terreni_sync_jobs,
    run_terreni_sync_job,
    serialize_terreni_sync_job,
    sync_terreni_batch,
    sync_terreni_for_request,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/elaborazioni/capacitas", tags=["elaborazioni-capacitas"])


async def _run_terreni_job_background(job_id: int) -> None:
    db = SessionLocal()
    manager: CapacitasSessionManager | None = None
    credential_id: int | None = None
    try:
        job = get_terreni_sync_job(db, job_id)
        if job is None:
            return

        try:
            credential, password = pick_credential(db, job.credential_id)
        except RuntimeError as exc:
            job.status = "failed"
            job.error_detail = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        credential_id = credential.id
        manager = CapacitasSessionManager(credential.username, password)
        await manager.login()
        await manager.activate_app("involture")
        client = InVoltureClient(manager)
        await run_terreni_sync_job(db, client, job)
        mark_credential_used(db, credential.id)
    except Exception as exc:
        logger.exception("Errore background job terreni Capacitas: job_id=%d err=%s", job_id, exc)
        db.rollback()
        if credential_id is not None:
            mark_credential_error(db, credential_id, str(exc))
        job = get_terreni_sync_job(db, job_id)
        if job is not None and job.status not in {"succeeded", "completed_with_errors", "failed"}:
            job.status = "failed"
            job.error_detail = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        if manager is not None:
            await manager.close()
        db.close()


@router.post("/credentials", response_model=CapacitasCredentialOut, status_code=status.HTTP_201_CREATED)
def create_cred(
    payload: CapacitasCredentialCreate,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasCredentialOut:
    return create_credential(db, payload)


@router.get("/credentials", response_model=list[CapacitasCredentialOut])
def list_creds(
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CapacitasCredentialOut]:
    return list_credentials(db)


@router.get("/credentials/{credential_id}", response_model=CapacitasCredentialOut)
def get_cred(
    credential_id: int,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasCredentialOut:
    credential = get_credential(db, credential_id)
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credenziale non trovata")
    return CapacitasCredentialOut.model_validate(credential)


@router.patch("/credentials/{credential_id}", response_model=CapacitasCredentialOut)
def update_cred(
    credential_id: int,
    payload: CapacitasCredentialUpdate,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasCredentialOut:
    credential = update_credential(db, credential_id, payload)
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credenziale non trovata")
    return credential


@router.delete("/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cred(
    credential_id: int,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    if not delete_credential(db, credential_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credenziale non trovata")


@router.post("/credentials/{credential_id}/test")
async def test_cred(
    credential_id: int,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str | bool | None]:
    result = await test_credential(db, credential_id)
    if not result["ok"]:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result["error"])
    return result


@router.post("/involture/search", response_model=CapacitasSearchResult)
async def search_anagrafica(
    body: AnagraficaSearchRequest,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasSearchResult:
    try:
        credential, password = pick_credential(db, body.credential_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    manager = CapacitasSessionManager(credential.username, password)
    try:
        await manager.login()
        await manager.activate_app("involture")
        client = InVoltureClient(manager)
        result = await client.search_anagrafica(
            q=body.q,
            tipo=body.tipo_ricerca,
            solo_con_beni=body.solo_con_beni,
        )
        mark_credential_used(db, credential.id)
        return result
    except Exception as exc:
        logger.exception("Errore ricerca anagrafica Capacitas: cred_id=%d err=%s", credential.id, exc)
        mark_credential_error(db, credential.id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Errore comunicazione con inVOLTURE: {exc}",
        ) from exc
    finally:
        await manager.close()


@router.get("/involture/frazioni", response_model=list[CapacitasLookupOption])
async def search_frazioni(
    q: str,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    credential_id: int | None = None,
) -> list[CapacitasLookupOption]:
    try:
        credential, password = pick_credential(db, credential_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    manager = CapacitasSessionManager(credential.username, password)
    try:
        await manager.login()
        await manager.activate_app("involture")
        client = InVoltureClient(manager)
        result = await client.search_frazioni(q)
        mark_credential_used(db, credential.id)
        return result
    except Exception as exc:
        logger.exception("Errore lookup frazioni Capacitas: cred_id=%d err=%s", credential.id, exc)
        mark_credential_error(db, credential.id, str(exc))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Errore lookup frazioni: {exc}") from exc
    finally:
        await manager.close()


@router.get("/involture/sezioni", response_model=list[CapacitasLookupOption])
async def search_sezioni(
    frazione_id: str,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    credential_id: int | None = None,
) -> list[CapacitasLookupOption]:
    try:
        credential, password = pick_credential(db, credential_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    manager = CapacitasSessionManager(credential.username, password)
    try:
        await manager.login()
        await manager.activate_app("involture")
        client = InVoltureClient(manager)
        result = await client.load_sezioni(frazione_id)
        mark_credential_used(db, credential.id)
        return result
    except Exception as exc:
        logger.exception("Errore lookup sezioni Capacitas: cred_id=%d err=%s", credential.id, exc)
        mark_credential_error(db, credential.id, str(exc))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Errore lookup sezioni: {exc}") from exc
    finally:
        await manager.close()


@router.get("/involture/fogli", response_model=list[CapacitasLookupOption])
async def search_fogli(
    frazione_id: str,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    sezione: str = "",
    credential_id: int | None = None,
) -> list[CapacitasLookupOption]:
    try:
        credential, password = pick_credential(db, credential_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    manager = CapacitasSessionManager(credential.username, password)
    try:
        await manager.login()
        await manager.activate_app("involture")
        client = InVoltureClient(manager)
        result = await client.load_fogli(frazione_id, sezione)
        mark_credential_used(db, credential.id)
        return result
    except Exception as exc:
        logger.exception("Errore lookup fogli Capacitas: cred_id=%d err=%s", credential.id, exc)
        mark_credential_error(db, credential.id, str(exc))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Errore lookup fogli: {exc}") from exc
    finally:
        await manager.close()


@router.post("/involture/terreni/search", response_model=CapacitasTerreniSearchResult)
async def search_terreni(
    body: CapacitasTerreniSearchRequest,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasTerreniSearchResult:
    try:
        credential, password = pick_credential(db, body.credential_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    manager = CapacitasSessionManager(credential.username, password)
    try:
        await manager.login()
        await manager.activate_app("involture")
        client = InVoltureClient(manager)
        result = await client.search_terreni(body)
        mark_credential_used(db, credential.id)
        return result
    except Exception as exc:
        logger.exception("Errore ricerca terreni Capacitas: cred_id=%d err=%s", credential.id, exc)
        mark_credential_error(db, credential.id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Errore comunicazione con inVOLTURE terreni: {exc}",
        ) from exc
    finally:
        await manager.close()


@router.post("/involture/terreni/sync", response_model=CapacitasTerreniSyncResponse)
async def sync_terreni(
    body: CapacitasTerreniSyncRequest,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasTerreniSyncResponse:
    try:
        credential, password = pick_credential(db, body.credential_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    manager = CapacitasSessionManager(credential.username, password)
    try:
        await manager.login()
        await manager.activate_app("involture")
        client = InVoltureClient(manager)
        result = await sync_terreni_for_request(
            db,
            client,
            body,
            fetch_certificati=body.fetch_certificati,
            fetch_details=body.fetch_details,
        )
        mark_credential_used(db, credential.id)
        return result
    except Exception as exc:
        logger.exception("Errore sync terreni Capacitas: cred_id=%d err=%s", credential.id, exc)
        db.rollback()
        mark_credential_error(db, credential.id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Errore sync terreni inVOLTURE: {exc}",
        ) from exc
    finally:
        await manager.close()


@router.post("/involture/terreni/sync-batch", response_model=CapacitasTerreniBatchResponse)
async def sync_terreni_batch_route(
    body: CapacitasTerreniBatchRequest,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasTerreniBatchResponse:
    try:
        credential, password = pick_credential(db, body.credential_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    manager = CapacitasSessionManager(credential.username, password)
    try:
        await manager.login()
        await manager.activate_app("involture")
        client = InVoltureClient(manager)
        result = await sync_terreni_batch(db, client, body)
        mark_credential_used(db, credential.id)
        return result
    except Exception as exc:
        logger.exception("Errore sync batch terreni Capacitas: cred_id=%d err=%s", credential.id, exc)
        db.rollback()
        mark_credential_error(db, credential.id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Errore sync batch terreni inVOLTURE: {exc}",
        ) from exc
    finally:
        await manager.close()


@router.post("/involture/terreni/jobs", response_model=CapacitasTerreniJobOut, status_code=status.HTTP_202_ACCEPTED)
def create_terreni_job(
    body: CapacitasTerreniJobCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasTerreniJobOut:
    job = create_terreni_sync_job(
        db,
        requested_by_user_id=current_user.id,
        credential_id=body.credential_id,
        payload=body,
    )
    background_tasks.add_task(_run_terreni_job_background, job.id)
    return serialize_terreni_sync_job(job)


@router.get("/involture/terreni/jobs", response_model=list[CapacitasTerreniJobOut])
def list_terreni_jobs(
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CapacitasTerreniJobOut]:
    return [serialize_terreni_sync_job(job) for job in list_terreni_sync_jobs(db)]


@router.get("/involture/terreni/jobs/{job_id}", response_model=CapacitasTerreniJobOut)
def get_terreni_job(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasTerreniJobOut:
    job = get_terreni_sync_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")
    return serialize_terreni_sync_job(job)


@router.post("/involture/terreni/jobs/{job_id}/run", response_model=CapacitasTerreniJobOut)
async def run_terreni_job(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasTerreniJobOut:
    job = get_terreni_sync_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")

    try:
        credential, password = pick_credential(db, job.credential_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    manager = CapacitasSessionManager(credential.username, password)
    try:
        await manager.login()
        await manager.activate_app("involture")
        client = InVoltureClient(manager)
        result = await run_terreni_sync_job(db, client, job)
        mark_credential_used(db, credential.id)
        return serialize_terreni_sync_job(result)
    except Exception as exc:
        logger.exception("Errore run job terreni Capacitas: job_id=%d cred_id=%d err=%s", job_id, credential.id, exc)
        mark_credential_error(db, credential.id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Errore esecuzione job terreni inVOLTURE: {exc}",
        ) from exc
    finally:
        await manager.close()
