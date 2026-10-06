from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, func, select, union_all
from sqlalchemy.orm import Session

from app.models.capacitas import CapacitasInCassSyncJob
from app.modules.ruolo.models import RuoloAvviso
from app.modules.utenze.models import (
    AnagraficaCompany,
    AnagraficaPaymentNotice,
    AnagraficaPerson,
    AnagraficaSubject,
)


@dataclass(frozen=True)
class RecoverySubject:
    subject_id: UUID
    identifiers: tuple[str, ...]
    display_name: str
    subject_type: str
    requires_review: bool = False


def normalize_identifier(value: str | None) -> str:
    return (value or "").strip().upper()


def _subject_record(subject, person, company) -> RecoverySubject:
    source = person if person is not None else company
    identifiers = tuple(
        dict.fromkeys(
            normalize_identifier(value)
            for value in (
                getattr(source, "partita_iva", None),
                getattr(source, "codice_fiscale", None),
            )
            if normalize_identifier(value)
        )
    )
    name = subject.source_name_raw
    if person is not None:
        name = f"{person.cognome} {person.nome}".strip()
    if company is not None:
        name = company.ragione_sociale
    return RecoverySubject(
        subject.id, identifiers, name, subject.subject_type, subject.requires_review
    )


def _identity_problem(subject, person, company, record, owners) -> str | None:
    if subject.status == "duplicate":
        return "duplicate_subject"
    if (person is None) == (company is None):
        return "missing_or_ambiguous_identity"
    expected_type = "person" if person is not None else "company"
    if subject.subject_type != expected_type:
        return "identity_type_conflict"
    if not record.identifiers:
        return "missing_tax_identifier"
    if not all(re.fullmatch(r"(?:\d{11}|[A-Z0-9]{16})", value) for value in record.identifiers):
        return "invalid_tax_identifier"
    if any(len(owners[value]) > 1 for value in record.identifiers):
        return "tax_identifier_multiple_subjects"
    return None


def _identifier_owners(db, records):
    identifiers = {value for record in records for value in record.identifiers}
    if not identifiers:
        return defaultdict(set)
    statements = []
    for model, column in (
        (AnagraficaPerson, AnagraficaPerson.codice_fiscale),
        (AnagraficaCompany, AnagraficaCompany.codice_fiscale),
        (AnagraficaCompany, AnagraficaCompany.partita_iva),
    ):
        identifier = func.upper(func.trim(column))
        statements.append(
            select(model.subject_id, identifier.label("tax_identifier"))
            .join(AnagraficaSubject, AnagraficaSubject.id == model.subject_id)
            .where(AnagraficaSubject.status != "duplicate")
        )
    owners = defaultdict(set)
    identities = union_all(*statements).subquery("canonical_identifier_owners")
    query = select(identities.c.subject_id, identities.c.tax_identifier)
    if len(identifiers) <= 20000:
        query = query.where(identities.c.tax_identifier.in_(identifiers))
    for subject_id, identifier in db.execute(query):
        owners[identifier].add(subject_id)
    return owners


def audit_recovery_subjects(
    db: Session, subject_ids=()
) -> tuple[list[RecoverySubject], list[dict]]:
    query = (
        select(AnagraficaSubject, AnagraficaPerson, AnagraficaCompany)
        .outerjoin(AnagraficaPerson, AnagraficaPerson.subject_id == AnagraficaSubject.id)
        .outerjoin(AnagraficaCompany, AnagraficaCompany.subject_id == AnagraficaSubject.id)
        .order_by(AnagraficaSubject.id)
    )
    if subject_ids:
        query = query.where(AnagraficaSubject.id.in_(subject_ids))
    rows = db.execute(query).all()
    records = [_subject_record(*row) for row in rows]
    owners = _identifier_owners(db, records)
    eligible, blocked = [], []
    for row, record in zip(rows, records, strict=True):
        problem = _identity_problem(*row, record, owners)
        if problem:
            blocked.append({"subject_id": str(record.subject_id), "reason": problem})
        else:
            eligible.append(record)
    return eligible, blocked


