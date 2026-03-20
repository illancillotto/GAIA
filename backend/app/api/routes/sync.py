from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require_active_user
from app.models.application_user import ApplicationUser
from app.schemas.sync import SyncCapabilitiesResponse, SyncPreviewRequest, SyncPreviewResponse
from app.services.nas_connector import build_sync_preview, get_sync_capabilities

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/capabilities", response_model=SyncCapabilitiesResponse)
def sync_capabilities(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
) -> SyncCapabilitiesResponse:
    return get_sync_capabilities()


@router.post("/preview", response_model=SyncPreviewResponse)
def sync_preview(
    payload: SyncPreviewRequest,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
) -> SyncPreviewResponse:
    return build_sync_preview(payload)
