from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy import inspect, select

from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.organigramma.services.inaz_onboarding import (
    ONBOARDING_NAMESPACE,
    InazOnboardingError,
    _create_identity,
    _NewIdentity,
    _parse_reviews,
    _synthetic_wc_id,
    _technical_username,
    _validate_changes,
    reconcile_inaz_onboarding,
)
from app.modules.organigramma.services.inaz_preview import (
    InazOrganizationSnapshot,
    InazOrganizationUnit,
    semantic_checksum,
)
from app.modules.presenze.mapping_audit import PresenzeCollaboratorMappingAudit
from app.modules.presenze.models import PresenzeCollaborator
from scripts import onboard_inaz_organization as onboarding_script


def _member(kint: str, employee: str | None) -> dict[str, str | None]:
    return {
        "kint": kint,
        "kkint": f"kk-{kint}",
        "company_code": "53",
        "employee_code": employee,
    }


def _snapshot(*members: dict[str, str | None]) -> InazOrganizationSnapshot:
    raw_unit = {
        "external_id": "root",
        "parent_external_id": None,
        "level": 0,
        "title": "Root",
        "is_staff": False,
        "responsible_kint": members[0]["kint"],
        "members": list(members),
    }
    unit = InazOrganizationUnit.model_validate(raw_unit)
    return InazOrganizationSnapshot.model_validate(
        {
            "schema_version": 2,
            "source_system": "inaz",
            "source_view": "Organigramma con Responsabile",
            "captured_at": "2026-09-05T10:00:00Z",
            "complete": True,
            "checksum_sha256": semantic_checksum([unit]),
            "units": [raw_unit],
        }
    )


def _review(total: int, *people: dict[str, object]) -> dict[str, object]:
    return {
        "auto_apply": False,
        "source": {"roster_people": total},
        "people": list(people),
    }


def _person(kint: str, *, candidate: int | None = None, options=None) -> dict[str, object]:
    return {
        "kint": kint,
        "inaz_name": f"Person {kint}",
        "candidate_gaia_user_id": candidate,
        "candidate_options": [] if options is None else options,
    }


def _collaborator(kint: str, employee: str, user_id: int | None) -> PresenzeCollaborator:
    return PresenzeCollaborator(
        kint=kint,
        kkint="old-token",
        company_code="53",
        employee_code=employee,
        name=f"Existing {kint}",
        application_user_id=user_id,
    )


def test_onboarding_is_audited_transactional_and_idempotent(session, make_user) -> None:
    actor = make_user("actor")
    existing_user = make_user("existing")
    same_kint_user = make_user("same-kint")
    session.add_all(
        [
            _collaborator("existing", "E1", existing_user.id),
            _collaborator("changed", "OLD", same_kint_user.id),
            _collaborator("", "NO-KINT", None),
        ]
    )
    session.commit()
    snapshot = _snapshot(
        _member("existing", "E1"),
        _member("changed", "E2"),
        _member("new", "E3"),
        _member("candidate", "E4"),
        _member("blocked", None),
    )
    review = _review(
        5,
        _person("new"),
        _person("candidate", candidate=99),
        _person("blocked"),
    )

    dry_run = reconcile_inaz_onboarding(
        session, snapshot, review, changed_by=actor, reason=" onboarding ", dry_run=True
    )
    assert dry_run.as_dict() == {
        "existing": 2,
        "exact_kint_updates": 0,
        "new_users": 1,
        "review_required": 1,
        "blocked": 1,
        "dry_run": True,
    }
    assert (
        session.scalar(
            select(PresenzeCollaborator).where(PresenzeCollaborator.employee_code == "E3")
        )
        is None
    )

    applied = reconcile_inaz_onboarding(
        session, snapshot, review, changed_by=actor, reason=" onboarding ", dry_run=False
    )
    assert applied.dry_run is False
    changed = session.scalar(
        select(PresenzeCollaborator).where(PresenzeCollaborator.kint == "changed")
    )
    created = session.scalar(select(PresenzeCollaborator).where(PresenzeCollaborator.kint == "new"))
    assert (changed.employee_code, changed.kkint) == ("OLD", "old-token")
    assert created.application_user_id is not None
    user = session.get(ApplicationUser, created.application_user_id)
    assert user.full_name == "Person new"
    assert user.is_active is False
    assert user.module_accessi is False
    operator = session.scalar(select(WCOperator).where(WCOperator.gaia_user_id == user.id))
    assert operator.enabled is False
    assert operator.email is None
    audit = session.query(PresenzeCollaboratorMappingAudit).one()
    assert audit.changed_by_user_id == actor.id
    assert audit.source == "inaz_organization_onboarding"
    assert audit.reason == "onboarding"

    repeated = reconcile_inaz_onboarding(
        session, snapshot, review, changed_by=actor, reason="onboarding", dry_run=False
    )
    assert repeated.as_dict() == {
        "existing": 3,
        "exact_kint_updates": 0,
        "new_users": 0,
        "review_required": 1,
        "blocked": 1,
        "dry_run": False,
    }
    assert session.query(PresenzeCollaboratorMappingAudit).count() == 1


def test_new_collaborator_is_persisted_before_mapping(session, make_user, monkeypatch) -> None:
    actor = make_user("actor")

    def assert_persisted(db, *, collaborator, **_kwargs) -> bool:
        assert db is session
        assert inspect(collaborator).persistent
        return True

    monkeypatch.setattr(
        "app.modules.organigramma.services.inaz_onboarding.stage_collaborator_mapping",
        assert_persisted,
    )

    _create_identity(
        session,
        _NewIdentity("new", "kk-new", "53", "E3", "Person new"),
        changed_by=actor,
        reason="onboarding",
    )


