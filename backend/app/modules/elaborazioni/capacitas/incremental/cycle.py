"""Acquisition, archive and promotion with durable checkpoints between external effects."""

import hashlib
import json
from datetime import datetime

from app.modules.elaborazioni.capacitas.incremental.journal import promote
from app.modules.elaborazioni.capacitas.incremental.normalize import (
    SnapshotInvalid,
    decode_workbook,
    digest,
)
from app.modules.elaborazioni.capacitas.incremental.observability import shadow_observation
from app.modules.elaborazioni.capacitas.incremental.storage import save_original
from app.services.google_drive import XLSX_MIME_TYPE


async def collect(db, cycle, client, config, policy) -> None:
    if not cycle.expected:
        years = await policy.run(
            client.list_ricerca_years,
            label="incremental_years",
            on_session_lost=client.refresh_session,
        )
        if not years or len(years) != len(set(years)):
            raise SnapshotInvalid("invalid_year_catalog")
        cycle.expected = sorted(years)
        db.commit()
    for year in cycle.expected:
        if year in cycle.artifacts:
            continue
        payload = await policy.run(
            lambda year=year: client.export_ricerca_avvisi(year),
            label="incremental_export",
            on_session_lost=client.refresh_session,
        )
        sha, path = save_original(config.root, payload.content)
        # Save provenance before parsing, including malformed/incomplete originals.
        artifact = {
            "snapshot_id": digest([cycle.id, year, sha]),
            "target": "incass_ricerca_avvisi",
            "year": year,
            "sha256": sha,
            "bytes": len(payload.content),
            "expected_rows": payload.rows,
            "acquired_at": datetime.now().astimezone().isoformat(),
            "path": str(path),
            "drive_id": None,
        }
        cycle.artifacts = {**cycle.artifacts, year: artifact}
        db.commit()
        decode_artifact(db, cycle, year, config)


def decode_artifact(db, cycle, year: str, config) -> None:
    from pathlib import Path

    artifact = cycle.artifacts[year]
    content = Path(artifact["path"]).read_bytes()
    if hashlib.sha256(content).hexdigest() != artifact["sha256"]:
        raise SnapshotInvalid("artifact_integrity_failure")
    rows, schema = decode_workbook(content, artifact["expected_rows"], config.header_map)
    if any(row["Anno"] != year for row in rows.values()):
        raise SnapshotInvalid("year_filter_mismatch")
    artifact = {
        **artifact,
        "rows": rows,
        "schema": schema,
        "signatures": {key: digest(row) for key, row in rows.items()},
    }
    cycle.artifacts = {**cycle.artifacts, year: artifact}
    db.commit()


async def archive(db, cycle, drive, parent: str, config, policy) -> None:
    from pathlib import Path

    folder = await policy.run(
        lambda: drive.ensure_folder(f"incremental-{cycle.id}", parent), label="incremental_folder"
    )
    for year, artifact in cycle.artifacts.items():
        if "rows" not in artifact:
            decode_artifact(db, cycle, year, config)
            artifact = cycle.artifacts[year]
        if artifact["drive_id"]:
            continue
        content = Path(artifact["path"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != artifact["sha256"]:
            raise SnapshotInvalid("artifact_integrity_failure")
        name = f"incass_ricerca_avvisi_{year}_{artifact['sha256']}.xlsx"

        async def upload(name=name, content=content):
            return await drive.find_child(name, folder) or await drive.upload_file(
                name, folder, content, XLSX_MIME_TYPE
            )

        drive_id = await policy.run(upload, label="incremental_archive")
        cycle.artifacts = {**cycle.artifacts, year: {**artifact, "drive_id": drive_id}}
        db.commit()
    manifest = {
        "cycle_id": cycle.id,
        "mode": cycle.mode,
        "state": "archived_pending_validation",
        "expected": cycle.expected,
        "artifacts": {
            year: {
                key: value
                for key, value in item.items()
                if key not in {"rows", "signatures", "path"}
            }
            for year, item in cycle.artifacts.items()
        },
    }
    await policy.run(
        lambda: drive.replace_or_upload(
            "manifest.json", folder, json.dumps(manifest).encode(), "application/json"
        ),
        label="incremental_manifest",
    )


async def execute_cycle(db, cycle, dependencies, config, now) -> None:
    if cycle.status == "validated":
        return
    cycle.attempts += 1
    cycle.report = {**cycle.report, "attempted_at": now.isoformat()}
    db.commit()
    try:
        await collect(db, cycle, dependencies.exports, config, dependencies.policy)
        await archive(
            db, cycle, dependencies.drive, dependencies.parent, config, dependencies.policy
        )
        # Observation must compare against the previous head, before promote updates it.
        cycle.rows = {
            key: row
            for item in cycle.artifacts.values()
            for key, row in item.get("rows", {}).items()
        }
        cycle.report = {**cycle.report, "ordinary_sync_comparison": shadow_observation(db, cycle)}
        promote(db, cycle, config, now)
    except Exception as exc:
        db.rollback()
        if isinstance(exc, SnapshotInvalid):
            cycle.status = "invalid"
        else:
            cycle.status = "failed" if cycle.attempts >= config.max_attempts else "partial"
        cycle.report = {
            **cycle.report,
            "error": str(exc) if isinstance(exc, SnapshotInvalid) else type(exc).__name__,
            "fallback": "legacy_autosync_unchanged",
        }
        db.commit()
        raise
