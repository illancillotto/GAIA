"""Unworked avventizio days are AG, without inventing attendance or paid time."""

from datetime import date, time
from types import SimpleNamespace

import pytest
from sqlalchemy import event
from test_presenze_api import (  # noqa: F401
    TestingSessionLocal,
    _create_user,
    _login,
    client,
    setup_database,
)
from test_presenze_meal_vouchers import _record

from app.modules.presenze.employment_models import PresenzeEmploymentPeriod
from app.modules.presenze.models import PresenzeDailyPunch, PresenzeDailyRecord
from app.modules.presenze.services.avventizio_absence import avventizio_absence_values
from app.modules.presenze.services.employment_periods import employment_period_values
from app.modules.presenze.services.xlsm_export import resolve_export_absence_code


def period(**kwargs):
    return SimpleNamespace(
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 12, 31),
        employment_relationship="avventizio",
        source_document_sha256="a" * 64,
        **kwargs,
    )


def synthetic(**kwargs):
    fields = dict(
        work_date=date(2026, 10, 2),
        employment_periods=[period()],
        resolved_absence_cause=None,
        raw_payload_json={},
        punches=[],
        request_description=None,
    )
    fields.update(kwargs)
    return SimpleNamespace(**fields)


def values(record, *, expected=420, ordinary=0, extra=0, special=False, quality=True):
    classification = SimpleNamespace(
        ordinary_minutes=ordinary, extra_minutes=extra, special_day=special
    )
    q = SimpleNamespace(expected_minutes=expected, notes=("source note",)) if quality else None
    return avventizio_absence_values(record, classification, q, today=date(2026, 11, 6))


def test_ag_is_derived_without_hours_pay_or_source_mutation():
    record = synthetic(absence_minutes=420, resolved_absence_cause="assenza_da_giustificare")
    before = record.__dict__.copy()
    result = values(record)
    assert result["export_absence_code"] == "AG"
    assert result["attendance_note"] == "Assenza di timbrature (Avventizio)"
    assert result["resolved_absence_cause"] == "assenza_giustificata"
    assert result["operational_missing_minutes"] == 0
    assert result["operational_status"] == "ok"
    assert (
        not {"ordinary_minutes", "justified_minutes", "absence_minutes", "paid_days"}
        & result.keys()
    )
    assert record.__dict__ == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("work_date", date(2026, 11, 6)),
        ("work_date", date(2026, 11, 7)),
        ("work_date", date(2025, 12, 31)),
        ("work_date", date(2027, 1, 1)),
        ("punches", [SimpleNamespace(entry_time=time(7), exit_time=None)]),
        ("resolved_absence_cause", "ferie"),
        ("resolved_absence_cause", "malattia"),
        ("resolved_absence_cause", "permesso"),
        ("resolved_absence_cause", "riposo"),
        ("resolved_absence_cause", "festivita"),
        ("request_description", "IN ATTESA"),
        ("ordinary_minutes", 1),
        ("mpe_minutes", 1),
        ("straordinario_minutes", 1),
        ("override_mpe_minutes", 1),
        ("override_straordinario_minutes", 1),
        ("justified_minutes", 1),
        ("raw_payload_json", {"detail_punch_rows": [{"Ora": "07:00", "EU": "E"}]}),
        ("raw_payload_json", {"detail_requests": [{"Codice": "FERIE"}]}),
    ],
)
def test_preserves_dates_attendance_and_existing_absences(field, value):
    assert not values(synthetic(**{field: value})).get("avventizio_no_punches")


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(expected=0),
        dict(expected=None),
        dict(special=True),
        dict(ordinary=1),
        dict(extra=1),
        dict(quality=False),
    ],
)
def test_requires_a_known_workday_without_work(kwargs):
    assert not values(synthetic(), **kwargs).get("avventizio_no_punches")


def test_relationship_validity_and_expiry_override_legacy_profile():
    record = synthetic(employment_periods=[])
    assert employment_period_values(record) == {}
    record.personnel_profile = SimpleNamespace(
        valid_from=date(2026, 1, 1), valid_to=None, employment_relationship="determinato"
    )
    assert employment_period_values(record) == {"employment_relationship": "determinato"}
    assert not values(record).get("avventizio_no_punches")
    record.employment_periods = [period()]
    assert employment_period_values(record)["employment_valid_to"] == "2026-12-31"
    record.work_date = date(2027, 1, 1)
    assert employment_period_values(record) == {"employment_relationship": None}


