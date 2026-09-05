from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter

from app.modules.catasto.routes.anagrafica.normalization import _build_denominazione, _norm_str
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagraficaDetail,
    CapacitasIntestatario,
)
from app.modules.utenze.models import (
    AnagraficaPerson,
    AnagraficaSubject,
)
from app.schemas.catasto_phase1 import (
    CatIntestatarioResponse,
)

router = APIRouter(
    prefix="/catasto/elaborazioni-massive/particelle", tags=["catasto-elaborazioni-massive"]
)
logger = logging.getLogger(__name__)
CATASTO_DISTRETTO_EXPORT_STORAGE_PATH = Path(
    os.getenv("CATASTO_DISTRETTO_EXPORT_STORAGE_PATH", "/data/catasto/exports/distretti")
)


# fmt: off

def _split_denominazione(value: str | None, *, fallback_cognome: str | None = None, fallback_nome: str | None = None) -> tuple[str, str]:
    normalized = _norm_str(value)
    if not normalized:
        return fallback_cognome or "N/D", fallback_nome or "N/D"
    parts = normalized.split()
    if len(parts) == 1:
        return parts[0], fallback_nome or "N/D"
    return parts[0], " ".join(parts[1:])


def _compose_address(toponimo: str | None, indirizzo: str | None, civico: str | None, sub: str | None) -> str | None:
    parts = [part for part in [_norm_str(toponimo), _norm_str(indirizzo), _norm_str(civico)] if part]
    value = " ".join(parts).strip()
    sub_norm = _norm_str(sub)
    if sub_norm:
        value = f"{value} {sub_norm}".strip()
    return value or None


def _person_response_from_db(person: AnagraficaPerson, subject: AnagraficaSubject, *, deceduto: bool | None = None) -> CatIntestatarioResponse:
    return CatIntestatarioResponse(
        id=person.subject_id,
        codice_fiscale=person.codice_fiscale,
        denominazione=_build_denominazione(person.cognome, person.nome),
        tipo="PF",
        cognome=person.cognome,
        nome=person.nome,
        data_nascita=person.data_nascita,
        luogo_nascita=person.comune_nascita,
        indirizzo=person.indirizzo,
        comune_residenza=person.comune_residenza,
        cap=person.cap,
        email=person.email,
        telefono=person.telefono,
        ragione_sociale=None,
        source=subject.source_system,
        last_verified_at=person.updated_at,
        deceduto=deceduto,
    )


def _build_person_payload_from_current_capacitas(
    detail: CapacitasAnagraficaDetail | None,
    intestatario: CapacitasIntestatario,
    normalized_cf: str | None,
) -> dict[str, object | None]:
    cognome, nome = _split_denominazione(
        (detail.cognome + " " + detail.nome).strip() if detail and detail.cognome and detail.nome else detail.denominazione if detail else intestatario.denominazione,
        fallback_cognome=detail.cognome if detail else None,
        fallback_nome=detail.nome if detail else None,
    )
    return {
        "cognome": detail.cognome if detail and detail.cognome else cognome,
        "nome": detail.nome if detail and detail.nome else nome,
        "codice_fiscale": normalized_cf or "",
        "data_nascita": detail.data_nascita if detail else intestatario.data_nascita,
        "comune_nascita": (detail.luogo_nascita if detail else None) or intestatario.luogo_nascita,
        "indirizzo": (
            _compose_address(
                detail.residenza_toponimo if detail else None,
                detail.residenza_indirizzo if detail else None,
                detail.residenza_civico if detail else None,
                detail.residenza_sub if detail else None,
            )
            if detail
            else None
        )
        or intestatario.residenza,
        "comune_residenza": (
            (detail.residenza_localita if detail else None)
            or (detail.residenza_belfiore if detail else None)
            or intestatario.comune_residenza
        ),
        "cap": (detail.residenza_cap if detail else None) or intestatario.cap,
        "email": detail.email if detail else None,
        "telefono": (detail.telefono or detail.cellulare) if detail else None,
        "note": " | ".join(detail.note) if detail and detail.note else None,
    }
