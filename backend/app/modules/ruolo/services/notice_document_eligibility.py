"""Current diagnostic only: no reservation or promise of future eligibility."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.modules.ruolo import tributi_repositories
from app.modules.ruolo.notice_register_models import NoticePosition
from app.modules.ruolo.services.notice_eligibility import eligibility


def _position_check(db, position):
    item = (
        tributi_repositories.get_tributi_avviso(db, position.avviso_id)
        if position.avviso_id
        else None
    )
    reasons = eligibility(db, item)["reasons"] if item else ["collegamenti_mancanti"]
    if item and not item["reminder_enabled"]:
        reasons.append("generazione_non_abilitata")
    return {
        "position_id": position.id,
        "avviso_id": position.avviso_id,
        "tax_year": position.tax_year,
        "eligible": not reasons,
        "reasons": reasons,
    }


def document_eligibility(db, document):
    positions = [
        _position_check(db, position)
        for position in db.scalars(
            select(NoticePosition)
            .where(NoticePosition.document_id == document.id)
            .order_by(NoticePosition.tax_year, NoticePosition.id)
        )
    ]
    reasons = {reason for position in positions for reason in position["reasons"]}
    if not positions:
        reasons.add("posizioni_assenti")
    if document.reconciled_into_id:
        reasons.add("documento_riconciliato")
    return {
        "document_id": document.id,
        "version": document.version,
        "checked_at": datetime.now(UTC),
        "eligible": not reasons,
        "reasons": sorted(reasons),
        "positions": positions,
        "authorizes_dispatch": False,
    }
