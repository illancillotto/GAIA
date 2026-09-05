from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime, time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.application_user import ApplicationUser
from app.modules.presenze import router
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeCollaboratorScheduleAssignment,
    PresenzeDailyRecord,
    PresenzeImportJob,
    PresenzeScheduleRule,
    PresenzeScheduleTemplate,
)
from app.modules.presenze.schemas import PresenzeBankHoursCompensationSummaryResponse


class _DbWithoutCollaborator:
    def get(self, *_args, **_kwargs):
        return None


class _ScalarRows:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None

    def scalar_one(self):
        return self.rows[0]


class _RecordingDb:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.added = []
        self.commits = 0

    def add(self, item):
        self.added.append(item)

    def flush(self):
        return None

    def commit(self):
        self.commits += 1

    def refresh(self, _item):
        return None

    def execute(self, _statement):
        return _ScalarRows(self.rows)

    def scalars(self, _statement):
        return _ScalarRows([])

    def get(self, _model, _identifier):
        return None


class _QueuedDb(_RecordingDb):
    def __init__(self, *row_sets):
        super().__init__()
        self.row_sets = list(row_sets)

    def execute(self, _statement):
        return _ScalarRows(self.row_sets.pop(0))


class _BranchDb(_QueuedDb):
    def __init__(self, *row_sets, stored=None):
        super().__init__(*row_sets)
        self.stored = stored
        self.deleted = []

    def get(self, _model, _identifier):
        return self.stored

    def delete(self, item):
        self.deleted.append(item)



def test_hr_routes_reject_viewers_before_accessing_payload_or_database() -> None:
    viewer = SimpleNamespace(role="viewer", is_super_admin=False)
    adjustment_id = uuid.uuid4()
    calls = [
        lambda: router.get_recovery_dashboard(None, viewer, None),
        lambda: router.list_recovery_adjustments(None, viewer, None),
        lambda: router.create_recovery_adjustment(None, None, viewer, None),
        lambda: router.update_recovery_adjustment(adjustment_id, None, None, viewer, None),
        lambda: router.review_recovery_adjustment(adjustment_id, None, None, viewer, None),
        lambda: router.delete_recovery_adjustment(adjustment_id, None, viewer, None),
        lambda: router.get_bank_hours_dashboard(None, viewer, None),
        lambda: router.get_bank_hours_collaborator_detail(adjustment_id, None, viewer, None),
        lambda: router.list_bank_hours_adjustments(None, viewer, None),
        lambda: router.create_bank_hours_adjustment(None, None, viewer, None),
        lambda: router.update_bank_hours_adjustment(adjustment_id, None, None, viewer, None),
        lambda: router.review_bank_hours_adjustment(adjustment_id, None, None, viewer, None),
        lambda: router.delete_bank_hours_adjustment(adjustment_id, None, viewer, None),
        lambda: router.get_bank_hours_guidance_policy(None, viewer, None),
        lambda: router.put_bank_hours_guidance_policy(None, None, viewer, None),
        lambda: router.get_bank_hours_guidance_policy_history(None, viewer, None),
    ]

    for call in calls:
        with pytest.raises(HTTPException) as exc_info:
            call()
        assert exc_info.value.status_code == 403


def test_adjustment_routes_return_not_found_for_unknown_ids() -> None:
    admin = SimpleNamespace(role="admin", is_super_admin=False, id=1)
    db = _DbWithoutCollaborator()
    adjustment_id = uuid.uuid4()
    calls = [
        lambda: router.update_recovery_adjustment(adjustment_id, None, db, admin, None),
        lambda: router.review_recovery_adjustment(adjustment_id, None, db, admin, None),
        lambda: router.delete_recovery_adjustment(adjustment_id, db, admin, None),
        lambda: router.update_bank_hours_adjustment(adjustment_id, None, db, admin, None),
        lambda: router.review_bank_hours_adjustment(adjustment_id, None, db, admin, None),
        lambda: router.delete_bank_hours_adjustment(adjustment_id, db, admin, None),
    ]

    for call in calls:
        with pytest.raises(HTTPException) as exc_info:
            call()
        assert exc_info.value.status_code == 404


def test_configuration_routes_return_not_found_for_unknown_ids() -> None:
    db = _DbWithoutCollaborator()
    calls = [
        lambda: router.update_presenze_holiday(999, None, db, None, None),
        lambda: router.delete_inaz_holiday(999, db, None, None),
        lambda: router.update_schedule_template(999, None, db, None, None),
        lambda: router.delete_schedule_template(999, db, None, None),
        lambda: router.create_schedule_rule(999, None, db, None, None),
        lambda: router.update_schedule_rule(999, None, db, None, None),
        lambda: router.delete_schedule_rule(999, db, None, None),
        lambda: router.create_collaborator_schedule_assignment(uuid.uuid4(), None, db, None, None),
        lambda: router.delete_schedule_assignment(999, db, None, None),
    ]

    for call in calls:
        with pytest.raises(HTTPException) as exc_info:
            call()
        assert exc_info.value.status_code == 404


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


def test_operai_bootstrap_preset_includes_legacy_inaz_alias_codes() -> None:
    preset = router._preset_by_key("operai_0714_primo_terzo_sabato")
    assert preset is not None
    assert "OPE0613" in preset.source_schedule_codes
    assert "OP_5.3_12.3" in preset.source_schedule_codes
    assert "OSAB5.3_12.3" in preset.source_schedule_codes
    summer_weekday_rules = [
        rule
        for rule in preset.rules
        if rule.ordinary_label == "OP_5.3_12.3" and rule.recurrence_kind == "weekly"
    ]
    weekday_labels = [rule.label for rule in preset.rules if rule.weekday in range(5)]
    assert len(summer_weekday_rules) == 5
    assert "Lun-Ven 07:00-14:00" not in weekday_labels
    assert "Lun 07:00-14:00" in weekday_labels
    assert "Gio 05:30-12:30" in weekday_labels
    assert all(rule.start_time == time(5, 30) and rule.end_time == time(12, 30) for rule in summer_weekday_rules)
    assert all(rule.season_start_month == 6 and rule.season_start_day == 1 for rule in summer_weekday_rules)
    assert all(rule.season_end_month == 9 and rule.season_end_day == 30 for rule in summer_weekday_rules)


def test_schedule_profile_definitions_map_gaia_profiles_to_inaz_templates() -> None:
    by_code = {profile.profile_code: profile for profile in router.SCHEDULE_PROFILE_DEFINITIONS}

    assert "OPE0714_1E3SAB" in by_code["operai_gaia"].template_codes
    assert "OPE0613" in by_code["operai_gaia"].template_codes
    assert "OP_5.3_12.3" in by_code["operai_gaia"].template_codes
    assert "OSAB5.3_12.3" in by_code["operai_gaia"].template_codes
    assert by_code["operai_gaia"].rule_summaries
    assert by_code["impiegati_gaia"].template_codes == ("IMP1_STD", "IMP1_RIENTRO")


def test_suggest_bootstrap_preset_supports_operai_alias_weekday_code() -> None:
    preset, confidence, reason = router._suggest_bootstrap_preset(["OP_5.3_12.3"], {"OP_5.3_12.3": 3})
    assert preset is not None
    assert preset.preset_key == "operai_0714_primo_terzo_sabato"
    assert confidence == "high"
    assert reason is not None


