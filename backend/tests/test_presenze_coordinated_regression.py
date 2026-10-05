"""Employee-wide authorization and manual edits across both GATE transports."""

import uuid

import pytest
from sqlalchemy import select
from test_presenze_api import (
    TestingSessionLocal,
    _create_user,
    _login,
    client,
    setup_database,  # noqa: F401 - shared isolated API database fixture
)
from test_presenze_meal_vouchers import _record

from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.shift_worker_models import PresenzeShiftAssignment
from app.services.gate_mobile_sync import _apply_presenze_pending_action


@pytest.mark.parametrize("role", ["admin", "super_admin", "hr_manager"])
def test_global_presenze_roles_can_assign_employee_range(role):
    owner = _create_user("limited-owner", role="operator")
    actor = _create_user("global-shift-actor", role=role)
    rid, _ = _record(owner.id)
    response = client.post(
        f"/presenze/giornaliere/{rid}/turnista",
        headers={"Authorization": "Bearer " + _login(actor.username)},
        json={
            "shift_worker_type": "telecontrollo",
            "date_from": "2026-10-01",
            "date_to": "2026-10-31",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["shift_worker_type"] == "telecontrollo"
    with TestingSessionLocal() as db:
        assignment = db.scalars(select(PresenzeShiftAssignment)).one()
        assert assignment.actor_user_id == actor.id
        assert assignment.source == "gaia"


@pytest.mark.parametrize("transport", ["lan", "outbound"])
def test_gate_manual_voucher_grant_retry_and_removal_remain_audited(transport):
    actor = _create_user("manual-" + transport)
    rid, _ = _record(actor.id)
    headers = {"Authorization": "Bearer " + _login(actor.username)}
    for enabled in [True, True, False]:
        if transport == "lan":
            response = client.post(
                f"/gate/presenze/giornaliere/{rid}/patch",
                headers=headers,
                json={"meal_voucher_manual": enabled},
            )
            assert response.status_code == 200, response.text
        else:
            with TestingSessionLocal() as db:
                _apply_presenze_pending_action(
                    db,
                    {
                        "id": str(uuid.uuid4()),
                        "action_type": "patch_daily_record",
                        "payload": {
                            "record_id": str(rid),
                            "gaia_user_id": actor.id,
                            "meal_voucher_manual": enabled,
                        },
                    },
                )
        with TestingSessionLocal() as db:
            assert db.get(PresenzeDailyRecord, rid).meal_voucher_manual is enabled
    response = client.get(f"/presenze/giornaliere/{rid}", headers=headers)
    assert response.status_code == 200
    assert response.json()["meal_voucher_count"] == 0
    assert len(response.json()["meal_voucher_audit"]) == 2
