from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.engine import make_url


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _configure_database_url_for_host() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        env_path = REPO_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("DATABASE_URL="):
                    db_url = line.split("=", 1)[1].strip()
                    break
    if not db_url:
        return
    try:
        parsed = make_url(db_url)
    except Exception:
        return
    if (parsed.host or "") != "postgres":
        os.environ.setdefault("DATABASE_URL", db_url)
        return
    fallback = parsed.set(host="127.0.0.1", port=5434 if parsed.port in (None, 5432) else parsed.port)
    os.environ["DATABASE_URL"] = fallback.render_as_string(hide_password=False)


_configure_database_url_for_host()

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.capacitas import CapacitasInCassSyncJob
from app.modules.elaborazioni.capacitas.models import CapacitasInCassSyncJobCreateRequest
from app.modules.utenze.models import AnagraficaPaymentNotice, AnagraficaSubject
from app.services.elaborazioni_capacitas_incass import create_incass_sync_job
from app.services.elaborazioni_capacitas_runtime import run_incass_job_by_id


@dataclass(frozen=True)
class DuplicateCase:
    retry_job: int
    subject_id: str
    identifier: str
    display_name: str
    notice_id: str
    notice_year: int


DUPLICATE_CASES: list[DuplicateCase] = [
    DuplicateCase(126, "4e040e41-cb3d-4ac0-8870-7bf0691ba829", "PDDNNL63D17L122O", "Podda Antonello", "120170008376340", 2017),
    DuplicateCase(126, "41eac757-5f79-4fb6-a113-23e2987b1f58", "PPPPGD71L18A357V", "PUPPIN PIERGUIDO", "020110010251660", 2011),
    DuplicateCase(126, "0191eb3a-fa6c-485f-8a98-ac3030f41b88", "PNNMRA25C61A621Q", "Pinna Maria", "020130009398860", 2013),
    DuplicateCase(126, "06dca1a9-b4f5-4f21-a80b-d34794a3bdbe", "LTZMHL36P70I384M", "Lutzu Michela", "020130006096820", 2013),
    DuplicateCase(126, "434abd28-4513-4d89-bd61-d00becdaf91b", "SRDFNC50A06F980X", "Sardu Francesco Angelo", "020150012395760", 2015),
    DuplicateCase(126, "148cdd5f-e39c-4afb-bf46-9138f3dda7d6", "TRODNL66L18G113F", "Tore Daniele", "020130013351620", 2013),
    DuplicateCase(126, "492b117c-874c-4544-a8d9-b3c785949624", "CLAFNC60P07A126S", "Cauli Francesco", "020140002243120", 2014),
    DuplicateCase(128, "773c98b9-83fb-45a2-9eda-be392570d2b9", "STCMRZ75P28E281O", "Stocchino Maurizio", "020130012990890", 2013),
    DuplicateCase(128, "6acfc3e8-64c1-4f8d-b1f1-fb7d1f074425", "CCIBNR76D03E972I", "CICU BERNARDINO", "020130002003630", 2013),
    DuplicateCase(128, "73bd42c1-0671-47d5-9441-23dceb0c61e6", "PNTRLL63R57A357J", "PANETTO ORNELLA MARIA", "020120009851540", 2012),
    DuplicateCase(128, "626618e2-0fe1-46aa-a370-3e89ff105cc6", "PNNGRG54R31L122Y", "PINNA GIORGIO", "020130009339270", 2013),
    DuplicateCase(128, "785df07a-d323-4ba6-be14-c2a733b525f7", "PTZMCR69P66E972I", "PUTZULU MARIA CARMELINA", "020130010560840", 2013),
    DuplicateCase(128, "7738444a-51a1-41b6-a4b6-ed86b7f1165e", "CRTGST60E13H301P", "Carta Augusto", "020150003247460", 2015),
    DuplicateCase(128, "705ffd8a-181c-4cba-9826-3e17b08cfea2", "MLSGNN65L23F979L", "MULAS GIOVANNI", "020120006953660", 2012),
    DuplicateCase(130, "e6c1fb14-8694-4040-a25f-614859909442", "CDDFBN59A20F980Q", "Cadeddu Fabiano", "120160001845020", 2016),
    DuplicateCase(130, "f37692c1-bab9-4639-a754-457f0a35b731", "FNEVGN28D63L122F", "FENU VIRGINIA", "120160004586270", 2016),
    DuplicateCase(130, "e79c6841-173f-48bb-adcc-4c7aea1525d9", "DSSPRN46S16L122E", "Dessi Pietrino", "020110005054100", 2011),
    DuplicateCase(130, "bd81edb9-de4d-4ff7-9c71-577ad2da3c72", "TCCSLV25H23L122O", "TOCCO SILVIO", "020130013119240", 2013),
    DuplicateCase(130, "9c06ebc2-e606-4634-bbb0-f1a1345ce18c", "SRRMRA33M53G113H", "Serra Maria", "020130012824200", 2013),
    DuplicateCase(130, "a34c56f7-101a-4c30-9ee0-d57d16de62b6", "DSELSN48C57I743U", "Deias Lisena", "120170003879960", 2017),
    DuplicateCase(130, "f8706c08-6a83-4912-a4d2-973f7d48463f", "TVRRNZ56S18L122S", "Tuveri Renzo", "120160013138430", 2016),
    DuplicateCase(130, "9da35d8c-ca3a-4389-859c-8a71792ea085", "TRTMLN74M47E972P", "Tirotto Emiliana", "020120013671910", 2012),
    DuplicateCase(130, "8d255311-eca6-4c91-ac83-d7429fb39b51", "MLSPTR75T15F979J", "Mulas Pietro", "020110007389170", 2011),
    DuplicateCase(130, "b975ce86-d2e4-4764-8e5f-d58c2ca65cc6", "TZNLND51C43L321N", "Atzeni Linda", "020120013842680", 2012),
    DuplicateCase(130, "ae4e566a-93f9-474e-811e-86464c63408c", "CDNGLC75C12G113J", "Cadoni Gianluca", "120170001911680", 2017),
    DuplicateCase(130, "bbdadba0-78c5-4811-a346-c7513cd0f033", "MNCFST61C14G113N", "Mancosu Fausto", "120170006525260", 2017),
    DuplicateCase(130, "8e3fd138-0ea2-4e6d-a8e2-9ad635a49619", "DSSGNN52A13G113K", "Dessi' Giovanni Angelo", "020130004344760", 2013),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rerun dei 27 casi residui duplicati inCass.")
    parser.add_argument("--chunk-size", type=int, default=10, help="Numero di soggetti per job.")
    parser.add_argument("--requested-by-user-id", type=int, default=None, help="User id da salvare sui job.")
    parser.add_argument("--credential-id", type=int, default=None, help="Credenziale Capacitas da forzare.")
    parser.add_argument("--throttle-ms", type=int, default=250, help="Pausa tra notice.")
    parser.add_argument("--apply", action="store_true", help="Crea i job su DB.")
    parser.add_argument("--run-inline", action="store_true", help="Esegue subito i job creati.")
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "exports" / "incass_duplicate_cases_rerun_report.md"),
        help="Report markdown finale.",
    )
    return parser.parse_args()


