from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatMeterReading, CatMeterReadingManualAudit
from app.modules.catasto.services.meter_reading_validation import validate_meter_reading_row
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson

EDITABLE_FIELDS = (
    "punto_consegna",
    "matricola",
    "record_type",
    "tipologia_idrante",
    "codice_fiscale",
    "note",
    "intervento_da_eseguire",
)

IMPORT_SNAPSHOT_FIELDS = (
    "excel_id",
    "punto_consegna",
    "matricola",
    "sigillo",
    "record_type",
    "tipologia_idrante",
    "firmware_version",
    "battery_level",
    "lettura_iniziale",
    "lettura_finale",
    "consumo_mc",
    "data_lettura",
    "operatore_lettura",
    "intervento_da_eseguire",
    "intervento_eseguito",
    "operatore_intervento",
    "data_intervento",
    "dui",
    "codice_fiscale",
    "coltura",
    "tariffa",
    "fondo_chiuso",
    "telefono",
    "note",
)


def _clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_meter_serial(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip().upper()


def _to_json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, list):
        return [_to_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_json_safe(item) for key, item in value.items()}
    return value


def build_import_payload_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: _to_json_safe(payload.get(field)) for field in IMPORT_SNAPSHOT_FIELDS}


def build_row_data_from_reading(reading: CatMeterReading) -> dict[str, Any]:
    return {field: getattr(reading, field) for field in IMPORT_SNAPSHOT_FIELDS}


def apply_manual_corrections(reading: CatMeterReading, corrections: dict[str, Any]) -> None:
    for field in EDITABLE_FIELDS:
        if field not in corrections:
            continue
        setattr(reading, field, _clean_optional_text(corrections[field]))


def _subject_display_name(db: Session, subject_id: UUID | None) -> str | None:
    if subject_id is None:
        return None
    person = db.execute(select(AnagraficaPerson).where(AnagraficaPerson.subject_id == subject_id)).scalar_one_or_none()
    if person is not None:
        return f"{person.cognome} {person.nome}".strip() or person.codice_fiscale
    company = db.execute(select(AnagraficaCompany).where(AnagraficaCompany.subject_id == subject_id)).scalar_one_or_none()
    if company is not None:
        return company.ragione_sociale or company.partita_iva or company.codice_fiscale
    return None


def revalidate_meter_reading(db: Session, reading: CatMeterReading) -> str | None:
    duplicate_conflict = db.execute(
        select(CatMeterReading.id).where(
            CatMeterReading.id != reading.id,
            CatMeterReading.anno == reading.anno,
            CatMeterReading.distretto_id == reading.distretto_id,
            CatMeterReading.punto_consegna == reading.punto_consegna,
            func.coalesce(CatMeterReading.matricola, "") == _normalize_meter_serial(reading.matricola),
        )
    ).scalar_one_or_none()

    status, messages, resolved = validate_meter_reading_row(
        db,
        row_data=build_row_data_from_reading(reading),
        anno=reading.anno,
        distretto_id=str(reading.distretto_id) if reading.distretto_id else None,
        duplicate_key_seen=duplicate_conflict is not None,
        allow_missing_distretto=reading.distretto_id is None,
    )
    reading.record_kind = resolved["record_kind"]
    reading.operational_state = resolved["operational_state"]
    reading.codice_fiscale_normalizzato = resolved["codice_fiscale_normalizzato"]
    reading.subject_id = resolved["subject_id"]
    reading.validation_status = status
    reading.validation_messages = [message.__dict__ for message in messages]
    if status == "error":
        first_error = next((message.message for message in messages if message.level == "error"), "Correzione non valida.")
        raise ValueError(first_error)
    return resolved["subject_display_name"] or _subject_display_name(db, reading.subject_id)


def update_meter_reading_manual_corrections(
    db: Session,
    *,
    reading: CatMeterReading,
    payload: dict[str, Any],
    current_user: ApplicationUser,
) -> str | None:
    previous_values = {field: getattr(reading, field) for field in EDITABLE_FIELDS}
    corrections = {field: payload[field] for field in EDITABLE_FIELDS if field in payload}
    change_note = _clean_optional_text(payload.get("change_note"))

    next_corrections = dict(reading.manual_corrections) if isinstance(reading.manual_corrections, dict) else {}
    for field, value in corrections.items():
        normalized = _clean_optional_text(value)
        import_snapshot = reading.import_payload_json if isinstance(reading.import_payload_json, dict) else {}
        if normalized == _clean_optional_text(import_snapshot.get(field)):
            next_corrections.pop(field, None)
        else:
            next_corrections[field] = normalized

    apply_manual_corrections(reading, corrections)
    subject_display_name = revalidate_meter_reading(db, reading)
    reading.manual_corrections = next_corrections or None
    reading.manual_override_updated_by = current_user.id
    reading.manual_override_updated_at = datetime.now(timezone.utc)

    new_values = {field: getattr(reading, field) for field in EDITABLE_FIELDS}
    changed_fields = {
        field: {"from": previous_values[field], "to": new_values[field]}
        for field in EDITABLE_FIELDS
        if previous_values[field] != new_values[field]
    }
    if changed_fields:
        db.add(
            CatMeterReadingManualAudit(
                meter_reading_id=reading.id,
                changed_by=current_user.id,
                change_note=change_note,
                previous_values=previous_values,
                new_values=new_values,
            )
        )
    return subject_display_name


def validate_meter_reading_manually(
    db: Session,
    *,
    reading: CatMeterReading,
    current_user: ApplicationUser,
    change_note: str | None = None,
) -> str | None:
    if reading.validation_status == "error":
        raise ValueError("Impossibile validare manualmente una lettura con errori bloccanti.")

    previous_messages = reading.validation_messages if isinstance(reading.validation_messages, list) else []
    next_messages = [message for message in previous_messages if not (isinstance(message, dict) and message.get("level") == "warning")]
    previous_status = reading.validation_status
    next_status = "valid"

    if previous_status == next_status and previous_messages == next_messages:
        return _subject_display_name(db, reading.subject_id)

    reading.validation_status = next_status
    reading.validation_messages = next_messages
    reading.manual_override_updated_by = current_user.id
    reading.manual_override_updated_at = datetime.now(timezone.utc)

    db.add(
        CatMeterReadingManualAudit(
            meter_reading_id=reading.id,
            changed_by=current_user.id,
            change_note=_clean_optional_text(change_note) or "Validazione manuale lettura confermata.",
            previous_values={
                "validation_status": previous_status,
                "validation_messages": previous_messages,
            },
            new_values={
                "validation_status": next_status,
                "validation_messages": next_messages,
            },
        )
    )
    return _subject_display_name(db, reading.subject_id)
