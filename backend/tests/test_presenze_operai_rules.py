from __future__ import annotations

from datetime import date
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord
from app.modules.presenze.services.operai_rules import (
    covered_operai_absence_minutes,
    default_operai_rule_configs,
    ensure_operai_rule_configs,
    load_operai_rule_configs,
    normalize_operai_group,
    resolve_operai_schedule_code,
    resolve_operai_rule,
    saturday_ordinal_in_month,
    serialize_default_operai_rule_payloads,
)


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _db_session() -> Session:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_default_operai_rule_configs_cover_agrario_and_catasto_groups() -> None:
    configs = default_operai_rule_configs()

    assert len(configs) == 2
    assert configs[0].operai_group == "agrario"
    assert configs[0].saturday_week_ordinals == (1, 3)
    assert configs[0].saturday_expected_minutes == 390
    assert configs[1].operai_group == "catasto_magazzino"
    assert configs[1].saturday_week_ordinals == ()
    assert configs[1].saturday_expected_minutes == 360


def test_resolve_operai_rule_uses_group_specific_saturday_configuration() -> None:
    configs = default_operai_rule_configs()
    agrario = PresenzeCollaborator(id=uuid.uuid4(), employee_code="1", name="Agrario", contract_kind="operaio", operai_group="agrario")
    catasto = PresenzeCollaborator(id=uuid.uuid4(), employee_code="2", name="Catasto", contract_kind="operaio", operai_group="catasto_magazzino")

    first_saturday = PresenzeDailyRecord(id=uuid.uuid4(), collaborator_id=agrario.id, work_date=date(2026, 6, 6), schedule_code="OPESAB")
    first_saturday_catasto = PresenzeDailyRecord(id=uuid.uuid4(), collaborator_id=catasto.id, work_date=date(2026, 6, 6), schedule_code="OPESAB")

    agrario_rule = resolve_operai_rule(agrario, first_saturday, configs)
    catasto_rule = resolve_operai_rule(catasto, first_saturday_catasto, configs)

    assert saturday_ordinal_in_month(first_saturday.work_date) == 1
    assert saturday_ordinal_in_month(first_saturday_catasto.work_date) == 1
    assert agrario_rule is not None
    assert agrario_rule.expected_minutes == 390
    assert agrario_rule.saturday_is_scheduled is True
    assert catasto_rule is not None
    assert catasto_rule.expected_minutes == 360
    assert catasto_rule.saturday_is_scheduled is True


def test_resolve_operai_rule_marks_unscheduled_saturday_with_zero_expected_minutes() -> None:
    configs = default_operai_rule_configs()
    agrario = PresenzeCollaborator(id=uuid.uuid4(), employee_code="1", name="Agrario", contract_kind="operaio", operai_group="agrario")
    second_saturday = PresenzeDailyRecord(id=uuid.uuid4(), collaborator_id=agrario.id, work_date=date(2026, 6, 13), schedule_code="OPESAB")
    catasto = PresenzeCollaborator(id=uuid.uuid4(), employee_code="2", name="Catasto", contract_kind="operaio", operai_group="catasto_magazzino")
    second_saturday_catasto = PresenzeDailyRecord(id=uuid.uuid4(), collaborator_id=catasto.id, work_date=date(2026, 6, 13), schedule_code="OPESAB")

    resolved = resolve_operai_rule(agrario, second_saturday, configs)
    resolved_catasto = resolve_operai_rule(catasto, second_saturday_catasto, configs)

    assert resolved is not None
    assert resolved.expected_minutes == 0
    assert resolved.saturday_is_scheduled is False
    assert resolved_catasto is not None
    assert resolved_catasto.expected_minutes == 360
    assert resolved_catasto.saturday_is_scheduled is True


def test_covered_operai_absence_minutes_counts_only_allowed_causes() -> None:
    configs = default_operai_rule_configs()
    agrario = PresenzeCollaborator(id=uuid.uuid4(), employee_code="1", name="Agrario", contract_kind="operaio", operai_group="agrario")
    ferie_record = PresenzeDailyRecord(
        id=uuid.uuid4(),
        collaborator_id=agrario.id,
        work_date=date(2026, 6, 6),
        schedule_code="OPESAB",
        resolved_absence_cause="ferie",
        absence_minutes=390,
        justified_minutes=10,
    )
    malattia_record = PresenzeDailyRecord(
        id=uuid.uuid4(),
        collaborator_id=agrario.id,
        work_date=date(2026, 6, 6),
        schedule_code="OPESAB",
        resolved_absence_cause="malattia",
        absence_minutes=390,
    )

    ferie_rule = resolve_operai_rule(agrario, ferie_record, configs)
    malattia_rule = resolve_operai_rule(agrario, malattia_record, configs)

    assert covered_operai_absence_minutes(ferie_record, ferie_rule) == 390
    assert covered_operai_absence_minutes(malattia_record, malattia_rule) == 0


def test_operai_rule_helpers_cover_normalization_and_payload_serialization() -> None:
    payloads = serialize_default_operai_rule_payloads()

    assert normalize_operai_group(" AGRARIO ") == "agrario"
    assert normalize_operai_group(None) is None
    assert normalize_operai_group("   ") is None
    assert normalize_operai_group("non_valido") is None
    assert payloads[0]["weekday_schedule_codes"] == ["OPE0714", "OPE0736", "OP_5.3_12.3"]
    assert payloads[1]["saturday_week_ordinals"] == []


def test_resolve_operai_schedule_code_reads_detail_when_explicit_schedule_is_missing() -> None:
    record = PresenzeDailyRecord(
        id=uuid.uuid4(),
        collaborator_id=uuid.uuid4(),
        work_date=date(2026, 6, 8),
        raw_payload_json={"detail_programmed_schedule": "OP_5.3_12.3 - Operai estate"},
    )

    assert resolve_operai_schedule_code(record) == "OP_5.3_12.3"