def test_suggest_bootstrap_preset_supports_operai_ope0613_code() -> None:
    preset, confidence, reason = router._suggest_bootstrap_preset(["OPE0613"], {"OPE0613": 3})
    assert preset is not None
    assert preset.preset_key == "operai_0714_primo_terzo_sabato"
    assert confidence == "high"
    assert reason is not None


def test_suggest_bootstrap_preset_supports_gaia_operai_template_code() -> None:
    preset, confidence, reason = router._suggest_bootstrap_preset(["OPE0714_1E3SAB"], {"OPE0714_1E3SAB": 3})
    assert preset is not None
    assert preset.preset_key == "operai_0714_primo_terzo_sabato"
    assert confidence == "high"
    assert reason is not None


@pytest.mark.parametrize(
    ("codes", "counts", "preset_key", "confidence"),
    [
        (["RIENTRO IMP"], {"RIENTRO IMP": 3}, "impiegati_rientro", "high"),
        (["IMP1"], {"IMP1": 3}, "impiegati_flessibile", "high"),
        (["OPE0736"], {"OPE0736": 3}, "operai_0620_1356", "high"),
        (["OPESAB", "ALTRO"], {"OPESAB": 2, "ALTRO": 2}, "operai_0714_primo_terzo_sabato", "low"),
    ],
)
def test_suggest_bootstrap_preset_covers_supported_profiles(
    codes: list[str], counts: dict[str, int], preset_key: str, confidence: str
) -> None:
    preset, actual_confidence, reason = router._suggest_bootstrap_preset(codes, counts)
    assert preset is not None
    assert preset.preset_key == preset_key
    assert actual_confidence == confidence
    assert reason


@pytest.mark.parametrize(
    ("codes", "counts", "expected_key"),
    [
        (["OPE0613"], {"OPE0613": 1}, "operai_0714_primo_terzo_sabato"),
        (["OP_5.3_12.3"], {"OP_5.3_12.3": 1}, "operai_0714_primo_terzo_sabato"),
        (["IMP1"], {"IMP1": 1}, "impiegati_flessibile"),
        (["RIENTRO IMP"], {"RIENTRO IMP": 1}, "impiegati_rientro"),
        (["OPE0736"], {"OPE0736": 1}, "operai_0620_1356"),
    ],
)
def test_probable_bootstrap_preset_profiles(
    codes: list[str], counts: dict[str, int], expected_key: str
) -> None:
    suggestion = router._suggest_probable_bootstrap_preset(codes, counts)
    assert suggestion is not None
    assert suggestion[0] is not None
    assert suggestion[0].preset_key == expected_key


def test_probable_bootstrap_preset_handles_empty_and_unknown_codes() -> None:
    assert router._suggest_probable_bootstrap_preset([], {}) is None
    assert router._suggest_probable_bootstrap_preset(["UNKNOWN"], {"UNKNOWN": 1}) is None
    assert router._suggest_bootstrap_preset(["UNKNOWN"], {"UNKNOWN": 1}) == (None, "none", None)


def test_schedule_configuration_status_covers_current_and_legacy_profiles() -> None:
    collaborator = SimpleNamespace(contract_kind="operaio", operai_group="agrario", standard_daily_minutes=420)
    status, notes = router._resolve_schedule_configuration_status(
        collaborator,
        assigned_template_code="OPE0714_1E3SAB",
        suggested_template_code="OPE0714_1E3SAB",
    )
    assert status == "current"
    assert notes == ["Configurazione allineata alla logica GAIA corrente."]

    legacy_status, legacy_notes = router._resolve_schedule_configuration_status(
        collaborator,
        assigned_template_code="IMP1",
        suggested_template_code=None,
    )
    assert legacy_status == "legacy_review"
    assert "non esiste un preset" in legacy_notes[0]

    mismatch_status, mismatch_notes = router._resolve_schedule_configuration_status(
        collaborator,
        assigned_template_code="IMP1",
        suggested_template_code="RIENTRO IMP",
    )
    assert mismatch_status == "legacy_review"
    assert "dati suggeriscono" in mismatch_notes[0]


def test_small_router_helpers_cover_empty_fallback_and_validation_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert router._build_collaborator_snapshot_map(None, []) == {}
    assert router._build_classification_map(None, []) == {}
    assert router._build_operational_quality_map(None, []) == {}
    assert router._build_monthly_night_bonus_map(None, []) == {}
    assert router._load_latest_template_codes_by_collaborator(None, []) == {}
    assert router._summarize_detail_values({}) == "—"

    request_record = SimpleNamespace(
        raw_payload_json={},
        request_type="permesso",
        request_description=None,
        request_status=None,
        request_authorized_by=None,
    )
    assert router._daily_record_has_requests(request_record) is True
    assert router._filter_anomaly_rows([request_record], only_anomalies=False, only_requests=True) == [request_record]

    no_request_record = SimpleNamespace(
        raw_payload_json={},
        request_type=None,
        request_description=None,
        request_status=None,
        request_authorized_by=None,
    )
    assert router._filter_anomaly_rows([no_request_record], only_anomalies=False, only_requests=True) == []

    weekday_record = SimpleNamespace(work_date=date(2026, 8, 24), raw_payload_json={"special": True})
    monkeypatch.setattr(router, "detail_indicates_special_day", lambda _payload: True)
    assert router._daily_record_is_special_day(weekday_record) is True
    weekday_record.raw_payload_json = None
    assert router._daily_record_is_special_day(weekday_record) is False

    assert len(router._resolve_recent_month_values(months=2, anchor_month=None)) == 2
    with pytest.raises(HTTPException, match="anchor_month must be"):
        router._resolve_recent_month_values(months=1, anchor_month="invalid")

    punches = [
        SimpleNamespace(entry_time=None, exit_time=time(10, 0)),
        SimpleNamespace(entry_time=time(22, 0), exit_time=time(2, 0)),
    ]
    assert router._complete_punch_minutes(punches) == 240

    positive_adjustment = SimpleNamespace(delta_minutes=30)
    router._validate_bank_hours_adjustment_balance(None, positive_adjustment)


def test_export_job_creation_persists_worker_start_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db = _RecordingDb()
    monkeypatch.setattr(router, "get_sync_artifact_dir", lambda _job_id: tmp_path)
    monkeypatch.setattr(router, "launch_xlsm_export_worker", lambda _job: (_ for _ in ()).throw(RuntimeError("xlsm boom")))

    with pytest.raises(HTTPException, match="xlsm boom") as xlsm_error:
        router._create_xlsm_export_job_record(
            db,
            requested_by_user_id=1,
            period_start=date(2026, 5, 1),
            collaborator_ids=None,
            employee_kind=None,
            template_path=None,
        )
    assert xlsm_error.value.status_code == 500
    assert db.added[-1].status == "failed"

    collaborator = SimpleNamespace(id=uuid.uuid4(), name="Collaboratore test")
    monkeypatch.setattr(
        router,
        "launch_straordinari_export_worker",
        lambda _job: (_ for _ in ()).throw(RuntimeError("straordinari boom")),
    )
    with pytest.raises(HTTPException, match="straordinari boom") as straordinari_error:
        router._create_straordinari_export_job_record(
            db,
            requested_by_user_id=1,
            collaborator=collaborator,
            period_start=date(2026, 5, 1),
            template_path=None,
            items=[],
        )
    assert straordinari_error.value.status_code == 500
    assert db.added[-1].status == "failed"


