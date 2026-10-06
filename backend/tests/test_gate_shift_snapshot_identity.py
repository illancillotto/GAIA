"""The mobile snapshot carries active shifts and explicit revocations."""

from datetime import UTC, date, datetime

from test_gate_mobile_sync import _build_session, _seed_presenze_daily_record

from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.services.shift_assignments import (
    ShiftAssignmentOrigin,
    record_shift_assignment,
)
from app.modules.presenze.shift_worker_schemas import ShiftWorkerAssignmentRequest
from app.services.gate_mobile_sync import build_presenze_giornaliere_push_payload


def test_snapshot_exposes_type_source_and_revocation():
    db = _build_session()
    try:
        record_id = _seed_presenze_daily_record(db)
        record = db.get(PresenzeDailyRecord, record_id)
        day = build_presenze_giornaliere_push_payload(db, month="2026-07")["records"][0]
        assert day["shift_worker_type"] == "none"
        assert day["shift_worker_source"] is None
        for kind, command in [("telecontrollo", "assigned"), ("none", "revoked")]:
            record_shift_assignment(
                db,
                record,
                ShiftWorkerAssignmentRequest(
                    shift_worker_type=kind,
                    date_from=date(2026, 7, 1),
                    date_to=date(2026, 7, 31),
                ),
                origin=ShiftAssignmentOrigin(
                    77, "gate", datetime(2026, 7, 10, tzinfo=UTC), command
                ),
            )
            day = build_presenze_giornaliere_push_payload(db, month="2026-07")["records"][0]
            assert day["shift_worker_type"] == kind
            assert day["shift_worker_source"] == "gate"
            assert day["shift_rules_version"]
    finally:
        db.close()
