from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson


def normalize_tax_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"[^A-Za-z0-9]", "", value).upper().strip()
    return normalized or None


@dataclass
class MeterReadingLinkResult:
    subject_id: UUID | None
    subject_display_name: str | None
    match_count: int


def link_subject_by_tax_code(db: Session, codice_fiscale: str | None) -> MeterReadingLinkResult:
    normalized = normalize_tax_code(codice_fiscale)
    if not normalized:
        return MeterReadingLinkResult(subject_id=None, subject_display_name=None, match_count=0)

    person_matches = db.execute(
        select(AnagraficaPerson).where(func.upper(func.replace(AnagraficaPerson.codice_fiscale, " ", "")) == normalized)
    ).scalars().all()
    company_matches = db.execute(
        select(AnagraficaCompany).where(
            or_(
                func.upper(func.replace(func.coalesce(AnagraficaCompany.codice_fiscale, ""), " ", "")) == normalized,
                func.upper(func.replace(func.coalesce(AnagraficaCompany.partita_iva, ""), " ", "")) == normalized,
            )
        )
    ).scalars().all()

    matches: list[tuple[UUID, str]] = []
    for person in person_matches:
        matches.append((person.subject_id, f"{person.cognome} {person.nome}".strip() or person.codice_fiscale))
    for company in company_matches:
        matches.append((company.subject_id, company.ragione_sociale or company.partita_iva or normalized))

    deduped = {(subject_id, label) for subject_id, label in matches}
    if len(deduped) != 1:
        return MeterReadingLinkResult(subject_id=None, subject_display_name=None, match_count=len(deduped))
    subject_id, label = next(iter(deduped))
    return MeterReadingLinkResult(subject_id=subject_id, subject_display_name=label, match_count=1)