def test_resolve_straordinari_collaborator_covers_explicit_and_inferred_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(id=7, role="viewer", is_super_admin=False)
    collaborator = SimpleNamespace(id=uuid.uuid4(), name="Unico")
    monkeypatch.setattr(router, "_can_access_collaborator", lambda *_args: True)

    explicit_db = _RecordingDb()
    explicit_db.get = lambda _model, _identifier: collaborator
    assert router._resolve_straordinari_collaborator(
        explicit_db, current_user=user, collaborator_id=collaborator.id
    ) is collaborator

    missing_db = _RecordingDb()
    with pytest.raises(HTTPException) as missing_explicit:
        router._resolve_straordinari_collaborator(
            missing_db, current_user=user, collaborator_id=uuid.uuid4()
        )
    assert missing_explicit.value.status_code == 404

    assert router._resolve_straordinari_collaborator(
        _RecordingDb([collaborator]), current_user=user, collaborator_id=None
    ) is collaborator
    with pytest.raises(HTTPException, match="Nessun collaboratore"):
        router._resolve_straordinari_collaborator(_RecordingDb(), current_user=user, collaborator_id=None)
    with pytest.raises(HTTPException, match="Seleziona il collaboratore"):
        router._resolve_straordinari_collaborator(
            _RecordingDb([collaborator, SimpleNamespace(id=uuid.uuid4(), name="Secondo")]),
            current_user=user,
            collaborator_id=None,
        )


@pytest.mark.parametrize("error", [FileNotFoundError("missing"), ValueError("invalid")])
def test_sync_xlsm_export_maps_generator_errors_to_not_found(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    monkeypatch.setattr(router, "generate_xlsm_export", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))
    with pytest.raises(HTTPException) as exc_info:
        router.export_giornaliere_xlsm(
            None,
            None,
            None,
            period_start=date(2026, 5, 1),
            collaborator_id=None,
            employee_kind=None,
            template_path=None,
        )
    assert exc_info.value.status_code == 404


def test_sync_job_error_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    admin = SimpleNamespace(id=1, role="admin", is_super_admin=False)
    job_id = uuid.uuid4()
    payload = SimpleNamespace(credential_id=1, year=2026, month=5, collaborator_limit=None, employee_codes=[])

    monkeypatch.setattr(router, "has_running_sync_job", lambda _db: True)
    with pytest.raises(HTTPException, match="Another Presenze sync"):
        router.create_sync_job(payload, None, admin, None)
    with pytest.raises(HTTPException, match="Another Presenze sync"):
        router.retry_sync_job(job_id, None, admin, None)
    with pytest.raises(HTTPException, match="Another Presenze sync"):
        router.retry_sync_job_selected(job_id, payload, None, admin, None)

    monkeypatch.setattr(router, "has_running_sync_job", lambda _db: False)
    monkeypatch.setattr(router, "get_credential", lambda *_args: None)
    with pytest.raises(HTTPException, match="Credenziale Presenze"):
        router.create_sync_job(payload, None, admin, None)

    missing_db = _RecordingDb()
    with pytest.raises(HTTPException, match="Sync job not found"):
        router.retry_sync_job(job_id, missing_db, admin, None)
    with pytest.raises(HTTPException, match="Sync job not found"):
        router.retry_sync_job_selected(job_id, payload, missing_db, admin, None)

    def db_for(job):
        db = _RecordingDb()
        db.get = lambda _model, _identifier: job
        return db

    pending = SimpleNamespace(status="pending", requested_by_user_id=admin.id)
    with pytest.raises(HTTPException, match="not retryable"):
        router.retry_sync_job(job_id, db_for(pending), admin, None)

    legacy = SimpleNamespace(status="completed", requested_by_user_id=admin.id, credential_id=None)
    with pytest.raises(HTTPException, match="configurazione legacy"):
        router.retry_sync_job(job_id, db_for(legacy), admin, None)
    with pytest.raises(HTTPException, match="configurazione legacy"):
        router.retry_sync_job_selected(job_id, payload, db_for(legacy), admin, None)

    exhausted = SimpleNamespace(
        status="failed",
        requested_by_user_id=admin.id,
        credential_id=1,
        params_json={},
        attempt_count=3,
        max_attempts=3,
    )
    with pytest.raises(HTTPException, match="max attempts"):
        router.retry_sync_job(job_id, db_for(exhausted), admin, None)

    empty_codes = SimpleNamespace(employee_codes=[])
    source = SimpleNamespace(requested_by_user_id=admin.id, credential_id=1)
    with pytest.raises(HTTPException, match="At least one employee code"):
        router.retry_sync_job_selected(job_id, empty_codes, db_for(source), admin, None)

    source.id = job_id
    monkeypatch.setattr(router, "_load_sync_job_summary", lambda _job_id: {})
    with pytest.raises(HTTPException, match="No failed collaborators"):
        router.retry_sync_job_selected(
            job_id, SimpleNamespace(employee_codes=["1854"]), db_for(source), admin, None
        )


def test_sync_job_record_rejects_missing_and_inactive_credentials() -> None:
    with pytest.raises(HTTPException) as missing:
        router._create_sync_job_record(
            _RecordingDb(),
            requested_by_user_id=1,
            credential_id=1,
            year=2026,
            month=5,
            collaborator_limit=None,
        )
    assert missing.value.status_code == 404

    inactive_db = _RecordingDb()
    inactive_db.get = lambda _model, _identifier: SimpleNamespace(active=False)
    with pytest.raises(HTTPException) as inactive:
        router._create_sync_job_record(
            inactive_db,
            requested_by_user_id=1,
            credential_id=1,
            year=2026,
            month=5,
            collaborator_limit=None,
        )
    assert inactive.value.status_code == 409


def test_cancel_sync_job_error_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    admin = SimpleNamespace(id=1, role="admin", is_super_admin=False)
    job_id = uuid.uuid4()
    with pytest.raises(HTTPException) as missing:
        router.cancel_sync_job(job_id, _RecordingDb(), admin, None)
    assert missing.value.status_code == 404

    def db_for(job):
        db = _RecordingDb()
        db.get = lambda _model, _identifier: job
        return db

    with pytest.raises(HTTPException, match="cannot be cancelled"):
        router.cancel_sync_job(
            job_id, db_for(SimpleNamespace(status="completed", requested_by_user_id=1)), admin, None
        )

    running = SimpleNamespace(status="running", requested_by_user_id=1, worker_pid=123)
    monkeypatch.setattr(router, "stop_sync_worker", lambda _job: (_ for _ in ()).throw(RuntimeError("stop failed")))
    with pytest.raises(HTTPException, match="stop failed") as stop_error:
        router.cancel_sync_job(job_id, db_for(running), admin, None)
    assert stop_error.value.status_code == 500


