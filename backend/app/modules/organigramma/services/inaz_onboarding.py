from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.organigramma.services.inaz_preview import InazOrganizationSnapshot
from app.modules.presenze.models import PresenzeCollaborator
from app.modules.presenze.services.collaborator_mapping import stage_collaborator_mapping

ONBOARDING_NAMESPACE = uuid.UUID("93427d66-119a-4f43-b8e0-f64352dc5eb3")


class InazOnboardingError(ValueError):
    pass


@dataclass(frozen=True)
class InazOnboardingReport:
    existing: int
    exact_kint_updates: int
    new_users: int
    review_required: int
    blocked: int
    dry_run: bool

    def as_dict(self) -> dict[str, int | bool]:
        return {
            "existing": self.existing,
            "exact_kint_updates": self.exact_kint_updates,
            "new_users": self.new_users,
            "review_required": self.review_required,
            "blocked": self.blocked,
            "dry_run": self.dry_run,
        }


@dataclass(frozen=True)
class _NewIdentity:
    kint: str
    kkint: str | None
    company_code: str
    employee_code: str
    full_name: str


def reconcile_inaz_onboarding(
    db: Session,
    snapshot: InazOrganizationSnapshot,
    review_artifact: Any,
    *,
    changed_by: ApplicationUser,
    reason: str,
    dry_run: bool,
) -> InazOnboardingReport:
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise InazOnboardingError("Il motivo dell'onboarding non puo essere vuoto")
    reviews = _parse_reviews(
        review_artifact, expected_people=sum(len(u.members) for u in snapshot.units)
    )
    collaborators = list(db.scalars(select(PresenzeCollaborator)).all())
    by_employee = {(row.company_code, row.employee_code): row for row in collaborators}
    by_kint: dict[str, list[PresenzeCollaborator]] = {}
    for collaborator in collaborators:
        if collaborator.kint:
            by_kint.setdefault(collaborator.kint, []).append(collaborator)

    existing = 0
    creations: list[_NewIdentity] = []
    review_required = 0
    blocked = 0
    for unit in snapshot.units:
        for member in unit.members:
            if member.company_code and member.employee_code:
                existing_collaborator = by_employee.get((member.company_code, member.employee_code))
                if existing_collaborator is not None:
                    if existing_collaborator.application_user_id is None:
                        blocked += 1
                    else:
                        existing += 1
                    continue
            exact = by_kint.get(member.kint, [])
            if _is_attested_kint_match(exact):
                existing += 1
                continue
            if exact:
                blocked += 1
                continue
            review = reviews.get(member.kint)
            if review is None or not member.company_code or not member.employee_code:
                blocked += 1
            elif review[1]:
                review_required += 1
            else:
                creations.append(
                    _NewIdentity(
                        member.kint,
                        member.kkint,
                        member.company_code,
                        member.employee_code,
                        review[0],
                    )
                )

    _validate_changes(db, creations)
    report = InazOnboardingReport(
        existing=existing,
        exact_kint_updates=0,
        new_users=len(creations),
        review_required=review_required,
        blocked=blocked,
        dry_run=dry_run,
    )
    if dry_run:
        return report
    for identity in creations:
        _create_identity(db, identity, changed_by=changed_by, reason=normalized_reason)
    db.commit()
    return report


def _parse_reviews(raw: Any, *, expected_people: int) -> dict[str, tuple[str, bool]]:
    if not isinstance(raw, dict) or raw.get("auto_apply") is not False:
        raise InazOnboardingError("Artefatto di revisione INAZ non valido")
    source = raw.get("source")
    people = raw.get("people")
    if not isinstance(source, dict) or source.get("roster_people") != expected_people:
        raise InazOnboardingError("Artefatto di revisione riferito a un roster diverso")
    if not isinstance(people, list):
        raise InazOnboardingError("Artefatto di revisione senza persone")
    result: dict[str, tuple[str, bool]] = {}
    for item in people:
        if not isinstance(item, dict):
            raise InazOnboardingError("Riga di revisione INAZ non valida")
        kint = str(item.get("kint") or "").strip()
        name = str(item.get("inaz_name") or "").strip()
        if not kint or not name or kint in result:
            raise InazOnboardingError("Identita di revisione INAZ incompleta o duplicata")
        has_candidate = item.get("candidate_gaia_user_id") is not None or bool(
            item.get("candidate_options")
        )
        result[kint] = (name, has_candidate)
    return result


def _is_attested_kint_match(rows: list[PresenzeCollaborator]) -> bool:
    return len(rows) == 1 and rows[0].application_user_id is not None


def _validate_changes(db: Session, creations: list[_NewIdentity]) -> None:
    target_keys = [(item.company_code, item.employee_code) for item in creations]
    if len(target_keys) != len(set(target_keys)):
        raise InazOnboardingError("Identita dipendente di destinazione duplicate")
    usernames = {_technical_username(item.company_code, item.employee_code) for item in creations}
    emails = {f"{username}@users.local" for username in usernames}
    if db.scalar(
        select(ApplicationUser.id).where(ApplicationUser.username.in_(usernames)).limit(1)
    ):
        raise InazOnboardingError("Username tecnico INAZ gia presente")
    if db.scalar(select(ApplicationUser.id).where(ApplicationUser.email.in_(emails)).limit(1)):
        raise InazOnboardingError("Email tecnica INAZ gia presente")


def _technical_username(company_code: str, employee_code: str) -> str:
    digest = hashlib.sha256(f"{company_code}\0{employee_code}".encode()).hexdigest()[:20]
    return f"inaz-{digest}"


def _create_identity(
    db: Session,
    identity: _NewIdentity,
    *,
    changed_by: ApplicationUser,
    reason: str,
) -> None:
    username = _technical_username(identity.company_code, identity.employee_code)
    user = ApplicationUser(
        username=username,
        email=f"{username}@users.local",
        full_name=identity.full_name,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        role=ApplicationUserRole.VIEWER.value,
        is_active=False,
        module_accessi=False,
    )
    db.add(user)
    db.flush()
    operator_id = uuid.uuid5(
        ONBOARDING_NAMESPACE, f"operator:{identity.company_code}:{identity.employee_code}"
    )
    db.add(
        WCOperator(
            id=operator_id,
            wc_id=_synthetic_wc_id(db, operator_id),
            username=username,
            enabled=False,
            gaia_user_id=user.id,
        )
    )
    collaborator = PresenzeCollaborator(
        id=uuid.uuid5(
            ONBOARDING_NAMESPACE,
            f"collaborator:{identity.company_code}:{identity.employee_code}",
        ),
        kint=identity.kint,
        kkint=identity.kkint,
        employee_code=identity.employee_code,
        company_code=identity.company_code,
        name=identity.full_name,
        is_active=True,
    )
    db.add(collaborator)
    # The mapping audit has a foreign key to this row and production disables autoflush.
    db.flush()
    stage_collaborator_mapping(
        db,
        collaborator=collaborator,
        application_user_id=user.id,
        changed_by=changed_by,
        reason=reason,
        source="inaz_organization_onboarding",
    )


def _synthetic_wc_id(db: Session, operator_id: uuid.UUID) -> int:
    candidate = -((operator_id.int % 2_000_000_000) + 1)
    while db.scalar(select(WCOperator.id).where(WCOperator.wc_id == candidate)) is not None:
        candidate -= 1
    return candidate
