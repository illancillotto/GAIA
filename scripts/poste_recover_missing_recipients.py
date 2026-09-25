"""One-off, fail-closed recovery of the 437 Poste recipient placeholders."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models.posta_online import PostaOnlineRegisteredMailSyncJob
from app.modules.ruolo.models import RuoloTributiRegisteredMail
from app.modules.ruolo.tributi_repositories import _parse_posta_online_detail_html
from app.services.elaborazioni_posta_online import pick_credential
from posta_online_client import PostaOnlineBrowserClient, PostaOnlineScrapeConfig

EXPECTED_COUNT = 437
PLACEHOLDER_WARNING = "destinatario_table_not_found"


def _write_private_json(path: Path, value: object) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=True, sort_keys=True, default=str)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _checkpoint_ids(path: Path) -> tuple[list[str], str]:
    raw = path.read_bytes()
    payload = json.loads(raw)
    ids = [str(item) for item in payload["archive_ids"]]
    if len(ids) != EXPECTED_COUNT or len(set(ids)) != EXPECTED_COUNT:
        raise RuntimeError("Il checkpoint non contiene esattamente 437 ID univoci")
    if payload.get("details"):
        raise RuntimeError(
            "Il checkpoint originale contiene gia dettagli: riesaminare prima di procedere"
        )
    return ids, hashlib.sha256(raw).hexdigest()


def _placeholder(db, shipment_id: str) -> RuoloTributiRegisteredMail:
    rows = db.scalars(
        select(RuoloTributiRegisteredMail).where(
            RuoloTributiRegisteredMail.source_system == "posta_online",
            RuoloTributiRegisteredMail.source_shipment_id == shipment_id,
        )
    ).all()
    if len(rows) != 1:
        raise RuntimeError(f"{shipment_id}: attesa una sola riga segnaposto, trovate {len(rows)}")
    row = rows[0]
    raw = row.raw_payload_json or {}
    if (
        row.recipient_index != 0
        or row.recipient_address
        or row.avviso_id
        or row.subject_id
        or row.recovered_payment_id
        or row.anomaly_key != "missing_recipient"
        or not isinstance(raw, dict)
        or raw.get("raw", {}).get("warning") != PLACEHOLDER_WARNING
    ):
        raise RuntimeError(f"{shipment_id}: riga diversa dal segnaposto atteso")
    return row


def _prepare_backup(factory, ids: list[str], path: Path, digest: str) -> None:
    if path.exists():
        backup = json.loads(path.read_text(encoding="utf-8"))
        if backup.get("source_sha256") != digest or len(backup.get("rows", [])) != EXPECTED_COUNT:
            raise RuntimeError("Backup preesistente incompatibile")
        return
    with factory() as db:
        rows = [_placeholder(db, shipment_id) for shipment_id in ids]
        snapshot = [
            {column.name: getattr(row, column.name) for column in row.__table__.columns}
            for row in rows
        ]
    _write_private_json(
        path, {"source_sha256": digest, "created_at": datetime.now(UTC), "rows": snapshot}
    )


def _validated_rows(shipment_id: str, html: str) -> list[dict]:
    rows = _parse_posta_online_detail_html(html, fallback_id=shipment_id, source_index=1)
    if not rows or any(
        row["source_shipment_id"] != shipment_id
        or not row.get("recipient_name")
        or not row.get("recipient_address")
        for row in rows
    ):
        raise RuntimeError(f"{shipment_id}: dettaglio senza destinatario e indirizzo validi")
    return rows


def _persist(factory, shipment_id: str, rows: list[dict]) -> None:
    if not rows or (len(rows) > 1 and [row.get("recipient_index") for row in rows] != [1, 2]):
        raise RuntimeError(
            f"{shipment_id}: indici destinatari inattesi, richiede revisione manuale"
        )
    with factory.begin() as db:
        mail = _placeholder(db, shipment_id)
        for index, detail in enumerate(rows):
            if index:
                recipient = RuoloTributiRegisteredMail(
                    source_system="posta_online",
                    source_shipment_id=shipment_id,
                    recipient_index=detail["recipient_index"],
                    import_job_id=mail.import_job_id,
                    annualita_json=mail.annualita_json,
                )
                db.add(recipient)
            else:
                recipient = mail
                if len(rows) > 1:
                    recipient.recipient_index = detail["recipient_index"]
            recipient.shipment_name = detail.get("shipment_name")
            recipient.service = detail.get("service")
            recipient.status_label = detail.get("status_label")
            recipient.sent_at = detail.get("sent_at")
            recipient.recipient_name = detail["recipient_name"]
            recipient.recipient_address = detail["recipient_address"]
            recipient.recipient_city = detail.get("recipient_city")
            recipient.recipient_province = detail.get("recipient_province")
            recipient.recipient_zipcode = detail.get("recipient_zipcode")
            recipient.tracking_number = detail.get("tracking_number")
            recipient.price_amount = detail.get("price_amount")
            recipient.match_reason = "Associazione non valutata durante recupero Poste"
            recipient.anomaly_key = "association_not_evaluated"
            recipient.raw_payload_json = {
                "raw": detail.get("raw"),
                "recovery_source": "poste_recover_missing_recipients",
            }


async def _recover(factory, ids: list[str], state_path: Path, limit: int) -> None:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    completed = set(state["completed_ids"])
    with factory() as db:
        credential, password = pick_credential(db)
        username = credential.username
    config = PostaOnlineScrapeConfig(
        min_delay_ms=5000,
        max_delay_ms=10000,
        burst_request_limit=12,
        burst_pause_min_ms=60000,
        burst_pause_max_ms=120000,
        max_retries=0,
        include_contacts=False,
        headless=True,
    )
    attempted = 0
    consecutive_errors = 0
    async with PostaOnlineBrowserClient(config) as client:
        await client.login(username, password)
        for shipment_id in ids:
            if shipment_id in completed or attempted >= limit:
                continue
            attempted += 1
            try:
                html = await client.fetch_detail_html(shipment_id)
                _persist(factory, shipment_id, _validated_rows(shipment_id, html))
            except Exception as exc:
                state["errors"][shipment_id] = {
                    "at": datetime.now(UTC).isoformat(),
                    "error": str(exc)[:300],
                }
                consecutive_errors += 1
                print(
                    f"{shipment_id}: errore ({type(exc).__name__}); consecutivi={consecutive_errors}",
                    flush=True,
                )
                _write_private_json(state_path, state)
                if consecutive_errors >= 2:
                    print("Circuito aperto dopo due errori consecutivi", flush=True)
                    break
                continue
            completed.add(shipment_id)
            state["completed_ids"] = sorted(completed)
            state["errors"].pop(shipment_id, None)
            consecutive_errors = 0
            _write_private_json(state_path, state)
            print(
                f"{shipment_id}: recuperato; totale={len(completed)}/{EXPECTED_COUNT}", flush=True
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.limit <= EXPECTED_COUNT:
        parser.error("--limit deve essere tra 1 e 437")
    ids, digest = _checkpoint_ids(args.checkpoint)
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    factory = sessionmaker(engine)
    with factory() as db:
        job = db.get(PostaOnlineRegisteredMailSyncJob, 9)
        if job is None or job.status != "cancelled":
            raise RuntimeError("Il job 9 non e inattivo")
    backup_path = args.state.with_name("poste-recovery-437-backup.json")
    _prepare_backup(factory, ids, backup_path, digest)
    if args.state.exists():
        state = json.loads(args.state.read_text(encoding="utf-8"))
        if state.get("source_sha256") != digest:
            raise RuntimeError("Stato di recupero incompatibile con il checkpoint")
    else:
        _write_private_json(
            args.state, {"source_sha256": digest, "completed_ids": [], "errors": {}}
        )
    if args.preflight_only:
        print(f"Preflight riuscito: {EXPECTED_COUNT} segnaposto, backup {backup_path}")
        return
    asyncio.run(_recover(factory, ids, args.state, args.limit))


if __name__ == "__main__":
    main()