def test_job_artifact_routes_cover_missing_invalid_and_absent_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    admin = SimpleNamespace(id=1, role="admin", is_super_admin=False)
    job_id = uuid.uuid4()
    calls = [
        (router.download_sync_job_artifact, SimpleNamespace(id=job_id, requested_by_user_id=1, params_json={})),
        (
            router.download_xlsm_export_job_artifact,
            SimpleNamespace(id=job_id, requested_by_user_id=1, params_json={"mode": "export_xlsm"}),
        ),
        (
            router.download_straordinari_export_job_artifact,
            SimpleNamespace(
                id=job_id,
                requested_by_user_id=1,
                params_json={"mode": "export_straordinari_xlsx"},
            ),
        ),
    ]
    for function, job in calls:
        with pytest.raises(HTTPException) as missing_job:
            function(job_id, "invalid", _RecordingDb(), admin, None, None) if function is router.download_xlsm_export_job_artifact else function(job_id, "invalid", _RecordingDb(), admin, None)
        assert missing_job.value.status_code == 404

        db = _RecordingDb()
        db.get = lambda _model, _identifier, job=job: job
        monkeypatch.setattr(router, "resolve_sync_artifact_path", lambda *_args: (_ for _ in ()).throw(ValueError("bad artifact")))
        with pytest.raises(HTTPException, match="bad artifact"):
            function(job_id, "invalid", db, admin, None, None) if function is router.download_xlsm_export_job_artifact else function(job_id, "invalid", db, admin, None)

        monkeypatch.setattr(router, "resolve_sync_artifact_path", lambda *_args: tmp_path / "missing")
        with pytest.raises(HTTPException, match="artifact not found"):
            function(job_id, "summary", db, admin, None, None) if function is router.download_xlsm_export_job_artifact else function(job_id, "summary", db, admin, None)


def test_job_detail_and_delete_error_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    admin = SimpleNamespace(id=1, role="admin", is_super_admin=False)
    job_id = uuid.uuid4()
    monkeypatch.setattr(router, "reconcile_stale_sync_jobs", lambda _db: None)

    detail_calls = [
        lambda db: router.get_import_job(job_id, db, admin, None),
        lambda db: router.get_sync_job(job_id, db, admin, None),
        lambda db: router.get_xlsm_export_job(job_id, db, admin, None, None),
        lambda db: router.get_straordinari_export_job(job_id, db, admin, None),
    ]
    for call in detail_calls:
        with pytest.raises(HTTPException) as exc_info:
            call(_RecordingDb())
        assert exc_info.value.status_code == 404

    delete_calls = [
        (router.delete_sync_job, {}),
        (router.delete_xlsm_export_job, {"mode": "export_xlsm"}),
        (router.delete_straordinari_export_job, {"mode": "export_straordinari_xlsx"}),
    ]
    for function, params_json in delete_calls:
        with pytest.raises(HTTPException) as missing:
            function(job_id, _RecordingDb(), admin, None, None) if function is router.delete_xlsm_export_job else function(job_id, _RecordingDb(), admin, None)
        assert missing.value.status_code == 404

        pending = SimpleNamespace(
            id=job_id, status="pending", requested_by_user_id=1, params_json=params_json
        )
        db = _RecordingDb()
        db.get = lambda _model, _identifier, pending=pending: pending
        with pytest.raises(HTTPException) as non_terminal:
            function(job_id, db, admin, None, None) if function is router.delete_xlsm_export_job else function(job_id, db, admin, None)
        assert non_terminal.value.status_code == 409


def test_bootstrap_preview_treats_orphan_assignment_as_unassigned() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(
        bind=engine,
        tables=[
            ApplicationUser.__table__,
            PresenzeCollaborator.__table__,
            PresenzeScheduleTemplate.__table__,
            PresenzeScheduleRule.__table__,
            PresenzeCollaboratorScheduleAssignment.__table__,
            PresenzeImportJob.__table__,
            PresenzeDailyRecord.__table__,
        ],
    )

    with SessionLocal() as db:
        collaborator = PresenzeCollaborator(employee_code="117", company_code="53", name="DESCHINO GIANNI")
        db.add(collaborator)
        db.flush()
        valid_template = PresenzeScheduleTemplate(code="OPE0714_1E3SAB", label="Operai 07:00-14:00")
        db.add(valid_template)
        db.flush()
        db.add(
            PresenzeCollaboratorScheduleAssignment(
                collaborator_id=collaborator.id,
                template_id=valid_template.id + 1000,
                notes="Assegnazione legacy non risolvibile",
            )
        )
        db.add(PresenzeDailyRecord(collaborator_id=collaborator.id, work_date=date(2026, 7, 1), schedule_code="OPE0714"))
        db.commit()

        preview = router._build_schedule_bootstrap_preview(db)

    suggestion = preview.collaborator_suggestions[0]
    assert suggestion.assigned_template_code is None
    assert suggestion.already_assigned is False
    assert suggestion.suggested_template_code == "OPE0714_1E3SAB"
    assert suggestion.suggestion_confidence == "high"


def test_suggest_bootstrap_preset_supports_operai_alias_saturday_code() -> None:
    preset, confidence, reason = router._suggest_bootstrap_preset(["OSAB5.3_12.3"], {"OSAB5.3_12.3": 3})
    assert preset is not None
    assert preset.preset_key == "operai_0714_primo_terzo_sabato"
    assert confidence == "medium"
    assert reason is not None


def test_ensure_system_schedule_templates_creates_new_visible_templates_without_forcing_saturday_minutes() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine, tables=[PresenzeScheduleTemplate.__table__, PresenzeScheduleRule.__table__])

    with SessionLocal() as db:
        templates = router.ensure_system_schedule_templates(db)
        codes = sorted(item.code for item in templates if item.code in {"OPE0613", "OP_5.3_12.3", "OSAB5.3_12.3"})
        assert codes == ["OPE0613", "OP_5.3_12.3", "OSAB5.3_12.3"]

        by_code = {
            item.code: item
            for item in db.execute(
                select(PresenzeScheduleTemplate).where(PresenzeScheduleTemplate.code.in_(["OPE0613", "OP_5.3_12.3", "OSAB5.3_12.3"]))
            ).scalars().all()
        }
        ope0613_rules = db.execute(
            select(PresenzeScheduleRule).where(PresenzeScheduleRule.template_id == by_code["OPE0613"].id)
        ).scalars().all()
        weekday_rules = db.execute(
            select(PresenzeScheduleRule).where(PresenzeScheduleRule.template_id == by_code["OP_5.3_12.3"].id)
        ).scalars().all()
        saturday_rules = db.execute(
            select(PresenzeScheduleRule).where(PresenzeScheduleRule.template_id == by_code["OSAB5.3_12.3"].id)
        ).scalars().all()

        assert len(ope0613_rules) == 5
        assert {rule.ordinary_label for rule in ope0613_rules} == {"OPE0613"}
        assert len(weekday_rules) == 5
        assert saturday_rules == []
        assert "operai_group" in (by_code["OSAB5.3_12.3"].notes or "")


def test_ensure_system_schedule_templates_realigns_existing_operai_bootstrap_template_rules() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine, tables=[PresenzeScheduleTemplate.__table__, PresenzeScheduleRule.__table__])

    with SessionLocal() as db:
        template = PresenzeScheduleTemplate(
            code="OPE0714_1E3SAB",
            label="Operai 07:00-14:00 con 1° e 3° sabato",
            company_code="53",
            is_active=True,
        )
        db.add(template)
        db.flush()
        db.add(
            PresenzeScheduleRule(
                template_id=template.id,
                label="Legacy feriale",
                weekday=0,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                ordinary_label="OPE0714",
                sort_order=0,
            )
        )
        db.commit()

        router.ensure_system_schedule_templates(db)

        refreshed = db.execute(
            select(PresenzeScheduleTemplate).where(PresenzeScheduleTemplate.code == "OPE0714_1E3SAB")
        ).scalar_one()
        refreshed_rules = db.execute(
            select(PresenzeScheduleRule)
            .where(PresenzeScheduleRule.template_id == refreshed.id)
            .order_by(PresenzeScheduleRule.sort_order.asc(), PresenzeScheduleRule.id.asc())
        ).scalars().all()

        assert len(refreshed_rules) == 14
        assert "01/06-30/09" in (refreshed.notes or "")
        assert any(
            rule.ordinary_label == "OP_5.3_12.3"
            and rule.start_time == time(5, 30)
            and rule.end_time == time(12, 30)
            and rule.season_start_month == 6
            and rule.season_start_day == 1
            and rule.season_end_month == 9
            and rule.season_end_day == 30
            for rule in refreshed_rules
        )


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
        created_at=datetime(2026, 6, 1, 8, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 1, 8, 0, tzinfo=UTC),
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
        created_at=datetime(2026, 6, 3, 8, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 3, 8, 0, tzinfo=UTC),
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


