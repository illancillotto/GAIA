from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models.application_user import ApplicationUserRole
from app.modules.organigramma.services.inaz_preview import (
    InazOrganizationMember,
    InazOrganizationSnapshot,
    InazOrganizationUnit,
    _identity_status,
    _load_collaborators_by_identity,
    semantic_checksum,
)
from app.modules.presenze.models import PresenzeCollaborator


def _member(
    kint: str,
    *,
    company_code: str | None = "53",
    employee_code: str | None = None,
) -> dict:
    return {
        "kint": kint,
        "kkint": f"volatile-{kint}",
        "company_code": company_code,
        "employee_code": employee_code or f"employee-{kint}",
    }


def _unit(
    external_id: str,
    *,
    parent_external_id: str | None = None,
    level: int = 0,
    responsible_kint: str | None = None,
    members: tuple[dict, ...] = (),
) -> dict:
    return {
        "external_id": external_id,
        "parent_external_id": parent_external_id,
        "level": level,
        "title": f"Unit {external_id}",
        "is_staff": False,
        "responsible_kint": responsible_kint,
        "members": list(members),
    }


def _snapshot(units: list[dict]) -> dict:
    parsed_units = [InazOrganizationUnit.model_validate(unit) for unit in units]
    return {
        "schema_version": 2,
        "source_system": "inaz",
        "source_view": "Organigramma con Responsabile",
        "captured_at": "2026-09-05T10:00:00+00:00",
        "complete": True,
        "checksum_sha256": semantic_checksum(parsed_units),
        "units": units,
    }


def _collaborator(kint: str, code: str, application_user_id: int | None):
    return PresenzeCollaborator(
        kint=kint,
        employee_code=code,
        company_code="53",
        name=f"Person {code}",
        application_user_id=application_user_id,
    )


def test_inaz_preview_is_ready_with_canonical_employee_mapping(
    client, make_user, auth_header, session
):
    admin = make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    first = make_user("first")
    second = make_user("second")
    session.add_all(
        [
            _collaborator("daily-kint-1", "employee-org-kint-1", first.id),
            _collaborator("daily-kint-2", "employee-org-kint-2", second.id),
        ]
    )
    session.commit()
    payload = _snapshot(
        [
            _unit(
                "root",
                responsible_kint="org-kint-1",
                members=(_member("org-kint-1"),),
            ),
            _unit(
                "child",
                parent_external_id="root",
                level=1,
                responsible_kint="org-kint-2",
                members=(_member("org-kint-2"),),
            ),
        ]
    )

    response = client.post(
        "/organigramma/sync/inaz/preview",
        json=payload,
        headers=auth_header(admin.username),
    )

    assert response.status_code == 200
    assert response.json() == {
        "snapshot_checksum": payload["checksum_sha256"],
        "unit_count": 2,
        "member_count": 2,
        "responsible_count": 2,
        "required_identity_count": 2,
        "mapped_identity_count": 2,
        "mapped_member_count": 2,
        "issues": {},
        "ready": True,
        "message": "Snapshot INAZ pronto per la pianificazione dell'import",
    }


def test_inaz_preview_reports_each_fail_closed_mapping_state(
    client, make_user, auth_header, session
):
    admin = make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    mapped = make_user("mapped")
    session.add_all(
        [
            _collaborator("daily-mapped", "employee-mapped", mapped.id),
            _collaborator("daily-unmapped", "employee-unmapped", None),
            PresenzeCollaborator(
                kint="daily-without-company",
                employee_code="employee-missing",
                company_code=None,
                name="No company",
                application_user_id=None,
            ),
        ]
    )
    session.commit()
    payload = _snapshot(
        [
            _unit(
                "root",
                responsible_kint="missing",
                members=(
                    _member("mapped"),
                    _member("unmapped"),
                    _member("missing"),
                ),
            )
        ]
    )

    response = client.post(
        "/organigramma/sync/inaz/preview",
        json=payload,
        headers=auth_header(admin.username),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is False
    assert body["mapped_identity_count"] == 1
    assert body["mapped_member_count"] == 1
    assert body["issues"] == {
        "missing_collaborator": 1,
        "unmapped_collaborator": 1,
    }


def test_identity_status_detects_all_fail_closed_states():
    complete = InazOrganizationMember(kint="org", company_code="53", employee_code="100")
    no_company = complete.model_copy(update={"company_code": None})
    no_employee = complete.model_copy(update={"employee_code": None})
    mapped = SimpleNamespace(application_user_id=10)
    unmapped = SimpleNamespace(application_user_id=None)

    assert _identity_status(no_employee, [], set()) == "missing_employee_code"
    assert _identity_status(no_company, [], set()) == "missing_company_code"
    assert _identity_status(complete, [], set()) == "missing_collaborator"
    assert _identity_status(complete, [mapped, mapped], {10}) == "duplicate_collaborator_identity"
    assert _identity_status(complete, [unmapped], {10}) == "unmapped_collaborator"
    assert _identity_status(complete, [mapped], set()) == "missing_application_user"
    assert _identity_status(complete, [mapped], {10}) == "mapped"


def test_load_collaborators_by_identity_skips_query_without_codes(session):
    member = InazOrganizationMember(kint="org", company_code="53")

    assert _load_collaborators_by_identity(session, [member]) == {}


@pytest.mark.parametrize(
    "mutate, message",
    [
        (
            lambda data: data["units"].append(deepcopy(data["units"][0])),
            "unità duplicate",
        ),
        (lambda data: data["units"][0].update(level=1), "radice di livello 0"),
        (
            lambda data: data["units"].append(
                _unit("child", parent_external_id="missing", level=1)
            ),
            "gerarchia incoerente",
        ),
        (
            lambda data: data["units"][0]["members"].append(
                deepcopy(data["units"][0]["members"][0])
            ),
            "appartenenze Kint duplicate",
        ),
        (
            lambda data: data["units"][0]["members"].append(
                {**_member("other-kint"), "employee_code": "employee-k-1"}
            ),
            "identità dipendente duplicate",
        ),
        (
            lambda data: data["units"][0].update(responsible_kint="unknown"),
            "responsabile senza appartenenza",
        ),
        (lambda data: data.update(checksum_sha256="0" * 64), "Checksum"),
    ],
)
def test_inaz_snapshot_rejects_invalid_content(mutate, message):
    payload = _snapshot([_unit("root", members=(_member("k-1"),))])
    mutate(payload)

    with pytest.raises(ValidationError, match=message):
        InazOrganizationSnapshot.model_validate(payload)


def test_inaz_snapshot_checksum_ignores_kkint_but_covers_employee_identity():
    unit = _unit("root", members=(_member("k-1"),))
    parsed = [InazOrganizationUnit.model_validate(unit)]
    changed_kkint = deepcopy(unit)
    changed_kkint["members"][0]["kkint"] = "new-volatile-value"
    changed_employee = deepcopy(unit)
    changed_employee["members"][0]["employee_code"] = "other-employee"

    assert semantic_checksum(parsed) == semantic_checksum(
        [InazOrganizationUnit.model_validate(changed_kkint)]
    )
    assert semantic_checksum(parsed) != semantic_checksum(
        [InazOrganizationUnit.model_validate(changed_employee)]
    )
