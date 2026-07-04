from __future__ import annotations

from datetime import date, datetime, time, timezone
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest
from fastapi import HTTPException

from app.modules.presenze import router
from app.modules.presenze.schemas import PresenzeBankHoursCompensationSummaryResponse


class _DbWithoutCollaborator:
    def get(self, *_args, **_kwargs):
        return None


def test_resolve_export_template_path_supports_existing_normalized_and_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    explicit = tmp_path / "Giornaliere" / "Giornaliere_2026_803_1.xlsm"
    explicit.parent.mkdir(parents=True)
    explicit.write_text("ok", encoding="utf-8")

    normalized = router.resolve_export_template_path(str(explicit))
    assert normalized == explicit

    typo_input = str(explicit).replace("/Giornaliere/", "/Giornalere/").replace("Giornaliere_", "Giornalere_")
    typo_resolved = router.resolve_export_template_path(typo_input)
    assert typo_resolved == explicit

    default_template = tmp_path / "default.xlsm"
    default_template.write_text("default", encoding="utf-8")
    monkeypatch.setattr(router, "DEFAULT_TEMPLATE_PATH", default_template)
    assert router.resolve_export_template_path(None) == default_template


def test_resolve_export_template_path_raises_when_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "Giornalere" / "Giornalere_2026_803_1.xlsm"

    with pytest.raises(HTTPException, match="Template XLSM not found"):
        router.resolve_export_template_path(str(missing))

    monkeypatch.setattr(router, "DEFAULT_TEMPLATE_PATH", tmp_path / "missing-default.xlsm")
    with pytest.raises(HTTPException, match="Template XLSM not found"):
        router.resolve_export_template_path(None)


def test_bootstrap_preset_lookup_helpers_are_case_insensitive_on_template_code() -> None:
    preset = router._preset_by_key("impiegati_rientro")
    assert preset is not None
    assert preset.template_code == "IMP1_RIENTRO"

    by_code = router._preset_by_template_code(" imp1_rientro ")
    assert by_code is not None
    assert by_code.preset_key == "impiegati_rientro"

    assert router._preset_by_key("unknown") is None
    assert router._preset_by_template_code("unknown") is None


def test_build_bank_hours_liquidation_guidance_covers_no_balance_and_no_overtime_cases() -> None:
    config = SimpleNamespace(
        allow_derived_profile=False,
        include_overtime_day=True,
        include_overtime_night=False,
        include_overtime_festive=False,
        include_overtime_festive_night=False,
        min_suggested_minutes=60,
    )
    summary = PresenzeBankHoursCompensationSummaryResponse(overtime_day_minutes_total=120)

    no_balance = router._build_bank_hours_liquidation_guidance(
        available_debit_minutes=0,
        standard_daily_minutes=420,
        contract_profile_source="explicit",
        compensation_summary=summary,
        guidance_config=config,
    )
    assert no_balance.reason_code == "no_available_balance"
    assert no_balance.liquidable_minutes == 0
    assert "non ha saldo banca ore disponibile" in no_balance.notes[0]

    no_overtime = router._build_bank_hours_liquidation_guidance(
        available_debit_minutes=120,
        standard_daily_minutes=420,
        contract_profile_source="explicit",
        compensation_summary=PresenzeBankHoursCompensationSummaryResponse(),
        guidance_config=config,
    )
    assert no_overtime.reason_code == "no_overtime_candidate"
    assert no_overtime.keep_in_bank_minutes == 120
    assert no_overtime.candidate_minutes_from_overtime == 0