def resolve_recovery_subjects(db: Session, subject_ids=(), limit=None):
    eligible, _ = audit_recovery_subjects(db, subject_ids)
    requested = set(subject_ids)
    records = [record for record in eligible if not requested or record.subject_id in requested]
    if limit is not None:
        records = records[:limit]
    return [
        (db.get(AnagraficaSubject, record.subject_id), record.identifiers[0], record.display_name)
        for record in records
    ]


def _successful_scan_ids(db: Session, refreshed_after: datetime) -> set[UUID]:
    payloads = db.scalars(
        select(CapacitasInCassSyncJob.result_json).where(
            CapacitasInCassSyncJob.completed_at >= refreshed_after,
            CapacitasInCassSyncJob.status.in_(("succeeded", "completed_with_errors")),
        )
    ).all()
    scanned = set()
    for payload in payloads:
        items = payload.get("items", []) if isinstance(payload, dict) else []
        for item in items:
            if isinstance(item, dict) and item.get("status") == "succeeded":
                scanned.add(UUID(item["subject_id"]))
    return scanned


def load_registry_incass_subject_ids(db, *, limit, exclude_synced, refreshed_after):
    eligible, _ = audit_recovery_subjects(db)
    query = select(AnagraficaPaymentNotice.subject_id).where(
        AnagraficaPaymentNotice.source_system == "incass"
    )
    excluded = set()
    if refreshed_after is not None:
        query = query.where(AnagraficaPaymentNotice.synced_at >= refreshed_after)
        excluded.update(_successful_scan_ids(db, refreshed_after))
    if exclude_synced or refreshed_after is not None:
        excluded.update(db.scalars(query).all())
    selected = [record.subject_id for record in eligible if record.subject_id not in excluded]
    return selected if limit is None else selected[:limit]


def assert_notice_owner(existing: AnagraficaPaymentNotice | None, subject_id: UUID) -> None:
    if existing is not None and existing.subject_id not in (None, subject_id):
        raise ValueError("Avviso Capacitas già assegnato a un altro soggetto canonico")


def assert_incass_downloads_complete(db, subject_id):
    notices = db.scalars(
        select(AnagraficaPaymentNotice).where(
            AnagraficaPaymentNotice.subject_id == subject_id,
            AnagraficaPaymentNotice.source_system == "incass",
        )
    ).all()
    missing = [
        notice.source_notice_id
        for notice in notices
        for link in notice.pdf_links_json or []
        if link.get("download_error") or not link.get("document_id")
    ]
    if missing:
        raise ValueError(f"PDF Capacitas non recuperati: {sorted(set(missing))}")


def load_incass_ruolo_subject_ids(
    db: Session,
    *,
    anno: int | None,
    limit_subjects: int | None,
    exclude_synced_subjects: bool,
    stale_synced_before: datetime | None = None,
) -> list[UUID]:
    if anno is None:
        return load_registry_incass_subject_ids(
            db,
            limit=limit_subjects,
            exclude_synced=exclude_synced_subjects,
            refreshed_after=stale_synced_before,
        )
    stmt = (
        select(RuoloAvviso.subject_id)
        .where(RuoloAvviso.subject_id.is_not(None))
        .group_by(RuoloAvviso.subject_id)
        .order_by(RuoloAvviso.subject_id)
    )
    stmt = stmt.where(RuoloAvviso.anno_tributario == anno)
    if exclude_synced_subjects:
        synced_notice_exists = exists(
            select(AnagraficaPaymentNotice.id).where(
                AnagraficaPaymentNotice.subject_id == RuoloAvviso.subject_id,
                AnagraficaPaymentNotice.source_system == "incass",
            )
        )
        stmt = stmt.where(~synced_notice_exists)
    if stale_synced_before is not None:
        fresh_notice_exists = exists(
            select(AnagraficaPaymentNotice.id).where(
                AnagraficaPaymentNotice.subject_id == RuoloAvviso.subject_id,
                AnagraficaPaymentNotice.source_system == "incass",
                AnagraficaPaymentNotice.synced_at >= stale_synced_before,
            )
        )
        stmt = stmt.where(~fresh_notice_exists)
    if limit_subjects is not None:
        stmt = stmt.limit(limit_subjects)
    return list(db.scalars(stmt).all())
