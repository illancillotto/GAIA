"""Repair missing daily/event references from an existing canonical identity.

No operator, account, personnel area, login permission or collaborator mapping
is created or changed. The caller owns the transaction and its verified backup.
"""

from sqlalchemy import select

from app.models.application_user import ApplicationUser
from app.modules.presenze.mapping_audit import PresenzeCollaboratorMappingAudit
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyRecord,
    PresenzeEventSummary,
)
from app.modules.presenze.services.dashboard_snapshot_store import (
    invalidate_all_dashboard_snapshots,
)


def _missing_references(db, model, collaborator):
    rows = db.scalars(
        select(model).where(model.collaborator_id == collaborator.id).with_for_update()
    ).all()
    if any(row.application_user_id not in (None, collaborator.application_user_id) for row in rows):
        raise ValueError("Conflicting non-null identity reference; explicit review required")
    return [row for row in rows if row.application_user_id is None]


def _repair_plan(db, identities):
    users, collaborators, planned = set(), set(), []
    for user_id, collaborator_id in identities:
        if user_id in users or collaborator_id in collaborators:
            raise ValueError("Duplicate canonical identity in repair manifest")
        users.add(user_id)
        collaborators.add(collaborator_id)
        person = db.scalar(
            select(PresenzeCollaborator)
            .where(PresenzeCollaborator.id == collaborator_id)
            .with_for_update()
        )
        if person is None or person.application_user_id != user_id:
            raise ValueError("Repair identity must equal the existing canonical mapping")
        if db.get(ApplicationUser, user_id) is None:
            raise ValueError("Canonical application user does not exist")
        daily = _missing_references(db, PresenzeDailyRecord, person)
        events = _missing_references(db, PresenzeEventSummary, person)
        planned.append((person, daily, events))
    if not planned:
        raise ValueError("Empty repair manifest")
    return planned


def repair_canonical_references(db, identities, *, actor, reason, dry_run=True):
    """Stage a fully validated batch and audit, leaving commit to the caller."""
    if actor is None or actor.role not in ("admin", "super_admin"):
        raise ValueError("Canonical reference repair requires an administrator")
    if not reason.strip():
        raise ValueError("An explicit audit reason is required")
    planned = _repair_plan(db, identities)
    report = {
        "dry_run": dry_run,
        "identities": len(planned),
        "daily_references": sum(len(daily) for _, daily, _ in planned),
        "event_references": sum(len(events) for _, _, events in planned),
        "canonical_mapping_changes": 0,
    }
    if dry_run:
        return report
    for person, daily, events in planned:
        if not daily and not events:
            continue
        for row in daily + events:
            row.application_user_id = person.application_user_id
        db.add(
            PresenzeCollaboratorMappingAudit(
                collaborator_id=person.id,
                previous_application_user_id=person.application_user_id,
                new_application_user_id=person.application_user_id,
                changed_by_user_id=actor.id,
                changed_by_username=actor.username,
                action="map",
                source="canonical_references",
                reason=f"{reason.strip()} | Missing references repaired: daily={len(daily)}, events={len(events)}; canonical mapping unchanged",
            )
        )
    if report["daily_references"] or report["event_references"]:
        invalidate_all_dashboard_snapshots(db)
    return report
