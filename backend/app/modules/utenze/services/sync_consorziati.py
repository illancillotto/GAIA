from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.elaborazioni.bonifica_oristanese.apps.users.client import BonificaUserRow
from app.modules.utenze.models import (
    AnagraficaCompany,
    AnagraficaPerson,
    AnagraficaSubject,
    BonificaUserStaging,
)


@dataclass(frozen=True)
class WhiteConsorziatiSyncResult:
    synced: int
    skipped: int
    errors: list[str]


def _normalize_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


def _normalize_tax(value: str | None) -> str | None:
    normalized = _normalize_value(value)
    if normalized is None:
        return None
    return normalized.replace(" ", "").upper()


def _match_subject(db: Session, row: BonificaUserRow) -> tuple[AnagraficaSubject | None, AnagraficaPerson | None, AnagraficaCompany | None]:
    normalized_tax = _normalize_tax(row.tax)
    if normalized_tax is None:
        return None, None, None

    person = db.scalar(
        select(AnagraficaPerson).where(
            func.upper(func.replace(AnagraficaPerson.codice_fiscale, " ", "")) == normalized_tax
        )
    )
    company_by_piva = db.scalar(
        select(AnagraficaCompany).where(
            func.upper(func.replace(AnagraficaCompany.partita_iva, " ", "")) == normalized_tax
        )
    )
    company_by_cf = db.scalar(
        select(AnagraficaCompany).where(
            func.upper(func.replace(func.coalesce(AnagraficaCompany.codice_fiscale, ""), " ", "")) == normalized_tax
        )
    )

    preferred_user_type = (row.user_type or "").strip().lower()
    if preferred_user_type == "company":
        company = company_by_piva or company_by_cf
        if company is not None:
            return db.get(AnagraficaSubject, company.subject_id), None, company
        if person is not None:
            return db.get(AnagraficaSubject, person.subject_id), person, None
    else:
        if person is not None:
            return db.get(AnagraficaSubject, person.subject_id), person, None
        company = company_by_piva or company_by_cf
        if company is not None:
            return db.get(AnagraficaSubject, company.subject_id), None, company

    return None, None, None


def _compare_field(mismatch_fields: dict[str, dict[str, str | None]], field: str, wc_value: str | None, gaia_value: str | None) -> None:
    normalized_wc = _normalize_value(wc_value)
    normalized_gaia = _normalize_value(gaia_value)
    if normalized_wc != normalized_gaia:
        mismatch_fields[field] = {"wc": normalized_wc, "gaia": normalized_gaia}


def _build_mismatch_fields(
    row: BonificaUserRow,
    subject: AnagraficaSubject,
    person: AnagraficaPerson | None,
    company: AnagraficaCompany | None,
) -> dict[str, dict[str, str | None]]:
    mismatch_fields: dict[str, dict[str, str | None]] = {}
    inferred_user_type = (row.user_type or "").strip().lower()

    if inferred_user_type == "company":
        if subject.subject_type != "company":
            mismatch_fields["subject_type"] = {"wc": "company", "gaia": subject.subject_type}
        if company is not None:
            _compare_field(mismatch_fields, "business_name", row.business_name, company.ragione_sociale)
            _compare_field(mismatch_fields, "email", row.email, company.email_pec)
            _compare_field(
                mismatch_fields,
                "phone",
                row.contact_mobile or row.contact_phone,
                company.telefono,
            )
    else:
        if subject.subject_type != "person":
            mismatch_fields["subject_type"] = {"wc": "person", "gaia": subject.subject_type}
        if person is not None:
            _compare_field(mismatch_fields, "first_name", row.first_name, person.nome)
            _compare_field(mismatch_fields, "last_name", row.last_name, person.cognome)
            _compare_field(mismatch_fields, "email", row.email, person.email)
            _compare_field(
                mismatch_fields,
                "phone",
                row.contact_mobile or row.contact_phone,
                person.telefono,
            )

    return mismatch_fields


def _apply_wc_fields(staging: BonificaUserStaging, row: BonificaUserRow) -> None:
    staging.username = row.username
    staging.email = row.email
    staging.user_type = row.user_type
    staging.business_name = row.business_name
    staging.first_name = row.first_name
    staging.last_name = row.last_name
    staging.tax = row.tax
    staging.phone = row.contact_phone
    staging.mobile = row.contact_mobile
    staging.role = row.role
    staging.enabled = row.enabled
    staging.wc_synced_at = datetime.now(timezone.utc)


def sync_white_consorziati(*, db: Session, rows: list[BonificaUserRow]) -> WhiteConsorziatiSyncResult:
    synced = 0
    skipped = 0
    errors: list[str] = []

    for row in rows:
        if (row.role or "").strip().lower() != "consorziato":
            skipped += 1
            continue
        try:
            staging = db.scalar(select(BonificaUserStaging).where(BonificaUserStaging.wc_id == row.wc_id))
            subject, person, company = _match_subject(db, row)

            if staging is None:
                staging = BonificaUserStaging(wc_id=row.wc_id)
                db.add(staging)
                created = True
            else:
                created = False

            _apply_wc_fields(staging, row)

            if not created and staging.review_status == "rejected":
                db.flush()
                skipped += 1
                continue

            staging.matched_subject_id = subject.id if subject is not None else None
            if subject is None:
                staging.review_status = "new"
                staging.mismatch_fields = None
            else:
                mismatch_fields = _build_mismatch_fields(row, subject, person, company)
                staging.review_status = "mismatch" if mismatch_fields else "matched"
                staging.mismatch_fields = mismatch_fields or None

            staging.reviewed_by = None
            staging.reviewed_at = None
            db.flush()
            synced += 1 if created else 0
            skipped += 0 if created else 1
        except Exception as exc:  # pragma: no cover
            errors.append(f"consorziato:{row.wc_id}: {exc}")

    db.commit()
    return WhiteConsorziatiSyncResult(synced=synced, skipped=skipped, errors=errors)
