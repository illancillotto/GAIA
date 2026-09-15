from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.presenze.services.punch_reminder_job import apply_whatsapp_webhook_events
from app.modules.presenze.services.whatsapp_config import load_whatsapp_config
from app.modules.presenze.services.whatsapp_waha import parse_waha_webhook, verify_waha_signature

router = APIRouter(prefix="/presenze/whatsapp")


# Chiamato solo dal container WAHA sulla rete Docker: nessun utente, autenticazione
# tramite firma HMAC-SHA512 del corpo con la chiave condivisa.
@router.post("/webhook", status_code=204)
async def receive_waha_webhook(
    request: Request, db: Annotated[Session, Depends(get_db)]
) -> Response:
    hmac_key = load_whatsapp_config(db).waha_hmac_key
    if not hmac_key:
        raise HTTPException(status_code=503, detail="Webhook WhatsApp non configurato")
    raw_body = await request.body()
    if not verify_waha_signature(raw_body, request.headers.get("x-webhook-hmac"), hmac_key):
        raise HTTPException(status_code=401, detail="Firma webhook non valida")
    try:
        body = json.loads(raw_body or b"{}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Corpo webhook non valido") from exc
    apply_whatsapp_webhook_events(db, parse_waha_webhook(body))
    return Response(status_code=204)
