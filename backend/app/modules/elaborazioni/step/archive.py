"""Import a verified ``raccolta-completa.zip`` produced by the STEP scraper.

The archive contains one ``contributors/<dir>/scheda.json`` per contribuente,
the PDF of each document next to it and a ``verification.json`` with the
expected totals. Totals are checked against ``verification.json`` before any
write, and every PDF is checked against the SHA-256 recorded in its scheda.
Re-importing the same archive is idempotent.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from sqlalchemy.orm import Session

from app.modules.elaborazioni.step import storage
from app.modules.elaborazioni.step.models import StepContribuente
from app.modules.elaborazioni.step.persistence import StoredPdf, persist_scheda
from app.modules.elaborazioni.step.ruolo_link import LINK_STATUSES, link_documents

ProgressCallback = Callable[[dict], None]


def _scheda_members(archive: ZipFile) -> list[PurePosixPath]:
    members = []
    for name in sorted(archive.namelist()):
        path = PurePosixPath(name)
        if len(path.parts) == 3 and path.parts[0] == "contributors" and path.name == "scheda.json":
            members.append(path)
    return members


def _scheda_totals(scheda: dict) -> dict[str, int]:
    documents = scheda.get("documents") or []
    downloaded = sum(
        1 for entry in documents if (entry.get("pdf") or {}).get("status") == "downloaded"
    )
    return {
        "contributors": 1,
        "documents": len(documents),
        "tributi": sum(len((entry.get("tributi") or {}).get("rows") or []) for entry in documents),
        "pdfs": downloaded,
        "unavailablePdfs": len(documents) - downloaded,
    }


def verify_archive(archive: ZipFile) -> dict:
    """Compare the schede in the archive with ``verification.json`` without writing anything."""

    expected = json.loads(archive.read("verification.json"))
    observed = dict.fromkeys(("contributors", "documents", "tributi", "pdfs", "unavailablePdfs"), 0)
    for member in _scheda_members(archive):
        for key, value in _scheda_totals(json.loads(archive.read(str(member)))).items():
            observed[key] += value
    mismatches = {
        key: {"expected": expected.get(key), "observed": value}
        for key, value in observed.items()
        if expected.get(key) != value
    }
    if mismatches:
        raise ValueError(f"Archivio STEP incoerente con verification.json: {mismatches}")
    return {**observed, "sha256": expected.get("sha256")}


class _ArchivePdfStore:
    def __init__(self, archive: ZipFile, folder: PurePosixPath) -> None:
        self.archive = archive
        self.folder = folder

    def __call__(self, contribuente: StepContribuente, entry: dict) -> StoredPdf:
        pdf = entry.get("pdf") or {}
        if pdf.get("status") != "downloaded":
            return StoredPdf(
                status="unavailable",
                unavailable_reason=pdf.get("reason") or "PDF non disponibile su STEP",
            )
        filename = str(pdf.get("file") or "")
        if not filename or PurePosixPath(filename).name != filename:
            raise ValueError(f"Percorso PDF non valido nella scheda {self.folder}")
        return storage.store_pdf(
            self.archive.read(str(self.folder / filename)),
            cod_ent=contribuente.cod_ent,
            original_filename=pdf.get("originalFilename"),
            expected_sha256=pdf.get("sha256"),
        )


def import_archive(
    db: Session,
    archive_path: Path,
    *,
    job_id: int | None,
    batch_size: int = 50,
    progress: ProgressCallback | None = None,
) -> dict:
    now = datetime.now(UTC)
    result: dict = {"archive": archive_path.name, "imported": 0, "changed": 0, "pagamenti": 0}
    links = dict.fromkeys(LINK_STATUSES, 0)
    pending: list[uuid.UUID] = []
    with ZipFile(archive_path) as archive:
        result["verification"] = verify_archive(archive)
        members = _scheda_members(archive)
        for index, member in enumerate(members, 1):
            scheda = json.loads(archive.read(str(member)))
            written = persist_scheda(
                db,
                scheda,
                job_id=job_id,
                now=now,
                pdf_store=_ArchivePdfStore(archive, member.parent),
            )
            result["imported"] += 1
            result["changed"] += int(written.changed)
            result["pagamenti"] += written.pagamenti
            pending.extend(written.document_ids)
            if index % batch_size == 0 or index == len(members):
                for status, count in link_documents(db, pending, now=now).items():
                    links[status] += count
                pending.clear()
                db.commit()
                if progress is not None:
                    progress({**result, "total": len(members), "links": dict(links)})
    return {**result, "links": links}
