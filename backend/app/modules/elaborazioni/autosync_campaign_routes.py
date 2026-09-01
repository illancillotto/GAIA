from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoPerpetualSyncItem
from app.schemas.catasto import CatastoPerpetualSyncItemResponse
from app.schemas.elaborazioni import ElaborazioneOperationResponse
from app.services.elaborazioni_perpetual_sync import (
    ROLE_CAMPAIGN_SCOPES,
    retry_perpetual_sync_failures,
)

router = APIRouter()


class AutoSyncCampaignItemsPage(BaseModel):
    items: list[CatastoPerpetualSyncItemResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


def _validate_campaign_scope(scope: str) -> None:
    if scope not in ROLE_CAMPAIGN_SCOPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Campagna AutoSync non valida",
        )


@router.get(
    "/ruolo-autosync/campaigns/{scope}/items",
    response_model=AutoSyncCampaignItemsPage,
)
def list_campaign_items(
    scope: str,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AutoSyncCampaignItemsPage:
    _validate_campaign_scope(scope)
    filters = (
        CatastoPerpetualSyncItem.user_id == current_user.id,
        CatastoPerpetualSyncItem.scope == scope,
    )
    total = int(
        db.scalar(select(func.count(CatastoPerpetualSyncItem.id)).where(*filters)) or 0
    )
    items = list(
        db.scalars(
            select(CatastoPerpetualSyncItem)
            .where(*filters)
            .order_by(
                CatastoPerpetualSyncItem.priority.asc(),
                CatastoPerpetualSyncItem.updated_at.desc(),
                CatastoPerpetualSyncItem.id.asc(),
            )
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return AutoSyncCampaignItemsPage(
        items=[CatastoPerpetualSyncItemResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )


@router.post(
    "/ruolo-autosync/campaigns/{scope}/retry-failed",
    response_model=ElaborazioneOperationResponse,
)
def retry_campaign_failures(
    scope: str,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ElaborazioneOperationResponse:
    _validate_campaign_scope(scope)
    retried = retry_perpetual_sync_failures(db, current_user.id, scope)
    return ElaborazioneOperationResponse(
        message=f"{retried} elementi falliti rimessi in coda per la campagna {scope}."
    )
