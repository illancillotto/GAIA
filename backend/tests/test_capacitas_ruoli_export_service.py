from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.modules.elaborazioni.capacitas.export_http import ExportStepError, SessionExpiredError
from app.modules.elaborazioni.capacitas.export_workbook import ExportPayload
from app.services import capacitas_ruoli_export as service
from app.services.capacitas_ruoli_export import (
    CapacitasPortal,
    ExportTarget,
    SnapshotRun,
    build_targets,
    export_file_name,
)
from app.services.capacitas_ruoli_export_retry import RetryPolicy
from app.services.capacitas_ruoli_export_state import ExportRunState, ExportStateStore

NOW = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


async def no_sleep(_seconds: float) -> None:
    return None


POLICY = RetryPolicy(max_attempts=2, base_delay_seconds=0, sleep=no_sleep)


class FakeDrive:
    def __init__(self, existing: dict[str, str] | None = None) -> None:
        self.existing = dict(existing or {})
        self.uploads: list[tuple[str, str, bytes]] = []
        self.manifests: list[dict] = []
        self.folders: list[tuple[str, str]] = []

    async def find_child(self, name, parent_id, *, mime_type=None):
        return self.existing.get(name)

    async def upload_file(self, name, parent_id, content, mime_type):
        self.uploads.append((name, parent_id, content))
        return f"id-{name}"

    async def replace_or_upload(self, name, parent_id, content, mime_type):
        self.manifests.append(json.loads(content))
        return "manifest-id"

    async def ensure_folder(self, name, parent_id):
        self.folders.append((name, parent_id))
        return f"folder-{name}"


def make_run(tmp_path, drive=None, state=None, relogins=None) -> SnapshotRun:
    async def relogin() -> None:
        if relogins is not None:
            relogins.append(1)

    store = ExportStateStore(tmp_path / "state.json")
    return SnapshotRun(
        drive or FakeDrive(),
        "folder",
        state or ExportRunState(snapshot="s"),
        store,
        POLICY,
        relogin,
    )


def target(keys, fetch) -> ExportTarget:
    async def list_keys():
        if isinstance(keys, Exception):
            raise keys
        return keys

    return ExportTarget("incass_ricerca_avvisi", list_keys, fetch)


def test_export_file_name_is_filesystem_safe():
    assert export_file_name("incass_ricerca_avvisi", "2025") == "incass_ricerca_avvisi_2025.xlsx"
    assert export_file_name("t", "a/b c") == "t_a_b_c.xlsx"


def test_snapshot_run_uploads_skips_empty_and_isolates_failures(tmp_path):
    calls: list[str] = []

    async def fetch(key: str) -> ExportPayload:
        calls.append(key)
        if key == "bad":
            raise ExportStepError("rotto", retryable=False)
        return ExportPayload(content=b"xlsx", rows=0 if key == "empty" else 5)

    drive = FakeDrive()
    run = make_run(tmp_path, drive)

    asyncio.run(run.export_target(target(["2025", "empty", "bad"], fetch)))

    items = run.state.items
    assert items["incass_ricerca_avvisi_2025.xlsx"]["status"] == "uploaded"
    assert (
        items["incass_ricerca_avvisi_2025.xlsx"]["drive_file_id"]
        == "id-incass_ricerca_avvisi_2025.xlsx"
    )
    assert items["incass_ricerca_avvisi_empty.xlsx"]["status"] == "empty"
    assert (
        items["incass_ricerca_avvisi_bad.xlsx"]["status"],
        items["incass_ricerca_avvisi_bad.xlsx"]["error"],
    ) == ("failed", "rotto")
    assert [name for name, _, _ in drive.uploads] == ["incass_ricerca_avvisi_2025.xlsx"]
    assert ExportStateStore(tmp_path / "state.json").load().items.keys() == items.keys()


def test_snapshot_run_resumes_and_deduplicates_drive_files(tmp_path):
    state = ExportRunState(
        snapshot="s", items={"incass_ricerca_avvisi_2024.xlsx": {"status": "uploaded"}}
    )
    drive = FakeDrive(existing={"incass_ricerca_avvisi_2025.xlsx": "already-there"})
    fetched: list[str] = []

    async def fetch(key: str) -> ExportPayload:
        fetched.append(key)
        return ExportPayload(content=b"x", rows=1)

    run = make_run(tmp_path, drive, state)
    asyncio.run(run.export_target(target(["2024", "2025"], fetch)))

    assert fetched == ["2025"]
    assert drive.uploads == []
    assert run.state.items["incass_ricerca_avvisi_2025.xlsx"]["drive_file_id"] == "already-there"


def test_snapshot_run_relogs_on_session_expiry(tmp_path):
    relogins: list[int] = []
    errors = [SessionExpiredError("scaduta")]

    async def fetch(key: str) -> ExportPayload:
        if errors:
            raise errors.pop(0)
        return ExportPayload(content=b"x", rows=1)

    run = make_run(tmp_path, relogins=relogins)
    asyncio.run(run.export_item(target([], fetch), "2025"))

    assert relogins == [1]
    assert run.state.is_done("incass_ricerca_avvisi_2025.xlsx")


def test_snapshot_run_records_listing_failure(tmp_path):
    run = make_run(tmp_path)

    async def fetch(key: str) -> ExportPayload:
        raise AssertionError("not called")

    asyncio.run(run.export_target(target(ExportStepError("pagina", retryable=False), fetch)))

    assert run.state.items["incass_ricerca_avvisi:elenco"]["status"] == "failed"


