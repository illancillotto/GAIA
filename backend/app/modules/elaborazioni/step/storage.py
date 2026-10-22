"""Filesystem locations and content-addressed PDF storage for STEP."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from app.modules.elaborazioni.step.persistence import StoredPdf


def document_storage_root() -> Path:
    return Path(os.getenv("STEP_DOCUMENT_STORAGE_PATH", "/data/catasto/step/documents"))


def import_root() -> Path:
    return Path(os.getenv("STEP_IMPORT_ROOT", "/data/catasto/step/import"))


def validate_pdf(content: bytes) -> str:
    if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-4096:]:
        raise ValueError("Il file ricevuto da STEP non e un PDF completo")
    return hashlib.sha256(content).hexdigest()


def store_pdf(
    content: bytes,
    *,
    cod_ent: str,
    original_filename: str | None,
    expected_sha256: str | None = None,
) -> StoredPdf:
    """Write the PDF once under ``<root>/<ente>/<sha[:2]>/<sha>.pdf`` and describe it."""

    sha256 = validate_pdf(content)
    if expected_sha256 is not None and sha256 != expected_sha256:
        raise ValueError("Impronta SHA-256 del PDF STEP diversa da quella registrata")
    relative = Path(cod_ent) / sha256[:2] / f"{sha256}.pdf"
    target = document_storage_root() / relative
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".part")
        temporary.write_bytes(content)
        os.chmod(temporary, 0o640)
        os.replace(temporary, target)
    return StoredPdf(
        status="downloaded",
        path=relative.as_posix(),
        sha256=sha256,
        bytes=len(content),
        original_filename=original_filename,
    )


def resolve_stored_pdf(relative_path: str) -> Path:
    root = document_storage_root().resolve()
    target = (root / relative_path).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise FileNotFoundError(relative_path)
    return target


def resolve_import_archive(name: str) -> Path:
    root = import_root().resolve()
    target = (root / name).resolve()
    if not target.is_relative_to(root) or target.suffix.lower() != ".zip" or not target.is_file():
        raise ValueError(f"Archivio STEP non trovato nella cartella import: {name}")
    return target
