"""Who pays an avviso instead of its registered taxpayer: heirs, buyers, office decisions.

The reminder of a reassigned avviso is addressed to the payer (name, tax code,
address, archive folder) and keeps the original taxpayer as reference.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.payer_assignment_models import PAYER_REASONS, RuoloTributiPayerAssignment
from app.modules.ruolo.services.incass_notice_numbering import with_avvisi
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaSubject

PAYER_KEY = "payer_assignment"
REASON_LABELS = {
    "decesso": "Decesso: paga l'erede",
    "vendita": "Vendita o voltura: paga l'acquirente",
    "ufficio": "Indicazione dell'ufficio",
}
PAYER_ROLES = {"decesso": "erede", "vendita": "acquirente"}


@dataclass(frozen=True)
class Payer:
    subject_id: uuid.UUID
    tax_code: str
    name: str
    address: str | None
    nas_folder_path: str | None


def _join(*parts: str | None) -> str | None:
    return " ".join(part.strip() for part in parts if part and part.strip()) or None


def load_payer(db: Session, subject_id: uuid.UUID) -> Payer | None:
    """Name, tax code and address of a GAIA subject (person or company)."""
    subject = db.get(AnagraficaSubject, subject_id)
    if subject is None:
        return None
    person = db.get(AnagraficaPerson, subject_id)
    if person is not None:
        return Payer(
            subject_id,
            person.codice_fiscale.upper(),
            _join(person.cognome, person.nome) or subject.source_name_raw,
            _join(person.indirizzo, person.cap, person.comune_residenza),
            subject.nas_folder_path,
        )
    company = db.get(AnagraficaCompany, subject_id)
    if company is None:
        return None
    return Payer(
        subject_id,
        (company.codice_fiscale or company.partita_iva).upper(),
        company.ragione_sociale,
        _join(company.sede_legale, company.cap, company.comune_sede),
        subject.nas_folder_path,
    )


def find_subject_by_tax_code(db: Session, tax_code: str) -> uuid.UUID | None:
    value = tax_code.strip().upper()
    person = db.scalar(
        select(AnagraficaPerson.subject_id).where(
            func.upper(AnagraficaPerson.codice_fiscale) == value
        )
    )
    if person is not None:
        return person
    return db.scalar(
        select(AnagraficaCompany.subject_id).where(
            or_(
                func.upper(AnagraficaCompany.codice_fiscale) == value,
                func.upper(AnagraficaCompany.partita_iva) == value,
            )
        )
    )


def active_assignment(db: Session, avviso_id: uuid.UUID) -> RuoloTributiPayerAssignment | None:
    return db.scalar(
        select(RuoloTributiPayerAssignment).where(
            RuoloTributiPayerAssignment.avviso_id == avviso_id,
            RuoloTributiPayerAssignment.voided_at.is_(None),
        )
    )


def history(db: Session, avviso_id: uuid.UUID) -> list[RuoloTributiPayerAssignment]:
    return list(
        db.scalars(
            select(RuoloTributiPayerAssignment)
            .where(RuoloTributiPayerAssignment.avviso_id == avviso_id)
            .order_by(
                RuoloTributiPayerAssignment.voided_at.is_(None).desc(),
                RuoloTributiPayerAssignment.voided_at.desc(),
                RuoloTributiPayerAssignment.created_at.desc(),
            )
        )
    )


def assign(
    db: Session,
    *,
    avviso_id: uuid.UUID,
    payer_tax_code: str,
    reason: str,
    notes: str | None,
    user_id: int | None,
) -> RuoloTributiPayerAssignment:
    """Replace the active payer of an avviso; the previous one stays as voided history."""
    avviso = db.get(RuoloAvviso, avviso_id)
    if avviso is None:
        raise LookupError("Avviso non trovato")
    if reason not in PAYER_REASONS:
        raise ValueError("Motivo non valido")
    tax_code = payer_tax_code.strip().upper()
    subject_id = find_subject_by_tax_code(db, tax_code)
    if subject_id is None:
        raise ValueError(
            f"{tax_code} non e presente in anagrafica: inseriscilo da Utenze prima di collegarlo"
        )
    if tax_code == (avviso.codice_fiscale_raw or "").strip().upper():
        raise ValueError("Il pagatore indicato e gia l'intestatario dell'avviso")
    void(db, avviso_id, user_id)
    assignment = RuoloTributiPayerAssignment(
        avviso_id=avviso_id,
        payer_subject_id=subject_id,
        reason=reason,
        notes=(notes or "").strip() or None,
        created_by=user_id,
    )
    db.add(assignment)
    db.flush()
    return assignment


def void(db: Session, avviso_id: uuid.UUID, user_id: int | None) -> bool:
    current = active_assignment(db, avviso_id)
    if current is None:
        return False
    current.voided_at = datetime.now(UTC)
    current.voided_by = user_id
    db.flush()
    return True


def payer_tax_code(db: Session, avviso_id: uuid.UUID) -> str | None:
    current = active_assignment(db, avviso_id)
    payer = load_payer(db, current.payer_subject_id) if current is not None else None
    return payer.tax_code if payer is not None else None


def active_payers(
    db: Session, avviso_ids: list[Any]
) -> dict[uuid.UUID, tuple[RuoloTributiPayerAssignment, Payer]]:
    if not avviso_ids:
        return {}
    rows = db.scalars(
        select(RuoloTributiPayerAssignment).where(
            RuoloTributiPayerAssignment.avviso_id.in_(avviso_ids),
            RuoloTributiPayerAssignment.voided_at.is_(None),
        )
    )
    result = {}
    for row in rows:
        payer = load_payer(db, row.payer_subject_id)
        if payer is not None:
            result[row.avviso_id] = (row, payer)
    return result


def reassign_candidates(db: Session, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Move every reassigned avviso to a notice of its own payer; the rest stay put."""
    payers = active_payers(db, [avviso["id"] for c in candidates for avviso in c["avvisi"]])
    if not payers:
        return candidates
    result: list[dict[str, Any]] = []
    for candidate in candidates:
        own = [avviso for avviso in candidate["avvisi"] if avviso["id"] not in payers]
        by_payer: dict[uuid.UUID, list[dict[str, Any]]] = {}
        for avviso in candidate["avvisi"]:
            if avviso["id"] in payers:
                by_payer.setdefault(payers[avviso["id"]][1].subject_id, []).append(avviso)
        if own:
            result.append(candidate if not by_payer else with_avvisi(candidate, own))
        for avvisi in by_payer.values():
            assignment, payer = payers[avvisi[0]["id"]]
            result.append(_payer_candidate(candidate, avvisi, assignment, payer))
    return result


def _payer_candidate(
    candidate: dict[str, Any],
    avvisi: list[dict[str, Any]],
    assignment: RuoloTributiPayerAssignment,
    payer: Payer,
) -> dict[str, Any]:
    moved = [{**avviso, "residenza_raw": payer.address, "domicilio_raw": None} for avviso in avvisi]
    return {
        **with_avvisi(candidate, moved),
        "codice_fiscale": payer.tax_code,
        "display_name": payer.name,
        "subject_id": payer.subject_id,
        "nas_folder_path": payer.nas_folder_path,
        "has_nas_folder": bool(payer.nas_folder_path),
        PAYER_KEY: {
            "intestatario": candidate["display_name"],
            "codice_fiscale": candidate["codice_fiscale"],
            "reason": assignment.reason,
            "role": PAYER_ROLES.get(assignment.reason),
        },
    }


def payload_overrides(candidate: dict[str, Any]) -> dict[str, Any]:
    return {PAYER_KEY: candidate[PAYER_KEY]} if PAYER_KEY in candidate else {}
