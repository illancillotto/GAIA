from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatDistretto, CatMeterReading, CatMeterReadingImport
from app.modules.catasto.services.meter_reading_parser import ParsedMeterReadingsFile, parse_meter_readings_excel
from app.modules.catasto.services.meter_reading_validation import ValidationMessage, validate_meter_reading_row


ImportMode = Literal["import", "upsert", "replace"]


@dataclass
class PreparedMeterReadingItem:
    row_number: int
    payload: dict[str, Any]
    validation_status: str
    validation_messages: list[ValidationMessage]
    subject_display_name: str | None


@dataclass
class PreparedMeterReadingsImport:
    filename: str
    anno: int | None
    distretto: CatDistretto | None
    items: list[PreparedMeterReadingItem]


def _normalize_distretto_code(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().upper().removeprefix("D")
    if normalized.isdigit():
        return str(int(normalized))
    return normalized


def resolve_distretto(db: Session, *, distretto_id: UUID | None = None, distretto_code: str | None = None) -> CatDistretto | None:
    if distretto_id is not None:
        return db.get(CatDistretto, distretto_id)
    normalized = _normalize_distretto_code(distretto_code)
    if not normalized:
        return None
    candidates = db.execute(select(CatDistretto).order_by(CatDistretto.num_distretto)).scalars().all()
    for item in candidates:
        if _normalize_distretto_code(item.num_distretto) == normalized:
            return item
    return None


def prepare_meter_readings_import(
    db: Session,
    *,
    file_bytes: bytes,
    filename: str,
    anno: int | None = None,
    distretto_id: UUID | None = None,
) -> PreparedMeterReadingsImport:
    parsed = parse_meter_readings_excel(file_bytes, filename)
    effective_anno = anno or parsed.anno
    distretto = resolve_distretto(db, distretto_id=distretto_id, distretto_code=parsed.distretto_code)

    duplicate_keys: set[tuple[int | None, UUID | None, str]] = set()
    items: list[PreparedMeterReadingItem] = []
    for row in parsed.rows:
        point = (row.data.get("punto_consegna") or "").strip().upper()
        key = (effective_anno, distretto.id if distretto else None, point)
        duplicate_seen = bool(point and key in duplicate_keys)
        if point:
            duplicate_keys.add(key)
        validation_status, validation_messages, resolved = validate_meter_reading_row(
            db,
            row_data=row.data,
            anno=effective_anno,
            distretto_id=str(distretto.id) if distretto else None,
            duplicate_key_seen=duplicate_seen,
        )
        payload = {
            **row.data,
            "anno": effective_anno,
            "distretto_id": distretto.id if distretto else None,
            "codice_fiscale_normalizzato": resolved["codice_fiscale_normalizzato"],
            "subject_id": resolved["subject_id"],
            "source": "excel",
        }
        items.append(
            PreparedMeterReadingItem(
                row_number=row.row_number,
                payload=payload,
                validation_status=validation_status,
                validation_messages=validation_messages,
                subject_display_name=resolved["subject_display_name"],
            )
        )

    return PreparedMeterReadingsImport(filename=filename, anno=effective_anno, distretto=distretto, items=items)


def import_meter_readings(
    db: Session,
    *,
    file_bytes: bytes,
    filename: str,
    uploaded_by: int | None,
    mode: ImportMode = "upsert",
    anno: int | None = None,
    distretto_id: UUID | None = None,
) -> tuple[CatMeterReadingImport, PreparedMeterReadingsImport]:
    prepared = prepare_meter_readings_import(db, file_bytes=file_bytes, filename=filename, anno=anno, distretto_id=distretto_id)
    if prepared.anno is None or prepared.distretto is None:
        raise ValueError("Anno o distretto non risolti.")

    if mode == "import":
        existing = db.execute(
            select(func.count()).select_from(CatMeterReading).where(
                CatMeterReading.anno == prepared.anno,
                CatMeterReading.distretto_id == prepared.distretto.id,
            )
        ).scalar_one()
        if existing:
            raise ValueError("Esistono già letture per distretto e anno selezionati.")
    elif mode == "replace":
        db.execute(
            delete(CatMeterReading).where(
                CatMeterReading.anno == prepared.anno,
                CatMeterReading.distretto_id == prepared.distretto.id,
            )
        )

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    import_record = CatMeterReadingImport(
        distretto_id=prepared.distretto.id,
        anno=prepared.anno,
        filename_originale=filename,
        file_hash=file_hash,
        stato="completed",
        totale_righe=len(prepared.items),
        righe_importate=sum(1 for item in prepared.items if item.validation_status != "error"),
        righe_con_warning=sum(1 for item in prepared.items if item.validation_status == "warning"),
        righe_scartate=sum(1 for item in prepared.items if item.validation_status == "error"),
        uploaded_by=uploaded_by,
        processed_at=datetime.now(timezone.utc),
        error_report=[
            {
                "row_number": item.row_number,
                "validation_status": item.validation_status,
                "messages": [message.__dict__ for message in item.validation_messages],
            }
            for item in prepared.items
            if item.validation_messages
        ],
    )
    db.add(import_record)
    db.flush()

    for item in prepared.items:
        if item.validation_status == "error":
            continue
        existing = db.execute(
            select(CatMeterReading).where(
                CatMeterReading.anno == prepared.anno,
                CatMeterReading.distretto_id == prepared.distretto.id,
                CatMeterReading.punto_consegna == item.payload["punto_consegna"],
            )
        ).scalar_one_or_none()

        target = existing or CatMeterReading(
            anno=prepared.anno,
            distretto_id=prepared.distretto.id,
            punto_consegna=item.payload["punto_consegna"],
        )
        target.import_id = import_record.id
        target.row_number = item.row_number
        target.excel_id = item.payload.get("excel_id")
        target.matricola = item.payload.get("matricola")
        target.sigillo = item.payload.get("sigillo")
        target.tipologia_idrante = item.payload.get("tipologia_idrante")
        target.firmware_version = item.payload.get("firmware_version")
        target.battery_level = item.payload.get("battery_level")
        target.lettura_iniziale = item.payload.get("lettura_iniziale")
        target.lettura_finale = item.payload.get("lettura_finale")
        target.consumo_mc = item.payload.get("consumo_mc")
        target.data_lettura = item.payload.get("data_lettura")
        target.operatore_lettura = item.payload.get("operatore_lettura")
        target.intervento_da_eseguire = item.payload.get("intervento_da_eseguire")
        target.intervento_eseguito = item.payload.get("intervento_eseguito")
        target.operatore_intervento = item.payload.get("operatore_intervento")
        target.data_intervento = item.payload.get("data_intervento")
        target.dui = item.payload.get("dui")
        target.codice_fiscale = item.payload.get("codice_fiscale")
        target.codice_fiscale_normalizzato = item.payload.get("codice_fiscale_normalizzato")
        target.subject_id = item.payload.get("subject_id")
        target.coltura = item.payload.get("coltura")
        target.tariffa = item.payload.get("tariffa")
        target.fondo_chiuso = item.payload.get("fondo_chiuso")
        target.telefono = item.payload.get("telefono")
        target.note = item.payload.get("note")
        target.validation_status = item.validation_status
        target.validation_messages = [message.__dict__ for message in item.validation_messages]
        target.source = "excel"
        if existing is None:
            db.add(target)

    db.commit()
    db.refresh(import_record)
    return import_record, prepared