def test_keeps_unrelated_technical_errors_visible():
    record = synthetic(raw_payload_json={"detail_error": "sync failed"})
    assert values(record)["operational_status"] == "in_analysis"
    record.raw_payload_json = {"detail_anomalies": [{"code": "OTHER"}]}
    assert values(record)["operational_status"] == "in_analysis"
    record.raw_payload_json = {"detail_anomalies": [{"code": "OREM"}]}
    assert values(record)["operational_status"] == "ok"


def test_real_database_api_matrix_snapshot_export_and_partial_punch():
    user = _create_user("avventizio-admin")
    rid, cid = _record(user.id, extra=0)
    with TestingSessionLocal() as db:
        record = db.get(PresenzeDailyRecord, rid)
        record.ordinary_minutes = 0
        record.teo_minutes = 420
        record.mpe_minutes = 0
        record.straordinario_minutes = 0
        record.raw_payload_json = {}
        db.query(PresenzeDailyPunch).filter_by(daily_record_id=rid).delete()
        db.add(
            PresenzeEmploymentPeriod(
                collaborator_id=cid,
                valid_from=date(2026, 1, 1),
                valid_to=date(2026, 12, 31),
                employment_relationship="avventizio",
                source_document_sha256="a" * 64,
                source_note="Synthetic HR attestation",
                actor_user_id=user.id,
            )
        )
        db.commit()
        projected = avventizio_absence_values(
            record, quality=SimpleNamespace(expected_minutes=420, notes=())
        )
        assert projected["export_absence_code"] == "AG"
        assert resolve_export_absence_code(record) == "AG"
    headers = {"Authorization": "Bearer " + _login(user.username)}
    for path in [
        f"/presenze/giornaliere/{rid}",
        f"/presenze/giornaliere/matrix?collaborator_id={cid}",
    ]:
        response = client.get(path, headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        item = body["items"][0] if "items" in body else body
        assert item["avventizio_no_punches"] is True
        assert item["export_absence_code"] == "AG"
        assert item["operational_missing_minutes"] == 0
        assert item["justified_minutes"] in (None, 0)
    from app.modules.presenze.services.gate_mobile_record_items import build_presenze_record_items

    with TestingSessionLocal() as db:
        record = db.get(PresenzeDailyRecord, rid)
        items, _ = build_presenze_record_items(db, month="2026-10", records=[record])
        assert items[0]["avventizio_no_punches"] is True
        assert items[0]["export_absence_code"] == "AG"
        assert items[0]["employment_valid_to"] == "2026-12-31"
        db.add(PresenzeDailyPunch(daily_record_id=rid, sequence=1, entry_time=time(7)))
        db.commit()
        assert not avventizio_absence_values(record).get("avventizio_no_punches")
        assert resolve_export_absence_code(record) is None


def test_employment_cache_reuses_periods_but_rechecks_each_records_date():
    user = _create_user("avventizio-cache-admin")
    rid, cid = _record(user.id)
    with TestingSessionLocal() as db:
        db.add(
            PresenzeEmploymentPeriod(
                collaborator_id=cid,
                valid_from=date(2026, 10, 1),
                valid_to=date(2026, 10, 1),
                employment_relationship="avventizio",
                source_document_sha256="c" * 64,
                source_note="Synthetic one-day contract",
                actor_user_id=user.id,
            )
        )
        next_day = PresenzeDailyRecord(
            collaborator_id=cid,
            owner_user_id=user.id,
            work_date=date(2026, 10, 2),
            reperibilita_unit="none",
            validation_status="pending",
        )
        db.add(next_day)
        db.commit()
        first_day = db.get(PresenzeDailyRecord, rid)
        queries = []

        def count_contract_queries(_connection, _cursor, statement, *_args):
            if (
                statement.lstrip().upper().startswith("SELECT")
                and "presenze_employment_periods" in statement
            ):
                queries.append(statement)

        engine = db.get_bind()
        event.listen(engine, "before_cursor_execute", count_contract_queries)
        try:
            assert employment_period_values(first_day)["employment_relationship"] == "avventizio"
            assert employment_period_values(next_day) == {"employment_relationship": None}
            assert employment_period_values(first_day)["employment_source_sha256"] == "c" * 64
            assert len(queries) == 1
            assert not db.dirty
            assert not db.new
        finally:
            event.remove(engine, "before_cursor_execute", count_contract_queries)
