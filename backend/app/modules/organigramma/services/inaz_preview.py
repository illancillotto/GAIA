from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.presenze.models import PresenzeCollaborator


class InazOrganizationMember(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kint: str = Field(min_length=1)
    kkint: str | None = None
    company_code: str | None = None
    employee_code: str | None = None


class InazOrganizationUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_id: str = Field(min_length=1)
    parent_external_id: str | None = None
    level: int = Field(ge=0)
    title: str = Field(min_length=1)
    is_staff: bool
    responsible_kint: str | None = None
    members: list[InazOrganizationMember] = Field(default_factory=list)


class InazOrganizationSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[2]
    source_system: Literal["inaz"]
    source_view: Literal["Organigramma con Responsabile"]
    captured_at: datetime
    complete: Literal[True]
    checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    units: list[InazOrganizationUnit] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_snapshot(self) -> InazOrganizationSnapshot:
        _validate_unit_tree(self.units)
        _validate_unique_members(self.units)
        if semantic_checksum(self.units) != self.checksum_sha256:
            raise ValueError("Checksum snapshot INAZ non valido")
        return self


class InazOrganizationPreview(BaseModel):
    snapshot_checksum: str
    unit_count: int
    member_count: int
    responsible_count: int
    required_identity_count: int
    mapped_identity_count: int
    mapped_member_count: int
    issues: dict[str, int]
    ready: bool
    message: str


def _validate_unit_tree(units: list[InazOrganizationUnit]) -> None:
    units_by_id = {unit.external_id: unit for unit in units}
    if len(units_by_id) != len(units):
        raise ValueError("Snapshot INAZ con unità duplicate")
    roots = [unit for unit in units if unit.parent_external_id is None]
    if len(roots) != 1 or roots[0].level != 0:
        raise ValueError("Snapshot INAZ senza una sola radice di livello 0")
    for unit in units:
        if unit.parent_external_id is None:
            continue
        parent = units_by_id.get(unit.parent_external_id)
        if parent is None or unit.level != parent.level + 1:
            raise ValueError("Snapshot INAZ con gerarchia incoerente")


def _validate_unique_members(units: list[InazOrganizationUnit]) -> None:
    members = [member for unit in units for member in unit.members]
    member_kints = [member.kint for member in members]
    if len(member_kints) != len(set(member_kints)):
        raise ValueError("Snapshot INAZ con appartenenze Kint duplicate")
    employee_keys = [
        (member.company_code, member.employee_code)
        for member in members
        if member.company_code and member.employee_code
    ]
    if len(employee_keys) != len(set(employee_keys)):
        raise ValueError("Snapshot INAZ con identità dipendente duplicate")
    unknown_responsibles = {
        unit.responsible_kint
        for unit in units
        if unit.responsible_kint and unit.responsible_kint not in set(member_kints)
    }
    if unknown_responsibles:
        raise ValueError("Snapshot INAZ con responsabile senza appartenenza")


def semantic_checksum(units: list[InazOrganizationUnit]) -> str:
    canonical = []
    for unit in sorted(units, key=lambda item: item.external_id):
        payload = unit.model_dump(exclude={"members"})
        payload["members"] = [
            {
                "kint": member.kint,
                "company_code": member.company_code,
                "employee_code": member.employee_code,
            }
            for member in sorted(unit.members, key=lambda item: item.kint)
        ]
        canonical.append(payload)
    encoded = json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def preview_inaz_organization(
    db: Session, snapshot: InazOrganizationSnapshot
) -> InazOrganizationPreview:
    members_by_kint = {member.kint: member for unit in snapshot.units for member in unit.members}
    member_kints = set(members_by_kint)
    responsible_kints = {
        unit.responsible_kint for unit in snapshot.units if unit.responsible_kint is not None
    }
    required_kints = member_kints | responsible_kints
    by_employee_identity = _load_collaborators_by_identity(db, members_by_kint.values())

    candidate_user_ids = {
        rows[0].application_user_id
        for rows in by_employee_identity.values()
        if len(rows) == 1 and rows[0].application_user_id is not None
    }
    existing_user_ids = set(
        db.scalars(
            select(ApplicationUser.id).where(ApplicationUser.id.in_(candidate_user_ids))
        ).all()
    )

    status_by_kint = {
        kint: _identity_status(
            members_by_kint[kint],
            by_employee_identity.get(_employee_identity(members_by_kint[kint]), []),
            existing_user_ids,
        )
        for kint in required_kints
    }
    issues = Counter(status for status in status_by_kint.values() if status != "mapped")
    mapped_kints = {kint for kint, status in status_by_kint.items() if status == "mapped"}
    ready = not issues
    return InazOrganizationPreview(
        snapshot_checksum=snapshot.checksum_sha256,
        unit_count=len(snapshot.units),
        member_count=len(member_kints),
        responsible_count=len(responsible_kints),
        required_identity_count=len(required_kints),
        mapped_identity_count=len(mapped_kints),
        mapped_member_count=len(member_kints & mapped_kints),
        issues=dict(sorted(issues.items())),
        ready=ready,
        message=(
            "Snapshot INAZ pronto per la pianificazione dell'import"
            if ready
            else "Snapshot INAZ bloccato da mapping canonici incompleti"
        ),
    )


def _load_collaborators_by_identity(
    db: Session, members: Iterable[InazOrganizationMember]
) -> dict[tuple[str, str], list[PresenzeCollaborator]]:
    employee_codes = {member.employee_code for member in members if member.employee_code}
    if not employee_codes:
        return {}
    collaborators = db.scalars(
        select(PresenzeCollaborator).where(PresenzeCollaborator.employee_code.in_(employee_codes))
    ).all()
    by_employee_identity: dict[tuple[str, str], list[PresenzeCollaborator]] = defaultdict(list)
    for collaborator in collaborators:
        if collaborator.company_code is not None:
            by_employee_identity[(collaborator.company_code, collaborator.employee_code)].append(
                collaborator
            )
    return by_employee_identity


def _identity_status(
    member: InazOrganizationMember,
    collaborators: list[PresenzeCollaborator],
    existing_user_ids: set[int],
) -> str:
    if not member.employee_code:
        return "missing_employee_code"
    if not member.company_code:
        return "missing_company_code"
    if not collaborators:
        return "missing_collaborator"
    if len(collaborators) != 1:
        return "duplicate_collaborator_identity"
    application_user_id = collaborators[0].application_user_id
    if application_user_id is None:
        return "unmapped_collaborator"
    if application_user_id not in existing_user_ids:
        return "missing_application_user"
    return "mapped"


def _employee_identity(member: InazOrganizationMember) -> tuple[str, str]:
    return member.company_code or "", member.employee_code or ""
