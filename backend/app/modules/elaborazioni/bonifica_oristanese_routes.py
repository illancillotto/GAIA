from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.elaborazioni.bonifica_oristanese.models import (
    BonificaOristaneseCredentialCreate,
    BonificaOristaneseCredentialOut,
    BonificaSyncRunRequest,
    BonificaSyncRunResponse,
    BonificaSyncStatusResponse,
    BonificaOristaneseCredentialTestResult,
    BonificaOristaneseCredentialUpdate,
)
from app.services.elaborazioni_bonifica_sync import get_bonifica_sync_status, run_bonifica_sync
from app.services.elaborazioni_bonifica_oristanese import (
    create_credential,
    delete_credential,
    get_credential,
    list_credentials,
    test_credential,
    update_credential,
)

router = APIRouter(tags=["elaborazioni-bonifica-oristanese"])


@router.post("/credentials", response_model=BonificaOristaneseCredentialOut, status_code=status.HTTP_201_CREATED)
def create_cred(
    payload: BonificaOristaneseCredentialCreate,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BonificaOristaneseCredentialOut:
    return create_credential(db, payload)


@router.get("/credentials", response_model=list[BonificaOristaneseCredentialOut])
def list_creds(
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[BonificaOristaneseCredentialOut]:
    return list_credentials(db)


@router.get("/credentials/{credential_id}", response_model=BonificaOristaneseCredentialOut)
def get_cred(
    credential_id: int,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BonificaOristaneseCredentialOut:
    credential = get_credential(db, credential_id)
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credenziale non trovata")
    return BonificaOristaneseCredentialOut.model_validate(credential)


@router.patch("/credentials/{credential_id}", response_model=BonificaOristaneseCredentialOut)
def update_cred(
    credential_id: int,
    payload: BonificaOristaneseCredentialUpdate,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BonificaOristaneseCredentialOut:
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


@router.post("/credentials/{credential_id}/test", response_model=BonificaOristaneseCredentialTestResult)
async def test_cred(
    credential_id: int,
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BonificaOristaneseCredentialTestResult:
    result = await test_credential(db, credential_id)
    if not result.ok:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result.error)
    return result


@router.post("/sync/run", response_model=BonificaSyncRunResponse)
async def run_sync(
    body: BonificaSyncRunRequest,
    current_user: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BonificaSyncRunResponse:
    try:
        return await run_bonifica_sync(db, current_user, body)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/sync/status", response_model=BonificaSyncStatusResponse)
def get_sync_status(
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BonificaSyncStatusResponse:
    return get_bonifica_sync_status(db)
