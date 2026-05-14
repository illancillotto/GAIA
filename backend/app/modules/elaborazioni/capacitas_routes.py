from __future__ import annotations

import logging
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import desc, func, select
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
    CapacitasParticellaAnomaliaOut,
    CapacitasRefetchCertificatiRequest,
    CapacitasRefetchCertificatiResponse,
    CapacitasResolveFragioneRequest,
    CapacitasResolveFragioneResponse,
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
from app.models.catasto_phase1 import CatCapacitasCertificato, CatCapacitasIntestatario, CatCapacitasTerrenoRow, CatComune, CatConsorzioOccupancy, CatParticella
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
    CapacitasFrazioneAmbiguaError,
    compute_terreni_sync_policy,
    create_terreni_sync_job,
    expire_stale_terreni_sync_jobs,
    delete_terreni_sync_job,
    get_terreni_sync_job,
    list_terreni_sync_jobs,
    refetch_certificati_senza_intestatari,
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
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


@router.post("/involture/certificati/refetch-empty", response_model=CapacitasRefetchCertificatiResponse)
async def refetch_certificati_empty(
    body: CapacitasRefetchCertificatiRequest,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasRefetchCertificatiResponse:
    """Re-fetcha i certificati salvati con 0 intestatari.

    Deve essere la prima operazione della sessione Capacitas (non chiamare
    search_terreni prima) altrimenti si riproduce il bug di session-state.
    """
    try:
        credential, password = pick_credential(db, body.credential_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    manager = CapacitasSessionManager(credential.username, password)
    try:
        await manager.login()
        await manager.activate_app("involture")
        client = InVoltureClient(manager)
        refetched = await refetch_certificati_senza_intestatari(
            db,
            client,
            limit=body.limit,
            throttle_ms=body.throttle_ms,
        )
        mark_credential_used(db, credential.id)
    except Exception as exc:
        logger.exception("Errore refetch certificati Capacitas: cred_id=%d err=%s", credential.id, exc)
        db.rollback()
        mark_credential_error(db, credential.id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Errore refetch certificati inVOLTURE: {exc}",
        ) from exc
    finally:
        await manager.close()

    certs_with_intestatari = select(CatCapacitasIntestatario.certificato_id).distinct().scalar_subquery()
    remaining_empty = db.scalar(
        select(func.count(CatCapacitasCertificato.id))
        .where(CatCapacitasCertificato.id.notin_(certs_with_intestatari))
    ) or 0

    return CapacitasRefetchCertificatiResponse(refetched=refetched, remaining_empty=remaining_empty)


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


@router.get("/involture/particelle/anomalie", response_model=list[CapacitasParticellaAnomaliaOut])
def list_particelle_anomalie(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[CapacitasParticellaAnomaliaOut]:
    rows = db.execute(
        select(CatParticella)
        .where(
            CatParticella.capacitas_anomaly_type.isnot(None),
            CatParticella.is_current.is_(True),
        )
        .order_by(CatParticella.capacitas_last_sync_at.desc().nullslast())
        .limit(limit)
        .offset(offset)
    ).scalars().all()

    result: list[CapacitasParticellaAnomaliaOut] = []
    for p in rows:
        comune = db.get(CatComune, p.comune_id) if p.comune_id else None
        data = p.capacitas_anomaly_data or {}
        candidates_raw = data.get("candidates", [])
        result.append(CapacitasParticellaAnomaliaOut(
            id=str(p.id),
            comune_id=str(p.comune_id) if p.comune_id else None,
            nome_comune=comune.nome_comune if comune else None,
            foglio=p.foglio,
            particella=p.particella,
            subalterno=p.subalterno,
            anomaly_type=p.capacitas_anomaly_type or "",
            candidates=[
                {
                    "frazione_id": c.get("frazione_id", ""),
                    "n_rows": c.get("n_rows", 0),
                    "ccos": c.get("ccos", []),
                    "stati": c.get("stati", []),
                }
                for c in candidates_raw
            ],
            capacitas_last_sync_at=p.capacitas_last_sync_at,
            capacitas_last_sync_error=p.capacitas_last_sync_error,
        ))
    return result


@router.post(
    "/involture/particelle/{particella_id}/resolve-frazione",
    response_model=CapacitasResolveFragioneResponse,
)
async def resolve_particella_frazione(
    particella_id: str,
    body: CapacitasResolveFragioneRequest,
    current_user: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CapacitasResolveFragioneResponse:
    from uuid import UUID as _UUID
    try:
        pid = _UUID(particella_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="particella_id non valido")

    particella = db.get(CatParticella, pid)
    if particella is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Particella non trovata")

    comune = db.get(CatComune, particella.comune_id) if particella.comune_id else None
    if comune is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Comune non disponibile sulla particella")

    credential = pick_credential(db)
    if credential is None:
        if body.credential_id is not None:
            credential = get_credential(db, body.credential_id)
        if credential is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Nessuna credenziale Capacitas disponibile")

    from app.services.elaborazioni_capacitas import _decrypt
    password = _decrypt(credential.password_encrypted)

    from app.modules.elaborazioni.capacitas.models import CapacitasTerreniBatchItem as _BatchItem
    batch_request = CapacitasTerreniBatchRequest(
        items=[
            _BatchItem(
                label=f"{comune.nome_comune} {particella.foglio}/{particella.particella}",
                comune=comune.nome_comune,
                frazione_id=body.frazione_id,
                sezione="",
                foglio=particella.foglio,
                particella=particella.particella,
                sub=particella.subalterno or "",
            )
        ],
        continue_on_error=False,
        credential_id=credential.id,
        fetch_certificati=body.fetch_certificati,
        fetch_details=body.fetch_details,
    )

    try:
        async with CapacitasSessionManager(credential.username, password) as manager:
            await manager.activate_app("involture")
            client = InVoltureClient(manager)
            sync_result = await sync_terreni_batch(db, client, batch_request)

        item_result = sync_result.items[0] if sync_result.items else None
        if item_result is None or not item_result.ok:
            return CapacitasResolveFragioneResponse(
                ok=False,
                error=item_result.error if item_result else "Nessun risultato dal sync",
            )

        # Clear anomaly
        particella.capacitas_anomaly_type = None
        particella.capacitas_anomaly_data = None
        particella.capacitas_last_sync_status = "synced"
        particella.capacitas_last_sync_error = None
        db.commit()

        return CapacitasResolveFragioneResponse(
            ok=True,
            total_rows=item_result.total_rows,
            imported_certificati=item_result.imported_certificati,
        )
    except CapacitasFrazioneAmbiguaError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:
        logger.exception("Errore resolve-frazione particella %s: %s", particella_id, exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


_RPT_CERTIFICATO_BASE = "https://involture1.servizicapacitas.com/pages/rptCertificato.aspx"


def _normalize_link_param(value: str | None, *, default: str = "") -> str:
    return (value or "").strip() or default


def _missing_link_fields(*, com: str | None, pvc: str | None, fra: str | None) -> list[str]:
    missing: list[str] = []
    if not _normalize_link_param(com):
        missing.append("COM")
    if not _normalize_link_param(pvc):
        missing.append("PVC")
    if not _normalize_link_param(fra):
        missing.append("FRA")
    return missing


def _collect_local_link_contexts(db: Session, *, cco: str) -> list[tuple[str, str, str, str]]:
    contexts: set[tuple[str, str, str, str]] = set()

    def _add_context(com: str | None, pvc: str | None, fra: str | None, ccs: str | None) -> None:
        com_norm = _normalize_link_param(com)
        pvc_norm = _normalize_link_param(pvc)
        fra_norm = _normalize_link_param(fra)
        if not (com_norm and pvc_norm and fra_norm):
            return
        contexts.add((com_norm, pvc_norm, fra_norm, _normalize_link_param(ccs, default="00000")))

    for cert in db.execute(select(CatCapacitasCertificato).where(CatCapacitasCertificato.cco == cco)).scalars().all():
        _add_context(cert.com, cert.pvc, cert.fra, cert.ccs)
    for occ in db.execute(select(CatConsorzioOccupancy).where(CatConsorzioOccupancy.cco == cco)).scalars().all():
        _add_context(occ.com, occ.pvc, occ.fra, occ.ccs)
    for row in db.execute(select(CatCapacitasTerrenoRow).where(CatCapacitasTerrenoRow.cco == cco)).scalars().all():
        _add_context(row.com, row.pvc, row.fra, row.ccs)

    return sorted(contexts)


def _filter_link_contexts(
    contexts: list[tuple[str, str, str, str]],
    *,
    com: str | None,
    pvc: str | None,
    fra: str | None,
    ccs: str | None,
    apply_ccs_filter: bool,
) -> list[tuple[str, str, str, str]]:
    filtered = contexts
    if com is not None:
        filtered = [ctx for ctx in filtered if ctx[0] == com]
    if pvc is not None:
        filtered = [ctx for ctx in filtered if ctx[1] == pvc]
    if fra is not None:
        filtered = [ctx for ctx in filtered if ctx[2] == fra]
    if apply_ccs_filter:
        filtered = [ctx for ctx in filtered if ctx[3] == ccs]
    return filtered


@router.get("/involture/link/rpt-certificato")
async def get_rpt_certificato_link(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    cco: str = Query(..., min_length=1),
    com: str | None = Query(default=None),
    pvc: str | None = Query(default=None),
    fra: str | None = Query(default=None),
    ccs: str | None = Query(default=None),
    credential_id: int | None = None,
) -> dict[str, str]:
    """Return the browser-session URL to rptCertificato.aspx for a given CCO."""
    _ = credential_id  # Backward-compatible query parameter; the link uses the browser's Capacitas session.
    cco = cco.strip()

    raw_ccs = ccs
    com = _normalize_link_param(com) or None
    pvc = _normalize_link_param(pvc) or None
    fra = _normalize_link_param(fra) or None
    ccs = _normalize_link_param(ccs, default="00000")
    apply_ccs_filter = raw_ccs is not None or any(value is not None for value in (com, pvc, fra))

    available_contexts = _filter_link_contexts(
        _collect_local_link_contexts(db, cco=cco),
        com=com,
        pvc=pvc,
        fra=fra,
        ccs=ccs,
        apply_ccs_filter=apply_ccs_filter,
    )
    if len(available_contexts) > 1 and not (com and pvc and fra):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"CCO {cco} ambiguo: trovati {len(available_contexts)} contesti locali diversi. "
                "Specifica COM, PVC, FRA e CCS per aprire il certificato corretto."
            ),
        )

    certificato_query = select(CatCapacitasCertificato).where(CatCapacitasCertificato.cco == cco)
    occ_query = select(CatConsorzioOccupancy).where(CatConsorzioOccupancy.cco == cco)
    row_query = select(CatCapacitasTerrenoRow).where(CatCapacitasTerrenoRow.cco == cco)
    if com is not None:
        certificato_query = certificato_query.where(CatCapacitasCertificato.com == com)
        occ_query = occ_query.where(CatConsorzioOccupancy.com == com)
        row_query = row_query.where(CatCapacitasTerrenoRow.com == com)
    if pvc is not None:
        certificato_query = certificato_query.where(CatCapacitasCertificato.pvc == pvc)
        occ_query = occ_query.where(CatConsorzioOccupancy.pvc == pvc)
        row_query = row_query.where(CatCapacitasTerrenoRow.pvc == pvc)
    if fra is not None:
        certificato_query = certificato_query.where(CatCapacitasCertificato.fra == fra)
        occ_query = occ_query.where(CatConsorzioOccupancy.fra == fra)
        row_query = row_query.where(CatCapacitasTerrenoRow.fra == fra)
    if apply_ccs_filter:
        certificato_query = certificato_query.where(func.coalesce(CatCapacitasCertificato.ccs, "00000") == ccs)
        occ_query = occ_query.where(func.coalesce(CatConsorzioOccupancy.ccs, "00000") == ccs)
        row_query = row_query.where(func.coalesce(CatCapacitasTerrenoRow.ccs, "00000") == ccs)

    certificato = db.execute(
        certificato_query
        .order_by(desc(CatCapacitasCertificato.collected_at))
        .limit(1)
    ).scalar_one_or_none()
    if certificato is not None:
        missing = _missing_link_fields(com=certificato.com, pvc=certificato.pvc, fra=certificato.fra)
        if not missing:
            com, pvc, fra, ccs = certificato.com, certificato.pvc, certificato.fra, certificato.ccs
            params = urlencode(
                {
                    "CCO": cco,
                    "COM": _normalize_link_param(com),
                    "PVC": _normalize_link_param(pvc),
                    "FRA": _normalize_link_param(fra),
                    "CCS": _normalize_link_param(ccs, default="00000"),
                }
            )
            return {"url": f"{_RPT_CERTIFICATO_BASE}?{params}"}

    occ = db.execute(
        occ_query
        .order_by(desc(CatConsorzioOccupancy.updated_at))
        .limit(1)
    ).scalar_one_or_none()
    if occ is not None:
        missing = _missing_link_fields(com=occ.com, pvc=occ.pvc, fra=occ.fra)
        if not missing:
            com, pvc, fra, ccs = occ.com, occ.pvc, occ.fra, occ.ccs
            params = urlencode(
                {
                    "CCO": cco,
                    "COM": _normalize_link_param(com),
                    "PVC": _normalize_link_param(pvc),
                    "FRA": _normalize_link_param(fra),
                    "CCS": _normalize_link_param(ccs, default="00000"),
                }
            )
            return {"url": f"{_RPT_CERTIFICATO_BASE}?{params}"}

    row = db.execute(
        row_query
        .order_by(desc(CatCapacitasTerrenoRow.collected_at))
        .limit(1)
    ).scalar_one_or_none()
    if row is not None:
        missing = _missing_link_fields(com=row.com, pvc=row.pvc, fra=row.fra)
        if not missing:
            com, pvc, fra, ccs = row.com, row.pvc, row.fra, row.ccs
            params = urlencode(
                {
                    "CCO": cco,
                    "COM": _normalize_link_param(com),
                    "PVC": _normalize_link_param(pvc),
                    "FRA": _normalize_link_param(fra),
                    "CCS": _normalize_link_param(ccs, default="00000"),
                }
            )
            return {"url": f"{_RPT_CERTIFICATO_BASE}?{params}"}

    if certificato is not None:
        missing = ", ".join(_missing_link_fields(com=certificato.com, pvc=certificato.pvc, fra=certificato.fra))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CCO {cco} presente in cat_capacitas_certificati ma incompleto: mancano {missing}.",
        )
    if occ is not None:
        missing = ", ".join(_missing_link_fields(com=occ.com, pvc=occ.pvc, fra=occ.fra))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CCO {cco} presente in cat_consorzio_occupancies ma incompleto: mancano {missing}.",
        )
    if row is not None:
        missing = ", ".join(_missing_link_fields(com=row.com, pvc=row.pvc, fra=row.fra))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CCO {cco} presente in cat_capacitas_terreni_rows ma incompleto: mancano {missing}.",
        )

    logger.info("Capacitas rpt-certificato link non risolto: cco=%s fonte_locale_assente", cco)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"CCO {cco} non presente nelle fonti locali Capacitas (certificati, occupancies, terreni).",
    )
