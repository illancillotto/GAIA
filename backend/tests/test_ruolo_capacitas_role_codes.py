from __future__ import annotations

import pytest

from app.modules.ruolo.services.capacitas_role_codes import (
    CAPACITAS_ROLE_ACCOUNTING_SCOPE_ORDINARY,
    CAPACITAS_ROLE_ACCOUNTING_SCOPE_OUT_OF_ORDINARY,
    CAPACITAS_ROLE_ACCOUNTING_SCOPE_UNCLASSIFIED,
    CAPACITAS_ROLE_KIND_AGENZIA_ENTRATE,
    CAPACITAS_ROLE_KIND_AGGREGATED_NOTICE,
    CAPACITAS_ROLE_KIND_ORDINARY,
    CAPACITAS_ROLE_KIND_REGULATION_VIOLATION,
    CAPACITAS_ROLE_KIND_TENANT_TAX_ADVANCE,
    CAPACITAS_ROLE_KIND_UNCLASSIFIED,
    CAPACITAS_ROLE_OPERATIONAL_POLICY_AUDIT_ONLY,
    CAPACITAS_ROLE_OPERATIONAL_POLICY_ORDINARY,
    classify_capacitas_role_code,
    normalize_capacitas_role_code,
    sort_capacitas_role_codes,
    split_capacitas_role_codes,
)


@pytest.mark.parametrize("raw_code", ["2025", 2026, " 2011 "])
def test_classify_capacitas_role_code_ordinary_years(raw_code: object) -> None:
    classification = classify_capacitas_role_code(raw_code)

    assert classification.kind == CAPACITAS_ROLE_KIND_ORDINARY
    assert classification.is_ordinary_role is True
    assert classification.is_known_special is False
    assert classification.ordinary_year == int(str(raw_code).strip())
    assert classification.issue_year is None
    assert classification.reference_year is None
    assert classification.default_tribute_code is None
    assert classification.accounting_scope == CAPACITAS_ROLE_ACCOUNTING_SCOPE_ORDINARY
    assert classification.operational_policy == CAPACITAS_ROLE_OPERATIONAL_POLICY_ORDINARY
    assert classification.impacts_ordinary_balance is True
    assert classification.requires_operator_review is False
    assert classification.requires_manual_audit is False
    assert classification.requires_partitario_reconstruction is False
    assert classification.requires_manual_allocation is False


@pytest.mark.parametrize(("raw_code", "issue_year"), [("2525", 2025), ("2626", 2026)])
def test_classify_capacitas_role_code_aggregated_notices(raw_code: str, issue_year: int) -> None:
    classification = classify_capacitas_role_code(raw_code)

    assert classification.kind == CAPACITAS_ROLE_KIND_AGGREGATED_NOTICE
    assert classification.is_ordinary_role is False
    assert classification.is_known_special is True
    assert classification.ordinary_year is None
    assert classification.issue_year == issue_year
    assert classification.reference_year is None
    assert classification.default_tribute_code is None
    assert classification.allocation_mode == CAPACITAS_ROLE_OPERATIONAL_POLICY_AUDIT_ONLY
    assert classification.accounting_scope == CAPACITAS_ROLE_ACCOUNTING_SCOPE_OUT_OF_ORDINARY
    assert classification.operational_policy == CAPACITAS_ROLE_OPERATIONAL_POLICY_AUDIT_ONLY
    assert classification.impacts_ordinary_balance is False
    assert classification.requires_operator_review is True
    assert classification.requires_manual_audit is True
    assert classification.requires_partitario_reconstruction is True
    assert classification.requires_manual_allocation is False
    assert classification.to_dict()["label"] == "Avviso accorpato"


