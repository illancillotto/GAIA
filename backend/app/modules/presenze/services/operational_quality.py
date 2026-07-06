from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Sequence

from app.modules.presenze.models import (
    PRESENZE_CONTRACT_KIND_OPERAIO,
    PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO,
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
)
from app.modules.presenze.services.operai_rules import (
    OperaiRuleConfig,
    covered_operai_absence_minutes,
    normalize_operai_schedule_code,
    resolve_operai_rule,
    resolve_operai_schedule_code,
)
from app.modules.presenze.services.parser import extract_detail_payload


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
    *,
    operai_rule_configs: Sequence[OperaiRuleConfig] | None = None,
    catasto_month_saturday_coverage_count: int | None = None,
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
    resolved_rule = resolve_operai_rule(collaborator, record, operai_rule_configs)
    if resolved_rule is None:
        return OperaiOperationalQuality(
            status="unknown",
            formula_code=None,
            expected_minutes=None,
            worked_minutes=None,
            missing_minutes=0,
            mpe_minutes=0,
        )

    formula_code = resolved_rule.formula_code
    expected_minutes = resolved_rule.expected_minutes
    worked_minutes = complete_punch_minutes(punches)
    has_inaz_anomaly = _record_has_inaz_anomaly(record)
    request_is_accepted = (record.request_status or "").strip().upper() == "ACC"
    covered_absence_minutes = covered_operai_absence_minutes(record, resolved_rule)
    notes: list[str] = [f"Formula operaio {formula_code}: teorico {expected_minutes // 60}h"]
    if getattr(collaborator, "operai_group", None):
        notes.append(f"Gruppo operaio: {collaborator.operai_group}")
    if (
        collaborator.operai_group == PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO
        and record.work_date.weekday() == 5
        and expected_minutes > 0
        and worked_minutes is None
        and covered_absence_minutes == 0
        and (catasto_month_saturday_coverage_count or 0) >= 2
    ):
        expected_minutes = 0
        notes[0] = f"Formula operaio {formula_code}: teorico 0h"
        notes.append("Sabato catasto coperto da altri due sabati lavorati/giustificati nel mese")
    if record.work_date.weekday() == 5 and expected_minutes == 0:
        notes.append("Sabato non previsto per il gruppo operaio configurato")

    if worked_minutes is None and covered_absence_minutes == 0 and expected_minutes > 0:
        return OperaiOperationalQuality(
            status="blocking" if has_inaz_anomaly else "unknown",
            formula_code=formula_code,
            expected_minutes=expected_minutes,
            worked_minutes=None,
            missing_minutes=expected_minutes if has_inaz_anomaly else 0,
            mpe_minutes=0,
            notes=tuple(notes + ["Timbrature complete non disponibili"]),
        )

    worked_minutes_value = worked_minutes or 0
    credited_minutes = worked_minutes_value + covered_absence_minutes
    missing_minutes = max(0, expected_minutes - credited_minutes)
    mpe_minutes = max(0, worked_minutes_value - expected_minutes)
    if missing_minutes > resolved_rule.rule.missing_tolerance_minutes:
        status = "blocking"
    elif mpe_minutes > resolved_rule.rule.mpe_review_threshold_minutes:
        status = "blocking"
    elif covered_absence_minutes > 0 and missing_minutes == 0:
        status = "ok"
    else:
        status = "ok"
    if has_inaz_anomaly and status != "blocking":
        notes.append("INAZ segnala anomalia, ma la formula GAIA quadra le ore")
    if request_is_accepted:
        notes.append("Richiesta INAZ accolta dal caposettore")
    if covered_absence_minutes > 0:
        notes.append(f"Assenza configurata copre {covered_absence_minutes} minuti del teorico")
    if mpe_minutes > 0:
        notes.append(f"MPE calcolata da timbrature: {mpe_minutes} minuti")
    if mpe_minutes > resolved_rule.rule.mpe_review_threshold_minutes:
        notes.append(f"MPE oltre soglia giornaliera: {mpe_minutes} minuti")
    if missing_minutes > resolved_rule.rule.missing_tolerance_minutes:
        notes.append(f"Mancano {missing_minutes} minuti rispetto alla formula GAIA")

    return OperaiOperationalQuality(
        status=status,
        formula_code=formula_code,
        expected_minutes=expected_minutes,
        worked_minutes=worked_minutes_value,
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
