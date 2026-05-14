from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, literal, select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoBatch, CatastoBatchStatus, CatastoComune, CatastoVisuraRequest
from app.modules.ruolo.models import RuoloParticella, RuoloPartita
from app.models.catasto import CatastoParcel
from app.services.elaborazioni_credentials import require_credentials_for_user


ADE_SCAN_PURPOSE = "ade_status_scan"
ADE_SCAN_PENDING_STATUSES = {"pending", "processing", "awaiting_captcha"}
UTC = timezone.utc

_SECTION_BY_PARTITA_COMUNE = {
    "DONIGALA": "B",
    "DONIGALA FENUGHEDU": "B",
    "MASSAMA": "C",
    "NURAXINIEDDU": "D",
    "SILI": "E",
    "SOLANAS": "B",
    "SAN VERO CONGIUS": "B",
}


@dataclass(slots=True)
class AdeStatusScanCandidate:
    ruolo_particella_id: UUID
    anno_tributario: int
    comune_nome: str
    comune_codice: str | None
    sezione: str | None
    foglio: str
    particella: str
    subalterno: str | None
    match_reason: str | None
    ade_scan_status: str | None
    ade_scan_classification: str | None
    ade_scan_checked_at: datetime | None
    ade_scan_document_id: UUID | None


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().upper().replace("'", " ").split())


def resolve_ade_section(comune_codice: str | None, partita_comune_nome: str | None) -> str | None:
    comune_key = _normalize_text(partita_comune_nome)
    if comune_key in _SECTION_BY_PARTITA_COMUNE:
        return _SECTION_BY_PARTITA_COMUNE[comune_key]

    # I casi Arborea provenienti dal ruolo storico Capacitas sono quelli che
    # SISTER espone come ARBOREA sezione C, come emerso dalla verifica manuale.
    if (comune_codice or "").strip().upper() == "A357" and comune_key == "ARBOREA":
        return "C"

    return None


def list_ade_status_scan_candidates(db: Session, *, limit: int = 200) -> list[AdeStatusScanCandidate]:
    rows = db.execute(
        select(
            RuoloParticella.id,
            RuoloParticella.anno_tributario,
            RuoloPartita.comune_nome,
            CatastoParcel.comune_codice,
            RuoloParticella.foglio,
            RuoloParticella.particella,
            RuoloParticella.subalterno,
            RuoloParticella.cat_particella_match_reason,
            RuoloParticella.ade_scan_status,
            RuoloParticella.ade_scan_classification,
            RuoloParticella.ade_scan_checked_at,
            RuoloParticella.ade_scan_document_id,
        )
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .outerjoin(CatastoParcel, CatastoParcel.id == RuoloParticella.catasto_parcel_id)
        .where(RuoloParticella.cat_particella_id.is_(None))
        .where(RuoloParticella.cat_particella_match_status == "unmatched")
        .where(
            RuoloParticella.ade_scan_status.is_(None)
            | (RuoloParticella.ade_scan_status == "failed")
        )
        .order_by(
            RuoloParticella.ade_scan_checked_at.asc().nullsfirst(),
            RuoloParticella.anno_tributario.desc(),
            RuoloParticella.id.asc(),
        )
        .limit(limit)
    ).all()

    candidates: list[AdeStatusScanCandidate] = []
    for row in rows:
        candidates.append(
            AdeStatusScanCandidate(
                ruolo_particella_id=row.id,
                anno_tributario=row.anno_tributario,
                comune_nome=row.comune_nome,
                comune_codice=row.comune_codice,
                sezione=resolve_ade_section(row.comune_codice, row.comune_nome),
                foglio=row.foglio,
                particella=row.particella,
                subalterno=row.subalterno,
                match_reason=row.cat_particella_match_reason,
                ade_scan_status=row.ade_scan_status,
                ade_scan_classification=row.ade_scan_classification,
                ade_scan_checked_at=row.ade_scan_checked_at,
                ade_scan_document_id=row.ade_scan_document_id,
            )
        )
    return candidates


