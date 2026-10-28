"""Posta Online outbox jobs: address check, drafts, reconciliation, deletion.

The worker prepares drafts and reads what Poste shows. INVIA is pressed by an
operator on Poste; an item becomes "sent" only when the archive shows it.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from app.models.posta_online import PostaOnlineRegisteredMailSyncJob
from app.modules.ruolo.services import poste_dispatch_work as work
from app.modules.ruolo.services.poste_dispatch_address import (
    match_address,
    normalize_suggestions,
    search_term,
    suggestion_label,
)
from app.modules.ruolo.services.poste_dispatch_state import DRAFT_STATUSES, DispatchConflict
from app.services.elaborazioni_posta_online import (
    mark_credential_error,
    mark_credential_used,
    pick_credential,
)
from posta_online_client import PostaOnlineBrowserClient, PostaOnlineScrapeConfig
from posta_online_dispatch import DraftNotSubmitted, DraftSubmitUncertain, PostaOnlineDispatchPortal

logger = logging.getLogger(__name__)

PRICE_SETTLE_SECONDS = 45
MAX_CONSECUTIVE_FAILURES = 2


def record_sent(db, item_id: UUID, **kwargs) -> None:
    # Imported on use, like the archive import in posta_online_sync: it loads the whole
    # tributi repository, which the worker does not need at start-up.
    from app.modules.ruolo.services.poste_dispatch_reconcile import record_sent as record

    record(db, item_id, **kwargs)


@dataclass
class DispatchRun:
    session_factory: sessionmaker
    job_id: int
    lot_id: UUID
    portal: PostaOnlineDispatchPortal
    counters: dict[str, int] = field(default_factory=dict)

    def write(self, action, *args, **kwargs):
        with self.session_factory() as db:
            result = action(db, *args, job_id=self.job_id, **kwargs)
            db.commit()
        return result

    def items(self, statuses: tuple[str, ...]) -> list[work.WorkItem]:
        with self.session_factory() as db:
            return work.lot_items(db, self.lot_id, statuses)

    def count(self, key: str) -> None:
        self.counters[key] = self.counters.get(key, 0) + 1


async def run_addresses(run: DispatchRun) -> None:
    run.portal.phase = "addresses"
    await run.portal.open_send_form()
    for item in run.items(("address_pending",)):
        suggestions = normalize_suggestions(
            await run.portal.suggestions(search_term(item.recipient))
        )
        match = match_address(item.recipient, suggestions)
        labels = [suggestion_label(suggestion) for suggestion in suggestions]
        run.write(
            work.record_address,
            item.id,
            suggestion=match.suggestion,
            reason=match.reason,
            labels=labels,
        )
        run.count("found" if match.suggestion else "review")


def _by_name(rows: list[work.DraftRow]) -> dict[str, list[work.DraftRow]]:
    names: dict[str, list[work.DraftRow]] = {}
    for row in rows:
        names.setdefault(row.name, []).append(row)
    return names


async def _create_one(run: DispatchRun, item: work.WorkItem) -> bool:
    async def before_submit() -> None:
        if not run.write(work.mark_draft_creating, item.id):
            raise DraftNotSubmitted("Stato dell'avviso cambiato: bozza non creata")

    try:
        with run.session_factory() as db:
            artifact = work.artifact_for_upload(db, item.id)
        await run.portal.create_draft(item, artifact, before_submit)
    except (DraftNotSubmitted, DispatchConflict) as exc:
        run.write(work.record_draft_failure, item.id, submitted=False, error=str(exc))
        return False
    except DraftSubmitUncertain as exc:
        logger.warning("Poste dispatch %s: esito CONTINUA incerto: %s", item.shipment_name, exc)
    found = _by_name(await run.portal.list_drafts()).get(item.shipment_name, [])
    if len(found) == 1:
        run.write(work.record_draft_row, item.id, row=found[0])
        return True
    error = (
        "Più bozze con lo stesso nome dopo CONTINUA"
        if found
        else "Bozza non trovata in Verifica e invia dopo CONTINUA"
    )
    run.write(work.record_draft_failure, item.id, submitted=True, error=error)
    return False


async def _create_missing_drafts(run: DispatchRun, rows: list[work.DraftRow]) -> None:
    existing, failures = _by_name(rows), 0
    for item in run.items(work.DRAFT_READY_STATUSES):
        matches = existing.get(item.shipment_name, [])
        if len(matches) == 1:
            run.write(work.record_draft_row, item.id, row=matches[0])
            continue
        if matches:
            run.write(
                work.record_anomaly,
                item.id,
                message="Più bozze Poste con questo nome: eliminarle prima di ricrearla",
            )
            continue
        created = await _create_one(run, item)
        run.count("created" if created else "failed")
        failures = 0 if created else failures + 1
        if failures >= MAX_CONSECUTIVE_FAILURES:
            raise RuntimeError("Due bozze consecutive non create: lavorazione interrotta")


async def run_drafts(run: DispatchRun) -> None:
    run.portal.phase = "draft"
    rows = await run.portal.list_drafts()
    run.write(work.apply_drafts_snapshot, run.lot_id, rows=rows)
    await _create_missing_drafts(run, rows)
    if run.counters.get("created"):
        await asyncio.sleep(PRICE_SETTLE_SECONDS)
    run.write(work.apply_drafts_snapshot, run.lot_id, rows=await run.portal.list_drafts())


async def _settle_missing(run: DispatchRun, missing: list[UUID]) -> None:
    """Items gone from the drafts were sent by the operator, deleted or expired."""
    if not missing:
        return
    index, complete = await run.portal.archive_index()
    for item in [item for item in run.items(tuple(DRAFT_STATUSES)) if item.id in missing]:
        shipment_ids = index.get(item.shipment_name, [])
        if len(shipment_ids) == 1:
            detail_html = await run.portal.client.fetch_detail_html(shipment_ids[0])
            run.write(record_sent, item.id, id_invio=shipment_ids[0], detail_html=detail_html)
            run.count("sent")
        elif shipment_ids:
            run.write(
                work.record_anomaly,
                item.id,
                message="Più spedizioni in archivio con questo nome: verificare su Poste",
            )
        elif complete:
            run.write(work.record_missing, item.id)
            run.count("missing")
        else:
            run.write(
                work.record_anomaly,
                item.id,
                message="Archivio Poste non letto per intero: stato non confermato",
            )


async def run_reconcile(run: DispatchRun) -> None:
    run.portal.phase = "reconcile"
    missing = run.write(work.apply_drafts_snapshot, run.lot_id, rows=await run.portal.list_drafts())
    await _settle_missing(run, missing)


async def run_delete(run: DispatchRun) -> None:
    run.portal.phase = "reconcile"
    rows = await run.portal.list_drafts()
    missing = run.write(work.apply_drafts_snapshot, run.lot_id, rows=rows)
    existing, requested = _by_name(rows), []
    for item in run.items(("cancel_requested",)):
        matches = existing.get(item.shipment_name, [])
        if len(matches) == 1:
            await run.portal.delete_draft(matches[0].draft_id)
            requested.append(item.id)
    remaining = _by_name(await run.portal.list_drafts())
    for item in [item for item in run.items(("cancel_requested",)) if item.id in requested]:
        if item.shipment_name in remaining:
            run.write(
                work.record_anomaly,
                item.id,
                message="Bozza ancora presente su Poste dopo l'eliminazione",
            )
        else:
            run.write(work.record_deleted, item.id)
            run.count("deleted")
    await _settle_missing(run, missing)


HANDLERS = {
    "poste_dispatch_addresses": run_addresses,
    "poste_dispatch_drafts": run_drafts,
    "poste_dispatch_reconcile": run_reconcile,
    "poste_dispatch_delete": run_delete,
}


def _finish(session_factory: sessionmaker, job_id: int, status: str, result: dict) -> None:
    with session_factory() as db:
        job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        job.status = status
        job.error_detail = result.get("error")
        job.completed_at = datetime.now(UTC)
        job.result_json = result
        db.commit()


def _job_context(session_factory: sessionmaker, job_id: int):
    with session_factory() as db:
        job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        credential, password = pick_credential(db, job.credential_id)
        config = PostaOnlineScrapeConfig(
            min_delay_ms=credential.min_delay_ms,
            max_delay_ms=credential.max_delay_ms,
            include_contacts=False,
        )
        return (
            job.mode,
            UUID((job.payload_json or {})["lot_id"]),
            credential.id,
            credential.username,
            password,
            config,
        )


async def run_dispatch_job(
    *,
    job_id: int,
    session_factory: sessionmaker,
    headless: bool,
    _client_class=PostaOnlineBrowserClient,
    _portal_class=PostaOnlineDispatchPortal,
) -> None:
    started_at, credential_id, logged_in = datetime.now(UTC), None, False
    try:
        mode, lot_id, credential_id, username, password, config = _job_context(
            session_factory, job_id
        )
        config.headless = headless
        async with _client_class(config) as client:
            portal = _portal_class(client)
            await portal.install_guard()
            await client.login(username, password)
            logged_in = True
            run = DispatchRun(session_factory, job_id, lot_id, portal)
            await HANDLERS[mode](run)
        result = {
            "started_at": started_at.isoformat(),
            "counters": run.counters,
            "blocked": portal.blocked,
        }
        _finish(session_factory, job_id, "succeeded", result)
        with session_factory() as db:
            mark_credential_used(db, credential_id)
    except Exception as exc:
        logger.exception("Job invio Poste %s fallito", job_id)
        _finish(
            session_factory,
            job_id,
            "failed",
            {"started_at": started_at.isoformat(), "error": str(exc)},
        )
        if not logged_in and credential_id is not None:
            with session_factory() as db:
                mark_credential_error(db, credential_id, str(exc))
                db.commit()
