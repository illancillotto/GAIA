"""The manual voucher contract must work through both GATE transports."""

import uuid
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from test_presenze_api import (  # noqa: F401 - shared isolated API database fixture
    TestingSessionLocal,
    _create_user,
    _login,
    client,
    setup_database,
)
from test_presenze_meal_vouchers import _record

from app.modules.presenze.gate_daily_record_schemas import GatePresenzeDailyRecordPatchRequest
from app.modules.presenze.gate_router import _gate_record_analysis_from_serialized
from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.services.gate_daily_record_patch import apply_gate_daily_record_patch
from app.services.gate_mobile_sync import (
    _apply_presenze_pending_action,
    build_presenze_giornaliere_push_payload,
)


@pytest.mark.parametrize("transport", ["lan", "outbound"])
def test_gate_manual_grant_and_revoke_are_persisted_audited_and_published(transport):
    actor = _create_user("meal-gate-" + transport)
    record_id, _ = _record(actor.id, extra=120)
    headers = {"Authorization": "Bearer " + _login(actor.username)}
    for enabled in [True, True, False]:
        data = {"meal_voucher_manual": enabled, "operator_note": "Test GATE"}
        if transport == "lan":
            response = client.post(
                f"/gate/presenze/giornaliere/{record_id}/patch", headers=headers, json=data
            )
            assert response.status_code == 200, response.text
        else:
            with TestingSessionLocal() as db:
                ack = _apply_presenze_pending_action(
                    db,
                    {
                        "id": str(uuid.uuid4()),
                        "action_type": "patch_daily_record",
                        "payload": {**data, "record_id": str(record_id), "gaia_user_id": actor.id},
                    },
                )
                assert ack["gaia_entity_id"] == str(record_id)
        with TestingSessionLocal() as db:
            record = db.get(PresenzeDailyRecord, record_id)
            assert record.meal_voucher_manual is enabled
            payload = build_presenze_giornaliere_push_payload(db, month="2026-10")
            day = next(row for row in payload["giornaliere"] if row["record_id"] == str(record_id))
            assert day["meal_voucher_manual"] is enabled
            assert day["meal_voucher_count"] == 1
    with TestingSessionLocal() as db:
        audit = db.get(PresenzeDailyRecord, record_id).meal_voucher_audit
        assert [entry["enabled"] for entry in audit] == [True, False]
        assert all(entry["source"] == "gate_console_mobile" for entry in audit)
        assert all(entry["actor_user_id"] == actor.id for entry in audit)


@pytest.mark.parametrize("value", [None, "true", 1])
def test_gate_rejects_invalid_voucher_value_before_persistence(value):
    actor = _create_user("meal-gate-invalid-" + str(value))
    record_id, _ = _record(actor.id)
    response = client.post(
        f"/gate/presenze/giornaliere/{record_id}/patch",
        headers={"Authorization": "Bearer " + _login(actor.username)},
        json={"meal_voucher_manual": value},
    )
    assert response.status_code == 422
    with TestingSessionLocal() as db:
        assert db.get(PresenzeDailyRecord, record_id).meal_voucher_manual is False
        with pytest.raises(ValidationError):
            _apply_presenze_pending_action(
                db,
                {
                    "id": str(uuid.uuid4()),
                    "action_type": "patch_daily_record",
                    "payload": {
                        "record_id": str(record_id),
                        "gaia_user_id": actor.id,
                        "meal_voucher_manual": value,
                    },
                },
            )


def test_omitted_voucher_does_not_clear_an_existing_manual_grant():
    actor = _create_user("meal-gate-km")
    record_id, _ = _record(actor.id)
    with TestingSessionLocal() as db:
        record = db.get(PresenzeDailyRecord, record_id)
        apply_gate_daily_record_patch(
            db, record, GatePresenzeDailyRecordPatchRequest(meal_voucher_manual=True), actor.id
        )
        db.commit()
        apply_gate_daily_record_patch(
            db, record, GatePresenzeDailyRecordPatchRequest(km_value=12), actor.id
        )
        db.commit()
        assert record.meal_voucher_manual and record.km_value == 12
        assert len(record.meal_voucher_audit) == 1
        apply_gate_daily_record_patch(
            db, record, GatePresenzeDailyRecordPatchRequest(meal_voucher_manual=False), actor.id
        )
        db.rollback()
        db.refresh(record)
        assert record.meal_voucher_manual and len(record.meal_voucher_audit) == 1


def test_gate_patch_requires_authentication_and_a_visible_record():
    actor = _create_user("meal-gate-auth")
    record_id, _ = _record(actor.id)
    assert (
        client.post(
            f"/gate/presenze/giornaliere/{record_id}/patch", json={"meal_voucher_manual": True}
        ).status_code
        == 401
    )
    missing = client.post(
        f"/gate/presenze/giornaliere/{uuid.uuid4()}/patch",
        headers={"Authorization": "Bearer " + _login(actor.username)},
        json={"meal_voucher_manual": True},
    )
    assert missing.status_code == 404
    with TestingSessionLocal() as db:
        assert db.get(PresenzeDailyRecord, record_id).meal_voucher_manual is False


def test_gate_analysis_does_not_downgrade_a_blocking_day_with_high_extra():
    record = SimpleNamespace(validation_status="pending")
    values = SimpleNamespace(
        operational_status="blocking",
        operational_missing_minutes=60,
        effective_extra_minutes=360,
        detail_error=None,
        detail_anomalies=[],
    )
    result = _gate_record_analysis_from_serialized(record, values)
    assert result.severity == "blocking"
    assert result.reasons == ["missing_or_blocking_time", "extra_over_5h"]


@pytest.mark.parametrize("quantity", [None, 0, 1])
def test_gate_availability_none_retains_existing_validation(quantity):
    if quantity == 1:
        with pytest.raises(ValidationError):
            GatePresenzeDailyRecordPatchRequest(
                reperibilita_unit="none", reperibilita_quantity=quantity
            )
    else:
        assert (
            GatePresenzeDailyRecordPatchRequest(
                reperibilita_unit="none", reperibilita_quantity=quantity
            ).reperibilita_quantity
            is None
        )


@pytest.mark.parametrize("quantity", [None, 0, 2])
def test_gate_availability_days_retains_existing_validation(quantity):
    if quantity in (None, 0):
        with pytest.raises(ValidationError):
            GatePresenzeDailyRecordPatchRequest(
                reperibilita_unit="days", reperibilita_quantity=quantity
            )
    else:
        assert (
            GatePresenzeDailyRecordPatchRequest(
                reperibilita_unit="days", reperibilita_quantity=quantity
            ).reperibilita_quantity
            == 2
        )
