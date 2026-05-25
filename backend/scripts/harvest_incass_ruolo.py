from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence

from app.core.database import SessionLocal
from app.modules.elaborazioni.capacitas.models import CapacitasInCassRuoloHarvestRequest
from app.services.elaborazioni_capacitas_incass import create_incass_ruolo_harvest_jobs, load_incass_ruolo_subject_ids
from app.services.elaborazioni_capacitas_runtime import run_incass_job_by_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Accoda job batch inCass per tutti i soggetti a ruolo.",
    )
    parser.add_argument("--anno", type=int, default=None, help="Filtra i soggetti con avvisi ruolo di uno specifico anno.")
    parser.add_argument("--chunk-size", type=int, default=100, help="Numero soggetti per job.")
    parser.add_argument("--limit-subjects", type=int, default=None, help="Limita il numero totale di soggetti da processare.")
    parser.add_argument("--credential-id", type=int, default=None, help="Credenziale Capacitas da usare per i job.")
    parser.add_argument("--requested-by-user-id", type=int, default=None, help="User id da salvare sul job.")
    parser.add_argument("--throttle-ms", type=int, default=250, help="Delay tra notice durante il sync.")
    parser.add_argument("--exclude-synced-subjects", action="store_true", help="Esclude soggetti che hanno gia notice in ana_payment_notices da inCass.")
    parser.add_argument("--run-inline", action="store_true", help="Esegue subito i job creati, uno dopo l'altro.")
    parser.add_argument("--apply", action="store_true", help="Scrive i job su DB. Senza flag fa solo dry-run.")
    return parser.parse_args()


def _load_ruolo_subject_ids(
    *,
    anno: int | None,
    limit_subjects: int | None,
    exclude_synced_subjects: bool,
) -> list[str]:
    db = SessionLocal()
    try:
        return [
            str(value)
            for value in load_incass_ruolo_subject_ids(
                db,
                anno=anno,
                limit_subjects=limit_subjects,
                exclude_synced_subjects=exclude_synced_subjects,
            )
        ]
    finally:
        db.close()


def _chunks(items: Sequence[str], size: int) -> list[list[str]]:
    return [list(items[index:index + size]) for index in range(0, len(items), size)]


def _create_jobs(
    *,
    anno: int | None,
    chunk_size: int,
    limit_subjects: int | None,
    credential_id: int | None,
    requested_by_user_id: int | None,
    throttle_ms: int,
    exclude_synced_subjects: bool,
    apply: bool,
) -> list[int]:
    db = SessionLocal()
    try:
        if not apply:
            return []
        result = create_incass_ruolo_harvest_jobs(
            db,
            requested_by_user_id=requested_by_user_id,
            payload=CapacitasInCassRuoloHarvestRequest(
                credential_id=credential_id,
                anno=anno,
                chunk_size=chunk_size,
                limit_subjects=limit_subjects,
                exclude_synced_subjects=exclude_synced_subjects,
                include_details=True,
                include_partitario=True,
                continue_on_error=True,
                throttle_ms=throttle_ms,
            ),
        )
        return result.job_ids
    finally:
        db.close()


async def _run_jobs_inline(job_ids: Sequence[int]) -> None:
    for job_id in job_ids:
        print(f"running job_id={job_id}")
        await run_incass_job_by_id(job_id)


def main() -> None:
    args = parse_args()
    if args.chunk_size <= 0:
        raise SystemExit("--chunk-size deve essere > 0")

    subject_ids = _load_ruolo_subject_ids(
        anno=args.anno,
        limit_subjects=args.limit_subjects,
        exclude_synced_subjects=args.exclude_synced_subjects,
    )
    chunked = _chunks(subject_ids, args.chunk_size)

    print(
        f"ruolo_subjects={len(subject_ids)} chunks={len(chunked)} chunk_size={args.chunk_size} "
        f"anno={args.anno or 'all'} exclude_synced={args.exclude_synced_subjects} apply={args.apply}"
    )
    if not args.apply:
        return

    job_ids = _create_jobs(
        anno=args.anno,
        chunk_size=args.chunk_size,
        limit_subjects=args.limit_subjects,
        credential_id=args.credential_id,
        requested_by_user_id=args.requested_by_user_id,
        throttle_ms=args.throttle_ms,
        exclude_synced_subjects=args.exclude_synced_subjects,
        apply=True,
    )
    print(f"created_jobs={len(job_ids)} first_job_id={job_ids[0] if job_ids else None} last_job_id={job_ids[-1] if job_ids else None}")

    if args.run_inline and job_ids:
        asyncio.run(_run_jobs_inline(job_ids))


if __name__ == "__main__":
    main()