@pytest.mark.parametrize(
    "raw,total,message",
    [
        ({}, 1, "non valido"),
        ({"auto_apply": False, "source": {}, "people": []}, 1, "roster diverso"),
        ({"auto_apply": False, "source": {"roster_people": 1}}, 1, "senza persone"),
        (_review(1, "bad"), 1, "Riga"),
        (_review(1, {"kint": "", "inaz_name": "Name"}), 1, "incompleta"),
        (_review(2, _person("x"), _person("x")), 2, "duplicata"),
    ],
)
def test_review_parser_rejects_invalid_artifacts(raw, total, message) -> None:
    with pytest.raises(InazOnboardingError, match=message):
        _parse_reviews(raw, expected_people=total)


def test_review_options_also_require_review() -> None:
    assert _parse_reviews(_review(1, _person("x", options=[{"id": 1}])), expected_people=1) == {
        "x": ("Person x", True)
    }


def test_onboarding_rejects_blank_reason_and_blocks_ambiguous_kint(session, make_user) -> None:
    actor = make_user("actor")
    snapshot = _snapshot(_member("x", "E1"))
    review = _review(1, _person("x"))
    with pytest.raises(InazOnboardingError, match="motivo"):
        reconcile_inaz_onboarding(
            session, snapshot, review, changed_by=actor, reason=" ", dry_run=True
        )
    session.add_all([_collaborator("x", "OLD1", actor.id), _collaborator("x", "OLD2", None)])
    session.commit()
    report = reconcile_inaz_onboarding(
        session, snapshot, review, changed_by=actor, reason="audit", dry_run=True
    )
    assert report.new_users == 0
    assert report.blocked == 1


def test_existing_unmapped_employee_identity_remains_blocked(session, make_user) -> None:
    actor = make_user("actor")
    session.add(_collaborator("x", "E1", None))
    session.commit()
    report = reconcile_inaz_onboarding(
        session,
        _snapshot(_member("x", "E1")),
        _review(1, _person("x")),
        changed_by=actor,
        reason="audit",
        dry_run=True,
    )
    assert report.existing == 0
    assert report.new_users == 0
    assert report.blocked == 1


def test_attested_kint_without_employee_code_remains_existing(session, make_user) -> None:
    actor = make_user("actor")
    session.add(_collaborator("x", "OLD", actor.id))
    session.commit()
    report = reconcile_inaz_onboarding(
        session,
        _snapshot(_member("x", None)),
        _review(1),
        changed_by=actor,
        reason="audit",
        dry_run=True,
    )
    assert report.existing == 1
    assert report.blocked == 0
    assert report.exact_kint_updates == 0


def test_employee_code_match_reuses_existing_canonical_mapping_without_changes(
    session, make_user
) -> None:
    actor = make_user("actor")
    collaborator = _collaborator("different-kint", "E1", actor.id)
    session.add(collaborator)
    session.commit()

    report = reconcile_inaz_onboarding(
        session,
        _snapshot(_member("new-kint", "E1")),
        _review(1, _person("new-kint")),
        changed_by=actor,
        reason="audit",
        dry_run=True,
    )

    assert report.existing == 1
    assert report.new_users == 0
    assert report.review_required == 0
    assert collaborator.application_user_id == actor.id
    assert collaborator.kint == "different-kint"
    assert session.query(PresenzeCollaboratorMappingAudit).count() == 0


def test_change_validation_rejects_duplicates_and_technical_collisions(session) -> None:
    identity = _NewIdentity("k", None, "53", "E1", "Person")
    with pytest.raises(InazOnboardingError, match="destinazione duplicate"):
        _validate_changes(session, [identity, identity])

    username = _technical_username("53", "E1")
    session.add(ApplicationUser(username=username, email="other@users.local", password_hash="x"))
    session.commit()
    with pytest.raises(InazOnboardingError, match="Username"):
        _validate_changes(session, [identity])
    session.query(ApplicationUser).delete()
    session.add(
        ApplicationUser(username="other", email=f"{username}@users.local", password_hash="x")
    )
    session.commit()
    with pytest.raises(InazOnboardingError, match="Email"):
        _validate_changes(session, [identity])


def test_synthetic_wc_id_moves_past_collision(session) -> None:
    operator_id = uuid.uuid5(ONBOARDING_NAMESPACE, "collision")
    first = -((operator_id.int % 2_000_000_000) + 1)
    session.add(WCOperator(wc_id=first))
    session.commit()
    assert _synthetic_wc_id(session, operator_id) == first - 1


def test_onboarding_script_runs_dry_run_and_rejects_unknown_actor(
    session, make_user, tmp_path: Path, monkeypatch, capsys
) -> None:
    actor = make_user("actor")
    snapshot = _snapshot(_member("new", "E1"))
    snapshot_path = tmp_path / "snapshot.json"
    review_path = tmp_path / "review.json"
    snapshot_path.write_text(snapshot.model_dump_json())
    review_path.write_text(json.dumps(_review(1, _person("new"))))
    monkeypatch.setattr(onboarding_script, "SessionLocal", lambda: session)
    args = [
        str(snapshot_path),
        str(review_path),
        "--changed-by-gaia-user-id",
        str(actor.id),
        "--reason",
        "test",
    ]
    assert onboarding_script.main(args) == 0
    assert '"new_users": 1' in capsys.readouterr().out
    args[3] = "99999"
    with pytest.raises(InazOnboardingError, match="autore"):
        onboarding_script.main(args)