def test_sync_summary_and_route_error_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(router, "resolve_sync_artifact_path", lambda *_args: missing)
    with pytest.raises(HTTPException, match="not available"):
        router._load_sync_job_summary("missing")

    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    monkeypatch.setattr(router, "resolve_sync_artifact_path", lambda *_args: invalid)
    with pytest.raises(HTTPException, match="not valid JSON"):
        router._load_sync_job_summary("invalid")

    unexpected = tmp_path / "unexpected.json"
    unexpected.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(router, "resolve_sync_artifact_path", lambda *_args: unexpected)
    with pytest.raises(HTTPException, match="unexpected structure"):
        router._load_sync_job_summary("unexpected")

    user = SimpleNamespace(id=7, role="viewer", is_super_admin=False)
    assert router.list_import_jobs(_RecordingDb(), user, None).total == 0
    assert router.list_sync_jobs(_QueuedDb([], [], [0]), user, None, limit=None).total == 0
    assert router.list_xlsm_export_jobs(_RecordingDb(), user, None, None, limit=None).total == 0
    assert router.list_straordinari_export_jobs(_RecordingDb(), user, None, limit=None).total == 0


def test_configuration_and_credential_error_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    admin = SimpleNamespace(id=1, role="admin", is_super_admin=False)
    viewer = SimpleNamespace(id=2, role="viewer", is_super_admin=False)
    collaborator_id = uuid.uuid4()

    for call in (
        lambda: router.list_inaz_application_users(None, viewer, None),
        lambda: router.list_supervisor_assignments(None, viewer, None, supervisor_user_id=None),
        lambda: router.update_supervisor_assignment(collaborator_id, None, None, viewer, None),
    ):
        with pytest.raises(HTTPException) as exc_info:
            call()
        assert exc_info.value.status_code == 403

    monkeypatch.setattr(router, "update_credential", lambda *_args: None)
    with pytest.raises(HTTPException) as update_error:
        router.update_presenze_credential(99, None, admin, None, None)
    assert update_error.value.status_code == 404

    monkeypatch.setattr(router, "delete_credential", lambda *_args: False)
    with pytest.raises(HTTPException) as delete_error:
        router.delete_inaz_credential(99, admin, None, None)
    assert delete_error.value.status_code == 404

    async def failed_test(*_args):
        return SimpleNamespace(ok=False, error="connection failed")

    monkeypatch.setattr(router, "test_credential", failed_test)
    with pytest.raises(HTTPException) as test_error:
        asyncio.run(router.test_presenze_credential(99, admin, None, None))
    assert test_error.value.status_code == 502

    monkeypatch.setattr(router, "ensure_operai_rule_configs", lambda _db: None)
    with pytest.raises(HTTPException) as rule_error:
        router.update_operai_rule_config(99, SimpleNamespace(model_dump=lambda **_kwargs: {}), _RecordingDb(), admin, None)
    assert rule_error.value.status_code == 404


def test_import_refresh_and_export_error_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    admin = SimpleNamespace(id=1, role="admin", is_super_admin=False)

    class Upload:
        filename = "input.json"

        async def read(self):
            return b"{}"

    monkeypatch.setattr(router, "load_json_payload", lambda _content: {})
    monkeypatch.setattr(router, "parse_import_payload", lambda _payload: {})
    monkeypatch.setattr(router, "run_import_job", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad import")))
    with pytest.raises(HTTPException, match="bad import"):
        asyncio.run(router.import_json(_RecordingDb(), admin, None, Upload()))

    monkeypatch.setattr(router, "has_running_sync_job", lambda _db: True)
    with pytest.raises(HTTPException) as running:
        router.refresh_giornaliera_from_inaz(uuid.uuid4(), None, admin, None)
    assert running.value.status_code == 409

    monkeypatch.setattr(router, "has_running_sync_job", lambda _db: False)
    monkeypatch.setattr(router, "_get_daily_record_or_404", lambda *_args: SimpleNamespace(collaborator_id=uuid.uuid4()))
    monkeypatch.setattr(router, "_get_collaborator_or_404", lambda *_args: SimpleNamespace(employee_code=""))
    with pytest.raises(HTTPException, match="matricola INAZ"):
        router.refresh_giornaliera_from_inaz(uuid.uuid4(), None, admin, None)

    monkeypatch.setattr(router, "_resolve_straordinari_collaborator", lambda *_args, **_kwargs: SimpleNamespace(id=uuid.uuid4()))
    monkeypatch.setattr(router, "build_straordinari_export_items", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("invalid export")))
    payload = SimpleNamespace(collaborator_id=None, template_path=None, items=[])
    with pytest.raises(HTTPException, match="invalid export"):
        router.create_straordinari_export_job(payload, None, admin, None)


def test_refresh_credential_resolution_prefers_auto_sync_and_rejects_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(id=7)
    active = SimpleNamespace(id=3, active=True)
    monkeypatch.setattr(router, "get_auto_sync_config", lambda _db: SimpleNamespace(credential_id=3))
    monkeypatch.setattr(router, "get_credential", lambda *_args: active)
    assert router._resolve_refresh_credential_for_user(None, user) is active

    monkeypatch.setattr(router, "get_auto_sync_config", lambda _db: SimpleNamespace(credential_id=None))
    with pytest.raises(HTTPException, match="Nessuna credenziale"):
        router._resolve_refresh_credential_for_user(_RecordingDb(), user)


