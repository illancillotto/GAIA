from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import (
    CatComune,
    CatConsorzioOccupancy,
    CatParticella,
)
from app.modules.elaborazioni.capacitas.models import (
    CapacitasTerrenoRow,
)
from app.schemas.catasto_phase1 import (
    CatAnagraficaBulkSearchRequest,
    CatAnagraficaBulkSearchRowResult,
    CatAnagraficaMatch,
)

router = APIRouter(
    prefix="/catasto/elaborazioni-massive/particelle", tags=["catasto-elaborazioni-massive"]
)
logger = logging.getLogger(__name__)
CATASTO_DISTRETTO_EXPORT_STORAGE_PATH = Path(
    os.getenv("CATASTO_DISTRETTO_EXPORT_STORAGE_PATH", "/data/catasto/exports/distretti")
)


# fmt: off

class _LiveSearchHit:
    __slots__ = ("frazione_id", "lookup_label", "row")

    def __init__(self, frazione_id: str, lookup_label: str, row: CapacitasTerrenoRow) -> None:
        self.frazione_id = frazione_id
        self.lookup_label = lookup_label
        self.row = row


class CapacitasLiveAuthoritativeSanitizer:
    """Sanitizes authoritative Capacitas-live matches for cadastral bulk export."""

    def sanitize(self, match: CatAnagraficaMatch) -> CatAnagraficaMatch:
        has_context = bool(
            (match.cert_com or "").strip()
            and (match.cert_pvc or "").strip()
            and (match.cert_fra or "").strip()
        )
        if has_context:
            return match

        if match.intestatari:
            logger.warning(
                "Capacitas live sanitize cleared owners without context: particella_id=%s cco=%s comune=%s foglio=%s particella=%s",
                match.particella_id,
                match.utenza_latest.cco if match.utenza_latest is not None else None,
                match.comune,
                match.foglio,
                match.particella,
            )
        match.intestatari = []
        match.stato_ruolo = None
        match.stato_cnc = None
        match.cert_com = None
        match.cert_pvc = None
        match.cert_fra = None
        match.cert_ccs = None
        return match


def _infer_bulk_kind(
    payload: CatAnagraficaBulkSearchRequest,
) -> Literal["CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"]:
    if payload.kind in ("CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"):
        return payload.kind
    has_particella_keys = any((r.comune or r.foglio or r.particella or r.sub or r.sezione) for r in payload.rows)
    has_tax_keys = any((r.codice_fiscale or r.partita_iva) for r in payload.rows)
    if has_particella_keys and not has_tax_keys:
        return "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"
    if has_tax_keys and not has_particella_keys:
        return "CF_PIVA_PARTICELLE"
    if has_tax_keys and has_particella_keys:
        return "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"
    return "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"


def _normalize_bulk_payload(payload: CatAnagraficaBulkSearchRequest) -> CatAnagraficaBulkSearchRequest:
    kind = _infer_bulk_kind(payload)
    include_live = payload.include_capacitas_live or kind == "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"
    return payload.model_copy(update={"kind": kind, "include_capacitas_live": include_live})


_FOGLIO_WITH_SEZIONE_RE = r"^\s*(?P<foglio>[^\s]+)\s+sez\.?\s*(?P<sezione>[A-Za-z0-9]+)(?:\s+.*)?$"
_COMUNE_LIVE_SWAP_LOOKUP: dict[str, str] = {
    "arborea": "Terralba",
    "terralba": "Arborea",
    "165": "Terralba",
    "280": "Arborea",
}


