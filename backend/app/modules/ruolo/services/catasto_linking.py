from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoComune, CatastoParcel
from app.models.catasto_phase1 import CatParticella
from app.modules.ruolo.services.parsing_common import (
    normalize_partita_comune_nome as _normalize_partita_comune_nome,
    resolve_section_hint_for_ruolo_comune as _resolve_section_hint_for_ruolo_comune,
)

logger = logging.getLogger(__name__)

_RE_CATASTO_CODE = re.compile(r"\b([A-Z]\d{3})\b")
_ARBOREA_TERRALBA_SWAP_CODES = {
    "A357": "L122",
    "L122": "A357",
}


def _normalize_comune_codice(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None

    cleaned = raw_value.strip().upper()
    if not cleaned:
        return None
    if len(cleaned) <= 10 and "#" not in cleaned:
        return cleaned

    first_segment = cleaned.split("#", maxsplit=1)[0].strip()
    if first_segment and len(first_segment) <= 10:
        cleaned = first_segment

    match = _RE_CATASTO_CODE.search(cleaned)
    if match:
        return match.group(1)

    return cleaned[:10] if cleaned else None


def _resolve_comune_codice_for_ruolo(db: Session, comune_nome: str) -> str | None:
    comune_nome_norm = _normalize_partita_comune_nome(comune_nome)

    comune_row = db.scalar(
        select(CatastoComune).where(func.upper(CatastoComune.nome) == comune_nome_norm.upper())
    )
    if comune_row is not None:
        return _normalize_comune_codice(comune_row.codice_sister)

    cat_particella_comuni = db.execute(
        select(CatParticella.codice_catastale)
        .where(func.upper(CatParticella.nome_comune) == comune_nome_norm.upper())
        .group_by(CatParticella.codice_catastale)
        .limit(2)
    ).all()
    if len(cat_particella_comuni) == 1:
        return _normalize_comune_codice(cat_particella_comuni[0][0])

    logger.warning("Comune non trovato in catasto_comuni: %s", comune_nome_norm)
    return None


def _first_two_cat_particella_ids(db: Session, *conditions) -> list[uuid.UUID]:
    return list(db.scalars(select(CatParticella.id).where(*conditions).limit(2)).all())


def _resolve_cat_particella_match_for_code(
    db: Session,
    *,
    comune_codice: str | None,
    foglio: str | None,
    particella: str | None,
    subalterno: str | None,
    sezione_catastale: str | None = None,
) -> tuple[uuid.UUID | None, str, str | None, str | None]:
    comune_codice_norm = comune_codice.strip().upper() if comune_codice else None
    foglio_norm = foglio.strip() if foglio else None
    particella_norm = particella.strip() if particella else None
    sub_norm = subalterno.strip().upper() if subalterno and subalterno.strip() else None
    sezione_norm = sezione_catastale.strip().upper() if sezione_catastale and sezione_catastale.strip() else None

    if not comune_codice_norm or not foglio_norm or not particella_norm:
        return None, "unmatched", None, "missing_match_key"

    base_conditions = [
        CatParticella.codice_catastale == comune_codice_norm,
        CatParticella.foglio == foglio_norm,
        CatParticella.particella == particella_norm,
        CatParticella.is_current.is_(True),
        CatParticella.suppressed.is_(False),
    ]
    if sezione_norm:
        base_conditions.append(func.upper(func.coalesce(CatParticella.sezione_catastale, "")) == sezione_norm)

    if sub_norm:
        exact_ids = _first_two_cat_particella_ids(
            db,
            *base_conditions,
            func.upper(func.coalesce(CatParticella.subalterno, "")) == sub_norm,
        )
        if len(exact_ids) == 1:
            return exact_ids[0], "matched", "exact_sub", None
        if len(exact_ids) > 1:
            return None, "ambiguous", None, "multiple_exact_sub_matches"

        base_ids = _first_two_cat_particella_ids(
            db,
            *base_conditions,
            func.coalesce(CatParticella.subalterno, "") == "",
        )
        if len(base_ids) == 1:
            return base_ids[0], "matched", "base_without_sub", "ruolo_sub_not_present_in_cat_particelle"
        if len(base_ids) > 1:
            return None, "ambiguous", None, "multiple_base_matches_for_ruolo_sub"

        return None, "unmatched", None, "no_cat_particella_for_sub_or_base"

    base_ids = _first_two_cat_particella_ids(
        db,
        *base_conditions,
        func.coalesce(CatParticella.subalterno, "") == "",
    )
    if len(base_ids) == 1:
        return base_ids[0], "matched", "exact_no_sub", None
    if len(base_ids) > 1:
        return None, "ambiguous", None, "multiple_base_matches"

    variant_ids = _first_two_cat_particella_ids(db, *base_conditions)
    if variant_ids:
        return None, "unmatched", None, "only_subalterno_variants_found"

    return None, "unmatched", None, "no_cat_particella_match"


def resolve_cat_particella_match(
    db: Session,
    *,
    comune_codice: str | None,
    foglio: str | None,
    particella: str | None,
    subalterno: str | None,
    sezione_catastale: str | None = None,
) -> tuple[uuid.UUID | None, str, str | None, str | None]:
    result = _resolve_cat_particella_match_for_code(
        db,
        comune_codice=comune_codice,
        foglio=foglio,
        particella=particella,
        subalterno=subalterno,
        sezione_catastale=sezione_catastale,
    )
    particella_id, status, confidence, reason = result
    if particella_id is not None or status == "ambiguous":
        return result

    comune_codice_norm = comune_codice.strip().upper() if comune_codice else None
    alternate_codice = _ARBOREA_TERRALBA_SWAP_CODES.get(comune_codice_norm or "")
    if alternate_codice is None:
        return result

    swapped = _resolve_cat_particella_match_for_code(
        db,
        comune_codice=alternate_codice,
        foglio=foglio,
        particella=particella,
        subalterno=subalterno,
        sezione_catastale=sezione_catastale,
    )
    swapped_id, swapped_status, swapped_confidence, _swapped_reason = swapped
    if swapped_id is None:
        return result

    if swapped_confidence == "exact_no_sub":
        confidence = "swapped_exact_no_sub"
    elif swapped_confidence == "exact_sub":
        confidence = "swapped_exact_sub"
    elif swapped_confidence == "base_without_sub":
        confidence = "swapped_base_without_sub"
    else:
        confidence = swapped_confidence
    return swapped_id, swapped_status, confidence, "swapped_arborea_terralba"


def _upsert_catasto_parcel(
    db: Session,
    *,
    comune_nome: str,
    foglio: str,
    particella: str,
    subalterno: str | None,
    sup_catastale_are: Decimal | None,
    anno: int,
) -> uuid.UUID | None:
    comune_nome = _normalize_partita_comune_nome(comune_nome)
    if not foglio or not particella:
        return None

    comune_codice = _resolve_comune_codice_for_ruolo(db, comune_nome)
    if not comune_codice:
        return None

    existing = db.scalar(
        select(CatastoParcel).where(
            CatastoParcel.comune_codice == comune_codice,
            CatastoParcel.foglio == foglio,
            CatastoParcel.particella == particella,
            CatastoParcel.subalterno == subalterno,
            CatastoParcel.valid_to.is_(None),
        )
    )
    same_from = db.scalar(
        select(CatastoParcel).where(
            CatastoParcel.comune_codice == comune_codice,
            CatastoParcel.foglio == foglio,
            CatastoParcel.particella == particella,
            CatastoParcel.subalterno == subalterno,
            CatastoParcel.valid_from == anno,
        )
    )

    if existing is not None:
        if existing.valid_from == anno:
            if existing.sup_catastale_are is None and sup_catastale_are is not None:
                existing.sup_catastale_are = float(sup_catastale_are)
                existing.sup_catastale_ha = float(sup_catastale_are / Decimal("100"))
                existing.updated_at = datetime.now(timezone.utc)
                db.flush()
            return existing.id

        existing_are = existing.sup_catastale_are
        new_are = float(sup_catastale_are) if sup_catastale_are else None

        if existing_are is None and new_are is None:
            return existing.id
        if existing_are is not None and new_are is not None:
            if abs(float(existing_are) - new_are) < 0.0001:
                return existing.id

        existing.valid_to = anno - 1
        existing.updated_at = datetime.now(timezone.utc)
        db.flush()

        if same_from is not None:
            if same_from.sup_catastale_are is None and sup_catastale_are is not None:
                same_from.sup_catastale_are = float(sup_catastale_are)
                same_from.sup_catastale_ha = float(sup_catastale_are / Decimal("100"))
                same_from.updated_at = datetime.now(timezone.utc)
                db.flush()
            return same_from.id

    if same_from is not None:
        if same_from.sup_catastale_are is None and sup_catastale_are is not None:
            same_from.sup_catastale_are = float(sup_catastale_are)
            same_from.sup_catastale_ha = float(sup_catastale_are / Decimal("100"))
            same_from.updated_at = datetime.now(timezone.utc)
            db.flush()
        return same_from.id

    sup_ha = (sup_catastale_are / Decimal("100")) if sup_catastale_are else None
    parcel = CatastoParcel(
        id=uuid.uuid4(),
        comune_codice=comune_codice,
        comune_nome=comune_nome,
        foglio=foglio,
        particella=particella,
        subalterno=subalterno,
        sup_catastale_are=float(sup_catastale_are) if sup_catastale_are else None,
        sup_catastale_ha=float(sup_ha) if sup_ha else None,
        valid_from=anno,
        valid_to=None,
        source="ruolo_import",
    )
    db.add(parcel)
    db.flush()
    return parcel.id


__all__ = [
    "_normalize_comune_codice",
    "_resolve_comune_codice_for_ruolo",
    "_resolve_section_hint_for_ruolo_comune",
    "_upsert_catasto_parcel",
    "resolve_cat_particella_match",
]