@pytest.mark.parametrize(
    ("raw_code", "kind", "label"),
    [
        ("7700", CAPACITAS_ROLE_KIND_REGULATION_VIOLATION, "Violazione di regolamento"),
        ("7890", CAPACITAS_ROLE_KIND_AGENZIA_ENTRATE, "Agenzia delle Entrate"),
    ],
)
def test_classify_capacitas_role_code_special_non_annual_codes(
    raw_code: str,
    kind: str,
    label: str,
) -> None:
    classification = classify_capacitas_role_code(raw_code)

    assert classification.kind == kind
    assert classification.label == label
    assert classification.is_ordinary_role is False
    assert classification.is_known_special is True
    assert classification.ordinary_year is None
    assert classification.issue_year is None
    assert classification.reference_year is None
    assert classification.default_tribute_code is None
    assert classification.allocation_mode is None
    assert classification.accounting_scope == CAPACITAS_ROLE_ACCOUNTING_SCOPE_OUT_OF_ORDINARY
    assert classification.operational_policy == CAPACITAS_ROLE_OPERATIONAL_POLICY_AUDIT_ONLY
    assert classification.impacts_ordinary_balance is False
    assert classification.requires_operator_review is True
    assert classification.requires_manual_audit is True
    assert classification.requires_partitario_reconstruction is False
    assert classification.requires_manual_allocation is False


@pytest.mark.parametrize(
    ("raw_code", "reference_year"),
    [("9923", 2023), ("9924", 2024), ("9925", 2025), ("9926", 2026)],
)
def test_classify_capacitas_role_code_tenant_tax_advances(raw_code: str, reference_year: int) -> None:
    classification = classify_capacitas_role_code(raw_code)

    assert classification.kind == CAPACITAS_ROLE_KIND_TENANT_TAX_ADVANCE
    assert classification.label == "Anticipo tributi conduttore"
    assert classification.is_ordinary_role is False
    assert classification.is_known_special is True
    assert classification.ordinary_year is None
    assert classification.issue_year == reference_year
    assert classification.reference_year == reference_year
    assert classification.default_tribute_code == "0668"
    assert classification.allocation_mode == CAPACITAS_ROLE_OPERATIONAL_POLICY_AUDIT_ONLY
    assert classification.accounting_scope == CAPACITAS_ROLE_ACCOUNTING_SCOPE_OUT_OF_ORDINARY
    assert classification.operational_policy == CAPACITAS_ROLE_OPERATIONAL_POLICY_AUDIT_ONLY
    assert classification.impacts_ordinary_balance is False
    assert classification.requires_operator_review is True
    assert classification.requires_manual_audit is True
    assert classification.requires_partitario_reconstruction is True
    assert classification.requires_manual_allocation is False


@pytest.mark.parametrize("raw_code", ["", None, "2323", "2424", "2100", "ABCD"])
def test_classify_capacitas_role_code_unclassified_codes(raw_code: object) -> None:
    classification = classify_capacitas_role_code(raw_code)

    assert classification.kind == CAPACITAS_ROLE_KIND_UNCLASSIFIED
    assert classification.label == "Codice Capacitas non classificato"
    assert classification.is_ordinary_role is False
    assert classification.is_known_special is False
    assert classification.ordinary_year is None
    assert classification.issue_year is None
    assert classification.reference_year is None
    assert classification.accounting_scope == CAPACITAS_ROLE_ACCOUNTING_SCOPE_UNCLASSIFIED
    assert classification.operational_policy == CAPACITAS_ROLE_OPERATIONAL_POLICY_AUDIT_ONLY
    assert classification.impacts_ordinary_balance is False
    assert classification.requires_operator_review is True
    assert classification.requires_manual_audit is True


def test_normalize_sort_and_split_capacitas_role_codes() -> None:
    assert normalize_capacitas_role_code(None) == ""
    assert normalize_capacitas_role_code(" 9925 ") == "9925"
    assert sort_capacitas_role_codes(["9925", "2025", "", "7700", "ABCD", "2025"]) == [
        "2025",
        "7700",
        "9925",
        "ABCD",
    ]

    split = split_capacitas_role_codes(
        ["2025", "9925", "7700", "2424", "2024", "9925", ""]
    )

    assert split.ordinary_years == [2024, 2025]
    assert split.special_codes == ["7700", "9925"]
    assert split.unclassified_codes == ["2424"]
    assert [classification.code for classification in split.classifications] == [
        "2025",
        "9925",
        "7700",
        "2424",
        "2024",
        "9925",
        "",
    ]
