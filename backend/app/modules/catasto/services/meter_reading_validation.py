from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.modules.catasto.services.meter_reading_linker import link_subject_by_tax_code, normalize_tax_code
from app.modules.catasto.services.validation import validate_codice_fiscale


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


def validate_meter_reading_row(
    db: Session,
    *,
    row_data: dict[str, Any],
    anno: int | None,
    distretto_id: str | None,
    duplicate_key_seen: bool,
) -> tuple[str, list[ValidationMessage], dict[str, Any]]:
    messages: list[ValidationMessage] = []

    punto_consegna = (row_data.get("punto_consegna") or "").strip() if row_data.get("punto_consegna") else ""
    if not punto_consegna:
        messages.append(ValidationMessage(level="error", code="PUNTO_CONSEGNA_MANCANTE", message="Punto consegna mancante.", field="punto_consegna"))
    if anno is None:
        messages.append(ValidationMessage(level="error", code="ANNO_MANCANTE", message="Anno mancante.", field="anno"))
    if not distretto_id:
        messages.append(ValidationMessage(level="error", code="DISTRETTO_MANCANTE", message="Distretto mancante o non deducibile.", field="distretto_id"))
    if duplicate_key_seen:
        messages.append(ValidationMessage(level="error", code="DUPLICATO_FILE", message="Duplicato nel file sulla chiave tecnica.", field="punto_consegna"))

    cf_raw = row_data.get("codice_fiscale")
    cf_validation = validate_codice_fiscale(cf_raw)
    cf_normalizzato = normalize_tax_code(str(cf_validation.get("cf_normalizzato")) if cf_validation.get("cf_normalizzato") else None)
    if not cf_normalizzato:
        messages.append(ValidationMessage(level="warning", code="CF_MANCANTE", message="Codice fiscale mancante.", field="codice_fiscale"))
    elif not bool(cf_validation.get("is_valid")):
        messages.append(ValidationMessage(level="warning", code="CF_ANOMALO", message="Codice fiscale anomalo.", field="codice_fiscale"))

    link = link_subject_by_tax_code(db, cf_normalizzato)
    if cf_normalizzato and link.match_count == 0:
        messages.append(ValidationMessage(level="warning", code="UTENZA_NON_TROVATA", message="Soggetto non trovato per codice fiscale.", field="codice_fiscale"))
    elif cf_normalizzato and link.match_count > 1:
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
        "codice_fiscale_normalizzato": cf_normalizzato,
        "subject_id": link.subject_id,
        "subject_display_name": link.subject_display_name,
    }
    return status, messages, resolved