def test_build_bank_hours_liquidation_guidance_covers_missing_profile_threshold_and_partial_keep() -> None:
    config = SimpleNamespace(
        allow_derived_profile=False,
        include_overtime_day=True,
        include_overtime_night=True,
        include_overtime_festive=True,
        include_overtime_festive_night=True,
        min_suggested_minutes=60,
    )
    summary = PresenzeBankHoursCompensationSummaryResponse(
        overtime_day_minutes_total=20,
        overtime_night_minutes_total=10,
        overtime_festive_minutes_total=5,
        overtime_festive_night_minutes_total=5,
        ordinary_night_bonus_rate=15,
    )

    missing_profile = router._build_bank_hours_liquidation_guidance(
        available_debit_minutes=120,
        standard_daily_minutes=None,
        contract_profile_source="missing",
        compensation_summary=summary,
        guidance_config=config,
    )
    assert missing_profile.reason_code == "partial_review"
    assert missing_profile.review_minutes == 40
    assert missing_profile.keep_in_bank_minutes == 80
    assert missing_profile.requires_profile_review is True
    assert any("profilo contrattuale non e completo" in note for note in missing_profile.notes)
    assert any("15%" in note for note in missing_profile.notes)

    below_threshold = router._build_bank_hours_liquidation_guidance(
        available_debit_minutes=120,
        standard_daily_minutes=420,
        contract_profile_source="explicit",
        compensation_summary=summary,
        guidance_config=config,
    )
    assert below_threshold.reason_code == "partial_review"
    assert below_threshold.liquidable_minutes == 0
    assert below_threshold.review_minutes == 40
    assert below_threshold.suggested_days == 0.0
    assert any("soglia minima configurata" in note for note in below_threshold.notes)

    partial_keep = router._build_bank_hours_liquidation_guidance(
        available_debit_minutes=200,
        standard_daily_minutes=420,
        contract_profile_source="explicit",
        compensation_summary=PresenzeBankHoursCompensationSummaryResponse(
            overtime_day_minutes_total=120,
            ordinary_night_bonus_rate=10,
        ),
        guidance_config=SimpleNamespace(
            allow_derived_profile=True,
            include_overtime_day=True,
            include_overtime_night=False,
            include_overtime_festive=False,
            include_overtime_festive_night=False,
            min_suggested_minutes=0,
        ),
    )
    assert partial_keep.reason_code == "ok"
    assert partial_keep.liquidable_minutes == 120
    assert partial_keep.keep_in_bank_minutes == 80
    assert partial_keep.suggested_days == 0.29
    assert "overtime_day" in partial_keep.included_overtime_buckets
    assert any("quota del saldo resta in banca ore" in note for note in partial_keep.notes)


def test_serialize_daily_record_exposes_detail_punch_rows() -> None:
    record_id = uuid.uuid4()
    collaborator_id = uuid.uuid4()
    payload = {
        "detail_punch_rows": [
            {"Ora": "06:55", "EU": "E", "Term": "FENO-Fenoso"},
            {"Ora": "10:30", "EU": "U", "Term": "FENO-Fenoso"},
            {"Ora": "10:45", "EU": "E", "Term": "FENO-Fenoso"},
            {"Ora": "12:30", "EU": "U", "Term": "FENO-Fenoso"},
        ],
        "detail_status": "Giornata anomala",
    }
    record = SimpleNamespace(
        id=record_id,
        collaborator_id=collaborator_id,
        owner_user_id=1,
        application_user_id=None,
        work_date=date(2026, 5, 16),
        schedule_code="OPESAB",
        teo_minutes=390,
        ordinary_minutes=330,
        absence_minutes=60,
        justified_minutes=0,
        maggiorazione_minutes=15,
        mpe_minutes=45,
        straordinario_minutes=75,
        km_value=None,
        trasferta_minutes=None,
        trasferta_montano=False,
        reperibilita_unit="none",
        reperibilita_quantity=None,
        override_straordinario_minutes=None,
        override_mpe_minutes=None,
        manual_note=None,
        request_type=None,
        request_description=None,
        request_status=None,
        request_authorized_by=None,
        resolved_absence_cause=None,
        validation_status="pending",
        validated_by_user_id=None,
        validated_at=None,
        validation_note=None,
        stato="Giornata anomala",
        evidenze="Ore mancanti",
        raw_weekday="V",
        raw_payload_json=payload,
        source_job_id=None,
        created_at=datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc),
    )
    punches = [
        SimpleNamespace(
            id=uuid.uuid4(),
            daily_record_id=record_id,
            sequence=1,
            entry_time=time(6, 55),
            exit_time=time(12, 30),
            terminal_label=None,
        )
    ]
    classification = SimpleNamespace(
        night_minutes=0,
        festive_minutes=0,
        festive_night_minutes=0,
        ordinary_night_minutes=0,
        overtime_day_minutes=0,
        overtime_night_minutes=0,
        overtime_festive_minutes=0,
        overtime_festive_night_minutes=0,
        shift_festive_day_minutes=0,
        shift_night_minutes=0,
        shift_festive_night_minutes=0,
        special_day=False,
        holiday_kind=None,
        grants_recovery_day=False,
    )

    serialized = router._serialize_daily_record(
        _DbWithoutCollaborator(),
        record,
        punches=punches,
        classification=classification,
        monthly_night_bonus={
            "monthly_night_shift_count": 0,
            "ordinary_night_bonus_threshold_met": False,
            "ordinary_night_bonus_rate": None,
        },
    )

    assert [row.time for row in serialized.detail_punch_rows] == ["06:55", "10:30", "10:45", "12:30"]
    assert [row.direction for row in serialized.detail_punch_rows] == ["E", "U", "E", "U"]
    assert all(row.terminal_label == "FENO-Fenoso" for row in serialized.detail_punch_rows)
    assert serialized.punches[0].terminal_label == "FENO-Fenoso"


