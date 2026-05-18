from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatAnomalia, CatDistretto, CatMeterReading, CatMeterReadingImport
from app.modules.catasto.services.meter_reading_parser import ParsedMeterReadingsFile, parse_meter_readings_excel
from app.modules.catasto.services.meter_reading_validation import (
    ValidationMessage,
    classify_meter_record_type,
    validate_meter_reading_row,
)


ImportMode = Literal["import", "upsert", "replace"]


@dataclass
class PreparedMeterReadingItem:
    row_number: int
    payload: dict[str, Any]
    validation_status: str
    validation_messages: list[ValidationMessage]
    subject_display_name: str | None


METER_READING_ANOMALIA_LABELS = {
    "MR-01-cont_tesser_cf_mancante": "Contatore tessera senza codice fiscale utenza",
    "MR-02-cont_no_tes_cf_mancante": "Contatore non tessera senza codice fiscale utenza",
}


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


def _distretto_code_candidates_from_filename(filename: str | None) -> list[str]:
    if not filename:
        return []
    normalized = unicodedata.normalize("NFD", filename)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    composite_match = re.search(r"\bD?\s*0*(\d{1,3})\s*[-_/ ]\s*([0-9A-Za-z]{1,3})\b", normalized, flags=re.IGNORECASE)
    if not composite_match:
        return []

    base_code = composite_match.group(1)
    suffix = composite_match.group(2).upper()
    candidates: list[str] = []
    if suffix.isdigit():
        candidates.append(f"{base_code}{suffix}")
        digit = int(suffix)
        if 1 <= digit <= 26:
            candidates.append(f"{base_code}{chr(ord('A') + digit - 1)}")
    else:
        candidates.append(f"{base_code}{suffix}")
    return candidates


def _normalize_filename_token(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFD", value)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.upper()
    normalized = re.sub(r"[^A-Z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def resolve_distretto(
    db: Session,
    *,
    distretto_id: UUID | None = None,
    distretto_code: str | None = None,
    filename: str | None = None,
) -> CatDistretto | None:
    if distretto_id is not None:
        return db.get(CatDistretto, distretto_id)

    candidates = db.execute(select(CatDistretto).order_by(CatDistretto.num_distretto)).scalars().all()
    normalized = _normalize_distretto_code(distretto_code)
    if normalized:
        for item in candidates:
            if _normalize_distretto_code(item.num_distretto) == normalized:
                return item

    composite_candidates = _distretto_code_candidates_from_filename(filename)
    if composite_candidates:
        normalized_composite = [_normalize_distretto_code(value) for value in composite_candidates]
        for wanted in normalized_composite:
            for item in candidates:
                if _normalize_distretto_code(item.num_distretto) == wanted:
                    return item

    normalized_filename = _normalize_filename_token(filename)
    if normalized_filename:
        # Prefer exact district-name tokens inside the filename when the numeric code is absent or ambiguous.
        for item in candidates:
            normalized_name = _normalize_filename_token(item.nome_distretto)
            if normalized_name and normalized_name in normalized_filename:
                return item

        filename_tokens = set(normalized_filename.split())
        for item in candidates:
            normalized_name = _normalize_filename_token(item.nome_distretto)
            if not normalized_name:
                continue
            name_tokens = [token for token in normalized_name.split() if token not in {"DISTRETTO", "IRRIGUO", "IRRIGUI"}]
            if name_tokens and all(token in filename_tokens for token in name_tokens):
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
    distretto = resolve_distretto(
        db,
        distretto_id=distretto_id,
        distretto_code=parsed.distretto_code,
        filename=filename,
    )

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
            "record_type": row.data.get("record_type"),
            "tipologia_idrante": row.data.get("tipologia_idrante"),
            "record_kind": resolved["record_kind"],
            "normalized_record_type": resolved["normalized_record_type"],
            "operational_state": resolved["operational_state"],
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


def _desired_anomaly_type(item: PreparedMeterReadingItem) -> str | None:
    if item.payload.get("record_kind") != "meter_reading":
        return None
    if item.payload.get("operational_state") in {"inactive", "dismissed_point"}:
        return None
    if item.payload.get("codice_fiscale_normalizzato"):
        return None
    normalized_type = item.payload.get("normalized_record_type")
    if normalized_type == "CONT_TESSER":
        return "MR-01-cont_tesser_cf_mancante"
    if normalized_type == "CONT_NO_TES":
        return "MR-02-cont_no_tes_cf_mancante"
    return None


def _sync_meter_reading_anomalies(
    db: Session,
    *,
    prepared: PreparedMeterReadingsImport,
    import_record: CatMeterReadingImport,
) -> None:
    if prepared.anno is None:
        return

    tracked_types = set(METER_READING_ANOMALIA_LABELS)
    target_distretto_id = str(prepared.distretto.id) if prepared.distretto else None
    existing = db.execute(
        select(CatAnomalia).where(
            CatAnomalia.anno_campagna == prepared.anno,
            CatAnomalia.tipo.in_(tracked_types),
            CatAnomalia.status == "aperta",
        )
    ).scalars().all()

    existing_by_key: dict[tuple[str, str, int], CatAnomalia] = {}
    for anomalia in existing:
        dati_json = anomalia.dati_json if isinstance(anomalia.dati_json, dict) else {}
        if str(dati_json.get("distretto_id") or "") != str(target_distretto_id or ""):
            continue
        key = (
            anomalia.tipo,
            str(dati_json.get("punto_consegna") or "").strip().upper(),
            int(dati_json.get("row_number") or 0),
        )
        existing_by_key[key] = anomalia

    desired_keys: set[tuple[str, str, int]] = set()
    for item in prepared.items:
        anomaly_type = _desired_anomaly_type(item)
        if anomaly_type is None:
            continue
        point = str(item.payload.get("punto_consegna") or "").strip().upper()
        key = (anomaly_type, point, item.row_number)
        desired_keys.add(key)
        if key in existing_by_key:
            continue
        db.add(
            CatAnomalia(
                anno_campagna=prepared.anno,
                tipo=anomaly_type,
                severita="warning",
                descrizione=METER_READING_ANOMALIA_LABELS[anomaly_type],
                dati_json={
                    "import_id": str(import_record.id),
                    "filename": prepared.filename,
                    "row_number": item.row_number,
                    "punto_consegna": item.payload.get("punto_consegna"),
                    "matricola": item.payload.get("matricola"),
                    "tipologia_idrante": item.payload.get("tipologia_idrante"),
                    "record_type": item.payload.get("record_type"),
                    "normalized_record_type": item.payload.get("normalized_record_type"),
                    "operational_state": item.payload.get("operational_state"),
                    "codice_fiscale": item.payload.get("codice_fiscale"),
                    "distretto_id": str(prepared.distretto.id) if prepared.distretto else None,
                    "distretto_numero": prepared.distretto.num_distretto if prepared.distretto else None,
                    "distretto_nome": prepared.distretto.nome_distretto if prepared.distretto else None,
                },
                status="aperta",
            )
        )

    for key, anomalia in existing_by_key.items():
        if key not in desired_keys:
            anomalia.status = "chiusa"
            anomalia.note_operatore = "Chiusura automatica dopo reimport letture contatori."
            db.add(anomalia)


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
        target.record_type = item.payload.get("record_type")
        target.record_kind = item.payload.get("record_kind")
        target.operational_state = item.payload.get("operational_state")
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

    _sync_meter_reading_anomalies(db, prepared=prepared, import_record=import_record)
    db.commit()
    db.refresh(import_record)
    return import_record, prepared
