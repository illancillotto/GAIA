from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.presenze.models import PresenzeCollaborator
from app.modules.presenze.services.collaborator_mapping import (
    commit_staged_collaborator_mappings,
    stage_collaborator_mapping,
)

PERSONNEL_AREAS = {"AGRARIO", "IMPIANTI"}
ENTRY_FIELDS = {"gaia_user_id", "personnel_area", "presenze_collaborator_id"}


class CanonicalIdentityManifestError(ValueError):
    pass


@dataclass(frozen=True)
class CanonicalIdentityEntry:
    gaia_user_id: int
    personnel_area: str
    presenze_collaborator_id: uuid.UUID | None = None


@dataclass(frozen=True)
class CanonicalIdentityBackfillReport:
    entries: int
    operator_area_changes: int
    collaborator_mapping_changes: int
    unchanged: int
    dry_run: bool

    def as_dict(self) -> dict[str, int | bool]:
        return {
            "entries": self.entries,
            "operator_area_changes": self.operator_area_changes,
            "collaborator_mapping_changes": self.collaborator_mapping_changes,
            "unchanged": self.unchanged,
            "dry_run": self.dry_run,
        }


def parse_canonical_identity_manifest(raw: Any) -> list[CanonicalIdentityEntry]:
    if (
        not isinstance(raw, dict)
        or raw.get("version") != 1
        or not isinstance(raw.get("people"), list)
    ):
        raise CanonicalIdentityManifestError(
            "Il manifest deve contenere version=1 e people come lista"
        )
    if not raw["people"]:
        raise CanonicalIdentityManifestError("Il manifest non contiene persone")

    entries: list[CanonicalIdentityEntry] = []
    gaia_user_ids: set[int] = set()
    collaborator_ids: set[uuid.UUID] = set()
    for position, item in enumerate(raw["people"], start=1):
        if not isinstance(item, dict) or set(item) - ENTRY_FIELDS:
            raise CanonicalIdentityManifestError(f"Riga {position}: campi non validi")
        gaia_user_id = _manifest_user_id(item.get("gaia_user_id"), position=position)
        if gaia_user_id in gaia_user_ids:
            raise CanonicalIdentityManifestError(f"Riga {position}: gaia_user_id duplicato")
        gaia_user_ids.add(gaia_user_id)

        personnel_area = item.get("personnel_area")
        if personnel_area not in PERSONNEL_AREAS:
            raise CanonicalIdentityManifestError(f"Riga {position}: personnel_area non valida")
        collaborator_id = _manifest_collaborator_id(
            item.get("presenze_collaborator_id"), position=position
        )
        if collaborator_id is not None:
            if collaborator_id in collaborator_ids:
                raise CanonicalIdentityManifestError(
                    f"Riga {position}: presenze_collaborator_id duplicato"
                )
            collaborator_ids.add(collaborator_id)
        entries.append(
            CanonicalIdentityEntry(
                gaia_user_id=gaia_user_id,
                personnel_area=str(personnel_area),
                presenze_collaborator_id=collaborator_id,
            )
        )
    return entries


def apply_canonical_identity_manifest(
    db: Session,
    entries: list[CanonicalIdentityEntry],
    *,
    changed_by: ApplicationUser,
    reason: str,
    dry_run: bool,
) -> CanonicalIdentityBackfillReport:
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise CanonicalIdentityManifestError("Il motivo del backfill non puo essere vuoto")
    resolved = [_resolve_entry(db, entry) for entry in entries]
    report = _build_backfill_report(resolved, dry_run=dry_run)
    if dry_run:
        return report

    for entry, operator, collaborator in resolved:
        operator.personnel_area = entry.personnel_area
        db.add(operator)
        if collaborator is not None:
            stage_collaborator_mapping(
                db,
                collaborator=collaborator,
                application_user_id=entry.gaia_user_id,
                changed_by=changed_by,
                reason=normalized_reason,
                source="canonical_manifest",
            )
    commit_staged_collaborator_mappings(db)
    return report


def _build_backfill_report(
    resolved: list[tuple[CanonicalIdentityEntry, WCOperator, PresenzeCollaborator | None]],
    *,
    dry_run: bool,
) -> CanonicalIdentityBackfillReport:
    area_changes = 0
    mapping_changes = 0
    unchanged = 0
    for entry, operator, collaborator in resolved:
        area_changed = operator.personnel_area != entry.personnel_area
        mapping_changed = (
            collaborator is not None and collaborator.application_user_id != entry.gaia_user_id
        )
        area_changes += area_changed
        mapping_changes += mapping_changed
        unchanged += not area_changed and not mapping_changed
    return CanonicalIdentityBackfillReport(
        entries=len(resolved),
        operator_area_changes=area_changes,
        collaborator_mapping_changes=mapping_changes,
        unchanged=unchanged,
        dry_run=dry_run,
    )


def _resolve_entry(
    db: Session,
    entry: CanonicalIdentityEntry,
) -> tuple[CanonicalIdentityEntry, WCOperator, PresenzeCollaborator | None]:
    if db.get(ApplicationUser, entry.gaia_user_id) is None:
        raise CanonicalIdentityManifestError(f"gaia_user_id {entry.gaia_user_id} non trovato")
    operators = list(
        db.scalars(select(WCOperator).where(WCOperator.gaia_user_id == entry.gaia_user_id)).all()
    )
    if len(operators) != 1:
        raise CanonicalIdentityManifestError(
            f"Relazione WCOperator non univoca per gaia_user_id {entry.gaia_user_id}"
        )
    collaborator = None
    if entry.presenze_collaborator_id is not None:
        collaborator = db.get(PresenzeCollaborator, entry.presenze_collaborator_id)
        if collaborator is None:
            raise CanonicalIdentityManifestError(
                f"presenze_collaborator_id {entry.presenze_collaborator_id} non trovato"
            )
        if collaborator.application_user_id not in {None, entry.gaia_user_id}:
            raise CanonicalIdentityManifestError(
                f"presenze_collaborator_id {entry.presenze_collaborator_id} collegato a un altro gaia_user_id"
            )
        owners = list(
            db.scalars(
                select(PresenzeCollaborator).where(
                    PresenzeCollaborator.application_user_id == entry.gaia_user_id,
                    PresenzeCollaborator.id != collaborator.id,
                )
            ).all()
        )
        if owners:
            raise CanonicalIdentityManifestError(
                f"gaia_user_id {entry.gaia_user_id} gia collegato a un altro collaboratore Presenze"
            )
    return entry, operators[0], collaborator


def _manifest_user_id(value: Any, *, position: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CanonicalIdentityManifestError(
            f"Riga {position}: gaia_user_id deve essere un intero positivo"
        )
    return value


def _manifest_collaborator_id(value: Any, *, position: int) -> uuid.UUID | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CanonicalIdentityManifestError(
            f"Riga {position}: presenze_collaborator_id deve essere un UUID"
        )
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise CanonicalIdentityManifestError(
            f"Riga {position}: presenze_collaborator_id deve essere un UUID"
        ) from exc
