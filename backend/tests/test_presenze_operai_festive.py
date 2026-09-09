from datetime import date, time
from uuid import uuid4

import pytest

from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
    PresenzeHoliday,
)
from app.modules.presenze.services.schedule_engine import ScheduleContext, classify_daily_record


@pytest.mark.parametrize("day", [14, 16])
@pytest.mark.parametrize("holiday_kind,festive", [("ordinary", True), ("suppressed", False)])
@pytest.mark.parametrize(
    "exit_time,ordinary,extra", [(time(13), 420, 0), (time(13, 24), 420, 24), (time(12), 360, 0)]
)
def test_operai_holiday_preserves_ordinary_and_extra_totals(
    day, holiday_kind, festive, exit_time, ordinary, extra
):
    collaborator = PresenzeCollaborator(
        id=uuid4(), employee_code="1399", name="Operaio", contract_kind="operaio"
    )
    record = PresenzeDailyRecord(
        id=uuid4(),
        collaborator_id=collaborator.id,
        work_date=date(2026, 8, day),
        schedule_code="OPE0613",
        km_value=50,
        reperibilita_unit="days",
        reperibilita_quantity=1,
    )
    holiday = PresenzeHoliday(
        holiday_date=record.work_date, label="Festivo", holiday_kind=holiday_kind
    )
    context = ScheduleContext(
        holidays_by_key={(record.work_date, None): [holiday]},
        assignments_by_collaborator={},
        templates_by_id={},
        rules_by_template_id={},
    )
    punches = [
        PresenzeDailyPunch(
            daily_record_id=record.id, sequence=1, entry_time=time(6), exit_time=exit_time
        )
    ]

    result = classify_daily_record(collaborator, record, punches, context)

    # Sunday remains festive even when a calendar entry is suppressed.
    festive = festive or day == 16
    assert result.source == "operai_formula"
    assert result.ordinary_minutes == ordinary
    assert (result.extra_minutes or 0) == extra
    assert result.special_day is festive
    assert result.shift_festive_day_minutes == (ordinary if festive else 0)
    assert result.overtime_festive_minutes == (extra if festive else 0)
    assert result.overtime_day_minutes == (0 if festive else extra)
    assert result.overtime_night_minutes == result.overtime_festive_night_minutes == 0
    assert record.km_value == 50
    assert (record.reperibilita_unit, record.reperibilita_quantity) == ("days", 1)


def test_imported_extra_without_punches_remains_available():
    collaborator = PresenzeCollaborator(
        id=uuid4(), employee_code="1", name="Impiegato", contract_kind="impiegato"
    )
    record = PresenzeDailyRecord(
        id=uuid4(),
        collaborator_id=collaborator.id,
        work_date=date(2026, 8, 13),
        ordinary_minutes=420,
        straordinario_minutes=30,
        raw_payload_json={"detail_status": "OK"},
    )
    result = classify_daily_record(collaborator, record, [], None)
    assert result.ordinary_minutes == 420
    assert result.extra_minutes == result.overtime_day_minutes == 30
