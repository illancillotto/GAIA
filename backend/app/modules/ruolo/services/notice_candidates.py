"""Reminder candidates as they are printed: selected taxpayers, reassigned payers, inCASS splits."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.ruolo.services import payer_assignments
from app.modules.ruolo.services.incass_notice_numbering import (
    incass_payload_overrides,
    split_incass_candidates,
)
from app.modules.ruolo.services.taxpayer_portal_access import PORTAL_ACCESS_KEY, with_portal_access


def batch_candidates(
    db: Session, candidates: list[dict[str, Any]], selected_tax_codes: list[str]
) -> list[dict[str, Any]]:
    """Selection is by registered taxpayer; a reassigned avviso then moves to its payer."""
    if selected_tax_codes:
        selected = set(selected_tax_codes)
        candidates = [
            candidate for candidate in candidates if candidate["codice_fiscale"] in selected
        ]
    return with_portal_access(
        db, split_incass_candidates(db, payer_assignments.reassign_candidates(db, candidates))
    )


def payload_overrides(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        **incass_payload_overrides(candidate),
        **payer_assignments.payload_overrides(candidate),
        PORTAL_ACCESS_KEY: candidate.get(PORTAL_ACCESS_KEY, []),
    }
