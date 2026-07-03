from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from app.modules.presenze.models import (
    PRESENZE_CONTRACT_KIND_OPERAIO,
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
)
from app.modules.presenze.services.parser import extract_detail_payload, parse_schedule_code_from_detail

OPERAI_EQUIVALENT_SCHEDULE_CODES = {
    "OPE0714",
    "OP_5.3_12.3",
    "OPESAB",
    "OSAB5.3_12.3",
}
OPERAI_DAILY_THEORETICAL_MINUTES = 7 * 60
OPERAI_MISSING_TOLERANCE_MINUTES = 5


@dataclass(frozen=True)
class OperaiOperationalQuality:
    status: str
    formula_code: str | None
    expected_minutes: int | None
    worked_minutes: int | None
    missing_minutes: int
    mpe_minutes: int
    notes: tuple[str, ...] = ()

    @property
    def is_applicable(self) -> bool:
        return self.formula_code is not None and self.expected_minutes is not None


def normalize_operai_schedule_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    if not normalized:
        return None
    for code in OPERAI_EQUIVALENT_SCHEDULE_CODES:
        if normalized == code.upper():
            return code
    return None


def resolve_operai_schedule_code(record: PresenzeDailyRecord) -> str | None:
    explicit = normalize_operai_schedule_code(record.schedule_code)
    if explicit is not None:
        return explicit
    if isinstance(record.raw_payload_json, dict):
        detail = extract_detail_payload(record.raw_payload_json)
        return normalize_operai_schedule_code(parse_schedule_code_from_detail(detail.get("programmed_schedule")))
    return None


def complete_punch_minutes(punches: list[PresenzeDailyPunch]) -> int | None:
    total = 0
    has_complete_pair = False
    for punch in punches:
        if punch.entry_time is None or punch.exit_time is None:
            continue
        has_complete_pair = True
        total += _minutes_between(punch.entry_time, punch.exit_time)
    return total if has_complete_pair else None


def build_operai_operational_quality(
    collaborator: PresenzeCollaborator | None,
    record: PresenzeDailyRecord,
    punches: list[PresenzeDailyPunch],
) -> OperaiOperationalQuality:
    if collaborator is None or collaborator.contract_kind != PRESENZE_CONTRACT_KIND_OPERAIO:
        return OperaiOperationalQuality(
            status="unknown",
            formula_code=None,
            expected_minutes=None,
            worked_minutes=None,
            missing_minutes=0,
            mpe_minutes=0,
        )
    formula_code = resolve_operai_schedule_code(record)
    if formula_code is None:
        return OperaiOperationalQuality(
            status="unknown",
            formula_code=None,
            expected_minutes=None,
            worked_minutes=None,
            missing_minutes=0,
            mpe_minutes=0,
        )

    expected_minutes = OPERAI_DAILY_THEORETICAL_MINUTES
    worked_minutes = complete_punch_minutes(punches)
    has_inaz_anomaly = _record_has_inaz_anomaly(record)
    request_is_accepted = (record.request_status or "").strip().upper() == "ACC"
    notes: list[str] = [f"Formula operaio {formula_code}: teorico {expected_minutes // 60}h"]

    if worked_minutes is None:
        return OperaiOperationalQuality(
            status="blocking" if has_inaz_anomaly else "unknown",
            formula_code=formula_code,
            expected_minutes=expected_minutes,
            worked_minutes=None,
            missing_minutes=expected_minutes if has_inaz_anomaly else 0,
            mpe_minutes=0,
            notes=tuple(notes + ["Timbrature complete non disponibili"]),
        )

    missing_minutes = max(0, expected_minutes - worked_minutes)
    mpe_minutes = max(0, worked_minutes - expected_minutes)
    if missing_minutes > OPERAI_MISSING_TOLERANCE_MINUTES:
        status = "blocking"
    elif has_inaz_anomaly or request_is_accepted:
        status = "in_analysis"
    else:
        status = "ok"
    if has_inaz_anomaly and status != "blocking":
        notes.append("INAZ segnala anomalia, ma la formula GAIA quadra le ore")
    if request_is_accepted:
        notes.append("Richiesta INAZ accolta dal caposettore")
    if mpe_minutes > 0:
        notes.append(f"MPE calcolata da timbrature: {mpe_minutes} minuti")
    if missing_minutes > OPERAI_MISSING_TOLERANCE_MINUTES:
        notes.append(f"Mancano {missing_minutes} minuti rispetto alla formula GAIA")

    return OperaiOperationalQuality(
        status=status,
        formula_code=formula_code,
        expected_minutes=expected_minutes,
        worked_minutes=worked_minutes,
        missing_minutes=missing_minutes,
        mpe_minutes=mpe_minutes,
        notes=tuple(notes),
    )


def _record_has_inaz_anomaly(record: PresenzeDailyRecord) -> bool:
    if isinstance(record.raw_payload_json, dict):
        detail = extract_detail_payload(record.raw_payload_json)
        if detail.get("anomalies") or detail.get("error"):
            return True
    values = (record.stato, record.evidenze)
    return any("anom" in (value or "").casefold() for value in values)


def _minutes_between(start: time, end: time) -> int:
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    if end_minutes < start_minutes:
        end_minutes += 24 * 60
    return end_minutes - start_minutes