def test_recovery_and_bank_hours_dashboard_filter_and_aggregate_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collaborator_id = uuid.uuid4()
    collaborator = SimpleNamespace(
        id=collaborator_id,
        employee_code="1854",
        name="Collaboratore",
        company_code="53",
        application_user_id=None,
    )
    record = SimpleNamespace(
        id=uuid.uuid4(),
        collaborator_id=collaborator_id,
        work_date=date(2026, 5, 17),
        validation_status="pending",
        raw_payload_json=None,
        resolved_absence_cause="riposo",
        request_description=None,
        evidenze=None,
        stato=None,
    )
    classification = SimpleNamespace(grants_recovery_day=True)
    adjustments = [
        SimpleNamespace(
            collaborator_id=collaborator_id,
            approval_status="approved",
            delta_days=-2,
            adjustment_date=date(2026, 5, 20),
        ),
        SimpleNamespace(
            collaborator_id=collaborator_id,
            approval_status="pending",
            delta_days=1,
            adjustment_date=date(2026, 5, 19),
        ),
    ]
    monkeypatch.setattr(router, "_build_classification_map", lambda *_args, **_kwargs: {record.id: classification})
    result = router._build_recovery_dashboard(
        _QueuedDb([collaborator], [record], adjustments),
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
        q="Collab",
    )
    assert result.matured_days_total == 1
    assert result.used_days_total == 1
    assert result.negative_balance_total == 1

    filtered = router._build_recovery_dashboard(
        _QueuedDb([collaborator], [], []),
        date_from=None,
        date_to=None,
        q="none",
        negative_only=True,
        pending_validation_only=True,
        pending_adjustments_only=True,
        manual_adjustments_only=True,
    )
    assert filtered.items == []

    profile = SimpleNamespace(contract_kind="operaio", standard_daily_minutes=420)
    monkeypatch.setattr(router, "_resolve_collaborator_contract_profile", lambda *_args, **_kwargs: (profile, "explicit"))
    monkeypatch.setattr(router, "_load_latest_template_codes_by_collaborator", lambda *_args: {})
    bank_adjustment = SimpleNamespace(
        approval_status="approved",
        adjustment_date=date(2026, 5, 20),
        delta_minutes=-5,
        kind="correction",
    )
    monkeypatch.setattr(
        router,
        "_load_bank_hours_context",
        lambda *_args, **_kwargs: ({}, {collaborator_id: [bank_adjustment]}),
    )
    bank_result = router._build_bank_hours_dashboard(
        _QueuedDb([collaborator]), date_from=None, date_to=None, q="Collab"
    )
    assert bank_result.negative_balance_total == 1

    monkeypatch.setattr(router, "_load_bank_hours_context", lambda *_args, **_kwargs: ({}, {}))
    bank_filtered = router._build_bank_hours_dashboard(
        _QueuedDb([collaborator]),
        date_from=None,
        date_to=None,
        q="none",
        negative_only=True,
        pending_adjustments_only=True,
        manual_adjustments_only=True,
    )
    assert bank_filtered.items == []


def test_bank_hours_compensation_and_balance_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    collaborator_id = uuid.uuid4()
    assert router._build_bank_hours_compensation_summary(
        _QueuedDb([]), collaborator_id=collaborator_id, date_from=None, date_to=None
    ).records_total == 0

    records = [
        SimpleNamespace(id=uuid.uuid4(), ordinary_minutes=0, straordinario_minutes=0, mpe_minutes=0),
        SimpleNamespace(id=uuid.uuid4(), ordinary_minutes=60, straordinario_minutes=0, mpe_minutes=0),
        SimpleNamespace(id=uuid.uuid4(), ordinary_minutes=60, straordinario_minutes=0, mpe_minutes=0),
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
    )
    monkeypatch.setattr(
        router,
        "_build_classification_map",
        lambda *_args, **_kwargs: {records[1].id: classification, records[2].id: classification},
    )
    monkeypatch.setattr(
        router,
        "_build_monthly_night_bonus_map",
        lambda *_args, **_kwargs: {
            records[2].id: {
                "monthly_night_shift_count": 12,
                "ordinary_night_bonus_threshold_met": True,
                "ordinary_night_bonus_rate": 10,
            }
        },
    )
    summary = router._build_bank_hours_compensation_summary(
        _QueuedDb(records, []), collaborator_id=collaborator_id, date_from=None, date_to=None
    )
    assert summary.records_total == 3
    assert summary.ordinary_night_bonus_threshold_met is True

    excluded_id = uuid.uuid4()
    balance_db = _QueuedDb(
        [SimpleNamespace(description="Banca ore", saldo_totale_minutes=100)],
        [SimpleNamespace(id=excluded_id, delta_minutes=20), SimpleNamespace(id=uuid.uuid4(), delta_minutes=-5)],
    )
    assert router._resolve_bank_hours_available_minutes(
        balance_db,
        collaborator_id=collaborator_id,
        up_to_date=date(2026, 5, 31),
        exclude_adjustment_id=excluded_id,
    ) == 95


def test_bootstrap_apply_skips_unresolvable_presets_and_suggestions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preview = SimpleNamespace(
        presets=[SimpleNamespace(already_exists=False, template_code="UNKNOWN")],
        collaborator_suggestions=[
            SimpleNamespace(suggested_template_code=None),
            SimpleNamespace(
                suggested_template_code="MISSING",
                suggestion_confidence="high",
                already_assigned=False,
            ),
        ],
    )
    monkeypatch.setattr(router, "_build_schedule_bootstrap_preview", lambda _db: preview)
    monkeypatch.setattr(router, "_preset_by_template_code", lambda _code: None)
    result = router.apply_schedule_bootstrap(
        SimpleNamespace(create_missing_templates=True, assign_unassigned_collaborators=True),
        _QueuedDb([]),
        None,
        None,
    )
    assert result.created_templates == 0
    assert result.created_assignments == 0
    assert result.skipped_existing_assignments == 1


def test_system_templates_backfill_missing_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    template = SimpleNamespace(code="SYSTEM", notes=None)
    definition = SimpleNamespace(code="SYSTEM", notes="Managed by GAIA", rules=())
    monkeypatch.setattr(router, "SYSTEM_SCHEDULE_TEMPLATE_DEFINITIONS", (definition,))
    monkeypatch.setattr(router, "BOOTSTRAP_TEMPLATE_PRESETS", ())
    db = _QueuedDb([template], [template])

    assert router.ensure_system_schedule_templates(db) == [template]
    assert template.notes == "Managed by GAIA"
    assert db.added == [template]
    assert db.commits == 1


def test_dashboard_summary_covers_travel_special_day_and_payload_schedule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collaborator_id = uuid.uuid4()
    record = SimpleNamespace(
        id=uuid.uuid4(),
        collaborator_id=collaborator_id,
        ordinary_minutes=60,
        absence_minutes=0,
        justified_minutes=0,
        override_straordinario_minutes=None,
        straordinario_minutes=0,
        override_mpe_minutes=None,
        mpe_minutes=0,
        km_value=5,
        trasferta_minutes=30,
        trasferta_montano=True,
        raw_payload_json={"detail_programmed_schedule": "IMP1 - Standard"},
        stato=None,
        resolved_absence_cause=None,
        schedule_code=None,
        request_description=None,
        evidenze=None,
    )
    classification = SimpleNamespace(special_day=True, grants_recovery_day=False)
    monkeypatch.setattr(router, "_build_classification_map", lambda *_args: {record.id: classification})
    monkeypatch.setattr(router, "_record_uses_recovery_day", lambda _record: False)
    result = router.get_dashboard_summary(
        _QueuedDb([1], [0], [1], [record]),
        SimpleNamespace(role="admin", is_super_admin=False),
        None,
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 31),
    )
    assert result.trasferta_days_total == 1
    assert result.trasferta_montano_days_total == 1
    assert result.special_day_total == 1
    assert result.schedule_stats == [{"code": "IMP1", "count": 1}]


def test_anomaly_month_summary_empty_and_non_anomaly_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(role="admin", is_super_admin=False)
    monkeypatch.setattr(router, "_resolve_recent_month_values", lambda **_kwargs: [])
    assert router.get_anomalie_month_summary(None, user, None).items == []

    monkeypatch.setattr(router, "_resolve_recent_month_values", lambda **_kwargs: ["2026-05"])
    monkeypatch.setattr(
        router,
        "_apply_daily_record_filters",
        lambda _db, _user, *, stmt, count_stmt, **_kwargs: (stmt, count_stmt),
    )
    monkeypatch.setattr(router, "_daily_record_has_anomaly", lambda _record: False)
    result = router.get_anomalie_month_summary(
        _QueuedDb([SimpleNamespace(work_date=date(2026, 5, 12))]), user, None
    )
    assert result.items == []


