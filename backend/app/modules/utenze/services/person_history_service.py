from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.utenze.models import AnagraficaPerson, AnagraficaPersonSnapshot


def person_to_snapshot_payload(person: AnagraficaPerson) -> dict[str, object | None]:
    return {
        "cognome": person.cognome,
        "nome": person.nome,
        "codice_fiscale": person.codice_fiscale,
        "data_nascita": person.data_nascita,
        "comune_nascita": person.comune_nascita,
        "indirizzo": person.indirizzo,
        "comune_residenza": person.comune_residenza,
        "cap": person.cap,
        "email": person.email,
        "telefono": person.telefono,
        "note": person.note,
    }


def snapshot_person_if_changed(
    db: Session,
    person: AnagraficaPerson | None,
    new_data: dict[str, object | None],
    *,
    source_system: str,
    source_ref: str | None = None,
    collected_at: datetime | None = None,
) -> bool:
    if person is None:
        return False

    current_data = person_to_snapshot_payload(person)
    if current_data == new_data:
        return False

    now = collected_at or datetime.now(UTC)
    db.add(
        AnagraficaPersonSnapshot(
            subject_id=person.subject_id,
            source_system=source_system,
            source_ref=source_ref,
            cognome=person.cognome,
            nome=person.nome,
            codice_fiscale=person.codice_fiscale,
            data_nascita=person.data_nascita,
            comune_nascita=person.comune_nascita,
            indirizzo=person.indirizzo,
            comune_residenza=person.comune_residenza,
            cap=person.cap,
            email=person.email,
            telefono=person.telefono,
            note=person.note,
            valid_from=person.updated_at or person.created_at,
            collected_at=now,
        )
    )
    return True


def persist_person_source_snapshot(
    db: Session,
    person: AnagraficaPerson | None,
    snapshot_data: dict[str, object | None],
    *,
    source_system: str,
    source_ref: str | None = None,
    collected_at: datetime | None = None,
    valid_from: datetime | None = None,
    is_capacitas_history: bool = False,
) -> bool:
    if person is None:
        return False

    if is_capacitas_history and source_ref:
        existing = db.scalar(
            select(AnagraficaPersonSnapshot).where(
                AnagraficaPersonSnapshot.subject_id == person.subject_id,
                AnagraficaPersonSnapshot.source_system == source_system,
                AnagraficaPersonSnapshot.source_ref == source_ref,
                AnagraficaPersonSnapshot.is_capacitas_history.is_(True),
            )
        )
        if existing is not None:
            return False

    now = collected_at or datetime.now(UTC)
    db.add(
        AnagraficaPersonSnapshot(
            subject_id=person.subject_id,
            is_capacitas_history=is_capacitas_history,
            source_system=source_system,
            source_ref=source_ref,
            cognome=str(snapshot_data.get("cognome") or ""),
            nome=str(snapshot_data.get("nome") or ""),
            codice_fiscale=str(snapshot_data.get("codice_fiscale") or ""),
            data_nascita=snapshot_data.get("data_nascita"),
            comune_nascita=snapshot_data.get("comune_nascita"),
            indirizzo=snapshot_data.get("indirizzo"),
            comune_residenza=snapshot_data.get("comune_residenza"),
            cap=snapshot_data.get("cap"),
            email=snapshot_data.get("email"),
            telefono=snapshot_data.get("telefono"),
            note=snapshot_data.get("note"),
            valid_from=valid_from,
            collected_at=now,
        )
    )
    return True