def get_ade_status_scan_summary(db: Session) -> dict[str, object]:
    base_count = (
        select(func.count())
        .select_from(RuoloParticella)
        .where(RuoloParticella.cat_particella_id.is_(None))
        .where(RuoloParticella.cat_particella_match_status == "unmatched")
    )
    pending_count = (
        select(func.count())
        .select_from(RuoloParticella)
        .where(RuoloParticella.ade_scan_status.in_(ADE_SCAN_PENDING_STATUSES))
    )
    buckets = db.execute(
        select(
            func.coalesce(RuoloParticella.ade_scan_status, literal("not_scanned")),
            func.coalesce(RuoloParticella.ade_scan_classification, literal("unknown")),
            func.count(),
        )
        .where(RuoloParticella.cat_particella_id.is_(None))
        .group_by(1, 2)
        .order_by(func.count().desc())
    ).all()
    last_checked_at = db.scalar(select(func.max(RuoloParticella.ade_scan_checked_at)))
    return {
        "total_unmatched": db.scalar(base_count) or 0,
        "pending": db.scalar(pending_count) or 0,
        "last_checked_at": last_checked_at,
        "buckets": [
            {"status": row[0], "classification": row[1], "count": int(row[2])}
            for row in buckets
        ],
    }


def create_ade_status_scan_batch(db: Session, *, user_id: int, limit: int = 50) -> dict[str, object]:
    require_credentials_for_user(db, user_id)
    candidates = list_ade_status_scan_candidates(db, limit=limit)
    if not candidates:
        return {"batch_id": None, "created": 0, "skipped": 0}

    comuni_by_code = {
        item.codice_sister.split("#", maxsplit=1)[0].upper(): item
        for item in db.scalars(select(CatastoComune)).all()
        if item.codice_sister
    }

    batch = CatastoBatch(
        user_id=user_id,
        name=f"Visure storiche AdE particelle non collegate {datetime.now(UTC):%Y-%m-%d %H:%M}",
        status=CatastoBatchStatus.PROCESSING.value,
        total_items=0,
        current_operation="Queued AdE historical visure",
    )
    db.add(batch)
    db.flush()

    created = 0
    skipped = 0
    requests: list[CatastoVisuraRequest] = []
    now = datetime.now(UTC)
    for candidate in candidates:
        codice = (candidate.comune_codice or "").strip().upper()
        comune = comuni_by_code.get(codice)
        ruolo_row = db.get(RuoloParticella, candidate.ruolo_particella_id)
        if comune is None or ruolo_row is None:
            if ruolo_row is not None:
                ruolo_row.ade_scan_status = "failed"
                ruolo_row.ade_scan_error = f"Comune SISTER non risolto per codice catastale {codice or '-'}"
                ruolo_row.ade_scan_checked_at = now
            skipped += 1
            continue

        request = CatastoVisuraRequest(
            batch_id=batch.id,
            user_id=user_id,
            row_index=created + 1,
            purpose=ADE_SCAN_PURPOSE,
            target_ruolo_particella_id=candidate.ruolo_particella_id,
            search_mode="immobile",
            comune=comune.nome,
            comune_codice=comune.codice_sister,
            catasto="Terreni",
            sezione=candidate.sezione,
            foglio=candidate.foglio,
            particella=candidate.particella,
            subalterno=candidate.subalterno,
            tipo_visura="Sintetica",
            request_type="STORICA",
            status="pending",
            current_operation="In coda per visura storica sintetica AdE",
        )
        requests.append(request)
        db.add(request)
        db.flush()
        ruolo_row.ade_scan_status = "pending"
        ruolo_row.ade_scan_request_id = request.id
        ruolo_row.ade_scan_error = None
        created += 1

    if not requests:
        batch.status = CatastoBatchStatus.COMPLETED.value
        batch.completed_at = now
        batch.current_operation = "Nessuna richiesta SISTER creata"
    else:
        batch.total_items = len(requests)
        batch.current_operation = f"{len(requests)} visure storiche sintetiche AdE in coda"
    db.commit()
    return {"batch_id": str(batch.id), "created": created, "skipped": skipped}


def persist_ade_status_scan_result(
    db: Session,
    *,
    ruolo_particella_id: UUID,
    request_id: UUID,
    status: str,
    classification: str | None,
    document_id: UUID | None = None,
    payload: dict | None = None,
    error: str | None = None,
) -> None:
    ruolo_row = db.get(RuoloParticella, ruolo_particella_id)
    if ruolo_row is None:
        return
    ruolo_row.ade_scan_status = status
    ruolo_row.ade_scan_classification = classification
    ruolo_row.ade_scan_checked_at = datetime.now(UTC)
    ruolo_row.ade_scan_request_id = request_id
    ruolo_row.ade_scan_document_id = document_id
    ruolo_row.ade_scan_error = error
    ruolo_row.ade_scan_payload_json = payload
