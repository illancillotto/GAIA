from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.presenze.models import (
    PRESENZE_CONTRACT_KIND_OPERAIO,
    PRESENZE_OPERAI_GROUP_AGRARIO,
    PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO,
    PresenzeCollaborator,
    PresenzeDailyRecord,
    PresenzeOperaiRuleConfig,
)
from app.modules.presenze.services.parser import (
    extract_detail_payload,
    parse_schedule_code_from_detail,
)

VALID_PRESENZE_OPERAI_GROUPS = {
    PRESENZE_OPERAI_GROUP_AGRARIO,
    PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO,
}
DEFAULT_MPE_REVIEW_THRESHOLD_MINUTES = 5 * 60
LEGACY_MPE_REVIEW_THRESHOLD_MINUTES = 2 * 60
PREVIOUS_MPE_REVIEW_THRESHOLD_MINUTES = 3 * 60

# Effective INAZ variants use the existing group policy, including persisted
# configurations. Explicit summer Saturday codes attest the day's duration.
SCHEDULE_VARIANTS = {
    "OPEF0613": "OPE0613",
    "OPESACE": "OPESAB",
    "OPSABE": "OPESAB",
    "OSAB5.3_11.3": "OSAB5.3_12.3",
}
SUMMER_SATURDAY_MINUTES = {"OPESACE": 360, "OPSABE": 390, "OSAB5.3_11.3": 360}


@dataclass(frozen=True)
class OperaiRuleConfig:
    code: str
    label: str
    operai_group: str | None
    weekday_schedule_codes: tuple[str, ...]
    saturday_schedule_codes: tuple[str, ...]
    saturday_week_ordinals: tuple[int, ...]
    weekday_expected_minutes: int
    saturday_expected_minutes: int
    missing_tolerance_minutes: int
    mpe_review_threshold_minutes: int
    allowed_absence_causes: tuple[str, ...]
    is_active: bool = True


@dataclass(frozen=True)
class ResolvedOperaiRule:
    rule: OperaiRuleConfig
    formula_code: str
    expected_minutes: int
    saturday_is_scheduled: bool


