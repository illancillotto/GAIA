from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoDocument
from app.models.catasto import CatastoVisuraRequest


def build_request_artifact_dir(root: Path, batch_id: UUID, request_id: UUID) -> Path:
    return root / "requests" / str(batch_id) / str(request_id)


def build_document_path(root: Path, _sister_username: str, request: CatastoVisuraRequest) -> Path:
    request_root = (
        root
        / datetime.now(timezone.utc).strftime("%Y")
        / str(request.user_id)
        / str(request.batch_id)
        / str(request.id)
        / str(request.execution_token or "legacy")
    )
    if request.search_mode == "soggetto":
        return request_root / _subject_filename(request)
    return request_root / immobile_filename(request)


def _subject_filename(request: CatastoVisuraRequest) -> str:
    filename = "_".join(
        (
            _slugify(request.subject_kind or "SOGGETTO"),
            _slugify(request.subject_id or "UNKNOWN"),
            _slugify(request.request_type or "ATTUALITA"),
        )
    )
    return f"{filename}.pdf"


def immobile_filename(request: CatastoVisuraRequest) -> str:
    components = [
        _slugify(request.comune or "SCONOSCIUTO"),
        str(request.foglio),
        str(request.particella),
    ]
    if request.subalterno:
        components.append(str(request.subalterno))
    return f"{'_'.join(components)}.pdf"


def sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def document_values(
    request: CatastoVisuraRequest,
    _sister_username: str,
    file_path: Path,
    file_size: int,
    sha256: str,
) -> dict[str, Any]:
    return {
        "user_id": request.user_id,
        "request_id": request.id,
        "search_mode": request.search_mode,
        "comune": request.comune,
        "foglio": request.foglio,
        "particella": request.particella,
        "subalterno": request.subalterno,
        "catasto": request.catasto,
        "tipo_visura": request.tipo_visura,
        "subject_kind": request.subject_kind,
        "subject_id": request.subject_id,
        "request_type": request.request_type,
        "intestazione": request.intestazione,
        "filename": file_path.name,
        "filepath": str(file_path),
        "file_size": file_size,
        "sha256": sha256,
        "codice_fiscale": request.subject_id if request.search_mode == "soggetto" else None,
    }


@dataclass(slots=True)
class DocumentNameCleanupResult:
    scanned: int = 0
    updated: int = 0
    renamed: int = 0
    missing: int = 0
    conflicts: int = 0

    def record_file_status(self, status: str) -> bool:
        if status == "conflict":
            self.conflicts += 1
            return False
        if status == "renamed":
            self.renamed += 1
        elif status == "missing":
            self.missing += 1
        return True


def normalize_legacy_immobile_documents(db: Session, *, dry_run: bool = False) -> DocumentNameCleanupResult:
    result = DocumentNameCleanupResult()
    rows = db.execute(
        select(CatastoDocument, CatastoVisuraRequest)
        .join(CatastoVisuraRequest, CatastoVisuraRequest.id == CatastoDocument.request_id)
        .where(CatastoDocument.search_mode == "immobile")
    ).all()
    for document, request in rows:
        result.scanned += 1
        canonical_name = immobile_filename(request)
        source_path = Path(document.filepath)
        target_path = source_path.with_name(canonical_name)
        if not result.record_file_status(_normalize_document_file(source_path, target_path, dry_run)):
            continue
        if _normalize_document_metadata(document, canonical_name, target_path, dry_run):
            result.updated += 1
    if not dry_run:
        db.commit()
    return result


def _normalize_document_file(source_path: Path, target_path: Path, dry_run: bool) -> str:
    if source_path == target_path:
        return "unchanged"
    if source_path.exists():
        if target_path.exists():
            return "conflict"
        if not dry_run:
            source_path.replace(target_path)
        return "renamed"
    return "ready" if target_path.exists() else "missing"


def _normalize_document_metadata(document, canonical_name: str, target_path: Path, dry_run: bool) -> bool:
    changed = (
        document.filename != canonical_name
        or document.codice_fiscale is not None
        or document.filepath != str(target_path)
    )
    if not changed or dry_run:
        return changed
    document.filename = canonical_name
    document.codice_fiscale = None
    document.filepath = str(target_path)
    return True


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper().strip()).strip("_")
