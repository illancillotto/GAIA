"""Honor the explicitly assigned INAZ first/third Saturday calendar without HR grouping."""


def is_inaz_monthly_calendar(template):
    return getattr(template, "code", None) == "OPE0714_1E3SAB"


def assigned_saturday_minutes(rule, matched_rules):
    monthly = any(
        item.weekday == 5
        and item.recurrence_kind in {"first_weekday_of_month", "nth_weekday_of_month"}
        for item in matched_rules
    )
    if monthly and rule.rule.code == "OPERAI_LEGACY_FALLBACK":
        return 390
    return rule.rule.saturday_expected_minutes
