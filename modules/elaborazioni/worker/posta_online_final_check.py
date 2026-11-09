"""Independent final pass: read every draft and archive page; never modify the portal."""

from datetime import UTC, datetime

from app.modules.ruolo.services.poste_dispatch_final_check import record_account_snapshot


async def run_final_check(run) -> None:
    started = datetime.now(UTC)
    run.portal.phase = "reconcile"
    drafts = await run.portal.list_drafts()
    archive, complete = await run.portal.archive_index()
    if not complete:
        raise RuntimeError("Archivio Poste incompleto: verifica finale non certificabile")
    run.write(
        record_account_snapshot,
        run.lot_id,
        snapshot={
            "started_at": started.isoformat(),
            "checked_at": datetime.now(UTC).isoformat(),
            "drafts": [
                {"name": row.name, "draft_id": row.draft_id, "status": row.status} for row in drafts
            ],
            "archive": archive,
        },
    )
    run.count("accounts_verified")
