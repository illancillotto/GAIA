from __future__ import annotations

import re
import uuid
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob
from app.modules.ruolo.services.capacitas_role_codes import classify_capacitas_role_code
from app.modules.utenze.models import (
    AnagraficaCompany,
    AnagraficaPaymentNotice,
    AnagraficaPerson,
    AnagraficaSubject,
)


def _ordinary_notice_year(notice: AnagraficaPaymentNotice) -> int | None:
    reference = notice.source_notice_id or ""
    classification = classify_capacitas_role_code(notice.anno)
    if (
        notice.source_system != "incass"
        or not classification.is_ordinary_role
        or not re.fullmatch(r"[01]\d{14}", reference)
        or reference[1:5] != str(classification.ordinary_year)
        or notice.subject_id is None
    ):
        return None
    return classification.ordinary_year


def _identifier(*values: str | None) -> str:
    return next((value.strip().upper() for value in values if value), "")


def _canonical_identifier(db: Session, notice: AnagraficaPaymentNotice) -> str:
    subject = db.get(AnagraficaSubject, notice.subject_id)
    person = db.get(AnagraficaPerson, notice.subject_id)
    company = db.get(AnagraficaCompany, notice.subject_id)
    if (
        subject is None
        or subject.status == "duplicate"
        or (person is not None and company is not None)
    ):
        raise ValueError("Identità canonica ambigua per la materializzazione Ruolo inCASS")
    source = person if person is not None else company
    identifiers = {
        _identifier(getattr(source, "partita_iva", None)),
        _identifier(getattr(source, "codice_fiscale", None)),
    } - {""}
    source_identifier = _identifier(notice.codice_fiscale, notice.partita_iva)
    if source_identifier not in identifiers:
        raise ValueError("CF/PIVA inCASS non coerente con l'identità canonica delle Utenze")
    return source_identifier


def _assert_existing_identity(
    avviso: RuoloAvviso, notice: AnagraficaPaymentNotice, identifier: str
) -> None:
    if (avviso.subject_id is not None and avviso.subject_id != notice.subject_id) or (
        avviso.codice_fiscale_raw and avviso.codice_fiscale_raw.strip().upper() != identifier
    ):
        raise ValueError("Il riferimento inCASS confligge con l'avviso Ruolo esistente")


def _notice_amount(value: str | None) -> Decimal | None:
    raw = (value or "").strip()
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        amount = Decimal(raw)
        if not amount.is_finite() or abs(amount) > Decimal("9999999999.99"):
            return None
        return amount.quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _ensure_header_import_job(db: Session, year: int) -> uuid.UUID:
    job_id = uuid.uuid5(uuid.NAMESPACE_URL, f"gaia:incass-role-header:{year}")
    db.execute(
        insert(RuoloImportJob)
        .values(
            id=job_id,
            anno_tributario=year,
            filename=f"incass_sync_headers_{year}",
            status="completed",
            params_json={
                "source": "ana_payment_notices",
                "mode": "incass_header_sync",
                "partitario_materialized": False,
            },
        )
        .on_conflict_do_nothing(index_elements=[RuoloImportJob.id])
    )
    return job_id


def _header_values(
    notice: AnagraficaPaymentNotice, identifier: str, year: int, job_id: uuid.UUID
) -> dict[str, object]:
    address = (
        " ".join(
            part.strip()
            for part in (notice.indirizzo, notice.cap, notice.citta, notice.provincia)
            if part and part.strip()
        )
        or None
    )
    return {
        "id": uuid.uuid5(uuid.NAMESPACE_URL, f"gaia:incass-role:{notice.source_notice_id}"),
        "import_job_id": job_id,
        "codice_cnc": f"01.{notice.source_notice_id[:-1]}",
        "anno_tributario": year,
        "subject_id": notice.subject_id,
        "codice_fiscale_raw": identifier,
        "nominativo_raw": (notice.display_name or "")[:300] or None,
        "domicilio_raw": address,
        "residenza_raw": address,
        "codice_utenza": (notice.source_internal_id or "")[:30] or None,
        "importo_totale_euro": _notice_amount(notice.importo_carico),
    }


def materialize_incass_notice_header(
    db: Session, notice: AnagraficaPaymentNotice
) -> RuoloAvviso | None:
    year = _ordinary_notice_year(notice)
    if year is None:
        return None
    identifier = _canonical_identifier(db, notice)
    cnc = f"01.{notice.source_notice_id[:-1]}"
    query = select(RuoloAvviso).where(
        RuoloAvviso.codice_cnc == cnc, RuoloAvviso.anno_tributario == year
    )
    avviso = db.scalar(query)
    if avviso is not None:
        _assert_existing_identity(avviso, notice, identifier)
        return avviso
    job_id = _ensure_header_import_job(db, year)
    db.execute(
        insert(RuoloAvviso)
        .values(**_header_values(notice, identifier, year, job_id))
        .on_conflict_do_nothing(
            index_elements=[RuoloAvviso.codice_cnc, RuoloAvviso.anno_tributario]
        )
    )
    avviso = db.scalar(query)
    _assert_existing_identity(avviso, notice, identifier)
    return avviso
