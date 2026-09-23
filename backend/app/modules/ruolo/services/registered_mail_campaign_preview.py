"""Read-only, review-required preview of the historical Poste 2022-2023 campaign.

The explicit creation cutoff freezes the campaign scope: future imports must not
silently inherit its annualities. Legacy links and candidate IDs are hints, not
proof of recipient identity or of the contents of an envelope.
"""

from collections import Counter
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloAvviso, RuoloTributiRegisteredMail
from app.modules.ruolo.notice_register_models import NoticeAttempt, NoticeDocument, NoticePosition
from app.modules.ruolo.services.registered_mail_association import manual_association

YEARS = (2022, 2023)
MAX_MAILS = 10000


def _hints(mail: RuoloTributiRegisteredMail) -> set[UUID]:
    payload = mail.raw_payload_json or {}
    candidates = payload.get("candidate_avviso_ids", [])
    result = set()
    if isinstance(candidates, list):
        for value in candidates:
            try:
                result.add(UUID(str(value)))
            except ValueError:
                continue
    if mail.avviso_id is not None:
        result.add(mail.avviso_id)
    return result


def _notice(avviso: RuoloAvviso) -> dict:
    return {
        "avviso_id": str(avviso.id),
        "subject_id": str(avviso.subject_id) if avviso.subject_id else None,
        "tax_year": avviso.anno_tributario,
        "codice_cnc": avviso.codice_cnc,
    }


def _classification(mail: RuoloTributiRegisteredMail, notices: list, reasons: list) -> str:
    association = manual_association(mail)
    if association is not None and association.get("avviso_id") is None:
        reasons.append("manual_unlinked")
    if reasons:
        return "review_required"
    counts = Counter(item.anno_tributario for item in notices)
    if any(counts[year] > 1 for year in YEARS):
        reasons.append("multiple_notices_per_year")
        return "ambiguous"
    if any(counts[year] == 0 for year in YEARS):
        reasons.append("missing_annual_notice")
        return "incomplete"
    return "extend_single_link" if mail.avviso_id is not None else "proposed_pair"


def _proposal(mail: RuoloTributiRegisteredMail, by_id: dict, by_subject: dict) -> dict:
    hints = _hints(mail)
    subjects = {by_id[key].subject_id for key in hints if key in by_id}
    if mail.subject_id is not None:
        subjects.add(mail.subject_id)
    reasons = []
    if not subjects or None in subjects:
        reasons.append("identity_unresolved")
    subjects.discard(None)
    if len(subjects) > 1:
        reasons.append("conflicting_subjects")
    if hints - by_id.keys():
        reasons.append("missing_or_out_of_campaign_hint")
    notices = [notice for subject in sorted(subjects) for notice in by_subject[subject]]
    classification = _classification(mail, notices, reasons)
    return {
        "mail_id": str(mail.id),
        "source_shipment_id": mail.source_shipment_id,
        "legacy_avviso_id": str(mail.avviso_id) if mail.avviso_id else None,
        "classification": classification,
        "reasons": reasons,
        "candidate_notices": [_notice(notice) for notice in notices],
        "requires_operator_confirmation": True,
        "register_document_id": None,
        "register_avviso_ids": [],
    }


def _register_scope(db: Session, mail_ids: list[UUID]) -> dict:
    rows = db.execute(
        select(NoticeAttempt.registered_mail_id, NoticeDocument, NoticePosition)
        .join(NoticeDocument, NoticeDocument.id == NoticeAttempt.document_id)
        .outerjoin(NoticePosition, NoticePosition.document_id == NoticeDocument.id)
        .where(NoticeAttempt.registered_mail_id.in_(mail_ids))
        .order_by(NoticePosition.tax_year, NoticePosition.id)
    )
    result = {}
    for mail_id, document, position in rows:
        entry = result.setdefault(mail_id, {"document": document, "positions": []})
        if position is not None:
            entry["positions"].append(position)
    return result


def _with_register(proposal: dict, scope: dict | None) -> dict:
    if scope is None:
        return proposal
    document, positions = scope["document"], scope["positions"]
    linked_ids = {str(position.avviso_id) for position in positions if position.avviso_id}
    proposal["register_document_id"] = str(document.id)
    proposal["register_avviso_ids"] = sorted(linked_ids)
    if not positions and document.source_system == "poste_db" and not document.reconciled_into_id:
        return proposal
    expected = sorted(
        (item["tax_year"], item["avviso_id"]) for item in proposal["candidate_notices"]
    )
    registered = sorted((position.tax_year, str(position.avviso_id)) for position in positions)
    complete = (
        proposal["classification"] in {"proposed_pair", "extend_single_link"}
        and registered == expected
        and document.reconciled_into_id is None
    )
    proposal["classification"] = "already_registered" if complete else "review_required"
    if not complete:
        proposal["reasons"].append("existing_register_scope_requires_review")
    return proposal


def preview_campaign(db: Session, *, created_before: datetime) -> dict:
    """No flush, mutation or inferred notification; includes all legacy match states."""
    if created_before.tzinfo is None or created_before.utcoffset() is None:
        raise ValueError("Il limite della campagna deve includere il fuso orario")
    with db.no_autoflush:
        mails = list(
            db.scalars(
                select(RuoloTributiRegisteredMail)
                .where(
                    RuoloTributiRegisteredMail.source_system == "posta_online",
                    RuoloTributiRegisteredMail.created_at < created_before,
                )
                .order_by(RuoloTributiRegisteredMail.id)
                .limit(MAX_MAILS + 1)
            )
        )
        if len(mails) > MAX_MAILS:
            raise ValueError("Campagna oltre 10000 raccomandate: restringere il perimetro")
        notices = list(
            db.scalars(
                select(RuoloAvviso)
                .where(RuoloAvviso.anno_tributario.in_(YEARS))
                .order_by(RuoloAvviso.anno_tributario, RuoloAvviso.id)
            )
        )
        by_id = {notice.id: notice for notice in notices}
        by_subject = {}
        for notice in notices:
            by_subject.setdefault(notice.subject_id, []).append(notice)
        # A mail can carry a subject hint even when no annual notice exists.
        for mail in mails:
            by_subject.setdefault(mail.subject_id, [])
        scopes = _register_scope(db, [mail.id for mail in mails])
        items = [
            _with_register(_proposal(mail, by_id, by_subject), scopes.get(mail.id))
            for mail in mails
        ]
    return {
        "campaign": "historical_poste_2022_2023",
        "created_before": created_before.isoformat(),
        "expected_years": list(YEARS),
        "read_only": True,
        "total": len(items),
        "counts": dict(Counter(item["classification"] for item in items)),
        "items": items,
    }