def normalize_operai_group(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized not in VALID_PRESENZE_OPERAI_GROUPS:
        return None
    return normalized


def normalize_operai_schedule_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def resolve_operai_schedule_code(record: PresenzeDailyRecord) -> str | None:
    explicit = normalize_operai_schedule_code(record.schedule_code)
    if explicit is not None:
        return explicit
    if isinstance(record.raw_payload_json, dict):
        detail = extract_detail_payload(record.raw_payload_json)
        return normalize_operai_schedule_code(parse_schedule_code_from_detail(detail.get("programmed_schedule")))
    return None


def default_operai_rule_configs() -> tuple[OperaiRuleConfig, ...]:
    return (
        OperaiRuleConfig(
            code="OPERAI_AGRARIO_1E3SAB",
            label="Operai agrario con sabati 1 e 3",
            operai_group=PRESENZE_OPERAI_GROUP_AGRARIO,
            weekday_schedule_codes=("OPE0714", "OPE0736", "OPE0613", "OP_5.3_12.3"),
            saturday_schedule_codes=("OPESAB", "OSAB5.3_12.3"),
            saturday_week_ordinals=(1, 3),
            weekday_expected_minutes=7 * 60,
            saturday_expected_minutes=6 * 60 + 30,
            missing_tolerance_minutes=5,
            mpe_review_threshold_minutes=DEFAULT_MPE_REVIEW_THRESHOLD_MINUTES,
            allowed_absence_causes=("ferie", "permesso"),
        ),
        OperaiRuleConfig(
            code="OPERAI_CATASTO_MAGAZZINO_ALTERNATI",
            label="Operai catasto o magazzino con sabati alternati",
            operai_group=PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO,
            weekday_schedule_codes=("OPE0714", "OPE0736", "OPE0613", "OP_5.3_12.3"),
            saturday_schedule_codes=("OPESAB", "OSAB5.3_12.3"),
            saturday_week_ordinals=(),
            weekday_expected_minutes=7 * 60,
            saturday_expected_minutes=6 * 60,
            missing_tolerance_minutes=5,
            mpe_review_threshold_minutes=DEFAULT_MPE_REVIEW_THRESHOLD_MINUTES,
            allowed_absence_causes=("ferie", "permesso"),
        ),
    )


def serialize_default_operai_rule_payloads() -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for item in default_operai_rule_configs():
        payloads.append(
            {
                "code": item.code,
                "label": item.label,
                "operai_group": item.operai_group,
                "weekday_schedule_codes": list(item.weekday_schedule_codes),
                "saturday_schedule_codes": list(item.saturday_schedule_codes),
                "saturday_week_ordinals": list(item.saturday_week_ordinals),
                "weekday_expected_minutes": item.weekday_expected_minutes,
                "saturday_expected_minutes": item.saturday_expected_minutes,
                "missing_tolerance_minutes": item.missing_tolerance_minutes,
                "mpe_review_threshold_minutes": item.mpe_review_threshold_minutes,
                "allowed_absence_causes": list(item.allowed_absence_causes),
                "is_active": item.is_active,
            }
        )
    return payloads


def ensure_operai_rule_configs(db: Session) -> list[PresenzeOperaiRuleConfig]:
    existing = db.execute(select(PresenzeOperaiRuleConfig).order_by(PresenzeOperaiRuleConfig.code.asc())).scalars().all()
    existing_by_code = {item.code.strip().upper(): item for item in existing}
    default_payloads_by_code = {str(payload["code"]).strip().upper(): payload for payload in serialize_default_operai_rule_payloads()}
    created = False
    updated = False
    for payload in serialize_default_operai_rule_payloads():
        code = str(payload["code"]).strip().upper()
        if code in existing_by_code:
            continue
        item = PresenzeOperaiRuleConfig(**payload)
        db.add(item)
        created = True
    for code, item in existing_by_code.items():
        default_payload = default_payloads_by_code.get(code)
        if default_payload is None:
            continue
        if item.mpe_review_threshold_minutes not in (LEGACY_MPE_REVIEW_THRESHOLD_MINUTES, PREVIOUS_MPE_REVIEW_THRESHOLD_MINUTES):
            continue
        item.mpe_review_threshold_minutes = int(default_payload["mpe_review_threshold_minutes"])
        updated = True
    if created or updated:
        db.flush()
    return db.execute(select(PresenzeOperaiRuleConfig).order_by(PresenzeOperaiRuleConfig.code.asc())).scalars().all()


def load_operai_rule_configs(db: Session) -> tuple[OperaiRuleConfig, ...]:
    rows = db.execute(select(PresenzeOperaiRuleConfig).order_by(PresenzeOperaiRuleConfig.code.asc())).scalars().all()
    if not rows:
        return default_operai_rule_configs()
    return tuple(_model_to_rule(item) for item in rows)


def resolve_operai_rule(
    collaborator: PresenzeCollaborator | None,
    record: PresenzeDailyRecord,
    configs: Sequence[OperaiRuleConfig] | None = None,
) -> ResolvedOperaiRule | None:
    if collaborator is None or collaborator.contract_kind != PRESENZE_CONTRACT_KIND_OPERAIO:
        return None
    schedule_code = resolve_operai_schedule_code(record)
    if schedule_code is None:
        return None
    normalized_group = normalize_operai_group(getattr(collaborator, "operai_group", None))
    active_configs = tuple(item for item in (configs or default_operai_rule_configs()) if item.is_active)
    is_saturday = record.work_date.weekday() == 5
    for rule in active_configs:
        if rule.operai_group is not None and rule.operai_group != normalized_group:
            continue
        matched_codes = rule.weekday_schedule_codes + rule.saturday_schedule_codes if is_saturday else rule.weekday_schedule_codes
        if schedule_code not in matched_codes and SCHEDULE_VARIANTS.get(schedule_code) not in matched_codes:
            continue
        return _resolved_schedule_rule(rule, schedule_code, record.work_date)

    if normalized_group is None and SCHEDULE_VARIANTS.get(schedule_code, schedule_code) in {"OPE0714", "OPE0736", "OPE0613", "OP_5.3_12.3", "OPESAB", "OSAB5.3_12.3"}:
        fallback = OperaiRuleConfig(
            code="OPERAI_LEGACY_FALLBACK",
            label="Fallback legacy operai",
            operai_group=None,
            weekday_schedule_codes=("OPE0714", "OPE0736", "OPE0613", "OP_5.3_12.3"),
            saturday_schedule_codes=("OPESAB", "OSAB5.3_12.3"),
            saturday_week_ordinals=(1, 2, 3, 4, 5),
            weekday_expected_minutes=7 * 60,
            saturday_expected_minutes=7 * 60,
            missing_tolerance_minutes=5,
            mpe_review_threshold_minutes=DEFAULT_MPE_REVIEW_THRESHOLD_MINUTES,
            allowed_absence_causes=("ferie", "permesso"),
        )
        return _resolved_schedule_rule(fallback, schedule_code, record.work_date)
    return None


def _resolved_schedule_rule(rule, code, work_date):
    if work_date.weekday() != 5 or SCHEDULE_VARIANTS.get(code, code) in rule.weekday_schedule_codes:
        return ResolvedOperaiRule(rule, code, rule.weekday_expected_minutes, False)
    if code in SUMMER_SATURDAY_MINUTES:
        return ResolvedOperaiRule(rule, code, SUMMER_SATURDAY_MINUTES[code], True)
    scheduled = (
        rule.operai_group == PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO
        or saturday_ordinal_in_month(work_date) in rule.saturday_week_ordinals
    )
    return ResolvedOperaiRule(
        rule, code, rule.saturday_expected_minutes if scheduled else 0, scheduled
    )


def saturday_ordinal_in_month(work_date: date) -> int:
    return ((work_date.day - 1) // 7) + 1


def covered_operai_absence_minutes(record: PresenzeDailyRecord, resolved_rule: ResolvedOperaiRule | None) -> int:
    if resolved_rule is None:
        return 0
    cause = getattr(record, "resolved_absence_cause", None)
    normalized_cause = cause.strip().lower() if isinstance(cause, str) else None
    if normalized_cause not in resolved_rule.rule.allowed_absence_causes:
        return 0
    absence_minutes = record.absence_minutes or 0
    justified_minutes = record.justified_minutes or 0
    return max(absence_minutes, justified_minutes)


def _normalize_codes(values: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        item = normalize_operai_schedule_code(value)
        if item:
            normalized.append(item)
    return tuple(normalized)


def _normalize_week_ordinals(values: Iterable[int]) -> tuple[int, ...]:
    normalized = sorted({int(value) for value in values if 1 <= int(value) <= 5})
    return tuple(normalized)


def _normalize_absence_causes(values: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        item = value.strip().lower()
        if item:
            normalized.append(item)
    return tuple(dict.fromkeys(normalized))


def _model_to_rule(item: PresenzeOperaiRuleConfig) -> OperaiRuleConfig:
    return OperaiRuleConfig(
        code=item.code,
        label=item.label,
        operai_group=normalize_operai_group(item.operai_group),
        weekday_schedule_codes=_normalize_codes(item.weekday_schedule_codes or []),
        saturday_schedule_codes=_normalize_codes(item.saturday_schedule_codes or []),
        saturday_week_ordinals=_normalize_week_ordinals(item.saturday_week_ordinals or []),
        weekday_expected_minutes=item.weekday_expected_minutes,
        saturday_expected_minutes=item.saturday_expected_minutes,
        missing_tolerance_minutes=item.missing_tolerance_minutes,
        mpe_review_threshold_minutes=item.mpe_review_threshold_minutes,
        allowed_absence_causes=_normalize_absence_causes(item.allowed_absence_causes or []),
        is_active=item.is_active,
    )
