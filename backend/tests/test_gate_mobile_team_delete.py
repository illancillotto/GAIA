from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from test_gate_mobile_sync import _build_session, _seed_presenze_daily_record

from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.presenze.models import (
    OrganizationTeam,
    OrganizationTeamMembership,
    OrganizationTeamSupervisorAssignment,
    PresenzeCollaborator,
    PresenzeDailyRecord,
)
from app.modules.presenze.services.gate_mobile_team_actions import TeamChangeApplyError
from app.services.gate_mobile_sync import _apply_presenze_pending_action


@pytest.fixture
def seeded_db():
    db = _build_session()
    _seed_presenze_daily_record(db)
    actor = db.get(ApplicationUser, 77)
    actor.role = ApplicationUserRole.ADMIN.value
    db.commit()
    try:
        yield db
    finally:
        db.close()


def deletion(target_id="018f88a2-1797-7365-bf5e-8bb8b7f9d002", area="AGRARIO"):
    return {
        "action_type": "propose_team_delete",
        "pending_action_id": "delete-request",
        "payload": {
            "gaia_user_id": "77",
            "operation": "delete_team",
            "team": {"team_id": target_id, "personnel_area": area},
        },
    }


@pytest.mark.parametrize("external_id", [False, True])
def test_delete_team_and_assignments_preserves_people_records_and_accepts_replay(
    seeded_db, external_id
):
    team = seeded_db.scalar(select(OrganizationTeam))
    target = str(team.id)
    if external_id:
        team.gate_mobile_team_id = "legacy-gate-team"
        target = team.gate_mobile_team_id
        seeded_db.commit()
    ack = _apply_presenze_pending_action(seeded_db, deletion(target))
    assert ack["gaia_entity_type"] == "organization_team"
    assert seeded_db.scalars(select(OrganizationTeam)).all() == []
    assert seeded_db.scalars(select(OrganizationTeamMembership)).all() == []
    assert seeded_db.scalars(select(OrganizationTeamSupervisorAssignment)).all() == []
    assert len(seeded_db.scalars(select(PresenzeCollaborator)).all()) == 1
    assert len(seeded_db.scalars(select(PresenzeDailyRecord)).all()) == 1
    replay = _apply_presenze_pending_action(seeded_db, deletion(target))
    assert replay["gaia_entity_id"] == target


@pytest.mark.parametrize(
    ("role", "enabled", "active", "allowed"),
    [
        ("admin", True, True, True),
        ("hr_manager", True, True, True),
        ("super_admin", False, True, True),
        ("admin", False, True, False),
        ("reviewer", True, True, False),
        ("admin", True, False, False),
    ],
)
def test_delete_requires_active_presenze_administrator(seeded_db, role, enabled, active, allowed):
    actor = seeded_db.get(ApplicationUser, 77)
    actor.role, actor.module_presenze, actor.is_active = role, enabled, active
    seeded_db.commit()
    if allowed:
        _apply_presenze_pending_action(seeded_db, deletion())
        assert seeded_db.scalar(select(OrganizationTeam)) is None
    else:
        with pytest.raises(ValueError):
            _apply_presenze_pending_action(seeded_db, deletion())
        assert seeded_db.scalar(select(OrganizationTeam)) is not None


@pytest.mark.parametrize(
    ("target", "area", "message"),
    [
        ("018f88a2-1797-7365-bf5e-8bb8b7f9d002", "IMPIANTI", "incoerente"),
        (None, "AGRARIO", "team_id mancante"),
        ("missing", "UNKNOWN", "personnel_area"),
    ],
)
def test_delete_rejects_invalid_target_and_area_without_changing_data(
    seeded_db, target, area, message
):
    with pytest.raises(TeamChangeApplyError, match=message):
        _apply_presenze_pending_action(seeded_db, deletion(target, area))
    assert seeded_db.scalar(select(OrganizationTeam)) is not None


def test_delete_unknown_uuid_is_idempotent(seeded_db):
    target = str(uuid.uuid4())
    assert _apply_presenze_pending_action(seeded_db, deletion(target))["gaia_entity_id"] == target
    assert seeded_db.scalar(select(OrganizationTeam)) is not None


@pytest.mark.parametrize(
    "count,enabled,console_enabled,role,allowed",
    [
        (0, True, True, "console_admin", False),
        (1, True, True, "console_admin", True),
        (2, True, True, "console_admin", False),
        (1, False, True, "console_admin", False),
        (1, True, False, "console_admin", False),
        (1, True, True, "team_manager", False),
    ],
)
def test_delete_accepts_only_unique_enabled_canonical_console_admin(
    seeded_db, count, enabled, console_enabled, role, allowed
):
    actor = seeded_db.get(ApplicationUser, 77)
    actor.role = "operator"
    for index in range(count):
        seeded_db.add(
            WCOperator(
                wc_id=9000 + index,
                gaia_user_id=77,
                enabled=enabled,
                gate_mobile_console_enabled=console_enabled,
                gate_mobile_console_role=role,
            )
        )
    seeded_db.commit()
    if allowed:
        _apply_presenze_pending_action(seeded_db, deletion())
        assert seeded_db.scalar(select(OrganizationTeam)) is None
    else:
        with pytest.raises(ValueError):
            _apply_presenze_pending_action(seeded_db, deletion())
        assert seeded_db.scalar(select(OrganizationTeam)) is not None
