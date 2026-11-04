from copy import deepcopy
from datetime import date, time
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.modules.me.router import common
from app.modules.me.router.common import _daily_record_effective_extra_minutes
from app.modules.me.router.routes.summary import get_me_summary
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
)
from app.modules.presenze.router.helpers.daily_records import _serialize_daily_record
from app.modules.presenze.services.dashboard_projection import _DashboardAggregation
from app.modules.presenze.services.impiegati_pending_overtime import effective_inaz_mpe_minutes
from app.modules.presenze.services.operai_daily_policy import effective_extra_values
from app.modules.presenze.services.schedule_engine import classify_daily_record
from app.modules.presenze.services.straordinari_export_job import (
    effective_extra_minutes,
    list_straordinari_available_months,
    list_straordinari_preview_items,
    resolve_straordinari_duration,
)

DAY = date(2026, 10, 30)
DETAIL = {
    "detail_status": "Giornata da calcolare",
    "detail_effective_schedule": "IMP1 - Impiegati Flessibile",
    "detail_time_slots": "07:30 - 13:55",
    "detail_day_summary": {"Ore Ordinarie": "03:05", "Maggior presenza": "00:15"},
    "punches": [{"entry": "10:50", "exit": "14:10"}, {"entry": "14:20", "exit": "18:24"}],
    "detail_requests": [
        {
            "KEvento": "PermBO - Permesso Banca Ore",
            "Dalle": "07:30",
            "Alle": "10:30",
            "Stato": "RIC",
        }
    ],
}


def _record(**values):
    return PresenzeDailyRecord(
        **{
            "id": uuid4(),
            "collaborator_id": uuid4(),
            "work_date": DAY,
            "schedule_code": "IMP1",
            "teo_minutes": 385,
            "ordinary_minutes": 185,
            "absence_minutes": 200,
            "trasferta_montano": False,
            "mpe_minutes": 15,
            "stato": "Giornata da calcolare",
            "request_description": "PermBO - Permesso Banca Ore",
            "request_status": "RIC",
            "raw_payload_json": deepcopy(DETAIL),
            **values,
        }
    )


def _punches(record):
    return [
        PresenzeDailyPunch(
            daily_record_id=record.id,
            sequence=sequence,
            entry_time=time.fromisoformat(row["entry"]),
            exit_time=time.fromisoformat(row["exit"]),
        )
        for sequence, row in enumerate(record.raw_payload_json["punches"], 1)
    ]


def test_october_30_replaces_provisional_morning_mpe_with_four_hours_four_minutes():
    record = _record()
    original = deepcopy(record.raw_payload_json)
    person = PresenzeCollaborator(id=record.collaborator_id, contract_kind="impiegato")
    punches = _punches(record)

    classification = classify_daily_record(person, record, punches, None)
    values = effective_extra_values(record, classification)
    duration = resolve_straordinari_duration(record, punches)

    assert classification.extra_minutes == classification.overtime_day_minutes == 244
    assert values["effective_extra_minutes"] == values["effective_mpe_minutes"] == 244
    assert _daily_record_effective_extra_minutes(record) == effective_extra_minutes(record) == 244
    assert duration.duration_minutes == duration.original_duration_minutes == 244
    assert duration.pause_deduction_minutes == 0
    assert (record.ordinary_minutes, record.absence_minutes, record.mpe_minutes) == (185, 200, 15)
    assert record.raw_payload_json == original
    aggregation = _DashboardAggregation()
    aggregation.add(record, classification, uses_recovery_day=False)
    assert aggregation.total("extra") == aggregation.total("mpe") == 244


@pytest.mark.parametrize(
    "raw_changes,record_changes",
    [
        ({"detail_status": "Giornata regolare"}, {}),
        ({"detail_status": "Giornata anomala"}, {}),
        ({"detail_status": None}, {"stato": None}),
        ({"detail_effective_schedule": "OPE0714"}, {}),
        ({"detail_effective_schedule": None}, {"schedule_code": None}),
        ({"detail_time_slots": "07:30 - 13:55 / 14:25 - 17:40"}, {}),
        ({"detail_time_slots": None}, {}),
        ({"detail_time_slots": "13:55 - 07:30"}, {}),
        ({"detail_time_slots": "25:00 - 26:00"}, {}),
        ({}, {"override_mpe_minutes": 0}),
        ({}, {"override_straordinario_minutes": 0}),
        ({}, {"straordinario_minutes": 60}),
    ],
)
def test_accounted_days_other_schedules_and_adjustments_keep_imported_mpe(
    raw_changes, record_changes
):
    record = _record(**record_changes)
    record.raw_payload_json.update(raw_changes)
    assert effective_inaz_mpe_minutes(record) == 15


