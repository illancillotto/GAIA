"""Read-only verification of workbook annual references for one Poste mail."""

import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloAvviso, RuoloTributiRegisteredMail
from app.modules.utenze.models import AnagraficaPaymentNotice


def _tax_code(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def _candidate_ids(mail: RuoloTributiRegisteredMail) -> tuple[list[uuid.UUID], str | None]:
    payload = mail.raw_payload_json or {}
    raw_ids = payload.get("candidate_avviso_ids")
    if not isinstance(raw_ids, list) or len(raw_ids) != 2:
        return [], "Coppia di candidati non univoca"
    try:
        ids = [uuid.UUID(str(value)) for value in raw_ids]
    except (TypeError, ValueError):
        return [], "Identificativo candidato non valido"
    return ids, None


def _candidate_notices(
    db: Session, mail: RuoloTributiRegisteredMail
) -> tuple[list[RuoloAvviso], str | None]:
    ids, reason = _candidate_ids(mail)
    if reason is not None:
        return [], reason
    notices = list(db.scalars(select(RuoloAvviso).where(RuoloAvviso.id.in_(ids))))
    if len(notices) != 2 or {item.anno_tributario for item in notices} != {2022, 2023}:
        return [], "Avvisi annuali incompleti"
    subjects = {item.subject_id for item in notices}
    codes = {_tax_code(item.codice_fiscale_raw) for item in notices}
    if len(subjects) != 1 or None in subjects or len(codes) != 1 or "" in codes:
        return [], "Contribuente non coerente fra gli avvisi"
    return notices, None


def _incass_mismatch(db: Session, notices: list[RuoloAvviso], refs: dict[int, str]) -> str | None:
    subject_id = notices[0].subject_id
    code = _tax_code(notices[0].codice_fiscale_raw)
    incass = list(
        db.scalars(
            select(AnagraficaPaymentNotice).where(
                AnagraficaPaymentNotice.source_system == "incass",
                AnagraficaPaymentNotice.source_notice_id.in_(refs.values()),
            )
        )
    )
    by_year = {(item.anno, item.source_notice_id): item for item in incass}
    for year, reference in refs.items():
        item = by_year.get((str(year), reference))
        if item is None:
            return f"Riferimento inCASS {year} non trovato"
        if (
            item.subject_id != subject_id
            or _tax_code(item.codice_fiscale or item.partita_iva) != code
        ):
            return f"Contribuente inCASS {year} non coerente"
    return None


def verify_workbook_references(
    db: Session, *, mail_id: uuid.UUID, ref_2022: str, ref_2023: str
) -> dict[str, str | bool]:
    mail = db.get(RuoloTributiRegisteredMail, mail_id)
    if (
        mail is None
        or mail.source_system != "posta_online"
        or mail.avviso_id is not None
        or mail.match_status != "ambiguous"
    ):
        return {"verified": False, "reason": "Raccomandata non disponibile per la coppia"}
    notices, reason = _candidate_notices(db, mail)
    if reason is None:
        reason = _incass_mismatch(db, notices, {2022: ref_2022, 2023: ref_2023})
    if reason is not None:
        return {"verified": False, "reason": reason}
    return {"verified": True, "reason": "Riferimenti inCASS e contribuente coerenti"}
