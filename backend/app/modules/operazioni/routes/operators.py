from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.schemas.operators import (
    AutoLinkResult,
    GaiaUserMin,
    LinkGaiaRequest,
    UnlinkedOperatorItem,
    UnlinkedOperatorsResponse,
    WCOperatorListResponse,
    WCOperatorResponse,
)


router = APIRouter(prefix="/operators", tags=["operazioni/operators"])


@router.get("", response_model=WCOperatorListResponse)
def list_operators_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    search: str | None = Query(None),
    role: str | None = Query(None),
    enabled: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    query = select(WCOperator)
    if search:
        like = f"%{search}%"
        query = query.where(
            (WCOperator.username.ilike(like))
            | (WCOperator.email.ilike(like))
            | (WCOperator.first_name.ilike(like))
            | (WCOperator.last_name.ilike(like))
            | (WCOperator.tax.ilike(like))
        )
    if role:
        query = query.where(WCOperator.role == role)
    if enabled is not None:
        query = query.where(WCOperator.enabled == enabled)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(WCOperator.role.asc(), WCOperator.last_name.asc(), WCOperator.first_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return WCOperatorListResponse(
        items=[WCOperatorResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get("/unlinked", response_model=UnlinkedOperatorsResponse)
def list_unlinked_operators(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    unlinked = db.scalars(
        select(WCOperator)
        .where(WCOperator.gaia_user_id.is_(None))
        .order_by(WCOperator.last_name.asc(), WCOperator.first_name.asc())
    ).all()

    # Build lookup maps for email and username matching
    all_gaia_users = db.scalars(select(ApplicationUser)).all()
    by_email: dict[str, ApplicationUser] = {}
    by_username: dict[str, ApplicationUser] = {}
    for u in all_gaia_users:
        if u.email:
            by_email[u.email.lower()] = u
        if u.username:
            by_username[u.username.lower()] = u

    items: list[UnlinkedOperatorItem] = []
    for op in unlinked:
        suggested: ApplicationUser | None = None
        if op.email:
            suggested = by_email.get(op.email.lower())
        if suggested is None and op.username:
            suggested = by_username.get(op.username.lower())

        items.append(UnlinkedOperatorItem(
            id=op.id,
            wc_id=op.wc_id,
            username=op.username,
            email=op.email,
            first_name=op.first_name,
            last_name=op.last_name,
            role=op.role,
            enabled=op.enabled,
            suggested_gaia_user=GaiaUserMin(
                id=suggested.id,
                username=suggested.username,
                email=suggested.email,
                is_active=suggested.is_active,
            ) if suggested else None,
        ))

    return UnlinkedOperatorsResponse(items=items, total=len(items))


@router.get("/gaia-users", response_model=list[GaiaUserMin])
def list_gaia_users_for_linking(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    search: str | None = Query(None),
):
    query = select(ApplicationUser)
    if search:
        like = f"%{search}%"
        query = query.where(
            ApplicationUser.username.ilike(like) | ApplicationUser.email.ilike(like)
        )
    users = db.scalars(query.order_by(ApplicationUser.username.asc()).limit(50)).all()
    return [GaiaUserMin(id=u.id, username=u.username, email=u.email, is_active=u.is_active) for u in users]


@router.post("/auto-link-gaia", response_model=AutoLinkResult)
def auto_link_gaia(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    unlinked = db.scalars(
        select(WCOperator).where(WCOperator.gaia_user_id.is_(None))
    ).all()

    all_gaia_users = db.scalars(select(ApplicationUser)).all()
    by_email: dict[str, ApplicationUser] = {}
    by_username: dict[str, ApplicationUser] = {}
    for u in all_gaia_users:
        if u.email:
            by_email[u.email.lower()] = u
        if u.username:
            by_username[u.username.lower()] = u

    linked = 0
    skipped = 0
    for op in unlinked:
        match: ApplicationUser | None = None
        if op.email:
            match = by_email.get(op.email.lower())
        if match is None and op.username:
            match = by_username.get(op.username.lower())
        if match:
            op.gaia_user_id = match.id
            linked += 1
        else:
            skipped += 1

    db.commit()
    return AutoLinkResult(linked=linked, already_linked=0, skipped=skipped)


@router.post("/{operator_id}/link-gaia", response_model=WCOperatorResponse)
def link_gaia_user(
    operator_id: UUID,
    body: LinkGaiaRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    op = db.get(WCOperator, operator_id)
    if op is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")
    gaia_user = db.get(ApplicationUser, body.gaia_user_id)
    if gaia_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GAIA user not found")
    op.gaia_user_id = gaia_user.id
    db.commit()
    db.refresh(op)
    return WCOperatorResponse.model_validate(op)


@router.post("/{operator_id}/unlink-gaia", response_model=WCOperatorResponse)
def unlink_gaia_user(
    operator_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    op = db.get(WCOperator, operator_id)
    if op is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")
    op.gaia_user_id = None
    db.commit()
    db.refresh(op)
    return WCOperatorResponse.model_validate(op)


@router.get("/{operator_id}", response_model=WCOperatorResponse)
def get_operator_endpoint(
    operator_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    item = db.get(WCOperator, operator_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")
    return WCOperatorResponse.model_validate(item)