@pytest.mark.parametrize("raw", [None, [], {}, {"punches": []}])
def test_absent_or_legacy_snapshots_keep_imported_mpe(raw):
    assert effective_inaz_mpe_minutes(_record(raw_payload_json=raw)) == 15


@pytest.mark.parametrize(
    "rows",
    [
        None,
        {},
        [],
        [None],
        [{"entry": None, "exit": "14:10"}],
        [{"entry": 1050, "exit": "14:10"}],
        [{"entry": "invalid", "exit": "14:10"}],
        [{"entry": "10:50"}],
        [{"entry": "14:10", "exit": "10:50"}],
        [{"entry": "14:10", "exit": "14:10"}],
        [{"entry": "22:00", "exit": "06:00"}],
        [{"entry": "10:50", "exit": "14:30"}, {"entry": "14:20", "exit": "18:24"}],
        [{"entry": "14:20", "exit": "18:24"}],
        [{"entry": "10:50", "exit": "18:24"}],
        [{"entry": "10:50", "exit": "13:00"}, {"entry": "14:20", "exit": "18:24"}],
        [{"entry": "10:50", "exit": "14:20"}, {"entry": "14:20", "exit": "18:24"}],
    ],
)
def test_unproven_afternoons_do_not_replace_imported_totals(rows):
    record = _record()
    record.raw_payload_json["punches"] = rows
    assert effective_inaz_mpe_minutes(record) == 15


def test_fallback_status_and_schedule_and_multiple_afternoon_pairs():
    record = _record(schedule_code="IMP2", mpe_minutes=None)
    record.raw_payload_json.update(
        detail_status=None,
        detail_effective_schedule=None,
        punches=[
            {"entry": "17:00", "exit": "18:24"},
            {"entry": "10:50", "exit": "14:10"},
            {"entry": "14:20", "exit": "16:00"},
        ],
    )
    assert effective_inaz_mpe_minutes(record) == 184


def test_administrative_adjustments_keep_priority_in_every_consumer():
    record = _record(override_mpe_minutes=0, override_straordinario_minutes=60)
    classification = classify_daily_record(
        PresenzeCollaborator(id=record.collaborator_id, contract_kind="impiegato"),
        record,
        _punches(record),
        None,
    )
    assert effective_extra_values(record, classification)["effective_extra_minutes"] == 60
    assert classification.extra_minutes == 60
    assert _daily_record_effective_extra_minutes(record) == effective_extra_minutes(record) == 60


def test_self_service_serialization_totals_and_export_preview_agree():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            user = ApplicationUser(
                username="pending_overtime",
                email="pending_overtime@example.local",
                password_hash="unused",
                role="viewer",
                is_active=True,
                module_presenze=True,
            )
            db.add(user)
            db.flush()
            person = PresenzeCollaborator(
                id=uuid4(),
                application_user_id=user.id,
                employee_code="test-pending",
                name="Test impiegato",
                contract_kind="impiegato",
            )
            db.add(person)
            db.flush()
            record = _record(collaborator_id=person.id, application_user_id=user.id)
            db.add(record)
            db.flush()
            db.add_all(_punches(record))
            db.flush()

            serialized = _serialize_daily_record(db, record)
            assert common._get_mapped_collaborator_or_409(db, user) is person
            summary = get_me_summary(db, user, period_start=DAY, period_end=DAY)
            _, preview = list_straordinari_preview_items(
                db, collaborator_id=person.id, period_start=DAY.replace(day=1)
            )

            assert serialized.effective_extra_minutes == serialized.effective_mpe_minutes == 244
            assert summary.extra_minutes == 244
            assert len(preview) == 1
            assert preview[0].duration_minutes == 244
            assert (preview[0].start_time, preview[0].end_time) == ("14:20", "18:24")
            assert list_straordinari_available_months(db, collaborator_id=person.id) == [
                DAY.replace(day=1)
            ]
    finally:
        engine.dispose()


def test_missing_pdf_converter_and_temporary_export_cleanup(tmp_path, monkeypatch):
    monkeypatch.setattr(common.shutil, "which", lambda _name: None)
    with pytest.raises(HTTPException) as exc:
        common._convert_xlsx_to_pdf(tmp_path / "straordinari.xlsx", tmp_path)
    assert exc.value.status_code == 503
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    (export_dir / "straordinari.xlsx").write_bytes(b"temporary export")
    common._cleanup_temp_dir(str(export_dir))
    assert not export_dir.exists()
    common._cleanup_temp_dir(str(export_dir))
