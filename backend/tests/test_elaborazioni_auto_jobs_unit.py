from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.services import elaborazioni_auto_jobs as auto_jobs


@dataclass
class FakeRow:
    enabled: bool
    updated_at: datetime | None = None
    updated_by_user_id: int | None = None


class FakeDb:
    def __init__(self, *, row: FakeRow | None = None, anpr_config=None) -> None:
        self.row = row
        self.anpr_config = anpr_config
        self.added: list[object] = []
        self.committed = False
        self.refreshed = False

    def scalar(self, statement):
        return self.row

    def add(self, value: object) -> None:
        self.added.append(value)
        if isinstance(value, FakeRow):
            self.row = value
        if hasattr(value, "job_enabled"):
            self.anpr_config = value

    def commit(self) -> None:
        self.committed = True

    def refresh(self, row: FakeRow) -> None:
        self.refreshed = True

    def get(self, model, primary_key):
        return self.anpr_config


def test_get_and_set_auto_job_toggle_state_cover_create_and_update() -> None:
    db = FakeDb(row=None)

    state = auto_jobs.get_auto_job_toggle_state(db, "job", default_enabled=True)
    assert state.enabled is True

    existing_row = FakeRow(enabled=False, updated_at=datetime.now(UTC), updated_by_user_id=11)
    existing_state = auto_jobs.get_auto_job_toggle_state(FakeDb(row=existing_row), "job", default_enabled=True)
    assert existing_state.enabled is False
    assert existing_state.updated_by_user_id == 11

    created = auto_jobs.set_auto_job_toggle_state(db, "job", enabled=False, updated_by_user_id=99)
    assert created.enabled is False
    assert db.committed is True
    assert db.refreshed is True
    assert len(db.added) == 1

    db_existing = FakeDb(row=FakeRow(enabled=False, updated_at=datetime.now(UTC), updated_by_user_id=1))
    updated = auto_jobs.set_auto_job_toggle_state(db_existing, "job", enabled=True, updated_by_user_id=7)
    assert updated.enabled is True
    assert db_existing.row is not None
    assert db_existing.row.updated_by_user_id == 7


def test_is_enabled_helpers_delegate_to_toggle_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.visure_nas_router_enabled", False)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.wc_sync_daily_enabled", True)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.wc_sync_operazioni_live_enabled", True)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.elaborazioni_db_backup_enabled", True)

    seen: list[tuple[str, bool]] = []

    def fake_get_state(db, job_key: str, *, default_enabled: bool):
        seen.append((job_key, default_enabled))
        return auto_jobs.AutoJobToggleState(enabled=not default_enabled, updated_at=None, updated_by_user_id=None)

    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.get_auto_job_toggle_state", fake_get_state)

    assert auto_jobs.is_visure_nas_router_enabled(object()) is True
    assert auto_jobs.is_whitecompany_daily_sync_enabled(object()) is False
    assert auto_jobs.is_whitecompany_operazioni_live_sync_enabled(object()) is False
    assert auto_jobs.is_elaborazioni_db_backup_enabled(object()) is False
    assert seen == [
        (auto_jobs.VISURE_NAS_ROUTER_JOB_KEY, False),
        (auto_jobs.WHITECOMPANY_DAILY_SYNC_JOB_KEY, True),
        (auto_jobs.WHITECOMPANY_OPERAZIONI_LIVE_SYNC_JOB_KEY, True),
        (auto_jobs.ELABORAZIONI_DB_BACKUP_JOB_KEY, True),
    ]