def test_serialize_daily_record_exposes_inaz_detail_punch_rows_with_orario_verso_shape() -> None:
    record_id = uuid.uuid4()
    collaborator_id = uuid.uuid4()
    payload = {
        "detail_punch_rows": [
            {"Orario": "07:25", "Verso": "E", "TipoTimbratura": "SW", "kterminali": "0", "RicOrario": "07:25"},
            {"Orario": "10:23", "Verso": "U", "TipoTimbratura": "TR", "kterminali": "CBON-Ingresso CBO", "RicOrario": "10:23"},
            {"Orario": "12:51", "Verso": "E", "TipoTimbratura": "TR", "kterminali": "CBON-Ingresso CBO", "RicOrario": "12:51"},
        ],
        "detail_status": "Giornata regolare",
    }
    record = SimpleNamespace(
        id=record_id,
        collaborator_id=collaborator_id,
        owner_user_id=1,
        application_user_id=None,
        work_date=date(2026, 6, 3),
        schedule_code="IMP1",
        teo_minutes=445,
        ordinary_minutes=237,
        absence_minutes=0,
        justified_minutes=148,
        maggiorazione_minutes=0,
        mpe_minutes=247,
        straordinario_minutes=0,
        km_value=None,
        trasferta_minutes=None,
        trasferta_montano=False,
        reperibilita_unit="none",
        reperibilita_quantity=None,
        override_straordinario_minutes=None,
        override_mpe_minutes=None,
        manual_note=None,
        request_type="Var. Timbrature",
        request_description="Inserimento - 07:25 E",
        request_status="ACC",
        request_authorized_by="SCANU MAURIZIO",
        resolved_absence_cause=None,
        validation_status="pending",
        validated_by_user_id=None,
        validated_at=None,
        validation_note=None,
        stato="Giornata regolare",
        evidenze=None,
        raw_weekday="M",
        raw_payload_json=payload,
        source_job_id=None,
        created_at=datetime(2026, 6, 3, 8, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 3, 8, 0, tzinfo=timezone.utc),
    )
    punches = [
        SimpleNamespace(
            id=uuid.uuid4(),
            daily_record_id=record_id,
            sequence=1,
            entry_time=time(7, 25),
            exit_time=time(10, 23),
            terminal_label=None,
        )
    ]
    classification = SimpleNamespace(
        night_minutes=0,
        festive_minutes=0,
        festive_night_minutes=0,
        ordinary_night_minutes=0,
        overtime_day_minutes=0,
        overtime_night_minutes=0,
        overtime_festive_minutes=0,
        overtime_festive_night_minutes=0,
        shift_festive_day_minutes=0,
        shift_night_minutes=0,
        shift_festive_night_minutes=0,
        special_day=False,
        holiday_kind=None,
        grants_recovery_day=False,
    )

    serialized = router._serialize_daily_record(
        _DbWithoutCollaborator(),
        record,
        punches=punches,
        classification=classification,
        monthly_night_bonus={
            "monthly_night_shift_count": 0,
            "ordinary_night_bonus_threshold_met": False,
            "ordinary_night_bonus_rate": None,
        },
    )

    assert [row.time for row in serialized.detail_punch_rows] == ["07:25", "10:23", "12:51"]
    assert [row.direction for row in serialized.detail_punch_rows] == ["E", "U", "E"]
    assert [row.terminal_label for row in serialized.detail_punch_rows] == ["0", "CBON-Ingresso CBO", "CBON-Ingresso CBO"]
    assert serialized.punches[0].terminal_label == "0"
