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


@dataclass(frozen=True)
class MeterReadingSubjectCandidate:
    subject_id: UUID
    subject_display_name: str
    matched_tax_code: str


def extract_tax_code_candidates(value: str | None) -> list[str]:
    if value is None:
        return []
    raw_candidates = re.findall(r"\b[A-Za-z0-9]{11,16}\b", value.upper())
    results: list[str] = []
    seen: set[str] = set()
    for candidate in raw_candidates:
        normalized = normalize_tax_code(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        results.append(normalized)
    return results


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


def link_subjects_by_tax_codes(db: Session, tax_codes: list[str]) -> list[MeterReadingSubjectCandidate]:
    candidates: list[MeterReadingSubjectCandidate] = []
    seen_subject_ids: set[UUID] = set()
    for tax_code in tax_codes:
        normalized = normalize_tax_code(tax_code)
        if not normalized:
            continue

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

        for person in person_matches:
            if person.subject_id in seen_subject_ids:
                continue
            seen_subject_ids.add(person.subject_id)
            candidates.append(
                MeterReadingSubjectCandidate(
                    subject_id=person.subject_id,
                    subject_display_name=f"{person.cognome} {person.nome}".strip() or person.codice_fiscale,
                    matched_tax_code=normalized,
                )
            )
        for company in company_matches:
            if company.subject_id in seen_subject_ids:
                continue
            seen_subject_ids.add(company.subject_id)
            candidates.append(
                MeterReadingSubjectCandidate(
                    subject_id=company.subject_id,
                    subject_display_name=company.ragione_sociale or company.partita_iva or normalized,
                    matched_tax_code=normalized,
                )
            )
    return candidates
