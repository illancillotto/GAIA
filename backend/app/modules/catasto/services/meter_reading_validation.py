from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.modules.catasto.services.meter_reading_linker import (
    extract_tax_code_candidates,
    link_subject_by_tax_code,
    link_subjects_by_tax_codes,
    normalize_tax_code,
)
from app.modules.catasto.services.validation import validate_codice_fiscale

METER_READING_TYPES = {"CONT_TESSER", "CONT_NO_TES"}


@dataclass
class ValidationMessage:
    level: str
    code: str
    message: str
    field: str | None = None


def _is_low_battery(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.lower()
    if "bassa" in lowered or "low" in lowered:
        return True
    match = re.search(r"(\d+)", lowered)
    return bool(match and int(match.group(1)) <= 20)


def _phone_is_anomalous(value: str | None) -> bool:
    if not value:
        return False
    digits = re.sub(r"\D", "", value)
    return bool(digits) and (len(digits) < 8 or len(digits) > 15)


def _decimal_abs(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.copy_abs()


def normalize_meter_record_type(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^A-Z0-9]+", "_", value.strip().upper()).strip("_") or None
    if normalized == "CONT_TES":
        return "CONT_TESSER"
    return normalized


def classify_meter_record_type(value: str | None) -> str:
    normalized = normalize_meter_record_type(value)
    if normalized is None:
        return "meter_reading"
    return "meter_reading" if normalized in METER_READING_TYPES else "operator_activity"


def detect_operational_state(
    *,
    record_type: str | None,
    asset_description: str | None,
    note: str | None,
) -> str:
    note_text = (note or "").strip().lower()
    asset_text = (asset_description or "").strip().lower()
    normalized_record_type = normalize_meter_record_type(record_type)

    if normalized_record_type == "DISMESSO" or "dismess" in asset_text or "dismess" in note_text:
        return "dismissed_point"
    if "inutilizz" in note_text:
        return "inactive"
    if normalized_record_type in METER_READING_TYPES:
        return "active"
    return "activity"


def validate_meter_reading_row(
    db: Session,
    *,
    row_data: dict[str, Any],
    anno: int | None,
    distretto_id: str | None,
    duplicate_key_seen: bool,
    allow_missing_distretto: bool = False,
) -> tuple[str, list[ValidationMessage], dict[str, Any]]:
    messages: list[ValidationMessage] = []
    normalized_record_type = normalize_meter_record_type(row_data.get("record_type"))
    record_kind = classify_meter_record_type(row_data.get("record_type"))
    operational_state = detect_operational_state(
        record_type=row_data.get("record_type"),
        asset_description=row_data.get("tipologia_idrante"),
        note=row_data.get("note"),
    )
    if operational_state == "dismissed_point":
        record_kind = "dismissed_point"
    is_meter_reading = record_kind == "meter_reading"
    is_dismissed_or_inactive = operational_state in {"inactive", "dismissed_point"}

    punto_consegna = (row_data.get("punto_consegna") or "").strip() if row_data.get("punto_consegna") else ""
    if is_meter_reading and not punto_consegna:
        messages.append(ValidationMessage(level="error", code="PUNTO_CONSEGNA_MANCANTE", message="Punto consegna mancante.", field="punto_consegna"))
    if anno is None:
        messages.append(ValidationMessage(level="error", code="ANNO_MANCANTE", message="Anno mancante.", field="anno"))
    if not distretto_id and allow_missing_distretto:
        messages.append(
            ValidationMessage(
                level="info",
                code="DISTRETTO_GENERICO",
                message="File progetto gestito senza assegnazione a un distretto specifico.",
                field="distretto_id",
            )
        )
    elif not distretto_id:
        messages.append(ValidationMessage(level="error", code="DISTRETTO_MANCANTE", message="Distretto mancante o non deducibile.", field="distretto_id"))
    if is_meter_reading and duplicate_key_seen:
        messages.append(ValidationMessage(level="error", code="DUPLICATO_FILE", message="Duplicato nel file sulla chiave tecnica.", field="punto_consegna"))

    cf_raw = row_data.get("codice_fiscale")
    tax_code_candidates = extract_tax_code_candidates(str(cf_raw) if cf_raw else None)
    has_multiple_tax_codes = len(tax_code_candidates) > 1
    candidate_links = []
    matched_labels: list[str] = []
    cf_validation = validate_codice_fiscale(cf_raw) if not has_multiple_tax_codes else {"cf_normalizzato": None, "is_valid": False}
    cf_normalizzato = normalize_tax_code(str(cf_validation.get("cf_normalizzato")) if cf_validation.get("cf_normalizzato") else None)
    if is_meter_reading:
        if has_multiple_tax_codes:
            candidate_links = link_subjects_by_tax_codes(db, tax_code_candidates)
            matched_labels = [item.subject_display_name for item in candidate_links]
            messages.append(
                ValidationMessage(
                    level="warning",
                    code="CONTATORE_CONDIVISO",
                    message=(
                        "Rilevati più codici fiscali o partite IVA sulla stessa riga; "
                        "il contatore viene mantenuto ma la lettura non viene assegnata automaticamente a un singolo soggetto."
                    ),
                    field="codice_fiscale",
                )
            )
            if not candidate_links:
                messages.append(
                    ValidationMessage(
                        level="warning",
                        code="UTENZE_NON_TROVATE",
                        message="Nessuno dei codici fiscali o partita IVA rilevati risulta associato a un soggetto noto.",
                        field="codice_fiscale",
                    )
                )
            cf_normalizzato = None
            link = link_subject_by_tax_code(db, None)
        elif not cf_normalizzato:
            if normalized_record_type == "CONT_TESSER":
                messages.append(ValidationMessage(
                    level="info" if is_dismissed_or_inactive else "warning",
                    code="CF_MANCANTE_CONT_TESSER",
                    message="Contatore tessera senza codice fiscale utenza.",
                    field="codice_fiscale",
                ))
            else:
                messages.append(ValidationMessage(
                    level="info" if is_dismissed_or_inactive else "warning",
                    code="CF_MANCANTE_CONT_NO_TES",
                    message="Contatore non tessera senza codice fiscale utenza.",
                    field="codice_fiscale",
                ))
            link = link_subject_by_tax_code(db, None)
        elif not bool(cf_validation.get("is_valid")):
            messages.append(ValidationMessage(level="warning", code="CF_ANOMALO", message="Codice fiscale anomalo.", field="codice_fiscale"))
            link = link_subject_by_tax_code(db, cf_normalizzato)
        else:
            link = link_subject_by_tax_code(db, cf_normalizzato)
    else:
        messages.append(
            ValidationMessage(
                level="info",
                code="ATTIVITA_OPERATORE",
                message="Riga registrata come attività operatore e non come lettura contatore standard.",
                field="record_type",
            )
        )
        link = link_subject_by_tax_code(db, None)

    if operational_state == "inactive":
        messages.append(
            ValidationMessage(
                level="info",
                code="CONTATORE_INUTILIZZATO",
                message="Contatore marcato come inutilizzato nelle note operative.",
                field="note",
            )
        )
    elif operational_state == "dismissed_point":
        messages.append(
            ValidationMessage(
                level="info",
                code="PUNTO_DISMESSO",
                message="Punto di consegna dismesso o fuori servizio.",
                field="tipologia_idrante",
            )
        )

    if is_meter_reading and not has_multiple_tax_codes and cf_normalizzato and link.match_count == 0:
        messages.append(ValidationMessage(level="warning", code="UTENZA_NON_TROVATA", message="Soggetto non trovato per codice fiscale.", field="codice_fiscale"))
    elif is_meter_reading and not has_multiple_tax_codes and cf_normalizzato and link.match_count > 1:
        messages.append(ValidationMessage(level="warning", code="UTENZE_MULTIPLE", message="Più soggetti trovati per lo stesso codice fiscale.", field="codice_fiscale"))

    if _phone_is_anomalous(row_data.get("telefono")):
        messages.append(ValidationMessage(level="warning", code="TELEFONO_ANOMALO", message="Telefono anomalo.", field="telefono"))

    lettura_iniziale = row_data.get("lettura_iniziale")
    lettura_finale = row_data.get("lettura_finale")
    consumo_mc = row_data.get("consumo_mc")
    if lettura_iniziale is not None and lettura_finale is not None and lettura_finale < lettura_iniziale:
        messages.append(ValidationMessage(level="warning", code="LETTURA_INVERTITA", message="Lettura finale minore della iniziale.", field="lettura_finale"))
    if (
        lettura_iniziale is not None
        and lettura_finale is not None
        and consumo_mc is not None
        and _decimal_abs((lettura_finale - lettura_iniziale) - consumo_mc) not in (None, Decimal("0"))
        and _decimal_abs((lettura_finale - lettura_iniziale) - consumo_mc) > Decimal("1")
    ):
        messages.append(ValidationMessage(level="warning", code="CONSUMO_INCOERENTE", message="Consumo incoerente con le letture.", field="consumo_mc"))

    if row_data.get("intervento_da_eseguire"):
        messages.append(ValidationMessage(level="warning", code="INTERVENTO_APERTO", message="Intervento da eseguire valorizzato.", field="intervento_da_eseguire"))
    if _is_low_battery(row_data.get("battery_level")):
        messages.append(ValidationMessage(level="warning", code="BATTERIA_BASSA", message="Batteria bassa.", field="battery_level"))

    status = "valid"
    if any(item.level == "error" for item in messages):
        status = "error"
    elif any(item.level == "warning" for item in messages):
        status = "warning"

    resolved = {
        "record_kind": record_kind,
        "normalized_record_type": normalized_record_type,
        "operational_state": operational_state,
        "codice_fiscale_normalizzato": cf_normalizzato,
        "subject_id": None if has_multiple_tax_codes else link.subject_id,
        "subject_display_name": (
            ", ".join(matched_labels[:3]) + ("..." if len(matched_labels) > 3 else "")
            if has_multiple_tax_codes and matched_labels
            else link.subject_display_name
        ),
        "tax_code_candidates": tax_code_candidates,
        "shared_meter_subject_ids": [str(item.subject_id) for item in candidate_links] if has_multiple_tax_codes else [],
        "shared_meter_subject_labels": matched_labels if has_multiple_tax_codes else [],
    }
    return status, messages, resolved
