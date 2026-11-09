"""Exercise authoritative writes on web, LAN and outbound against an isolated DB."""

import uuid
from datetime import time

import pytest
from fastapi import HTTPException
from test_presenze_api import (  # noqa: F401 - isolated API fixture
    TestingSessionLocal,
    _create_user,
    _login,
    client,
    setup_database,
)
from test_presenze_meal_vouchers import _record

from app.modules.presenze.models import PresenzeDailyPunch, PresenzeDailyRecord
from app.services.gate_mobile_sync import _apply_presenze_pending_action


def _write(transport, record_id, actor, values):
    if transport == "outbound":
        with TestingSessionLocal() as db:
            try:
                _apply_presenze_pending_action(
                    db,
                    {
                        "id": str(uuid.uuid4()),
                        "action_type": "patch_daily_record",
                        "payload": {
                            **values,
                            "record_id": str(record_id),
                            "gaia_user_id": actor.id,
                        },
                    },
                )
            except HTTPException as error:
                db.rollback()
                return error.status_code
        return 200
    headers = {"Authorization": "Bearer " + _login(actor.username)}
    if transport == "web":
        return client.patch(
            f"/presenze/giornaliere/{record_id}", headers=headers, json=values
        ).status_code
    return client.post(
        f"/gate/presenze/giornaliere/{record_id}/patch", headers=headers, json=values
    ).status_code


@pytest.mark.parametrize("transport", ["web", "lan", "outbound"])
@pytest.mark.parametrize("blank_row", [False, True])
def test_absent_punches_block_positive_writes_but_keep_removal_and_availability(
    transport, blank_row
):
    actor = _create_user("presence-" + transport)
    rid, _ = _record(actor.id, with_presence=False)
    # A stale grant is preserved until explicitly removed. No retroactive cleanup.
    with TestingSessionLocal() as db:
        if blank_row:
            db.add(PresenzeDailyPunch(daily_record_id=rid, sequence=1))
        record = db.get(PresenzeDailyRecord, rid)
        record.km_value = 12
        record.meal_voucher_manual = True
        db.commit()
    for values in [
        {"km_value": 13},
        {"meal_voucher_manual": True},
        {"km_value": 13, "meal_voucher_manual": False},
        {"km_value": 0, "meal_voucher_manual": True},
        {"km_value": 13, "detail_punch_rows": [{"entry_time": "06:00"}]},
    ]:
        assert _write(transport, rid, actor, values) == 422
        with TestingSessionLocal() as db:
            record = db.get(PresenzeDailyRecord, rid)
            assert record.km_value == 12 and record.meal_voucher_manual
            assert not record.meal_voucher_audit
    for values in [
        {"km_value": 0, "meal_voucher_manual": False},
        {"km_value": None},
        {"reperibilita_unit": "days", "reperibilita_quantity": 1},
    ]:
        assert _write(transport, rid, actor, values) == 200
    with TestingSessionLocal() as db:
        record = db.get(PresenzeDailyRecord, rid)
        assert not record.meal_voucher_manual and record.km_value is None
        assert record.reperibilita_quantity == 1
        assert len(record.meal_voucher_audit) == 1


@pytest.mark.parametrize("transport", ["web", "lan", "outbound"])
@pytest.mark.parametrize("pair", [(time(6, 45), time(12)), (None, time(13)), (time(0), None)])
def test_partial_presence_attests_travel_without_requiring_seven_hours(transport, pair):
    actor = _create_user("partial-" + transport)
    rid, _ = _record(actor.id, with_presence=False)
    with TestingSessionLocal() as db:
        db.add(
            PresenzeDailyPunch(
                daily_record_id=rid, sequence=1, entry_time=pair[0], exit_time=pair[1]
            )
        )
        db.commit()
    assert _write(transport, rid, actor, {"km_value": 12}) == 200
    assert _write(transport, rid, actor, {"meal_voucher_manual": True}) == 200
    with TestingSessionLocal() as db:
        record = db.get(PresenzeDailyRecord, rid)
        assert record.km_value == 12 and record.meal_voucher_manual