def _norm_str(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    return v if v else None


def _looks_like_int(value: str | None) -> bool:
    if value is None:
        return False
    v = value.strip()
    return v.isdigit()


def _safe_int(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = value.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _normalize_capacitas_code(value: str | int | None, *, width: int) -> str | None:
    if value is None:
        return None
    if isinstance(value, int):
        return str(value).zfill(width)
    normalized = _norm_str(value)
    if not normalized:
        return None
    if normalized.isdigit():
        return normalized.zfill(width)
    return normalized


def _build_denominazione(cognome: str | None, nome: str | None) -> str | None:
    value = " ".join(part for part in [cognome, nome] if part and part.strip()).strip()
    return value or None


def _normalize_cf(value: str | None) -> str | None:
    normalized = _norm_str(value)
    return normalized.upper() if normalized else None


def _normalize_ccs(value: str | None) -> str:
    return _normalize_capacitas_code(value, width=5) or "00000"


def _normalize_com(value: str | int | None) -> str | None:
    return _normalize_capacitas_code(value, width=3)


def _normalize_pvc(value: str | int | None) -> str | None:
    return _normalize_capacitas_code(value, width=3)


def _normalize_fra(value: str | int | None) -> str | None:
    return _normalize_capacitas_code(value, width=2)


def _normalize_sezione_value(value: str | None) -> str | None:
    normalized = _norm_str(value)
    if not normalized:
        return None
    lowered = normalized.casefold()
    if lowered.startswith("sez"):
        tail = normalized[3:].lstrip(" .:-")
        return _norm_str(tail) or normalized
    return normalized


def _normalize_bulk_particella_inputs(
    comune: str | None,
    sezione: str | None,
    foglio: str | None,
) -> tuple[str | None, str | None, str | None]:
    comune_norm = _norm_str(comune)
    sezione_norm = _normalize_sezione_value(sezione)
    foglio_norm = _norm_str(foglio)

    if foglio_norm is None:
        return comune_norm, sezione_norm, foglio_norm

    import re

    match = re.match(_FOGLIO_WITH_SEZIONE_RE, foglio_norm, flags=re.IGNORECASE)
    if match:
        foglio_norm = _norm_str(match.group("foglio"))
        if sezione_norm is None:
            sezione_norm = _normalize_sezione_value(match.group("sezione"))

    return comune_norm, sezione_norm, foglio_norm


def _alternate_live_lookup_comune(comune: str | None) -> str | None:
    comune_norm = _norm_str(comune)
    if comune_norm is None:
        return None
    return _COMUNE_LIVE_SWAP_LOOKUP.get(comune_norm.casefold())


def _looks_like_codice_catastale(value: str) -> bool:
    normalized = value.strip().upper()
    return len(normalized) == 4 and normalized[0].isalpha() and normalized[1:].isdigit()


def _query_particelle_candidates(
    db: Session,
    *,
    comune_norm: str,
    sezione_norm: str | None,
    foglio_norm: str,
    particella_norm: str,
    sub_norm: str | None,
) -> list[CatParticella]:
    query = (
        select(CatParticella)
        .outerjoin(CatComune, CatComune.id == CatParticella.comune_id)
        .where(
            CatParticella.is_current.is_(True),
            CatParticella.foglio == foglio_norm,
            CatParticella.particella == particella_norm,
        )
        .order_by(CatParticella.cod_comune_capacitas, CatParticella.foglio, CatParticella.particella)
    )

    if sezione_norm:
        query = query.where(CatParticella.sezione_catastale == sezione_norm)
    if sub_norm:
        query = query.where(CatParticella.subalterno == sub_norm)

    if _looks_like_int(comune_norm):
        query = query.where(CatParticella.cod_comune_capacitas == int(comune_norm))
    elif _looks_like_codice_catastale(comune_norm):
        codice_catastale_norm = comune_norm.strip().upper()
        query = query.where(
            func.upper(func.coalesce(CatParticella.codice_catastale, CatComune.codice_catastale, "")) == codice_catastale_norm
        )
    else:
        query = query.where(
            func.lower(func.coalesce(CatParticella.nome_comune, CatComune.nome_comune, "")) == comune_norm.lower()
        )

    return db.execute(query.limit(50)).scalars().all()


def _occupancy_rank(occupancy: CatConsorzioOccupancy | None) -> tuple[int, str, str]:
    return (
        1 if bool(occupancy and occupancy.is_current) else 0,
        occupancy.valid_from.isoformat() if occupancy and occupancy.valid_from else "",
        occupancy.updated_at.isoformat() if occupancy and occupancy.updated_at else "",
    )


def _build_summary(results: list[CatAnagraficaBulkSearchRowResult]) -> dict[str, int]:
    s = {"total": len(results), "found": 0, "notFound": 0, "multiple": 0, "invalid": 0, "error": 0}
    for r in results:
        if r.esito == "FOUND":
            s["found"] += 1
        elif r.esito == "NOT_FOUND":
            s["notFound"] += 1
        elif r.esito == "MULTIPLE_MATCHES":
            s["multiple"] += 1
        elif r.esito == "INVALID_ROW":
            s["invalid"] += 1
        elif r.esito == "ERROR":
            s["error"] += 1
    return s


def _empty_bulk_summary(total: int = 0) -> dict[str, int]:
    return {"total": total, "found": 0, "notFound": 0, "multiple": 0, "invalid": 0, "error": 0}
