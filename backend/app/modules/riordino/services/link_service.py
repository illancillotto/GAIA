"""Parcel and party link services."""

from __future__ import annotations

import csv
import io
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatParticella
from app.modules.riordino.models import RiordinoParcelLink, RiordinoPartyLink, RiordinoPractice
from app.modules.riordino.repositories import PracticeRepository
from app.modules.utenze.models import AnagraficaSubject


def _require_practice(db: Session, practice_id: UUID) -> None:
    if not PracticeRepository(db).get(practice_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")


def _require_subject(db: Session, subject_id: UUID) -> None:
    if not db.get(AnagraficaSubject, subject_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")


def _normalize_parcel_key(value: str | None) -> str | None:
    normalized = (value or "").strip().upper()
    return normalized or None


def _candidate_particelle(
    db: Session,
    parcel: RiordinoParcelLink,
    *,
    municipality: str | None,
) -> list[CatParticella]:
    foglio = _normalize_parcel_key(parcel.foglio)
    particella = _normalize_parcel_key(parcel.particella)
    subalterno = _normalize_parcel_key(parcel.subalterno)
    if not foglio or not particella:
        return []

    conditions = [
        CatParticella.is_current.is_(True),
        CatParticella.suppressed.is_(False),
        func.upper(CatParticella.foglio) == foglio,
        func.upper(CatParticella.particella) == particella,
    ]
    if subalterno:
        conditions.append(func.upper(func.coalesce(CatParticella.subalterno, "")) == subalterno)
    else:
        conditions.append(func.coalesce(CatParticella.subalterno, "") == "")
    if municipality:
        conditions.append(func.upper(func.coalesce(CatParticella.nome_comune, "")) == municipality.strip().upper())

    return list(db.scalars(select(CatParticella).where(*conditions).limit(2)).all())


def _enrich_parcel_catasto_match(db: Session, practice: RiordinoPractice, parcel: RiordinoParcelLink) -> None:
    candidates = _candidate_particelle(db, parcel, municipality=practice.municipality)
    reason: str | None = None
    if not candidates and practice.municipality:
        candidates = _candidate_particelle(db, parcel, municipality=None)
        reason = "no_match_in_practice_municipality" if candidates else None

    if len(candidates) == 1:
        match = candidates[0]
        parcel.cat_particella_id = match.id
        parcel.cat_particella_match_status = "matched"
        parcel.cat_particella_match_reason = reason
        parcel.cat_particella_nome_comune = match.nome_comune
        parcel.cat_particella_num_distretto = match.num_distretto
        parcel.cat_particella_has_geometry = match.geometry is not None
        return

    parcel.cat_particella_id = None
    parcel.cat_particella_match_status = "ambiguous" if len(candidates) > 1 else "unmatched"
    parcel.cat_particella_match_reason = "multiple_cat_particelle_matches" if len(candidates) > 1 else "no_cat_particella_match"
    parcel.cat_particella_nome_comune = None
    parcel.cat_particella_num_distretto = None
    parcel.cat_particella_has_geometry = None


def list_parcels(db: Session, practice_id: UUID) -> list[RiordinoParcelLink]:
    practice = PracticeRepository(db).get(practice_id)
    if not practice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")
    parcels = list(
        db.scalars(
            select(RiordinoParcelLink)
            .where(RiordinoParcelLink.practice_id == practice_id)
            .order_by(RiordinoParcelLink.created_at.desc())
        )
    )
    for parcel in parcels:
        _enrich_parcel_catasto_match(db, practice, parcel)
    return parcels


def create_parcel(db: Session, practice_id: UUID, data: dict) -> RiordinoParcelLink:
    _require_practice(db, practice_id)
    if data.get("title_holder_subject_id"):
        _require_subject(db, data["title_holder_subject_id"])
    parcel = RiordinoParcelLink(practice_id=practice_id, **data)
    db.add(parcel)
    db.flush()
    db.refresh(parcel)
    return parcel


def delete_parcel(db: Session, practice_id: UUID, parcel_id: UUID) -> RiordinoParcelLink:
    parcel = db.scalar(
        select(RiordinoParcelLink).where(
            RiordinoParcelLink.practice_id == practice_id,
            RiordinoParcelLink.id == parcel_id,
        )
    )
    if not parcel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcel link not found")
    db.delete(parcel)
    db.flush()
    return parcel


def import_parcels_csv(db: Session, practice_id: UUID, file: UploadFile) -> list[RiordinoParcelLink]:
    _require_practice(db, practice_id)
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="CSV file required")
    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    items: list[RiordinoParcelLink] = []
    for row in reader:
        if not row.get("foglio") or not row.get("particella"):
            continue
        payload = {
            "foglio": row["foglio"].strip(),
            "particella": row["particella"].strip(),
            "subalterno": (row.get("subalterno") or "").strip() or None,
            "quality_class": (row.get("quality_class") or "").strip() or None,
            "title_holder_name": (row.get("title_holder_name") or "").strip() or None,
            "source": (row.get("source") or "csv_import").strip() or "csv_import",
            "notes": (row.get("notes") or "").strip() or None,
        }
        subject_raw = (row.get("title_holder_subject_id") or "").strip()
        if subject_raw:
            payload["title_holder_subject_id"] = UUID(subject_raw)
            _require_subject(db, payload["title_holder_subject_id"])
        parcel = RiordinoParcelLink(practice_id=practice_id, **payload)
        db.add(parcel)
        items.append(parcel)
    db.flush()
    for item in items:
        db.refresh(item)
    return items


def list_parties(db: Session, practice_id: UUID) -> list[RiordinoPartyLink]:
    return list(
        db.scalars(
            select(RiordinoPartyLink)
            .where(RiordinoPartyLink.practice_id == practice_id)
            .order_by(RiordinoPartyLink.created_at.desc())
        )
    )


def create_party(db: Session, practice_id: UUID, data: dict) -> RiordinoPartyLink:
    _require_practice(db, practice_id)
    _require_subject(db, data["subject_id"])
    party = RiordinoPartyLink(practice_id=practice_id, **data)
    db.add(party)
    db.flush()
    db.refresh(party)
    return party


def delete_party(db: Session, practice_id: UUID, party_id: UUID) -> RiordinoPartyLink:
    party = db.scalar(
        select(RiordinoPartyLink).where(
            RiordinoPartyLink.practice_id == practice_id,
            RiordinoPartyLink.id == party_id,
        )
    )
    if not party:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Party link not found")
    db.delete(party)
    db.flush()
    return party
