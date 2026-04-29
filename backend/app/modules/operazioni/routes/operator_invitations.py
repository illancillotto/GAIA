"""Operator invitation and self-activation flow."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_active_user, require_not_operator
from app.core.database import get_db
from app.core.security import hash_password
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.operator_invitation import OperatorInvitation
from app.modules.operazioni.models.wc_operator import WCOperator

router = APIRouter(tags=["operazioni/operator-invitations"])

# Public router — no module/auth guard — mounted directly on the api router
public_router = APIRouter(prefix="/auth", tags=["auth/operator-activation"])

INVITATION_EXPIRY_DAYS = 7
UTC = timezone.utc


# ─── schemas ──────────────────────────────────────────────────────────────────

class InvitationResponse(BaseModel):
    token: str
    expires_at: str
    activation_url_path: str
    already_activated: bool


class InvitationStatusResponse(BaseModel):
    has_pending: bool
    has_activated: bool
    token: str | None
    expires_at: str | None
    activated_at: str | None
    gaia_user_id: int | None


class ActivationInfo(BaseModel):
    wc_operator_id: str
    first_name: str | None
    last_name: str | None
    email: str | None
    suggested_username: str | None
    already_activated: bool


class ActivateRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Username deve essere di almeno 3 caratteri")
        if not v.replace("_", "").replace(".", "").replace("-", "").isalnum():
            raise ValueError("Username può contenere solo lettere, cifre, _, . e -")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La password deve essere di almeno 8 caratteri")
        return v


class ActivationResult(BaseModel):
    user_id: int
    username: str
    message: str


class BulkImportedOperator(BaseModel):
    wc_operator_id: str
    full_name: str
    username: str
    temp_password: str
    skipped: bool
    skip_reason: str | None


class BulkImportResult(BaseModel):
    created: int
    skipped: int
    operators: list[BulkImportedOperator]


# ─── endpoints ────────────────────────────────────────────────────────────────

@router.post("/operators/{wc_operator_id}/invite", response_model=InvitationResponse)
def create_invitation(
    wc_operator_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_not_operator)],
    db: Annotated[Session, Depends(get_db)],
):
    op = db.get(WCOperator, wc_operator_id)
    if op is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")

    # If already linked to an active GAIA user, return early
    if op.gaia_user_id is not None:
        existing_user = db.get(ApplicationUser, op.gaia_user_id)
        if existing_user and existing_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Operator is already linked to an active GAIA user",
            )

    # Revoke any existing pending invitation for this operator
    pending = db.scalars(
        select(OperatorInvitation)
        .where(OperatorInvitation.wc_operator_id == wc_operator_id)
        .where(OperatorInvitation.activated_at.is_(None))
    ).all()
    for inv in pending:
        db.delete(inv)

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(days=INVITATION_EXPIRY_DAYS)

    invitation = OperatorInvitation(
        wc_operator_id=wc_operator_id,
        token=token,
        created_by_user_id=current_user.id,
        expires_at=expires_at,
    )
    db.add(invitation)
    db.commit()

    return InvitationResponse(
        token=token,
        expires_at=expires_at.isoformat(),
        activation_url_path=f"/auth/attiva/{token}",
        already_activated=False,
    )


@router.get("/operators/{wc_operator_id}/invitation-status", response_model=InvitationStatusResponse)
def get_invitation_status(
    wc_operator_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    op = db.get(WCOperator, wc_operator_id)
    if op is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")

    activated = db.scalar(
        select(OperatorInvitation)
        .where(OperatorInvitation.wc_operator_id == wc_operator_id)
        .where(OperatorInvitation.activated_at.isnot(None))
        .order_by(OperatorInvitation.activated_at.desc())
    )
    if activated:
        return InvitationStatusResponse(
            has_pending=False,
            has_activated=True,
            token=None,
            expires_at=None,
            activated_at=activated.activated_at.isoformat() if activated.activated_at else None,
            gaia_user_id=op.gaia_user_id,
        )

    pending = db.scalar(
        select(OperatorInvitation)
        .where(OperatorInvitation.wc_operator_id == wc_operator_id)
        .where(OperatorInvitation.activated_at.is_(None))
        .order_by(OperatorInvitation.created_at.desc())
    )
    if pending:
        return InvitationStatusResponse(
            has_pending=True,
            has_activated=False,
            token=pending.token,
            expires_at=pending.expires_at.isoformat(),
            activated_at=None,
            gaia_user_id=None,
        )

    return InvitationStatusResponse(
        has_pending=False, has_activated=False, token=None,
        expires_at=None, activated_at=None, gaia_user_id=None,
    )


@router.post("/operators/bulk-import-gaia", response_model=BulkImportResult)
def bulk_import_operators_as_gaia_users(
    current_user: Annotated[ApplicationUser, Depends(require_not_operator)],
    db: Annotated[Session, Depends(get_db)],
):
    unlinked = db.scalars(
        select(WCOperator)
        .where(WCOperator.gaia_user_id.is_(None))
        .order_by(WCOperator.last_name.asc(), WCOperator.first_name.asc())
    ).all()

    existing_usernames: set[str] = set(db.scalars(select(ApplicationUser.username)).all())

    results: list[BulkImportedOperator] = []
    created = 0
    skipped = 0

    for op in unlinked:
        full_name = " ".join(p for p in [op.last_name, op.first_name] if p).strip()
        if not full_name and not op.username:
            results.append(BulkImportedOperator(
                wc_operator_id=str(op.id),
                full_name=f"WC {op.wc_id}",
                username="",
                temp_password="",
                skipped=True,
                skip_reason="Nome e username mancanti",
            ))
            skipped += 1
            continue

        # Build candidate username: lastname.firstname, all lowercase, no spaces/accents
        if op.last_name and op.first_name:
            base = f"{op.last_name.lower()}.{op.first_name.lower()}"
        elif op.username:
            base = op.username.lower()
        else:
            base = full_name.lower()

        import re
        base = re.sub(r"[^a-z0-9._-]", "", base.replace(" ", "."))
        base = base.strip(".")

        username = base
        suffix = 1
        while username in existing_usernames:
            username = f"{base}{suffix}"
            suffix += 1
        existing_usernames.add(username)

        temp_password = secrets.token_urlsafe(10)

        email = op.email or f"{username}@operatori.local"
        # Deduplicate email too
        existing_emails = {u.email for u in db.scalars(select(ApplicationUser)).all()}
        if email in existing_emails:
            email = f"{username}@operatori.local"

        new_user = ApplicationUser(
            username=username,
            email=email,
            password_hash=hash_password(temp_password),
            role=ApplicationUserRole.OPERATOR.value,
            is_active=True,
            module_operazioni=True,
        )
        db.add(new_user)
        db.flush()

        op.gaia_user_id = new_user.id

        results.append(BulkImportedOperator(
            wc_operator_id=str(op.id),
            full_name=full_name or username,
            username=username,
            temp_password=temp_password,
            skipped=False,
            skip_reason=None,
        ))
        created += 1

    db.commit()
    return BulkImportResult(created=created, skipped=skipped, operators=results)


@public_router.get("/invite/{token}", response_model=ActivationInfo)
def get_activation_info(
    token: str,
    db: Annotated[Session, Depends(get_db)],
):
    invitation = db.scalar(
        select(OperatorInvitation).where(OperatorInvitation.token == token)
    )
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link non valido")

    if invitation.activated_at is not None:
        op = db.get(WCOperator, invitation.wc_operator_id)
        return ActivationInfo(
            wc_operator_id=str(invitation.wc_operator_id),
            first_name=op.first_name if op else None,
            last_name=op.last_name if op else None,
            email=op.email if op else None,
            suggested_username=None,
            already_activated=True,
        )

    if datetime.now(UTC) > invitation.expires_at:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link scaduto")

    op = db.get(WCOperator, invitation.wc_operator_id)
    if op is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operatore non trovato")

    # Suggest a username: lastname.firstname lowercased, no spaces
    suggested = None
    if op.last_name and op.first_name:
        suggested = f"{op.last_name.lower().replace(' ', '')}.{op.first_name.lower().replace(' ', '')}"
    elif op.username:
        suggested = op.username.lower()

    return ActivationInfo(
        wc_operator_id=str(op.id),
        first_name=op.first_name,
        last_name=op.last_name,
        email=op.email,
        suggested_username=suggested,
        already_activated=False,
    )


@public_router.post("/invite/{token}/activate", response_model=ActivationResult)
def activate_account(
    token: str,
    body: ActivateRequest,
    db: Annotated[Session, Depends(get_db)],
):
    invitation = db.scalar(
        select(OperatorInvitation).where(OperatorInvitation.token == token)
    )
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link non valido")
    if invitation.activated_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account già attivato")
    if datetime.now(UTC) > invitation.expires_at:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link scaduto")

    op = db.get(WCOperator, invitation.wc_operator_id)
    if op is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operatore non trovato")

    # Ensure username is unique
    existing = db.scalar(
        select(ApplicationUser).where(ApplicationUser.username == body.username)
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username già in uso")

    new_user = ApplicationUser(
        username=body.username,
        email=op.email or f"{body.username}@operatori.local",
        password_hash=hash_password(body.password),
        role=ApplicationUserRole.OPERATOR.value,
        is_active=True,
        module_operazioni=True,
    )
    db.add(new_user)
    db.flush()

    op.gaia_user_id = new_user.id
    invitation.activated_at = datetime.now(UTC)
    invitation.activated_user_id = new_user.id

    db.commit()

    return ActivationResult(
        user_id=new_user.id,
        username=new_user.username,
        message="Account attivato con successo. Puoi ora accedere a GAIA.",
    )
