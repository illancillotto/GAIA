"""Recover evidence for known sent mail, with private resumable files and no DB writes."""

import argparse
import asyncio
import fcntl
import hashlib
import json
import os
import random
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import text

from app.core.database import SessionLocal
from app.services.elaborazioni_posta_online import pick_credential
from posta_online_client import PostaOnlineBrowserClient, PostaOnlineScrapeConfig
from posta_online_delivery import (
    InteractiveCheckRequired,
    read_acceptance_receipt,
    read_tracking,
    tracking_code,
)
from posta_online_dispatch import PostaOnlineDispatchPortal
from posta_online_leases import acquire_portal_lease

_PLAN_SQL = """
select cast(i.id as text) item_id, cast(m.id as text) mail_id,
       l.credential_id account_id, c.username account_username,
       l.poste_username lot_username, i.poste_draft_id shipment_id,
       m.source_shipment_id imported_shipment_id,
       i.tracking_number tracking, m.tracking_number imported_tracking
from ruolo_poste_dispatch_items i
join ruolo_poste_dispatch_lots l on l.id=i.lot_id
left join posta_online_credentials c on c.id=l.credential_id
left join ruolo_tributi_registered_mails m on m.id=i.registered_mail_id
where i.status='sent'
order by l.credential_id, i.poste_draft_id, i.id
"""


def private_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def save_json(path: Path, payload) -> None:
    private_write(path, json.dumps(payload, ensure_ascii=False, indent=2).encode())


def load_plan(output: Path) -> list[dict]:
    with SessionLocal() as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        rows = [dict(row) for row in db.execute(text(_PLAN_SQL)).mappings()]
        db.rollback()
    for row in rows:
        validate_identity(row)
    path = output / "plan.json"
    if path.exists() and json.loads(path.read_text()) != rows:
        raise ValueError("Il perimetro degli invii è cambiato: usare una nuova directory")
    save_json(path, rows)
    return rows


def validate_identity(row: dict) -> None:
    if not row["mail_id"] or row["shipment_id"] != row["imported_shipment_id"]:
        raise ValueError("Collegamento spedizione/import non coerente")
    if re.fullmatch(r"[0-9]+", str(row["shipment_id"])) is None:
        raise ValueError("Identificativo spedizione non valido")
    if tracking_code(row["tracking"]) != row["imported_tracking"]:
        raise ValueError("Tracking spedizione/import non coerente")
    username = (row["account_username"] or "").strip().casefold()
    if not username or username != (row["lot_username"] or "").strip().casefold():
        raise ValueError("Account corrente diverso dall'account mittente del lotto")


def pending(rows: list[dict], output: Path, phase: str, retry_errors: bool) -> list[dict]:
    result = []
    for row in rows:
        path = output / row["item_id"] / f"{phase}.json"
        if not path.exists():
            result.append(row)
            continue
        saved = json.loads(path.read_text())
        if phase == "receipt" and saved.get("available"):
            pdf = path.with_name("acceptance.pdf")
            if not pdf.exists() or hashlib.sha256(pdf.read_bytes()).hexdigest() != saved["sha256"]:
                raise ValueError("Ricevuta salvata assente o alterata: revisione richiesta")
        if retry_errors and saved.get("error"):
            result.append(row)
    return result


def observation(output: Path, row: dict, phase: str, **result) -> None:
    save_json(
        output / row["item_id"] / f"{phase}.json",
        {
            "account_id": row["account_id"],
            "shipment_id": row["shipment_id"],
            "mail_id": row["mail_id"],
            "tracking": row["tracking"],
            "observed_at": datetime.now(UTC).isoformat(),
            **result,
        },
    )


async def recover_tracking(rows: list[dict], output: Path) -> None:
    failures = 0
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as http:
        for row in rows:
            await asyncio.sleep(random.uniform(5, 9))
            try:
                data = await read_tracking(http, row["tracking"])
                observation(output, row, "tracking", payload=data)
                failures = 0
            except Exception as exc:
                observation(output, row, "tracking", error=str(exc))
                failures += 1
                if (
                    isinstance(exc, InteractiveCheckRequired)
                    or "HTTP 403" in str(exc)
                    or "HTTP 429" in str(exc)
                    or failures >= 2
                ):
                    break


async def recover_account(rows: list[dict], output: Path) -> None:
    account = rows[0]
    with SessionLocal() as db:
        credential, password = pick_credential(db, account["account_id"])
        if credential.username.strip().casefold() != account["account_username"].strip().casefold():
            raise ValueError("Account modificato dopo il piano di recupero")
        username = credential.username
        lease = acquire_portal_lease(db.get_bind(), None)
    if lease is None:
        raise RuntimeError("Portale Poste occupato: nessuna sessione avviata")
    try:
        config = PostaOnlineScrapeConfig(
            min_delay_ms=5000,
            max_delay_ms=10000,
            max_retries=0,
            include_contacts=False,
            storage_state_path=None,
            cdp_url=None,
        )
        async with PostaOnlineBrowserClient(config) as client:
            portal = PostaOnlineDispatchPortal(client)
            await portal.install_guard()
            await client.login(username, password)
            portal.phase = "reconcile"
            await recover_receipts(client, rows, output)
    finally:
        lease.close()


async def recover_receipts(client, rows: list[dict], output: Path) -> None:
    for row in rows:
        try:
            detail = await client.fetch_detail_html(row["shipment_id"])
            receipt = await read_acceptance_receipt(client, detail, row["tracking"])
            if receipt is None:
                observation(output, row, "receipt", available=False)
                continue
            content, metadata = receipt
            private_write(output / row["item_id"] / "acceptance.pdf", content)
            observation(output, row, "receipt", available=True, **metadata)
        except Exception as exc:
            observation(output, row, "receipt", error=str(exc))
            # Stop this session on any failed detail/receipt. Never try a different
            # account for the same shipment and never repeat a refused request.
            break


async def run(args) -> None:
    rows = load_plan(args.output)
    if args.account is not None:
        rows = [row for row in rows if row["account_id"] == args.account]
    if args.phase == "plan":
        print(json.dumps({"planned": len(rows)}), flush=True)
        return
    phase = "tracking" if args.phase == "tracking" else "receipt"
    rows = pending(rows, args.output, phase, args.retry_errors)[: args.limit]
    if phase == "tracking":
        await recover_tracking(rows, args.output)
        return
    accounts = defaultdict(list)
    for row in rows:
        accounts[row["account_id"]].append(row)
    for account_rows in accounts.values():
        try:
            await recover_account(account_rows, args.output)
        except Exception as exc:
            save_json(
                args.output / f"account-{account_rows[0]['account_id']}-error.json",
                {"observed_at": datetime.now(UTC).isoformat(), "error": str(exc)},
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--phase", choices=("plan", "tracking", "receipts"), default="plan")
    parser.add_argument("--account", type=int)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--retry-errors", action="store_true")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit deve essere positivo")
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (args.output / ".recovery.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        asyncio.run(run(args))


if __name__ == "__main__":
    main()
