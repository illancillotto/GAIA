"""Canonical NAS folder path for Utenze / Anagrafica subjects."""

from __future__ import annotations

from app.core.config import get_settings


def canonical_subject_nas_folder_path(
    *,
    source_name_raw: str,
    nas_folder_letter: str | None,
) -> str | None:
    """
    Path atteso sotto l'archivio NAS: ``{root}/{letter}/{source_name_raw}``.

    Usa ``UTENZE_NAS_ARCHIVE_ROOT`` se valorizzato, altrimenti ``ANAGRAFICA_NAS_ARCHIVE_ROOT``.
    Coerente con la struttura lettera / cartella soggetto usata dallo scanner import.
    """
    settings = get_settings()
    root = (settings.utenze_nas_archive_root or settings.anagrafica_nas_archive_root or "").strip()
    if not root:
        return None

    letter = (nas_folder_letter or "").strip().upper()
    if len(letter) != 1 or not letter.isalpha():
        return None

    slug = (source_name_raw or "").strip()
    if not slug or "/" in slug or "\\" in slug or slug in (".", ".."):
        return None

    return f"{root.rstrip('/')}/{letter}/{slug}"
