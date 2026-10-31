"""Weekly export of the Capacitas ruoli grids (inCASS, inBOLLETTINI) to dated Google Drive snapshots."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.elaborazioni.capacitas.apps.inbollettini.exports import InBollettiniExportClient
from app.modules.elaborazioni.capacitas.apps.incass.exports import InCassExportClient, minuta_years
from app.modules.elaborazioni.capacitas.export_workbook import ExportPayload
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
from app.services.capacitas_ruoli_export_retry import RetryPolicy
from app.services.capacitas_ruoli_export_state import (
    ITEM_EMPTY,
    ITEM_FAILED,
    ITEM_UPLOADED,
    ExportRunState,
    ExportStateStore,
    WeeklySchedule,
)
from app.services.elaborazioni_capacitas import (
    mark_credential_error,
    mark_credential_used,
    pick_credential,
)
from app.services.google_drive import (
    XLSX_MIME_TYPE,
    GoogleDriveClient,
    drive_credentials_from_settings,
)

logger = logging.getLogger(__name__)

GROUP_INCASS = "incass"
GROUP_INBOLLETTINI = "inbollettini"
GROUP_FOLDERS = {GROUP_INCASS: "inCASS", GROUP_INBOLLETTINI: "inBOLLETTINI"}
MANIFEST_NAME = "manifest.json"
RETRY_PARTIAL_AFTER = timedelta(hours=1)
DRIVE_TIMEOUT_SECONDS = 300.0


@dataclass(frozen=True, slots=True)
class ExportTarget:
    name: str
    list_keys: Callable[[], Awaitable[list[str]]]
    fetch: Callable[[str], Awaitable[ExportPayload]]


def export_file_name(target: str, key: str) -> str:
    return f"{target}_{re.sub(r'[^A-Za-z0-9._-]+', '_', key)}.xlsx"


def utc_now() -> datetime:
    return datetime.now(UTC)


class CapacitasPortal:
    """One logged-in Capacitas session for an app; re-login is what the retry policy calls on expiry."""

    def __init__(self, app_key: str, credential_id: int | None) -> None:
        self.app_key = app_key
        self.credential_id = credential_id
        self.manager: CapacitasSessionManager | None = None

    async def open(self) -> CapacitasSessionManager:
        with SessionLocal() as db:
            credential, password = pick_credential(db, self.credential_id)
            credential_id, username = credential.id, credential.username
        self.manager = CapacitasSessionManager(username, password)
        try:
            await self.relogin()
        except Exception as exc:
            with SessionLocal() as db:
                mark_credential_error(db, credential_id, f"Export ruoli: {exc}")
            raise
        with SessionLocal() as db:
            mark_credential_used(db, credential_id)
        return self.manager

    async def relogin(self) -> None:
        await self.manager.login()
        await self.manager.activate_app(self.app_key)

    async def close(self) -> None:
        if self.manager is not None:
            await self.manager.close()


def build_targets(
    group: str, manager: CapacitasSessionManager, now: datetime
) -> list[ExportTarget]:
    if group == GROUP_INBOLLETTINI:
        bollettini = InBollettiniExportClient(manager)
        return [
            ExportTarget(
                "inbollettini_registro_bollettini",
                bollettini.list_esercizi,
                bollettini.export_registro,
            )
        ]
    incass = InCassExportClient(
        manager, progress_timeout_seconds=settings.capacitas_ruoli_export_progress_timeout_seconds
    )

    async def ruoli() -> list[str]:
        return minuta_years(now.year)

    return [
        ExportTarget(
            "incass_ricerca_avvisi", incass.list_ricerca_years, incass.export_ricerca_avvisi
        ),
        ExportTarget("incass_avvisi_minuta", ruoli, incass.export_avvisi_minuta),
    ]


@dataclass
class SnapshotRun:
    """Uploads one snapshot, recording each file in the resumable state as soon as it is settled."""

    drive: GoogleDriveClient
    folder_id: str
    state: ExportRunState
    store: ExportStateStore
    policy: RetryPolicy
    on_session_lost: Callable[[], Awaitable[None]]

    def _settle(self, file_name: str, outcome: dict[str, object]) -> None:
        self.state.record(file_name, {**outcome, "settled_at": utc_now().isoformat()})
        self.store.save(self.state)

    async def export_target(self, target: ExportTarget) -> None:
        try:
            keys = await self.policy.run(
                target.list_keys, label=target.name, on_session_lost=self.on_session_lost
            )
        except Exception as exc:
            logger.exception("Export ruoli %s: elenco anni non disponibile", target.name)
            self._settle(f"{target.name}:elenco", {"status": ITEM_FAILED, "error": str(exc)[:500]})
            return
        for key in keys:
            await self.export_item(target, key)

    async def export_item(self, target: ExportTarget, key: str) -> None:
        file_name = export_file_name(target.name, key)
        if self.state.is_done(file_name):
            return
        try:
            payload = await self.policy.run(
                lambda: target.fetch(key), label=file_name, on_session_lost=self.on_session_lost
            )
            drive_id = await self._upload(file_name, payload) if payload.rows else None
        except Exception as exc:
            logger.exception("Export ruoli %s fallito", file_name)
            self._settle(file_name, {"status": ITEM_FAILED, "error": str(exc)[:500]})
            return
        status = ITEM_UPLOADED if drive_id else ITEM_EMPTY
        self._settle(
            file_name,
            {
                "status": status,
                "rows": payload.rows,
                "bytes": len(payload.content),
                "drive_file_id": drive_id,
            },
        )

    async def _upload(self, file_name: str, payload: ExportPayload) -> str:
        async def upload() -> str:
            existing = await self.drive.find_child(file_name, self.folder_id)
            return existing or await self.drive.upload_file(
                file_name, self.folder_id, payload.content, XLSX_MIME_TYPE
            )

        return await self.policy.run(upload, label=f"upload {file_name}")

    async def publish_manifest(self, group: str) -> None:
        manifest = json.dumps(
            {"group": group, **asdict(self.state)}, indent=2, ensure_ascii=False
        ).encode()

        async def publish() -> str:
            return await self.drive.replace_or_upload(
                MANIFEST_NAME, self.folder_id, manifest, "application/json"
            )

        await self.policy.run(publish, label=f"manifest {group}")


async def snapshot_folder(drive: GoogleDriveClient, group: str, snapshot: str) -> str:
    group_folder = await drive.ensure_folder(
        GROUP_FOLDERS[group], settings.capacitas_ruoli_export_drive_folder_id
    )
    return await drive.ensure_folder(snapshot, group_folder)


def default_policy() -> RetryPolicy:
    return RetryPolicy(
        max_attempts=settings.capacitas_ruoli_export_max_attempts,
        base_delay_seconds=settings.capacitas_ruoli_export_retry_base_seconds,
    )


def state_store(group: str) -> ExportStateStore:
    return ExportStateStore(Path(settings.capacitas_ruoli_export_state_path) / f"{group}.json")


def schedule_from_settings() -> WeeklySchedule:
    return WeeklySchedule(
        weekday=settings.capacitas_ruoli_export_weekday,
        hour=settings.capacitas_ruoli_export_hour,
        timezone=settings.capacitas_ruoli_export_timezone,
    )


def export_is_due(group: str, now: datetime) -> bool:
    snapshot = schedule_from_settings().snapshot_label(now)
    return state_store(group).load().is_due(snapshot, now, RETRY_PARTIAL_AFTER)


async def run_group_export(group: str, now: datetime | None = None) -> ExportRunState:
    """Export every target of ``group`` into this week's snapshot, resuming files already settled."""
    now = now or utc_now()
    store, policy = state_store(group), default_policy()
    state = store.load()
    state.start(schedule_from_settings().snapshot_label(now), now)
    store.save(state)
    portal = CapacitasPortal(group, settings.capacitas_ruoli_export_credential_id)
    async with httpx.AsyncClient(timeout=DRIVE_TIMEOUT_SECONDS) as drive_http:
        drive = GoogleDriveClient(drive_credentials_from_settings(), drive_http)
        folder_id = await policy.run(
            lambda: snapshot_folder(drive, group, state.snapshot), label="cartella Drive"
        )
        run = SnapshotRun(drive, folder_id, state, store, policy, portal.relogin)
        try:
            manager = await portal.open()
            for target in build_targets(group, manager, now):
                await run.export_target(target)
        finally:
            await portal.close()
        state.finish()
        store.save(state)
        await run.publish_manifest(group)
    logger.info("Export ruoli %s snapshot %s: %s", group, state.snapshot, state.status)
    return state
