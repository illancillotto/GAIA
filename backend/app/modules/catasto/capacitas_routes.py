from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_admin_user
from app.core.database import get_db
from app.modules.catasto.capacitas.client import InVoltureClient
from app.modules.catasto.capacitas.models import (
    AnagraficaSearchRequest,
    CapacitasCredentialCreate,
    CapacitasCredentialOut,
    CapacitasCredentialUpdate,
    CapacitasSearchResult,
)
from app.modules.catasto.capacitas.session import CapacitasSessionManager
from app.models.application_user import ApplicationUser
from app.services.catasto_capacitas import (
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catasto/capacitas", tags=["catasto-capacitas"])


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
