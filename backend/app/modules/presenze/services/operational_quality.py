from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import time

from app.modules.presenze.models import (
    PRESENZE_CONTRACT_KIND_OPERAIO,
    PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO,
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
)
from app.modules.presenze.services.operai_daily_policy import (
    recognized_daily_minutes,
    recognized_extra_minutes,
)
from app.modules.presenze.services.operai_recognized_minutes import RecognizedOperaiMinutes
from app.modules.presenze.services.operai_rules import (
    OperaiRuleConfig,
    covered_operai_absence_minutes,
    normalize_operai_schedule_code,  # noqa: F401 - compatibility re-export
    resolve_operai_rule,
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
    recognized_minutes: RecognizedOperaiMinutes | None = None

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
    return evaluate_operai_operational_quality(
        collaborator, record, punches,
        operai_rule_configs=operai_rule_configs,
        catasto_month_saturday_coverage_count=catasto_month_saturday_coverage_count,
    )


def evaluate_operai_operational_quality(
    collaborator: PresenzeCollaborator | None,
    record: PresenzeDailyRecord,
    punches: list[PresenzeDailyPunch],
    *,
    operai_rule_configs: Sequence[OperaiRuleConfig] | None = None,
    catasto_month_saturday_coverage_count: int | None = None,
    recognized_minutes: RecognizedOperaiMinutes | None = None,
) -> OperaiOperationalQuality:
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
    worked_minutes = complete_punch_minutes(punches)
    has_inaz_anomaly = _record_has_inaz_anomaly(record)
    covered_absence_minutes = covered_operai_absence_minutes(record, resolved_rule)
    expected_minutes, notes = _operai_expected_minutes(
        collaborator, record, resolved_rule, worked_minutes, covered_absence_minutes,
        catasto_month_saturday_coverage_count,
    )

    if worked_minutes is None and covered_absence_minutes == 0 and expected_minutes > 0:
        return OperaiOperationalQuality(
            status="blocking" if has_inaz_anomaly else "unknown",
            formula_code=formula_code,
            expected_minutes=expected_minutes,
            worked_minutes=None,
            missing_minutes=expected_minutes if has_inaz_anomaly else 0,
            mpe_minutes=0,
            notes=tuple([*notes, "Timbrature complete non disponibili"]),
        )

    worked_minutes_value = worked_minutes or 0
    recognized_minutes = recognized_minutes or recognized_daily_minutes(punches, resolved_rule)
    worked_minutes_value, missing_minutes, mpe_minutes = _operai_accounted_totals(
        record, recognized_minutes, worked_minutes_value, expected_minutes, covered_absence_minutes,
    )
    quality = OperaiOperationalQuality(
        status=_operai_status(missing_minutes, mpe_minutes, resolved_rule),
        formula_code=formula_code,
        expected_minutes=expected_minutes,
        worked_minutes=worked_minutes_value,
        missing_minutes=missing_minutes,
        mpe_minutes=mpe_minutes,
        notes=tuple(notes),
        recognized_minutes=recognized_minutes,
    )
    return _with_operai_notes(record, quality, resolved_rule, covered_absence_minutes)


def _operai_expected_minutes(collaborator, record, rule, worked_minutes, absence, saturday_count):
    expected_minutes = rule.expected_minutes
    formula_code = rule.formula_code
    notes: list[str] = [f"Formula operaio {formula_code}: teorico {expected_minutes // 60}h"]
    if getattr(collaborator, "operai_group", None):
        notes.append(f"Gruppo operaio: {collaborator.operai_group}")
    if (
        collaborator.operai_group == PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO
        and record.work_date.weekday() == 5
        and expected_minutes > 0
        and worked_minutes is None
        and absence == 0
        and (saturday_count or 0) >= 2
    ):
        expected_minutes = 0
        notes[0] = f"Formula operaio {formula_code}: teorico 0h"
        notes.append("Sabato catasto coperto da altri due sabati lavorati/giustificati nel mese")
    if record.work_date.weekday() == 5 and expected_minutes == 0:
        notes.append("Sabato non previsto per il gruppo operaio configurato")

    return expected_minutes, notes


def _operai_status(missing, extra, rule):
    if missing > rule.rule.missing_tolerance_minutes:
        return "blocking"
    if extra > rule.rule.mpe_review_threshold_minutes:
        return "in_analysis"
    return "ok"


def _with_operai_notes(record, quality, resolved_rule, covered_absence_minutes):
    notes = list(quality.notes)
    if _record_has_inaz_anomaly(record) and quality.status != "blocking":
        notes.append("INAZ segnala anomalia, ma la formula GAIA quadra le ore")
    if (record.request_status or "").strip().upper() == "ACC":
        notes.append("Richiesta INAZ accolta dal caposettore")
    if covered_absence_minutes > 0:
        notes.append(f"Assenza configurata copre {covered_absence_minutes} minuti del teorico")
    if quality.mpe_minutes > 0:
        notes.append(f"MPE calcolata da timbrature: {quality.mpe_minutes} minuti")
    if quality.mpe_minutes > resolved_rule.rule.mpe_review_threshold_minutes:
        notes.append(f"MPE oltre soglia giornaliera: {quality.mpe_minutes} minuti")
    if quality.missing_minutes > resolved_rule.rule.missing_tolerance_minutes:
        notes.append(f"Mancano {quality.missing_minutes} minuti rispetto alla formula GAIA")

    return replace(quality, notes=tuple(notes))


def build_daily_operational_quality(
    collaborator: PresenzeCollaborator | None,
    record: PresenzeDailyRecord,
    punches: list[PresenzeDailyPunch],
    *,
    classification=None,
    operai_rule_configs: Sequence[OperaiRuleConfig] | None = None,
    catasto_month_saturday_coverage_count: int | None = None,
) -> OperaiOperationalQuality:
    if collaborator is None or collaborator.contract_kind == PRESENZE_CONTRACT_KIND_OPERAIO:
        return evaluate_operai_operational_quality(
            collaborator,
            record,
            punches,
            operai_rule_configs=operai_rule_configs,
            catasto_month_saturday_coverage_count=catasto_month_saturday_coverage_count,
            recognized_minutes=getattr(classification, "recognized_minutes", None),
        )
    return build_non_operai_operational_quality(
        collaborator,
        record,
        punches,
        classification=classification,
    )


def build_non_operai_operational_quality(
    collaborator: PresenzeCollaborator | None,
    record: PresenzeDailyRecord,
    punches: list[PresenzeDailyPunch],
    *,
    classification=None,
) -> OperaiOperationalQuality:
    if collaborator is None or collaborator.contract_kind == PRESENZE_CONTRACT_KIND_OPERAIO:
        return OperaiOperationalQuality(
            status="unknown",
            formula_code=None,
            expected_minutes=None,
            worked_minutes=None,
            missing_minutes=0,
            mpe_minutes=0,
        )
    worked_minutes = complete_punch_minutes(punches)
    has_inaz_anomaly = _record_has_inaz_anomaly(record)
    request_is_accepted = (record.request_status or "").strip().upper() == "ACC"
    classification_ordinary = getattr(classification, "ordinary_minutes", None)
    if classification_ordinary is None:
        classification_ordinary = record.teo_minutes
    classification_extra = getattr(classification, "extra_minutes", None)
    if classification_extra is None and worked_minutes is not None and classification_ordinary is not None:
        classification_extra = max(0, worked_minutes - classification_ordinary)
    classification_extra_value = classification_extra or 0
    classification_source = getattr(classification, "source", None)
    notes: list[str] = []
    if classification_source:
        notes.append(f"Classificazione GAIA: {classification_source}")
    if request_is_accepted:
        notes.append("Richiesta INAZ accolta dal caposettore")
    if worked_minutes is not None:
        notes.append(f"Timbrature complete ricostruite: {worked_minutes} minuti")
    if classification_extra_value > 0:
        notes.append(f"Extra ricostruiti da GAIA: {classification_extra_value} minuti")
    if has_inaz_anomaly and request_is_accepted and worked_minutes is not None and classification_ordinary is not None:
        notes.append("INAZ segnala un'anomalia tecnica, ma GAIA ricostruisce la giornata da timbrature e richiesta accolta")
        return OperaiOperationalQuality(
            status="ok",
            formula_code=None,
            expected_minutes=classification_ordinary,
            worked_minutes=worked_minutes,
            missing_minutes=0,
            mpe_minutes=classification_extra_value,
            notes=tuple(notes),
        )
    return OperaiOperationalQuality(
        status="unknown",
        formula_code=None,
        expected_minutes=classification_ordinary,
        worked_minutes=worked_minutes,
        missing_minutes=0,
        mpe_minutes=classification_extra_value,
        notes=tuple(notes),
    )


def _operai_accounted_totals(record, recognized, worked, expected, absence):
    if recognized is None:
        return worked, max(0, expected - worked - absence), max(0, worked - expected)
    return (
        recognized.ordinary_minutes + recognized.overtime_minutes,
        max(0, recognized.missing_minutes - absence),
        recognized_extra_minutes(record, recognized),
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
