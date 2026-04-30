from __future__ import annotations

import logging
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_admin_user
from app.core.database import get_db
from app.modules.elaborazioni.capacitas.client import InVoltureClient
from app.modules.elaborazioni.capacitas.models import (
    AnagraficaSearchRequest,
    CapacitasAnagraficaDetail,
    CapacitasAnagraficaHistoryImportJobCreateRequest,
    CapacitasAnagraficaHistoryImportJobOut,
    CapacitasAnagraficaHistoryImportRequest,
    CapacitasAnagraficaHistoryImportResponse,
    CapacitasLookupOption,
    CapacitasParticelleSyncJobCreateRequest,
    CapacitasParticelleSyncJobOut,
    CapacitasParticelleSyncJobSpeedPatch,
    CapacitasStoricoAnagraficaRow,
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
from app.models.catasto_phase1 import CatCapacitasTerrenoRow, CatConsorzioOccupancy
from app.services.elaborazioni_capacitas_anagrafica_history import (
    CapacitasAnagraficaHistoryImportError,
    create_anagrafica_history_job,
    delete_anagrafica_history_job,
    expire_stale_anagrafica_history_jobs,
    get_anagrafica_history_job,
    import_anagrafica_history_batch,
    list_anagrafica_history_jobs,
    load_anagrafica_history_import_request,
    serialize_anagrafica_history_job,
)
from app.services.elaborazioni_capacitas_particelle_sync import (
    cancel_particelle_sync_job,
    compute_sync_policy,
    create_particelle_sync_job,
    expire_stale_particelle_sync_jobs,
    delete_particelle_sync_job,
    get_particelle_sync_job,
    list_particelle_sync_jobs,
    serialize_particelle_sync_job,
)
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
    compute_terreni_sync_policy,
    create_terreni_sync_job,
    expire_stale_terreni_sync_jobs,
    delete_terreni_sync_job,
    get_terreni_sync_job,
    list_terreni_sync_jobs,
    serialize_terreni_sync_job,
    sync_terreni_batch,
    sync_terreni_for_request,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/elaborazioni/capacitas", tags=["elaborazioni-capacitas"])


def _enqueue_capacitas_job(db: Session, job) -> None:
    job.status = "pending"
    job.started_at = None
    job.completed_at = None
    job.error_detail = None
    db.commit()
    db.refresh(job)


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


@router.get("/involture/anagrafica/{idxana}/storico", response_model=list[CapacitasStoricoAnagraficaRow])
async def get_anagrafica_storico(
    idxana: str,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    credential_id: int | None = None,
) -> list[CapacitasStoricoAnagraficaRow]:
    try:
        credential, password = pick_credential(db, credential_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    manager = CapacitasSessionManager(credential.username, password)
    try:
        await manager.login()
        await manager.activate_app("involture")
        client = InVoltureClient(manager)
        result = await client.fetch_anagrafica_history(idxana=idxana)
        mark_credential_used(db, credential.id)
        return result
    except Exception as exc:
        logger.exception("Errore storico anagrafica Capacitas: cred_id=%d idxana=%s err=%s", credential.id, idxana, exc)
        mark_credential_error(db, credential.id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Errore recupero storico anagrafica da inVOLTURE: {exc}",
        ) from exc
    finally:
        await manager.close()


@router.get("/involture/anagrafica/storico/{history_id}", response_model=CapacitasAnagraficaDetail)
async def get_anagrafica_storico_detail(
    history_id: str,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    credential_id: int | None = None,
) -> CapacitasAnagraficaDetail:
    try:
        credential, password = pick_credential(db, credential_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    manager = CapacitasSessionManager(credential.username, password)
    try:
        await manager.login()
        await manager.activate_app("involture")
        client = InVoltureClient(manager)
        result = await client.fetch_anagrafica_detail(history_id=history_id)
        mark_credential_used(db, credential.id)
        return result
    except Exception as exc:
        logger.exception(
            "Errore dettaglio storico anagrafica Capacitas: cred_id=%d history_id=%s err=%s",
            credential.id,
            history_id,
            exc,
        )
        mark_credential_error(db, credential.id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Errore recupero dettaglio storico anagrafica da inVOLTURE: {exc}",
        ) from exc
    finally:
        await manager.close()


@router.post("/involture/anagrafica/storico/import", response_model=CapacitasAnagraficaHistoryImportResponse)
async def import_anagrafica_storico(
    body: CapacitasAnagraficaHistoryImportRequest,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasAnagraficaHistoryImportResponse:
    try:
        credential, password = pick_credential(db, body.credential_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    manager = CapacitasSessionManager(credential.username, password)
    try:
        await manager.login()
        await manager.activate_app("involture")
        client = InVoltureClient(manager)
        result = await import_anagrafica_history_batch(db, client, body)
        mark_credential_used(db, credential.id)
        return result
    except CapacitasAnagraficaHistoryImportError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Errore import storico anagrafica Capacitas: cred_id=%d err=%s", credential.id, exc)
        db.rollback()
        mark_credential_error(db, credential.id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Errore import storico anagrafica da inVOLTURE: {exc}",
        ) from exc
    finally:
        await manager.close()


@router.post("/involture/anagrafica/storico/import-file", response_model=CapacitasAnagraficaHistoryImportResponse)
async def import_anagrafica_storico_file(
    file: Annotated[UploadFile, File()],
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    credential_id: Annotated[int | None, Form()] = None,
    continue_on_error: Annotated[bool, Form()] = True,
) -> CapacitasAnagraficaHistoryImportResponse:
    try:
        payload = load_anagrafica_history_import_request(
            filename=file.filename or "anagrafica-storico.csv",
            content=await file.read(),
            credential_id=credential_id,
        )
        payload.continue_on_error = continue_on_error
    except CapacitasAnagraficaHistoryImportError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return await import_anagrafica_storico(payload, _, db)


@router.post("/involture/anagrafica/storico/jobs", response_model=CapacitasAnagraficaHistoryImportJobOut, status_code=status.HTTP_202_ACCEPTED)
async def create_anagrafica_history_import_job_route(
    body: CapacitasAnagraficaHistoryImportJobCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasAnagraficaHistoryImportJobOut:
    expire_stale_anagrafica_history_jobs(db)
    if body.credential_id is not None:
        try:
            pick_credential(db, body.credential_id)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    job = create_anagrafica_history_job(
        db,
        requested_by_user_id=current_user.id,
        credential_id=body.credential_id,
        payload=body,
    )
    return serialize_anagrafica_history_job(job)


@router.get("/involture/anagrafica/storico/jobs", response_model=list[CapacitasAnagraficaHistoryImportJobOut])
def list_anagrafica_history_import_jobs_route(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CapacitasAnagraficaHistoryImportJobOut]:
    expire_stale_anagrafica_history_jobs(db)
    return [serialize_anagrafica_history_job(job) for job in list_anagrafica_history_jobs(db)]


@router.get("/involture/anagrafica/storico/jobs/{job_id}", response_model=CapacitasAnagraficaHistoryImportJobOut)
def get_anagrafica_history_import_job_route(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasAnagraficaHistoryImportJobOut:
    expire_stale_anagrafica_history_jobs(db)
    job = get_anagrafica_history_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")
    return serialize_anagrafica_history_job(job)


@router.delete("/involture/anagrafica/storico/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_anagrafica_history_import_job_route(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    expire_stale_anagrafica_history_jobs(db)
    job = get_anagrafica_history_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")
    if job.status not in {"succeeded", "completed_with_errors", "failed"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Il job puo essere eliminato solo quando e terminato")
    delete_anagrafica_history_job(db, job)


@router.post("/involture/anagrafica/storico/jobs/{job_id}/run", response_model=CapacitasAnagraficaHistoryImportJobOut)
async def run_anagrafica_history_import_job_route(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasAnagraficaHistoryImportJobOut:
    expire_stale_anagrafica_history_jobs(db)
    job = get_anagrafica_history_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")
    _enqueue_capacitas_job(db, job)
    return serialize_anagrafica_history_job(job)


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
        result = await sync_terreni_batch(
            db,
            client,
            body,
            policy=compute_terreni_sync_policy(
                double_speed=body.double_speed,
                parallel_workers=body.parallel_workers,
                throttle_ms=body.throttle_ms,
            ),
        )
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
async def create_terreni_job(
    body: CapacitasTerreniJobCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasTerreniJobOut:
    expire_stale_terreni_sync_jobs(db)
    if body.credential_id is not None:
        try:
            pick_credential(db, body.credential_id)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    job = create_terreni_sync_job(
        db,
        requested_by_user_id=current_user.id,
        credential_id=body.credential_id,
        payload=body,
    )
    return serialize_terreni_sync_job(job)


@router.get("/involture/terreni/jobs", response_model=list[CapacitasTerreniJobOut])
def list_terreni_jobs(
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CapacitasTerreniJobOut]:
    expire_stale_terreni_sync_jobs(db)
    return [serialize_terreni_sync_job(job) for job in list_terreni_sync_jobs(db)]


@router.get("/involture/terreni/jobs/{job_id}", response_model=CapacitasTerreniJobOut)
def get_terreni_job(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasTerreniJobOut:
    expire_stale_terreni_sync_jobs(db)
    job = get_terreni_sync_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")
    return serialize_terreni_sync_job(job)


@router.delete("/involture/terreni/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_terreni_job(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    expire_stale_terreni_sync_jobs(db)
    job = get_terreni_sync_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")
    if job.status not in {"succeeded", "completed_with_errors", "failed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Il job puo essere eliminato solo quando e terminato",
        )
    delete_terreni_sync_job(db, job)


@router.post("/involture/terreni/jobs/{job_id}/run", response_model=CapacitasTerreniJobOut)
async def run_terreni_job(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasTerreniJobOut:
    expire_stale_terreni_sync_jobs(db)
    job = get_terreni_sync_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")

    _enqueue_capacitas_job(db, job)
    return serialize_terreni_sync_job(job)


@router.post("/involture/particelle/jobs", response_model=CapacitasParticelleSyncJobOut, status_code=status.HTTP_202_ACCEPTED)
async def create_particelle_job(
    body: CapacitasParticelleSyncJobCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasParticelleSyncJobOut:
    expire_stale_particelle_sync_jobs(db)
    if body.credential_id is not None:
        try:
            pick_credential(db, body.credential_id)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    job = create_particelle_sync_job(
        db,
        requested_by_user_id=current_user.id,
        credential_id=body.credential_id,
        payload=body,
    )
    return serialize_particelle_sync_job(job)


@router.get("/involture/particelle/jobs", response_model=list[CapacitasParticelleSyncJobOut])
def list_particelle_jobs(
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CapacitasParticelleSyncJobOut]:
    expire_stale_particelle_sync_jobs(db)
    return [serialize_particelle_sync_job(job) for job in list_particelle_sync_jobs(db)]


@router.get("/involture/particelle/jobs/{job_id}", response_model=CapacitasParticelleSyncJobOut)
def get_particelle_job(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasParticelleSyncJobOut:
    expire_stale_particelle_sync_jobs(db)
    job = get_particelle_sync_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")
    return serialize_particelle_sync_job(job)


@router.delete("/involture/particelle/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_particelle_job(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    expire_stale_particelle_sync_jobs(db)
    job = get_particelle_sync_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")
    if job.status not in {"succeeded", "completed_with_errors", "failed", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Il job puo essere eliminato solo quando e terminato")
    delete_particelle_sync_job(db, job)


@router.post("/involture/particelle/jobs/{job_id}/stop", response_model=CapacitasParticelleSyncJobOut)
def stop_particelle_job(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasParticelleSyncJobOut:
    job = get_particelle_sync_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")
    if job.status in {"succeeded", "completed_with_errors", "failed", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Il job e gia terminato")
    return serialize_particelle_sync_job(cancel_particelle_sync_job(db, job))


@router.patch("/involture/particelle/jobs/{job_id}/speed", response_model=CapacitasParticelleSyncJobOut)
def patch_particelle_job_speed(
    job_id: int,
    body: CapacitasParticelleSyncJobSpeedPatch,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasParticelleSyncJobOut:
    job = get_particelle_sync_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")
    if job.status not in {"processing", "queued_resume"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La velocita puo essere modificata solo su job in esecuzione")

    new_policy = compute_sync_policy(double_speed=body.double_speed, parallel_workers=1)
    result_json = dict(job.result_json or {})
    result_json["throttle_ms"] = new_policy.throttle_ms
    result_json["speed_multiplier"] = new_policy.speed_multiplier
    job.result_json = result_json

    payload_json = dict(job.payload_json or {})
    payload_json["double_speed"] = body.double_speed
    job.payload_json = payload_json

    db.commit()
    db.refresh(job)
    return serialize_particelle_sync_job(job)


@router.post("/involture/particelle/jobs/{job_id}/run", response_model=CapacitasParticelleSyncJobOut)
async def run_particelle_job(
    job_id: int,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasParticelleSyncJobOut:
    expire_stale_particelle_sync_jobs(db)
    job = get_particelle_sync_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")

    _enqueue_capacitas_job(db, job)
    return serialize_particelle_sync_job(job)


_RPT_CERTIFICATO_BASE = "https://involture1.servizicapacitas.com/pages/rptCertificato.aspx"


@router.get("/involture/link/rpt-certificato")
async def get_rpt_certificato_link(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    cco: str = Query(..., min_length=1),
    credential_id: int | None = None,
) -> dict[str, str]:
    """Return the browser-session URL to rptCertificato.aspx for a given CCO."""
    _ = credential_id  # Backward-compatible query parameter; the link uses the browser's Capacitas session.
    cco = cco.strip()

    row = db.execute(
        select(CatCapacitasTerrenoRow)
        .where(CatCapacitasTerrenoRow.cco == cco)
        .where(CatCapacitasTerrenoRow.com.is_not(None))
        .limit(1)
    ).scalar_one_or_none()

    if row is None:
        occ = db.execute(
            select(CatConsorzioOccupancy)
            .where(CatConsorzioOccupancy.cco == cco)
            .where(CatConsorzioOccupancy.com.is_not(None))
            .limit(1)
        ).scalar_one_or_none()
        if occ is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parametri COM/PVC/FRA non trovati per CCO {cco}. Eseguire prima la sincronizzazione Capacitas.",
            )
        com, pvc, fra, ccs = occ.com, occ.pvc, occ.fra, occ.ccs
    else:
        com, pvc, fra, ccs = row.com, row.pvc, row.fra, row.ccs

    params = urlencode(
        {
            "CCO": cco,
            "COM": com or "",
            "PVC": pvc or "",
            "FRA": fra or "",
            "CCS": ccs or "00000",
        }
    )
    return {"url": f"{_RPT_CERTIFICATO_BASE}?{params}"}