def test_list_elaborazione_auto_job_controls_covers_missing_and_present_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.visure_nas_router_enabled", True)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.visure_nas_router_cron", "15 */2 * * *")
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.visure_nas_inbox_path", None)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.wc_sync_daily_enabled", True)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.wc_sync_daily_cron", "0 2 * * *")
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.wc_sync_daily_lookback_days", 0)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.wc_sync_operazioni_live_enabled", True)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.wc_sync_operazioni_live_interval_seconds", 3600)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.wc_sync_operazioni_live_start_hour", 6)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.wc_sync_operazioni_live_end_hour", 21)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.wc_sync_operazioni_live_timezone", "Europe/Rome")
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.wc_sync_operazioni_live_lookback_days", 0)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.anpr_daily_call_hard_limit", 90)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.elaborazioni_db_backup_enabled", True)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.elaborazioni_db_backup_cron", "5 2 * * *")
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.elaborazioni_db_backup_timezone", "Europe/Rome")
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.settings.elaborazioni_db_backup_retention_count", 0)

    ruolo_config = SimpleNamespace(enabled=True, credential_id=None, updated_at=None, updated_by_user_id=None)
    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.get_ruolo_autosync_config", lambda db, user_id: ruolo_config)

    states = {
        auto_jobs.VISURE_NAS_ROUTER_JOB_KEY: auto_jobs.AutoJobToggleState(True, None, None),
        auto_jobs.WHITECOMPANY_DAILY_SYNC_JOB_KEY: auto_jobs.AutoJobToggleState(False, None, None),
        auto_jobs.WHITECOMPANY_OPERAZIONI_LIVE_SYNC_JOB_KEY: auto_jobs.AutoJobToggleState(True, None, None),
        auto_jobs.ELABORAZIONI_DB_BACKUP_JOB_KEY: auto_jobs.AutoJobToggleState(True, None, None),
    }
    monkeypatch.setattr(
        "app.services.elaborazioni_auto_jobs.get_auto_job_toggle_state",
        lambda db, job_key, default_enabled: states[job_key],
    )

    db = FakeDb(row=None, anpr_config=None)
    controls = auto_jobs.list_elaborazione_auto_job_controls(db, user_id=1)
    items = {item.key: item for item in controls}

    assert items[auto_jobs.ANPR_JOB_KEY].enabled is True
    assert "0 8-17 * * *" in (items[auto_jobs.ANPR_JOB_KEY].detail or "")
    assert "credenziale mancante" in (items[auto_jobs.RUOLO_VISURE_AUTOSYNC_JOB_KEY].detail or "")
    assert "lookback 1 giorni" in (items[auto_jobs.WHITECOMPANY_DAILY_SYNC_JOB_KEY].detail or "")
    assert "Ogni 60 minuti dalle 06:00 alle 21:00" in (items[auto_jobs.WHITECOMPANY_OPERAZIONI_LIVE_SYNC_JOB_KEY].detail or "")
    assert "retention 1 snapshot" in (items[auto_jobs.ELABORAZIONI_DB_BACKUP_JOB_KEY].detail or "")

    db.anpr_config = SimpleNamespace(
        job_enabled=False,
        job_cron="30 3 * * *",
        max_calls_per_day=10,
        updated_at=None,
        updated_by_user_id=5,
    )
    ruolo_config.credential_id = "cred-1"
    controls = auto_jobs.list_elaborazione_auto_job_controls(db, user_id=1)
    items = {item.key: item for item in controls}
    assert items[auto_jobs.ANPR_JOB_KEY].enabled is False
    assert "30 3 * * *" in (items[auto_jobs.ANPR_JOB_KEY].detail or "")
    assert items[auto_jobs.RUOLO_VISURE_AUTOSYNC_JOB_KEY].detail == "Scheduler ogni minuto"


