from __future__ import annotations

from datetime import UTC, datetime

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
