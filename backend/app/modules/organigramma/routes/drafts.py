from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.organigramma.deps import require_organigramma_manage_or_inaz
from app.modules.organigramma import repositories as repo
from app.modules.organigramma.schemas import (
    OrgAssignmentResponse,
    OrgChangeEventResponse,
    OrgDraftCreate,
    OrgDraftDetailResponse,
    OrgRevisionResponse,
    OrgUnitTreeNode,
)
from app.modules.organigramma.services import drafts_service as svc

router = APIRouter(prefix="/drafts", tags=["organigramma/drafts"])


@router.get("/revisions", response_model=list[OrgRevisionResponse])
def list_revisions(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
) -> list[OrgRevisionResponse]:
    svc.ensure_published_revision(db, user_id=None)
    return svc.list_revision_responses(db)


@router.get("/revisions/current", response_model=OrgRevisionResponse)
def get_current_revision(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
) -> OrgRevisionResponse:
    return svc.ensure_published_revision(db, user_id=current_user.id)


@router.get("/my-active", response_model=OrgDraftDetailResponse | None)
def get_my_active_draft(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
) -> OrgDraftDetailResponse | None:
    return svc.get_active_draft_response(db, user_id=current_user.id)


@router.post("", response_model=OrgDraftDetailResponse, status_code=status.HTTP_201_CREATED)
def create_draft(
    payload: OrgDraftCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
) -> OrgDraftDetailResponse:
    try:
        return svc.create_draft_from_current(db, payload, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{draft_id}", response_model=OrgDraftDetailResponse)
def get_draft(
    draft_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
) -> OrgDraftDetailResponse:
    draft = repo.get_draft(db, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    return svc.build_draft_detail(db, draft)


@router.get("/{draft_id}/tree", response_model=list[OrgUnitTreeNode])
def get_draft_tree(
    draft_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
) -> list[OrgUnitTreeNode]:
    draft = repo.get_draft(db, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    return svc.build_tree_for_revision(db, draft.working_revision_id)


@router.get("/{draft_id}/assignments", response_model=list[OrgAssignmentResponse])
def get_draft_assignments(
    draft_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
) -> list[OrgAssignmentResponse]:
    draft = repo.get_draft(db, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    return svc.list_assignment_responses_for_revision(db, draft.working_revision_id)


@router.get("/{draft_id}/events", response_model=list[OrgChangeEventResponse])
def get_draft_events(
    draft_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
) -> list[OrgChangeEventResponse]:
    draft = repo.get_draft(db, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    return [OrgChangeEventResponse.model_validate(event) for event in repo.list_change_events(db, draft_id)]


@router.post("/{draft_id}/publish", response_model=OrgDraftDetailResponse)
def publish_draft(
    draft_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
) -> OrgDraftDetailResponse:
    draft = repo.get_draft(db, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    if draft.status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active drafts can be published")
    try:
        return svc.publish_draft(db, draft, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{draft_id}/discard", response_model=OrgDraftDetailResponse)
def discard_draft(
    draft_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
) -> OrgDraftDetailResponse:
    draft = repo.get_draft(db, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    if draft.status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active drafts can be discarded")
    return svc.discard_draft(db, draft, user_id=current_user.id)