def test_update_elaborazione_auto_job_control_covers_all_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.elaborazioni_auto_jobs.list_elaborazione_auto_job_controls",
        lambda db, user_id: [
            auto_jobs.ElaborazioneAutoJobControlResponse(
                key=key,
                label=key,
                description="desc",
                enabled=True,
            )
            for key in (
                auto_jobs.VISURE_NAS_ROUTER_JOB_KEY,
                auto_jobs.ANPR_JOB_KEY,
                auto_jobs.RUOLO_VISURE_AUTOSYNC_JOB_KEY,
                auto_jobs.WHITECOMPANY_DAILY_SYNC_JOB_KEY,
                auto_jobs.WHITECOMPANY_OPERAZIONI_LIVE_SYNC_JOB_KEY,
                auto_jobs.ELABORAZIONI_DB_BACKUP_JOB_KEY,
            )
        ],
    )

    set_calls: list[tuple[str, bool, int]] = []
    monkeypatch.setattr(
        "app.services.elaborazioni_auto_jobs.set_auto_job_toggle_state",
        lambda db, control_key, enabled, updated_by_user_id: set_calls.append((control_key, enabled, updated_by_user_id)),
    )

    update_ruolo_calls: list[tuple[int, bool, object]] = []
    monkeypatch.setattr(
        "app.services.elaborazioni_auto_jobs.get_ruolo_autosync_config",
        lambda db, user_id: SimpleNamespace(credential_id="123e4567-e89b-12d3-a456-426614174000"),
    )
    monkeypatch.setattr(
        "app.services.elaborazioni_auto_jobs.update_ruolo_autosync_config",
        lambda db, user_id, payload: update_ruolo_calls.append((user_id, payload.enabled, payload.credential_id)),
    )

    anpr_config = SimpleNamespace(job_enabled=True, updated_by_user_id=None)
    db = FakeDb(row=None, anpr_config=anpr_config)

    response = auto_jobs.update_elaborazione_auto_job_control(
        db,
        user_id=7,
        control_key=auto_jobs.ANPR_JOB_KEY,
        enabled=False,
    )
    assert response.key == auto_jobs.ANPR_JOB_KEY
    assert anpr_config.job_enabled is False

    db_missing = FakeDb(row=None, anpr_config=None)
    auto_jobs.update_elaborazione_auto_job_control(
        db_missing,
        user_id=8,
        control_key=auto_jobs.ANPR_JOB_KEY,
        enabled=True,
    )
    assert isinstance(db_missing.anpr_config, auto_jobs.AnprSyncConfig)

    auto_jobs.update_elaborazione_auto_job_control(
        db,
        user_id=9,
        control_key=auto_jobs.RUOLO_VISURE_AUTOSYNC_JOB_KEY,
        enabled=True,
    )
    assert str(update_ruolo_calls[0][2]) == "123e4567-e89b-12d3-a456-426614174000"

    for control_key in (
        auto_jobs.VISURE_NAS_ROUTER_JOB_KEY,
        auto_jobs.WHITECOMPANY_DAILY_SYNC_JOB_KEY,
        auto_jobs.WHITECOMPANY_OPERAZIONI_LIVE_SYNC_JOB_KEY,
        auto_jobs.ELABORAZIONI_DB_BACKUP_JOB_KEY,
    ):
        auto_jobs.update_elaborazione_auto_job_control(
            db,
            user_id=10,
            control_key=control_key,
            enabled=False,
        )

    assert set_calls == [
        (auto_jobs.VISURE_NAS_ROUTER_JOB_KEY, False, 10),
        (auto_jobs.WHITECOMPANY_DAILY_SYNC_JOB_KEY, False, 10),
        (auto_jobs.WHITECOMPANY_OPERAZIONI_LIVE_SYNC_JOB_KEY, False, 10),
        (auto_jobs.ELABORAZIONI_DB_BACKUP_JOB_KEY, False, 10),
    ]

    with pytest.raises(ValueError):
        auto_jobs.update_elaborazione_auto_job_control(
            db,
            user_id=1,
            control_key="unknown",
            enabled=True,
        )

    monkeypatch.setattr("app.services.elaborazioni_auto_jobs.list_elaborazione_auto_job_controls", lambda db, user_id: [])
    with pytest.raises(ValueError):
        auto_jobs.update_elaborazione_auto_job_control(
            db,
            user_id=1,
            control_key=auto_jobs.VISURE_NAS_ROUTER_JOB_KEY,
            enabled=True,
        )
