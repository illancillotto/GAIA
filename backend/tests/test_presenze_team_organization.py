"""Canonical links, hierarchy projection and explicit team-management permissions."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from test_gate_mobile_sync import _build_session, _seed_presenze_team

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.organigramma.models.org_assignment import OrgAssignment
from app.modules.organigramma.models.org_unit import OrgUnit
from app.modules.presenze.gate_router import router as teams_router
from app.modules.presenze.models import OrganizationTeam
from app.modules.presenze.services.team_organization import (
    build_team_organization_directory,
    require_team_org_unit,
)
from app.modules.presenze.team_organization_models import PresenzeTeamOrganization
from app.modules.presenze.team_organization_router import router
from app.services.gate_mobile_sync import build_presenze_teams_push_payload


@pytest.fixture
def db():
    with _build_session() as session:
        yield session


def unit(db, **values):
    result = OrgUnit(nome="Synthetic", tipo="reparto", structure_kind="organigramma", **values)
    db.add(result)
    db.flush()
    return result


def test_explicit_link_projects_only_canonical_active_hierarchy_and_leaders(db):
    _seed_presenze_team(db)
    sector = unit(db)
    department = unit(db, parent_id=sector.id)
    team = db.query(OrganizationTeam).one()
    assert build_presenze_teams_push_payload(db)["teams"][0]["organization"] is None
    db.add(
        PresenzeTeamOrganization(
            team_id=team.id, org_unit_id=require_team_org_unit(db, department.id)
        )
    )
    db.flush()
    user = db.query(ApplicationUser).first()
    user.full_name = None
    db.add_all(
        [
            OrgAssignment(
                user_id=user.id,
                org_unit_id=sector.id,
                position_code="capo_settore",
                valid_from=datetime(2026, 10, 1, tzinfo=UTC),
                valid_to=datetime(2026, 10, 31, tzinfo=UTC),
            ),
            OrgAssignment(user_id=user.id, org_unit_id=department.id, position_code="capo_reparto"),
            OrgAssignment(
                user_id=user.id, org_unit_id=department.id, position_code="collaboratore"
            ),
            OrgAssignment(
                user_id=user.id,
                org_unit_id=department.id,
                position_code="capo_reparto",
                active=False,
            ),
            OrgAssignment(
                user_id=user.id,
                org_unit_id=department.id,
                position_code="capo_reparto",
                structure_kind="other",
            ),
        ]
    )
    db.flush()
    organization = build_presenze_teams_push_payload(db)["teams"][0]["organization"]
    assert organization["unit_id"] == str(department.id)
    assert [row["id"] for row in organization["path"]] == [str(sector.id), str(department.id)]
    assert [len(row["leaders"]) for row in organization["path"]] == [1, 1]
    assert organization["path"][0]["leaders"][0] == {
        "gaia_user_id": str(user.id),
        "user_label": user.username,
        "position_code": "capo_settore",
        "valid_from": "2026-10-01T00:00:00+00:00",
        "valid_to": "2026-10-31T00:00:00+00:00",
    }
    user.full_name = "Synthetic Chief"
    db.flush()
    assert (
        build_team_organization_directory(db)[department.id]["path"][0]["leaders"][0]["user_label"]
        == "Synthetic Chief"
    )
    user.is_active = False
    db.flush()
    assert all(
        not row["leaders"] for row in build_team_organization_directory(db)[department.id]["path"]
    )


def test_missing_inactive_other_structure_and_cyclic_paths_fail_closed(db):
    valid = unit(db)
    inactive = unit(db, is_active=False)
    foreign = OrgUnit(nome="Foreign", tipo="reparto", structure_kind="other")
    db.add(foreign)
    db.flush()
    for unit_id in [uuid4(), inactive.id, foreign.id]:
        with pytest.raises(HTTPException) as error:
            require_team_org_unit(db, unit_id)
        assert error.value.status_code == 422
    assert require_team_org_unit(db, None) is None
    child = unit(db, parent_id=inactive.id)
    assert child.id not in build_team_organization_directory(db)
    valid.parent_id = valid.id
    db.flush()
    assert valid.id not in build_team_organization_directory(db)


def test_team_api_persists_explicit_links_and_detects_stale_edits(db):
    linked = unit(db)
    second = unit(db)
    user = ApplicationUser(
        id=100,
        username="admin",
        email="admin@example.invalid",
        password_hash="synthetic",
        role="admin",
        is_active=True,
        module_presenze=True,
    )
    db.add(user)
    db.commit()
    app = FastAPI()
    app.include_router(teams_router)
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_active_user] = lambda: user
    with TestClient(app) as client:
        response = client.post(
            "/gate/presenze/teams", json={"name": "Synthetic", "personnel_area": "AGRARIO"}
        )
        assert response.status_code == 200, response.text
        team_id = response.json()["id"]
        url = f"/gate/presenze/teams/{team_id}/organization"

        def put(new, previous=None):
            return client.put(
                url,
                json={
                    "org_unit_id": str(new) if new else None,
                    "expected_org_unit_id": str(previous) if previous else None,
                },
            )

        assert put(linked.id).json()["org_unit_id"] == str(linked.id)
        info = client.get("/gate/presenze/team-organizations").json()
        assert info["teams"] == [{"team_id": team_id, "org_unit_id": str(linked.id)}]
        assert len(info["units"]) == 2
        assert put(second.id).status_code == 409
        assert put(uuid4(), linked.id).status_code == 422
        db.rollback()
        assert put(second.id, linked.id).json()["org_unit_id"] == str(second.id)
        assert put(None, second.id).json()["org_unit_id"] is None
        assert put(None).status_code == 200
        assert (
            client.put(
                f"/gate/presenze/teams/{uuid4()}/organization",
                json={"org_unit_id": None, "expected_org_unit_id": None},
            ).status_code
            == 404
        )
        assert client.put(url, json={"org_unit_id": None}).status_code == 422
        user.role = "viewer"
        assert put(linked.id).status_code == 403
        assert client.get("/gate/presenze/team-organizations").status_code == 403


def test_assignment_datetimes_preserve_utc_contract():
    from app.modules.presenze.services.team_organization import _assignment_datetime

    assert _assignment_datetime(datetime(2026, 10, 1, tzinfo=UTC)) == "2026-10-01T00:00:00+00:00"


def test_registry_loads_the_association_model_for_migrations():
    from app.db import base

    assert base.PresenzeTeamOrganization is PresenzeTeamOrganization
    assert (
        base.Base.metadata.tables["presenze_team_organization"]
        is PresenzeTeamOrganization.__table__
    )


def test_hr_console_role_is_validated_persisted_and_published_without_changing_personnel_area(db):
    from test_gate_mobile_sync import _seed_operator

    from app.modules.operazioni.models.wc_operator import WCOperator
    from app.modules.operazioni.schemas.operators import GateMobileConsoleUpdateRequest
    from app.services.gate_mobile_sync import (
        _apply_operator_console_fields,
        build_mobile_operator_push_payload,
    )

    _seed_operator(db)
    request = GateMobileConsoleUpdateRequest(enabled=True, role="hr_manager")
    operator = db.query(WCOperator).one()
    _apply_operator_console_fields(
        operator,
        {
            "gate_mobile_console_enabled": request.enabled,
            "gate_mobile_console_role": request.role,
        },
    )
    db.commit()
    db.expire_all()
    published = build_mobile_operator_push_payload(db)["operators"][0]
    assert published["gate_mobile_console_enabled"] is True
    assert published["gate_mobile_console_role"] == "hr_manager"
    assert published["personnel_area"] == "AGRARIO"