def test_publish_manifest_contains_state(tmp_path):
    drive = FakeDrive()
    run = make_run(tmp_path, drive, ExportRunState(snapshot="2026-11-01", status="completed"))

    asyncio.run(run.publish_manifest("incass"))

    assert drive.manifests == [
        {
            "group": "incass",
            "snapshot": "2026-11-01",
            "status": "completed",
            "last_attempt_at": "",
            "items": {},
        }
    ]


def test_build_targets_per_group():
    manager = SimpleNamespace()
    incass = build_targets("incass", manager, NOW)
    assert [t.name for t in incass] == ["incass_ricerca_avvisi", "incass_avvisi_minuta"]
    assert asyncio.run(incass[1].list_keys())[0] == "2026"
    assert [t.name for t in build_targets("inbollettini", manager, NOW)] == [
        "inbollettini_registro_bollettini"
    ]


class FakeSessionManager:
    def __init__(self, username, password, *, fail=False):
        self.username, self.password, self.fail = username, password, fail
        self.calls: list[str] = []

    async def login(self):
        self.calls.append("login")
        if self.fail:
            raise RuntimeError("credenziali errate")

    async def activate_app(self, app):
        self.calls.append(f"activate:{app}")

    async def close(self):
        self.calls.append("close")


@contextmanager
def fake_session():
    yield SimpleNamespace()


def patch_credentials(monkeypatch, *, fail=False) -> dict[str, list]:
    events: dict[str, list] = {"used": [], "error": [], "managers": []}

    def manager_factory(username, password):
        manager = FakeSessionManager(username, password, fail=fail)
        events["managers"].append(manager)
        return manager

    monkeypatch.setattr(service, "SessionLocal", fake_session)
    monkeypatch.setattr(
        service,
        "pick_credential",
        lambda db, cid: (SimpleNamespace(id=7, username="PORCUAL"), "pw"),
    )
    monkeypatch.setattr(service, "mark_credential_used", lambda db, cid: events["used"].append(cid))
    monkeypatch.setattr(
        service, "mark_credential_error", lambda db, cid, msg: events["error"].append((cid, msg))
    )
    monkeypatch.setattr(service, "CapacitasSessionManager", manager_factory)
    return events


def test_portal_open_marks_credential_used(monkeypatch):
    events = patch_credentials(monkeypatch)
    portal = CapacitasPortal("incass", None)

    async def scenario():
        await portal.open()
        await portal.close()

    asyncio.run(scenario())

    assert events["used"] == [7]
    assert events["managers"][0].calls == ["login", "activate:incass", "close"]


def test_portal_open_failure_marks_credential_error(monkeypatch):
    events = patch_credentials(monkeypatch, fail=True)

    with pytest.raises(RuntimeError, match="credenziali errate"):
        asyncio.run(CapacitasPortal("incass", 7).open())

    assert events["error"] == [(7, "Export ruoli: credenziali errate")]
    assert events["used"] == []


def test_portal_close_without_open_is_noop():
    asyncio.run(CapacitasPortal("incass", None).close())


def configure_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(service.settings, "capacitas_ruoli_export_state_path", str(tmp_path))
    monkeypatch.setattr(service.settings, "capacitas_ruoli_export_drive_folder_id", "root")
    monkeypatch.setattr(service.settings, "capacitas_ruoli_export_retry_base_seconds", 0)
    monkeypatch.setattr(service.settings, "capacitas_ruoli_export_weekday", 6)
    monkeypatch.setattr(service.settings, "capacitas_ruoli_export_hour", 7)
    monkeypatch.setattr(service.settings, "capacitas_ruoli_export_timezone", "Europe/Rome")


@pytest.mark.parametrize("failing_key", [None, "2024"])
def test_run_group_export_end_to_end(monkeypatch, tmp_path, failing_key):
    configure_settings(monkeypatch, tmp_path)
    patch_credentials(monkeypatch)
    drive = FakeDrive()
    monkeypatch.setattr(service, "GoogleDriveClient", lambda credentials, http: drive)
    monkeypatch.setattr(service, "drive_credentials_from_settings", lambda: "credentials")

    async def fetch(key: str) -> ExportPayload:
        if key == failing_key:
            raise ExportStepError("rotto", retryable=False)
        return ExportPayload(content=b"x", rows=3)

    monkeypatch.setattr(
        service, "build_targets", lambda group, manager, now: [target(["2025", "2024"], fetch)]
    )

    assert service.export_is_due("incass", NOW) is True
    state = asyncio.run(service.run_group_export("incass", NOW))

    assert state.snapshot == "2026-11-01"
    assert state.status == ("partial" if failing_key else "completed")
    assert drive.folders == [("inCASS", "root"), ("2026-11-01", "folder-inCASS")]
    assert drive.manifests[-1]["status"] == state.status
    # Completed runs wait for next week; partial ones wait RETRY_PARTIAL_AFTER before retrying.
    assert service.export_is_due("incass", NOW) is False


def test_run_group_export_keeps_partial_state_when_login_fails(monkeypatch, tmp_path):
    configure_settings(monkeypatch, tmp_path)
    patch_credentials(monkeypatch, fail=True)
    drive = FakeDrive()
    monkeypatch.setattr(service, "GoogleDriveClient", lambda credentials, http: drive)
    monkeypatch.setattr(service, "drive_credentials_from_settings", lambda: "credentials")

    with pytest.raises(RuntimeError):
        asyncio.run(service.run_group_export("inbollettini", NOW))

    state = service.state_store("inbollettini").load()
    assert state.status == "partial" and state.snapshot == "2026-11-01"
    assert drive.manifests == []


def test_utc_now_is_aware():
    assert service.utc_now().tzinfo is UTC
