from __future__ import annotations

import argparse
import asyncio
import fcntl
import json
import logging
import sys
from pathlib import Path

import httpx

from app.core.database import SessionLocal
from app.models.application_user import ApplicationUser
from app.modules.elaborazioni.capacitas.apps.incass.client import CapacitasInCassSessionExpiredError
from app.modules.elaborazioni.capacitas.apps.involture.client import CapacitasSessionExpiredError
from app.modules.elaborazioni.capacitas.recovery_identity import audit_recovery_subjects
from app.modules.elaborazioni.capacitas.recovery_manifest import RecoveryManifest
from app.modules.elaborazioni.capacitas.recovery_service import RecoveryRunner
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
from app.services.elaborazioni_capacitas import pick_credential


def parser():
    command = argparse.ArgumentParser(
        description="Recupero Capacitas completo dall'anagrafica GAIA"
    )
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--apply", action="store_true")
    command.add_argument("--credential-id", type=int, default=1)
    command.add_argument("--user-id", type=int, default=1)
    command.add_argument("--priority-identifier", default="")
    command.add_argument("--retry-failed", action="store_true")
    command.add_argument("--status", action="store_true")
    command.add_argument("--max-tasks", type=int)
    return command


def prepare_manifest(db, args, manifest):
    eligible, blocked = audit_recovery_subjects(db)
    args.output.joinpath("identity-audit.json").write_text(
        json.dumps(
            {
                "eligible": len(eligible),
                "review_flagged_eligible": sum(record.requires_review for record in eligible),
                "blocked": blocked,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    priority = None
    for subject in eligible:
        payload = {"identifiers": list(subject.identifiers)}
        manifest.add(subject.subject_id, "01_incass", "all", payload, commit=False)
        manifest.add(subject.subject_id, "02_discovery", "all", payload, commit=False)
        if args.priority_identifier.upper() in subject.identifiers:
            priority = subject.subject_id
    manifest.connection.commit()
    return priority


async def execute_with_retry(runner, task):
    attempt = 0
    while True:
        try:
            return await runner.execute(task)
        except (
            httpx.TransportError,
            CapacitasSessionExpiredError,
            CapacitasInCassSessionExpiredError,
        ):
            runner.db.rollback()
            if attempt == 2:
                raise
            attempt += 1
            await runner.manager.close()
            await asyncio.sleep(2 * attempt)
            await runner.manager.login()
            await runner.manager.activate_app("incass")
            await runner.manager.activate_app("involture")


async def run_tasks(runner, priority, max_tasks):
    processed = 0
    while max_tasks is None or processed < max_tasks:
        task = runner.manifest.next_task(priority)
        if task is None:
            break
        try:
            result = await execute_with_retry(runner, task)
            runner.manifest.finish(task, result=result)
            status = "succeeded"
        except Exception as error:
            runner.db.rollback()
            runner.manifest.finish(task, error=str(error))
            status = "failed"
        processed += 1
        print(json.dumps({"task": task["task_key"], "status": status}), flush=True)
        await asyncio.sleep(0.25)
    return runner.manifest.summary()


async def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    with args.output.joinpath("campaign.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = RecoveryManifest(args.output / "manifest.sqlite")
        try:
            if args.status:
                print(json.dumps(manifest.summary()), flush=True)
                return
            with SessionLocal() as db:
                db.get_bind().hide_parameters = True
                priority = prepare_manifest(db, args, manifest)
                if not args.apply:
                    print(json.dumps(manifest.summary()), flush=True)
                    return
                if db.get(ApplicationUser, args.user_id) is None:
                    raise ValueError("Utente di audit GAIA inesistente")
                credential, password = pick_credential(db, args.credential_id)
                async with CapacitasSessionManager(credential.username, password) as manager:
                    await manager.activate_app("incass")
                    await manager.activate_app("involture")
                    if args.retry_failed:
                        manifest.retry_failed()
                    runner = RecoveryRunner(db, manager, manifest, args.output, args.user_id)
                    summary = await run_tasks(runner, priority, args.max_tasks)
                    args.output.joinpath("summary.json").write_text(
                        json.dumps(summary, indent=2), encoding="utf-8"
                    )
                    print(json.dumps(summary), flush=True)
                    if any(row["status"] == "failed" for row in summary):
                        raise RuntimeError(
                            "Campagna conclusa con task falliti: consultare il manifest"
                        )
        finally:
            args.output.joinpath("summary.json").write_text(
                json.dumps(manifest.summary(), indent=2), encoding="utf-8"
            )
            manifest.close()


def main():
    logging.getLogger("app.modules.elaborazioni.capacitas.session").setLevel(logging.WARNING)
    try:
        asyncio.run(run(parser().parse_args()))
    except Exception as error:
        message = str(getattr(error, "orig", error)).splitlines()[0][:400]
        print(f"Recupero Capacitas interrotto: {message}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
