"""Motore di visibilità dell'organigramma.

Logica PURA e testabile: `compute_visibility` lavora solo su sequenze di oggetti
(non tocca il DB), mentre `effective_visibility` carica i dati e delega.

Regole (vedi specifica):
  - super_admin: vede tutto (full=True).
  - base gerarchica: per ogni org_unit dove il viewer è il responsabile diretto dei
    membri (org_assignment.manager_user_id == viewer) si include quell'unità + TUTTI i
    discendenti a cascata, con le relative persone. Il manager di una unità ne è, di
    fatto, il responsabile.
  - override attivi (is_active e finestra valid_from/valid_to che include "ora") dove
    viewer_user_id == viewer: si aggiunge il target_org_unit (+ sottoalbero) oppure il
    target_user.
  - La provenienza GERARCHIA ha sempre precedenza sull'OVERRIDE quando un'unità/persona
    è raggiungibile da entrambe.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.organigramma.models import (
    OrgAssignment,
    OrgUnit,
    OrgVisibilityOverride,
)

VIA_HIERARCHY = "gerarchia"
VIA_OVERRIDE = "override"


class _UnitLike(Protocol):
    id: UUID
    parent_id: UUID | None


class _AssignmentLike(Protocol):
    user_id: int
    org_unit_id: UUID
    manager_user_id: int | None
    active: bool


class _OverrideLike(Protocol):
    viewer_user_id: int
    target_type: str
    target_user_id: int | None
    target_org_unit_id: UUID | None
    scope: str
    is_active: bool
    valid_from: datetime | None
    valid_to: datetime | None


@dataclass
class EffectiveVisibility:
    viewer_id: int
    full: bool
    unit_via: dict[UUID, str] = field(default_factory=dict)
    unit_scope: dict[UUID, str | None] = field(default_factory=dict)
    person_via: dict[int, str] = field(default_factory=dict)

    @property
    def unit_ids(self) -> set[UUID]:
        return set(self.unit_via.keys())

    @property
    def person_ids(self) -> set[int]:
        return set(self.person_via.keys())


def ensure_aware(dt: datetime | None) -> datetime | None:
    """Normalizza i datetime naive (es. letti da sqlite) come UTC, così i confronti
    con `now` (tz-aware) non sollevano TypeError."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _within_window(
    now: datetime, valid_from: datetime | None, valid_to: datetime | None
) -> bool:
    valid_from = ensure_aware(valid_from)
    valid_to = ensure_aware(valid_to)
    if valid_from is not None and valid_from > now:
        return False
    if valid_to is not None and valid_to < now:
        return False
    return True


def _build_children_map(units: Iterable[_UnitLike]) -> dict[UUID | None, list[UUID]]:
    children: dict[UUID | None, list[UUID]] = {}
    for unit in units:
        children.setdefault(unit.parent_id, []).append(unit.id)
    return children


def _descendants(root_id: UUID, children_map: dict[UUID | None, list[UUID]]) -> set[UUID]:
    """Root incluso + tutti i discendenti (a cascata)."""
    out: set[UUID] = set()
    stack = [root_id]
    while stack:
        current = stack.pop()
        if current in out:
            continue
        out.add(current)
        for child in children_map.get(current, ()):  # noqa: SIM118
            stack.append(child)
    return out


def compute_visibility(
    *,
    viewer_id: int,
    is_super_admin: bool,
    units: Sequence[_UnitLike],
    assignments: Sequence[_AssignmentLike],
    overrides: Sequence[_OverrideLike],
    now: datetime | None = None,
) -> EffectiveVisibility:
    now = now or datetime.now(timezone.utc)
    children_map = _build_children_map(units)
    all_unit_ids = {unit.id for unit in units}

    result = EffectiveVisibility(viewer_id=viewer_id, full=is_super_admin)

    def add_unit(unit_id: UUID, via: str, scope: str | None = None) -> None:
        if unit_id not in all_unit_ids:
            return
        existing = result.unit_via.get(unit_id)
        if existing == VIA_HIERARCHY:
            return  # gerarchia ha precedenza, niente downgrade
        if via == VIA_HIERARCHY:
            result.unit_via[unit_id] = VIA_HIERARCHY
            result.unit_scope[unit_id] = None
        elif existing is None:
            result.unit_via[unit_id] = VIA_OVERRIDE
            result.unit_scope[unit_id] = scope

    if is_super_admin:
        for unit_id in all_unit_ids:
            add_unit(unit_id, VIA_HIERARCHY)
    else:
        manager_units = {
            a.org_unit_id
            for a in assignments
            if a.manager_user_id == viewer_id and a.active
        }
        for unit_id in manager_units:
            for descendant in _descendants(unit_id, children_map):
                add_unit(descendant, VIA_HIERARCHY)

        for override in overrides:
            if override.viewer_user_id != viewer_id or not override.is_active:
                continue
            if not _within_window(now, override.valid_from, override.valid_to):
                continue
            if override.target_type == "org_unit" and override.target_org_unit_id is not None:
                for descendant in _descendants(override.target_org_unit_id, children_map):
                    add_unit(descendant, VIA_OVERRIDE, override.scope)
            elif override.target_type == "user" and override.target_user_id is not None:
                for a in assignments:
                    if a.user_id == override.target_user_id and a.active:
                        add_unit(a.org_unit_id, VIA_OVERRIDE, override.scope)

    def add_person(user_id: int, via: str) -> None:
        existing = result.person_via.get(user_id)
        if existing == VIA_HIERARCHY:
            return
        if via == VIA_HIERARCHY or existing is None:
            result.person_via[user_id] = via

    for a in assignments:
        if not a.active:
            continue
        via = result.unit_via.get(a.org_unit_id)
        if via is not None:
            add_person(a.user_id, via)

    if not is_super_admin:
        for override in overrides:
            if override.viewer_user_id != viewer_id or not override.is_active:
                continue
            if not _within_window(now, override.valid_from, override.valid_to):
                continue
            if override.target_type == "user" and override.target_user_id is not None:
                add_person(override.target_user_id, VIA_OVERRIDE)

    return result


def effective_visibility(
    db: Session, viewer: ApplicationUser, now: datetime | None = None
) -> EffectiveVisibility:
    units = db.execute(select(OrgUnit)).scalars().all()
    assignments = db.execute(select(OrgAssignment)).scalars().all()
    overrides = db.execute(select(OrgVisibilityOverride)).scalars().all()
    return compute_visibility(
        viewer_id=viewer.id,
        is_super_admin=viewer.is_super_admin,
        units=units,
        assignments=assignments,
        overrides=overrides,
        now=now,
    )
