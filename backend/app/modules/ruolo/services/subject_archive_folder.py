"""Assign the NAS archive folder of a subject without taking one another subject owns."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.utenze.models import AnagraficaSubject


def assign_subject_folder(
    db: Session, subject: AnagraficaSubject, *, letter: str, nas_folder_path: str
) -> str:
    # A duplicate subject (e.g. from the NAS archive import) may already own this folder:
    # reuse it, the path is unique.
    owner = db.scalar(
        select(AnagraficaSubject.id).where(
            AnagraficaSubject.nas_folder_path == nas_folder_path,
            AnagraficaSubject.id != subject.id,
        )
    )
    if owner is not None:
        return nas_folder_path
    subject.nas_folder_letter = letter
    subject.nas_folder_path = nas_folder_path
    db.add(subject)
    db.flush()
    return nas_folder_path
