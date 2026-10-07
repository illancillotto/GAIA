"""Ordinary OPE days for attested Impianti technicians use Saturdays 1 and 3."""

from dataclasses import replace

from app.modules.presenze.services.personnel_profiles import technician_profile


def resolve_technician_operai_rule(record):
    # Imported here because the ordinary resolver delegates this profile-specific policy.
    from app.modules.presenze.services.operai_rules import (
        SCHEDULE_VARIANTS,
        _resolved_schedule_rule,
        default_operai_rule_configs,
        resolve_operai_schedule_code,
        saturday_ordinal_in_month,
    )

    if technician_profile(record) is None:
        return None
    code = resolve_operai_schedule_code(record)
    # Confirmed for Impianti technicians: OPESAC has the ordinary 6h30 Saturday.
    code = {"OPESAC": "OPESAB"}.get(code, code)
    base = default_operai_rule_configs()[0]
    if (
        SCHEDULE_VARIANTS.get(code, code)
        not in base.weekday_schedule_codes + base.saturday_schedule_codes
    ):
        return None
    rule = replace(
        base,
        code="OPERAI_IMPIANTI_TECNICO_TURNISTA_1E3SAB",
        label="Tecnico/Turnista Impianti: OPE, sabati 1 e 3",
        operai_group="tecnico_turnista",
    )
    resolved = _resolved_schedule_rule(rule, code, record.work_date)
    if record.work_date.weekday() != 5:
        return resolved
    scheduled = saturday_ordinal_in_month(record.work_date) in (1, 3)
    return replace(
        resolved,
        expected_minutes=resolved.expected_minutes if scheduled else 0,
        saturday_is_scheduled=scheduled,
    )


def individual_saturday_eligible(record, template):
    if technician_profile(record) is not None:
        return False
    if record.work_date.weekday() != 5 or template is None or not template.is_active:
        return False
    if template.valid_from and record.work_date < template.valid_from:
        return False
    return not template.valid_to or record.work_date <= template.valid_to