def test_matrix_serializer_builds_default_classification_and_quality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    quality = SimpleNamespace(
        status="ok",
        formula_code="test",
        expected_minutes=0,
        worked_minutes=0,
        missing_minutes=0,
        mpe_minutes=0,
        notes=(),
    )
    monkeypatch.setattr(router, "_build_daily_record_classification", lambda *_args, **_kwargs: classification)
    monkeypatch.setattr(router, "build_daily_operational_quality", lambda *_args, **_kwargs: quality)
    monkeypatch.setattr(router, "_record_uses_recovery_day", lambda _record: False)
    monkeypatch.setattr(router, "_resolved_absence_cause_for_response", lambda *_args: None)
    monkeypatch.setattr(
        router,
        "PresenzeDailyRecordResponse",
        SimpleNamespace(model_validate=lambda value: value),
    )
    record = SimpleNamespace(
        raw_payload_json=None,
        override_straordinario_minutes=None,
        straordinario_minutes=None,
        override_mpe_minutes=None,
        mpe_minutes=None,
        request_type=None,
        request_description=None,
        request_status=None,
        request_authorized_by=None,
        resolved_absence_cause=None,
        evidenze=None,
        stato=None,
    )

    serialized = router._serialize_daily_record_matrix(record)
    assert serialized["operational_status"] == "ok"
    assert serialized["night_minutes"] == 0


def test_mapping_helpers_cover_missing_related_rows_and_expired_assignment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collaborator_id = uuid.uuid4()
    record = SimpleNamespace(id=uuid.uuid4(), collaborator_id=collaborator_id, work_date=date(2026, 5, 1))
    monkeypatch.setattr(router, "build_schedule_context", lambda *_args, **_kwargs: object())
    sentinel = object()
    monkeypatch.setattr(router, "classify_daily_record", lambda *_args: sentinel)
    assert router._build_classification_map(
        _QueuedDb([]), [record], punches_by_record_id={}
    )[record.id] is sentinel

    catasto_collaborator = SimpleNamespace(
        contract_kind=router.PRESENZE_CONTRACT_KIND_OPERAIO,
        operai_group=router.PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO,
    )
    counts = router._build_catasto_saturday_coverage_counts(
        _QueuedDb([]), [record], {collaborator_id: catasto_collaborator}
    )
    assert counts[(collaborator_id, 2026, 5)] == 0

    monthly_record = SimpleNamespace(id=uuid.uuid4(), collaborator_id=collaborator_id, work_date=date(2026, 5, 3))
    monkeypatch.setattr(router, "_build_classification_map", lambda *_args, **_kwargs: {})
    bonus = router._build_monthly_night_bonus_map(_QueuedDb([monthly_record], []), [monthly_record])
    assert bonus[monthly_record.id]["monthly_night_shift_count"] == 0

    assignment = SimpleNamespace(
        collaborator_id=collaborator_id,
        template_id=10,
        valid_from=date(2025, 1, 1),
        valid_to=date(2025, 12, 31),
    )
    template = SimpleNamespace(id=10, code="LEGACY")
    selected = router._load_latest_template_codes_by_collaborator(
        _QueuedDb([assignment], [template]),
        [collaborator_id],
        reference_date=date(2026, 5, 1),
    )
    assert selected[collaborator_id] == "LEGACY"

    assert router._load_bank_hours_context(
        None, [], date_to=None
    ) == ({}, {})


def test_bootstrap_preview_ignores_blank_schedule_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    collaborator_id = uuid.uuid4()
    collaborator = SimpleNamespace(
        id=collaborator_id,
        employee_code="1",
        name="Blank schedule",
        company_code="53",
        contract_kind=None,
        operai_group=None,
        standard_daily_minutes=None,
    )
    monkeypatch.setattr(router, "_load_latest_template_codes_by_collaborator", lambda *_args: {})
    preview = router._build_schedule_bootstrap_preview(
        _QueuedDb([collaborator], [(collaborator_id, "  ")], [])
    )
    assert preview.collaborator_suggestions[0].schedule_codes == []


def test_modular_router_facade_forwards_and_restores_legacy_attributes() -> None:
    original = router._normalize_employee_codes

    def replacement(_values):
        return ["patched"]

    router._normalize_employee_codes = replacement
    assert router._normalize_employee_codes is replacement
    delattr(router, "_normalize_employee_codes")
    assert router._normalize_employee_codes is original

    router.coverage_probe = 1
    assert router.coverage_probe == 1
    delattr(router, "coverage_probe")
    router.__coverage_probe__ = 2
    assert router.__coverage_probe__ == 2
    delattr(router, "__coverage_probe__")
    delattr(router, "never_set_probe")

    with pytest.raises(AttributeError):
        router.__getattr__("missing_legacy_symbol")


def test_modular_schedule_helper_legacy_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    collaborator = SimpleNamespace(contract_kind=None, operai_group=None, standard_daily_minutes=0)
    status, notes = router._resolve_schedule_configuration_status(
        collaborator,
        assigned_template_code="OPE0613",
        suggested_template_code="OPE0613",
    )
    assert status == "legacy_review"
    assert len(notes) == 3

    definition = router._SystemScheduleTemplateDefinition(
        code="OPE0613",
        label="Operai",
        company_code="53",
        notes="Default",
        rules=(router._BootstrapRuleDefinition(None, 0, "weekly", time(7), time(14)),),
    )
    existing = SimpleNamespace(code="OPE0613", notes="Already configured")
    monkeypatch.setattr(router, "SYSTEM_SCHEDULE_TEMPLATE_DEFINITIONS", (definition,))
    monkeypatch.setattr(router, "BOOTSTRAP_TEMPLATE_PRESETS", ())
    monkeypatch.setattr(router, "_upsert_template_rules", lambda *_args: False)
    db = _QueuedDb([existing])
    assert router.ensure_system_schedule_templates(db) == [existing]
    assert db.commits == 0