def _chunks(items: list[DuplicateCase], size: int) -> list[list[DuplicateCase]]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def _load_subject_existence(subject_ids: list[str]) -> set[str]:
    db = SessionLocal()
    try:
        rows = db.scalars(select(AnagraficaSubject.id).where(AnagraficaSubject.id.in_([UUID(value) for value in subject_ids]))).all()
        return {str(value) for value in rows}
    finally:
        db.close()


def _create_jobs(args: argparse.Namespace, chunks: list[list[DuplicateCase]]) -> list[int]:
    db = SessionLocal()
    try:
        job_ids: list[int] = []
        for chunk in chunks:
            payload = CapacitasInCassSyncJobCreateRequest(
                credential_id=args.credential_id,
                subject_ids=[UUID(item.subject_id) for item in chunk],
                include_details=True,
                include_partitario=True,
                continue_on_error=True,
                throttle_ms=args.throttle_ms,
            )
            job = create_incass_sync_job(
                db,
                requested_by_user_id=args.requested_by_user_id,
                credential_id=args.credential_id,
                payload=payload,
            )
            job_ids.append(job.id)
        return job_ids
    finally:
        db.close()


async def _run_jobs_inline(job_ids: list[int]) -> None:
    for job_id in job_ids:
        print(f"running job_id={job_id}")
        await run_incass_job_by_id(job_id)


