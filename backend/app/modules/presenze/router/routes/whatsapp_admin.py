from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.presenze.router.common import RequirePresenzeAdmin, RequirePresenzeModule
from app.modules.presenze.services.punch_reminder_job import reconcile_uncertain_attempt
from app.modules.presenze.services.whatsapp_admin import (
    build_preview,
    dashboard_summary,
    list_messages,
    list_opt_outs,
    remove_opt_out,
    update_phone,
)
from app.modules.presenze.whatsapp_admin_schemas import (
    WhatsAppDashboardSummaryResponse,
    WhatsAppMessageListResponse,
    WhatsAppMessageQuery,
    WhatsAppOptOutResponse,
    WhatsAppPhoneResponse,
    WhatsAppPhoneUpdate,
    WhatsAppPreviewResponse,
    WhatsAppReconcileRequest,
)

router = APIRouter(prefix="/presenze/whatsapp")


@router.get("/dashboard", response_model=WhatsAppDashboardSummaryResponse)
def get_whatsapp_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> dict[str, object]:
    return dashboard_summary(db)


@router.get("/messages", response_model=WhatsAppMessageListResponse)
def get_whatsapp_messages(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
    query: Annotated[WhatsAppMessageQuery, Query()],
) -> dict[str, object]:
    return list_messages(
        db,
        status=query.status,
        query=query.q,
        page=query.page,
        page_size=query.page_size,
    )


@router.get("/preview", response_model=WhatsAppPreviewResponse)
def get_whatsapp_preview(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> dict[str, object]:
    return build_preview(db)


@router.get("/opt-outs", response_model=list[WhatsAppOptOutResponse])
def get_whatsapp_opt_outs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> list[dict[str, object]]:
    return list_opt_outs(db)


@router.delete("/opt-outs/{user_id}", status_code=204)
def delete_whatsapp_opt_out(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> Response:
    if not remove_opt_out(db, user_id):
        raise HTTPException(status_code=404, detail="STOP WhatsApp non trovato")
    return Response(status_code=204)


@router.patch("/users/{user_id}/phone", response_model=WhatsAppPhoneResponse)
def patch_whatsapp_phone(
    user_id: int,
    payload: WhatsAppPhoneUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> dict[str, object]:
    result = update_phone(db, user_id, payload.phone)
    if result is None:
        raise HTTPException(status_code=404, detail="Utente GAIA non trovato")
    return result


@router.post("/messages/{message_id}/reconcile", status_code=204)
def reconcile_whatsapp_message(
    message_id: UUID,
    payload: WhatsAppReconcileRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> Response:
    try:
        reconcile_uncertain_attempt(
            db,
            message_id,
            sent=payload.sent,
            evidence=payload.evidence,
            provider_message_id=payload.provider_message_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(status_code=204)
