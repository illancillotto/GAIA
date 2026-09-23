from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.catasto import (
    CatastoDocument,
    CatastoSisterExtraction,
    CatastoSisterHistoryEvent,
    CatastoSisterOwner,
    CatastoSisterParcel,
)
from app.models.catasto_phase1 import CatIntestatario, CatParticella
from app.services.sister_visura_parser import PARSER_VERSION, parse_sister_visura_pdf, sister_pdf_sha256


def _jsonable(value: Any) -> Any:
    if isinstance(value, (date,)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _resolve_particella(db: Session, payload: dict[str, Any]) -> CatParticella | None:
    parcel = payload.get("parcel") or {}
    foglio = str(parcel.get("foglio") or "").strip()
    particella = str(parcel.get("particella") or "").strip()
    if not foglio or not particella:
        return None
    query = select(CatParticella).where(
        CatParticella.is_current.is_(True),
        CatParticella.foglio == foglio,
        CatParticella.particella == particella,
    )
    codice = str(payload.get("comune_codice") or "").strip().casefold()
    nome = str(payload.get("comune_nome") or "").strip().casefold()
    candidates = db.execute(query).scalars().all()
    matches = [item for item in candidates if codice and (item.codice_catastale or "").casefold() == codice]
    if not matches and nome:
        matches = [item for item in candidates if (item.nome_comune or "").casefold() == nome]
    return matches[0] if len(matches) == 1 else None


def persist_sister_visura(db: Session, document: CatastoDocument) -> CatastoSisterExtraction:
    existing = db.scalar(select(CatastoSisterExtraction).where(CatastoSisterExtraction.document_id == document.id))
    pdf_sha256 = sister_pdf_sha256(document.filepath)
    if existing is not None and existing.pdf_sha256 == pdf_sha256 and existing.parser_version == PARSER_VERSION:
        return existing
    try:
        parsed = parse_sister_visura_pdf(document.filepath)
        payload = _jsonable(parsed)
        extraction = existing or CatastoSisterExtraction(document_id=document.id, parser_version=PARSER_VERSION, pdf_sha256=pdf_sha256, payload_json={})
        extraction.parser_version = PARSER_VERSION
        extraction.pdf_sha256 = pdf_sha256
        extraction.status = str(payload.get("status") or "review_required")
        extraction.observed_at = date.fromisoformat(payload["observed_at"]) if payload.get("observed_at") else None
        extraction.payload_json = payload
        extraction.error_message = None
        db.add(extraction)
        db.flush()
        db.execute(delete(CatastoSisterParcel).where(CatastoSisterParcel.extraction_id == extraction.id))
        db.execute(delete(CatastoSisterHistoryEvent).where(CatastoSisterHistoryEvent.extraction_id == extraction.id))
        canonical_particella = _resolve_particella(db, payload)
        parcel = CatastoSisterParcel(
            extraction_id=extraction.id,
            comune_nome=payload.get("comune_nome"),
            comune_codice=payload.get("comune_codice"),
            foglio=(payload.get("parcel") or {}).get("foglio"),
            particella=(payload.get("parcel") or {}).get("particella"),
            subalterno=(payload.get("parcel") or {}).get("subalterno"),
            payload_json=payload.get("parcel") or {},
            cat_particella_id=canonical_particella.id if canonical_particella else None,
        )
        db.add(parcel)
        db.flush()
        for owner_payload in payload.get("owners") or []:
            cf = str(owner_payload.get("codice_fiscale") or "").strip().upper() or None
            canonical = db.scalar(select(CatIntestatario).where(func.upper(CatIntestatario.codice_fiscale) == cf)) if cf else None
            db.add(CatastoSisterOwner(
                sister_parcel_id=parcel.id,
                cat_intestatario_id=canonical.id if canonical else None,
                codice_fiscale=cf,
                denominazione=owner_payload.get("denominazione"),
                cognome=owner_payload.get("cognome"),
                nome=owner_payload.get("nome"),
                data_nascita=date.fromisoformat(owner_payload["data_nascita"]) if owner_payload.get("data_nascita") else None,
                luogo_nascita=owner_payload.get("luogo_nascita"),
                diritto=owner_payload.get("diritto"),
                quota=owner_payload.get("quota"),
                payload_json=owner_payload,
            ))
        for event in payload.get("history_events") or []:
            owner = event.get("owner") or {}
            db.add(
                CatastoSisterHistoryEvent(
                    extraction_id=extraction.id,
                    from_date=date.fromisoformat(event["from_date"]) if event.get("from_date") else None,
                    act_date=date.fromisoformat(event["act_date"]) if event.get("act_date") else None,
                    codice_fiscale=owner.get("codice_fiscale"),
                    denominazione=owner.get("denominazione"),
                    diritto=owner.get("diritto"),
                    quota=owner.get("quota"),
                    act_description=event.get("act"),
                    payload_json=event,
                )
            )
        return extraction
    except Exception as exc:
        extraction = existing or CatastoSisterExtraction(document_id=document.id, parser_version=PARSER_VERSION, pdf_sha256=pdf_sha256, payload_json={})
        extraction.status = "failed"
        extraction.error_message = str(exc)
        extraction.payload_json = {}
        db.add(extraction)
        return extraction


__all__ = ["persist_sister_visura"]