def test_modular_daily_helper_empty_and_fallback_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=7)
    monkeypatch.setattr(router, "get_auto_sync_config", lambda _db: SimpleNamespace(credential_id=3))
    monkeypatch.setattr(router, "get_credential", lambda *_args: SimpleNamespace(active=False))
    with pytest.raises(HTTPException, match="Nessuna credenziale"):
        router._resolve_refresh_credential_for_user(_QueuedDb([]), user)

    monkeypatch.setattr(router, "build_schedule_context", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(router, "classify_daily_record", lambda collaborator, *_args: collaborator)
    record = SimpleNamespace(collaborator_id=uuid.uuid4(), work_date=date(2026, 5, 1))
    assert router._build_daily_record_classification(None, record, punches=[]).id == record.collaborator_id
    assert router._build_daily_record_classification(_BranchDb(stored=None), record, punches=[]).id == record.collaborator_id
    stored = SimpleNamespace(id=record.collaborator_id)
    assert router._build_daily_record_classification(_BranchDb(stored=stored), record, punches=[]) is stored

    monthly_record = SimpleNamespace(id=uuid.uuid4(), collaborator_id=uuid.uuid4(), work_date=date(2026, 5, 1))
    monkeypatch.setattr(router, "_build_classification_map", lambda *_args, **_kwargs: {})
    bonus = router._build_monthly_night_bonus_map(_QueuedDb([]), [monthly_record])
    assert bonus[monthly_record.id]["monthly_night_shift_count"] == 0


def test_modular_bank_and_recovery_helper_alternative_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    collaborator_id = uuid.uuid4()
    assert router._load_bank_hours_context(_QueuedDb([], []), [collaborator_id], date_to=None) == ({}, {})

    record = SimpleNamespace(id=uuid.uuid4(), ordinary_minutes=0, straordinario_minutes=0, mpe_minutes=0)
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
    )
    monkeypatch.setattr(router, "_build_classification_map", lambda *_args, **_kwargs: {record.id: classification})
    monkeypatch.setattr(router, "_build_monthly_night_bonus_map", lambda *_args, **_kwargs: {})
    summary = router._build_bank_hours_compensation_summary(
        _QueuedDb([record], []), collaborator_id=collaborator_id, date_from=None, date_to=None
    )
    assert summary.worked_days_total == 0

    config = SimpleNamespace(
        allow_derived_profile=False,
        include_overtime_day=False,
        include_overtime_night=False,
        include_overtime_festive=False,
        include_overtime_festive_night=False,
        min_suggested_minutes=0,
    )
    guidance = router._build_bank_hours_liquidation_guidance(
        available_debit_minutes=0,
        standard_daily_minutes=420,
        contract_profile_source="explicit",
        compensation_summary=PresenzeBankHoursCompensationSummaryResponse(),
        guidance_config=config,
    )
    assert guidance.included_overtime_buckets == []
    assert router._build_recovery_dashboard(_QueuedDb([]), date_from=None, date_to=None, q=None).items == []

    collaborator = SimpleNamespace(
        id=collaborator_id,
        employee_code="1",
        name="Recovery",
        company_code="53",
        application_user_id=None,
    )
    records = [
        SimpleNamespace(
            id=uuid.uuid4(),
            collaborator_id=collaborator_id,
            work_date=date(2026, 5, 1),
            validation_status="validated",
        )
        for _ in range(2)
    ]
    monkeypatch.setattr(
        router,
        "_build_classification_map",
        lambda *_args, **_kwargs: {
            record.id: SimpleNamespace(grants_recovery_day=True) for record in records
        },
    )
    monkeypatch.setattr(router, "_record_uses_recovery_day", lambda _record: True)
    result = router._build_recovery_dashboard(
        _QueuedDb([collaborator], records, []), date_from=None, date_to=None, q=None
    )
    assert result.matured_days_total == 2
    assert result.used_days_total == 2


def test_modular_route_optional_and_no_change_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    admin = SimpleNamespace(role="admin", is_super_admin=False, id=1)
    monkeypatch.setattr(router, "_can_manage_supervisors", lambda _user: True)
    assert router.list_supervisor_assignments(_QueuedDb([]), admin, None, supervisor_user_id=None) == []
    monkeypatch.setattr(router, "_get_collaborator_or_404", lambda *_args: object())
    assert router.update_supervisor_assignment(
        uuid.uuid4(), SimpleNamespace(supervisor_user_id=None), _QueuedDb([]), admin, None
    ) is None
    monkeypatch.setattr(
        router,
        "PresenzeSupervisorAssignmentResponse",
        SimpleNamespace(model_validate=lambda value: value),
    )
    assignment = SimpleNamespace(collaborator_id=uuid.uuid4(), supervisor_user_id=99)
    serialized = router._serialize_supervisor_assignment(_BranchDb(stored=None), assignment)
    assert serialized["supervisor"] is None
    assert router.list_presenze_holidays(_QueuedDb([]), None, None, year=None) == []

    monkeypatch.setattr(router, "delete_credential", lambda *_args: True)
    assert router.delete_inaz_credential(1, admin, None, None) is None
    assert router.list_recovery_adjustments(
        _QueuedDb([]), admin, None, collaborator_id=None, approval_status=None
    ) == []
    assert router.list_bank_hours_adjustments(
        _QueuedDb([]), admin, None, collaborator_id=None, approval_status=None
    ) == []

    recovery_item = SimpleNamespace(id=uuid.uuid4())
    bank_item = SimpleNamespace(id=uuid.uuid4())
    monkeypatch.setattr(router, "_serialize_recovery_adjustment", lambda _db, item: item)
    monkeypatch.setattr(router, "_serialize_bank_hours_adjustment", lambda _db, item: item)
    assert router.update_recovery_adjustment(
        recovery_item.id, SimpleNamespace(model_dump=lambda **_kwargs: {}), _BranchDb(stored=recovery_item), admin, None
    ) is recovery_item
    assert router.update_bank_hours_adjustment(
        bank_item.id, SimpleNamespace(model_dump=lambda **_kwargs: {}), _BranchDb(stored=bank_item), admin, None
    ) is bank_item


def test_modular_daily_route_empty_and_out_of_period_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    admin = SimpleNamespace(role="admin", is_super_admin=False)
    monkeypatch.setattr(
        router,
        "_apply_daily_record_filters",
        lambda _db, _user, *, stmt, count_stmt, **_kwargs: (stmt, count_stmt),
    )
    monkeypatch.setattr(router, "_resolve_recent_month_values", lambda **_kwargs: ["2026-05"])
    monkeypatch.setattr(router, "_daily_record_has_anomaly", lambda _record: True)
    result = router.get_anomalie_month_summary(
        _QueuedDb([SimpleNamespace(work_date=date(2026, 4, 1))]), admin, None
    )
    assert result.items == []

    monkeypatch.setattr(router, "load_operai_rule_configs", lambda _db: {})
    assert router.list_giornaliere_matrix(
        _QueuedDb([], [0]), admin, None, page=1, page_size=31
    ).items == []

    monkeypatch.setattr(router, "ensure_operai_rule_configs", lambda _db: None)
    monkeypatch.setattr(router, "PresenzeOperaiRuleConfigResponse", SimpleNamespace(model_validate=lambda item: item))
    item = SimpleNamespace(id=1)
    result = router.update_operai_rule_config(
        1,
        SimpleNamespace(model_dump=lambda **_kwargs: {"label": "Updated"}),
        _BranchDb(stored=item),
        None,
        None,
    )
    assert result.label == "Updated"


def test_modular_bootstrap_and_dashboard_disabled_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        router,
        "_build_schedule_bootstrap_preview",
        lambda _db: SimpleNamespace(presets=[], collaborator_suggestions=[]),
    )
    result = router.apply_schedule_bootstrap(
        SimpleNamespace(create_missing_templates=False, assign_unassigned_collaborators=False),
        _QueuedDb([]),
        None,
        None,
    )
    assert result.created_templates == 0
    assert result.created_assignments == 0

    record = SimpleNamespace(
        id=uuid.uuid4(), collaborator_id=uuid.uuid4(), ordinary_minutes=0, absence_minutes=0,
        justified_minutes=0, override_straordinario_minutes=None, straordinario_minutes=0,
        override_mpe_minutes=None, mpe_minutes=0, km_value=0, trasferta_minutes=0,
        trasferta_montano=False, raw_payload_json=None, stato=None, resolved_absence_cause=None,
        schedule_code=None, request_description=None, evidenze=None,
    )
    monkeypatch.setattr(router, "_build_classification_map", lambda *_args: {})
    monkeypatch.setattr(router, "_record_uses_recovery_day", lambda _record: False)
    dashboard = router.get_dashboard_summary(
        _QueuedDb([1], [0], [1], [record]),
        SimpleNamespace(role="admin", is_super_admin=False),
        None,
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 31),
    )
    assert dashboard.worked_days_total == 0
    assert dashboard.schedule_stats == []