def test_operai_rule_configs_persist_defaults_and_reload_normalized_values() -> None:
    db = _db_session()
    try:
        created = ensure_operai_rule_configs(db)
        db.commit()

        assert [item.code for item in created] == [
            "OPERAI_AGRARIO_1E3SAB",
            "OPERAI_CATASTO_MAGAZZINO_ALTERNATI",
        ]

        created[0].weekday_schedule_codes = [" ope0714 ", "ope0736", "", "OP_5.3_12.3"]
        created[0].saturday_schedule_codes = [" opesab ", "OSAB5.3_12.3", ""]
        created[0].saturday_week_ordinals = [0, 3, 3, 6, 1]
        created[0].allowed_absence_causes = [" FERIE ", "permesso", "ferie", " "]
        created[0].operai_group = " AGRARIO "
        db.commit()

        loaded = load_operai_rule_configs(db)

        assert len(loaded) == 2
        assert loaded[0].weekday_schedule_codes == ("OPE0714", "OPE0736", "OP_5.3_12.3")
        assert loaded[0].saturday_schedule_codes == ("OPESAB", "OSAB5.3_12.3")
        assert loaded[0].saturday_week_ordinals == (1, 3)
        assert loaded[0].allowed_absence_causes == ("ferie", "permesso")
        assert loaded[0].operai_group == "agrario"

        second_pass = ensure_operai_rule_configs(db)
        assert len(second_pass) == 2
    finally:
        db.close()


def test_load_operai_rule_configs_falls_back_to_defaults_without_rows() -> None:
    db = _db_session()
    try:
        loaded = load_operai_rule_configs(db)
        assert loaded == default_operai_rule_configs()
    finally:
        db.close()


def test_resolve_operai_rule_covers_non_operai_missing_schedule_and_legacy_fallback() -> None:
    operaio = PresenzeCollaborator(id=uuid.uuid4(), employee_code="1", name="Operaio", contract_kind="operaio")
    impiegato = PresenzeCollaborator(id=uuid.uuid4(), employee_code="2", name="Impiegato", contract_kind="impiegato")

    missing_schedule = PresenzeDailyRecord(id=uuid.uuid4(), collaborator_id=operaio.id, work_date=date(2026, 6, 8))
    weekday = PresenzeDailyRecord(id=uuid.uuid4(), collaborator_id=operaio.id, work_date=date(2026, 6, 8), schedule_code="OPE0714")
    saturday = PresenzeDailyRecord(id=uuid.uuid4(), collaborator_id=operaio.id, work_date=date(2026, 6, 27), schedule_code="OSAB5.3_12.3")
    invalid_group = PresenzeCollaborator(
        id=uuid.uuid4(),
        employee_code="3",
        name="Operaio Altro",
        contract_kind="operaio",
        operai_group="gruppo_non_supportato",
    )

    assert resolve_operai_rule(None, weekday) is None
    assert resolve_operai_rule(impiegato, weekday) is None
    assert resolve_operai_rule(operaio, missing_schedule) is None

    weekday_fallback = resolve_operai_rule(operaio, weekday)
    saturday_fallback = resolve_operai_rule(invalid_group, saturday)

    assert weekday_fallback is not None
    assert weekday_fallback.rule.code == "OPERAI_LEGACY_FALLBACK"
    assert weekday_fallback.expected_minutes == 420
    assert weekday_fallback.saturday_is_scheduled is False
    assert saturday_fallback is not None
    assert saturday_fallback.rule.code == "OPERAI_LEGACY_FALLBACK"
    assert saturday_fallback.expected_minutes == 420
    assert saturday_fallback.saturday_is_scheduled is True


def test_resolve_operai_rule_uses_weekday_codes_from_active_configs() -> None:
    configs = default_operai_rule_configs()
    agrario = PresenzeCollaborator(
        id=uuid.uuid4(),
        employee_code="1",
        name="Agrario",
        contract_kind="operaio",
        operai_group="agrario",
    )
    weekday = PresenzeDailyRecord(
        id=uuid.uuid4(),
        collaborator_id=agrario.id,
        work_date=date(2026, 6, 8),
        schedule_code="OP_5.3_12.3",
    )
    other_schedule = PresenzeDailyRecord(
        id=uuid.uuid4(),
        collaborator_id=agrario.id,
        work_date=date(2026, 6, 8),
        schedule_code="ALTRO",
    )

    resolved = resolve_operai_rule(agrario, weekday, configs)
    resolved_ope0736 = resolve_operai_rule(
        agrario,
        PresenzeDailyRecord(
            id=uuid.uuid4(),
            collaborator_id=agrario.id,
            work_date=date(2026, 6, 10),
            schedule_code="OPE0736",
        ),
        configs,
    )

    assert resolved is not None
    assert resolved.rule.code == "OPERAI_AGRARIO_1E3SAB"
    assert resolved.expected_minutes == 420
    assert resolved.saturday_is_scheduled is False
    assert resolved_ope0736 is not None
    assert resolved_ope0736.rule.code == "OPERAI_AGRARIO_1E3SAB"
    assert resolved_ope0736.expected_minutes == 420
    assert resolve_operai_rule(agrario, other_schedule, configs) is None


def test_covered_operai_absence_minutes_returns_zero_without_resolved_rule() -> None:
    record = PresenzeDailyRecord(
        id=uuid.uuid4(),
        collaborator_id=uuid.uuid4(),
        work_date=date(2026, 6, 8),
        schedule_code="OPE0714",
        resolved_absence_cause="ferie",
        absence_minutes=120,
    )

    assert covered_operai_absence_minutes(record, None) == 0