def _load_job(job_id: int) -> CapacitasInCassSyncJob | None:
    db = SessionLocal()
    try:
        job = db.get(CapacitasInCassSyncJob, job_id)
        if job is None:
            return None
        db.expunge(job)
        return job
    finally:
        db.close()


def _load_notice_state(notice_id: str) -> dict[str, Any] | None:
    db = SessionLocal()
    try:
        notice = db.scalar(
            select(AnagraficaPaymentNotice).where(
                AnagraficaPaymentNotice.source_system == "incass",
                AnagraficaPaymentNotice.source_notice_id == notice_id,
            )
        )
        if notice is None:
            return None
        return {
            "subject_id": str(notice.subject_id) if notice.subject_id else None,
            "display_name": notice.display_name,
            "anno": notice.anno,
            "lista_descrizione": notice.lista_descrizione,
            "synced_at": notice.synced_at.isoformat() if notice.synced_at else None,
            "has_partitario": bool(
                isinstance(notice.raw_detail_json, dict)
                and (
                    "partitario" in notice.raw_detail_json
                    or "partite" in notice.raw_detail_json
                )
            ),
        }
    finally:
        db.close()


def _write_report(path: Path, *, chunks: list[list[DuplicateCase]], job_ids: list[int]) -> None:
    job_map = {}
    for index, chunk in enumerate(chunks):
        job_map[index] = {"job_id": job_ids[index] if index < len(job_ids) else None, "cases": chunk}

    lines = [
        "# Rerun casi duplicati inCass",
        "",
        f"- Casi previsti: `{len(DUPLICATE_CASES)}`",
        f"- Chunk: `{len(chunks)}`",
        f"- Job creati: `{len(job_ids)}`",
        "",
        "## Job",
        "",
    ]

    for index, entry in job_map.items():
        job_id = entry["job_id"]
        job = _load_job(job_id) if job_id is not None else None
        result_json = job.result_json if job is not None and isinstance(job.result_json, dict) else {}
        lines.append(
            f"- chunk `{index + 1}`: job_id=`{job_id}` status=`{job.status if job else 'missing'}` "
            f"processed=`{result_json.get('processed_subjects', 0)}` failed=`{result_json.get('failed_subjects', 0)}` "
            f"notices_synced=`{result_json.get('notices_synced', 0)}`"
        )

    lines.extend(["", "## Casi", "", "| Retry job | Subject ID | Nominativo | Avviso | Stato DB | Subject notice | Partitario |", "| --- | --- | --- | --- | --- | --- | --- |"])

    for case in DUPLICATE_CASES:
        notice_state = _load_notice_state(case.notice_id)
        if notice_state is None:
            db_state = "missing"
            notice_subject = ""
            has_partitario = ""
        else:
            db_state = "present"
            notice_subject = notice_state.get("subject_id") or ""
            has_partitario = "yes" if notice_state.get("has_partitario") else "no"
        lines.append(
            f"| {case.retry_job} | `{case.subject_id}` | {case.display_name} | `{case.notice_id}` | {db_state} | "
            f"`{notice_subject}` | {has_partitario} |"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.chunk_size <= 0:
        raise SystemExit("--chunk-size deve essere > 0")

    cases = DUPLICATE_CASES
    existing_subjects = _load_subject_existence([item.subject_id for item in cases])
    missing_subjects = [item.subject_id for item in cases if item.subject_id not in existing_subjects]
    print(f"cases={len(cases)} existing_subjects={len(existing_subjects)} missing_subjects={len(missing_subjects)}")
    if missing_subjects:
        print("missing_subject_ids=" + json.dumps(missing_subjects))

    chunks = _chunks(cases, args.chunk_size)
    print(f"chunks={len(chunks)} chunk_size={args.chunk_size} apply={args.apply} run_inline={args.run_inline}")
    if not args.apply:
        return

    job_ids = _create_jobs(args, chunks)
    print("job_ids=" + json.dumps(job_ids))

    if args.run_inline and job_ids:
        asyncio.run(_run_jobs_inline(job_ids))

    report_path = Path(args.output)
    _write_report(report_path, chunks=chunks, job_ids=job_ids)
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
