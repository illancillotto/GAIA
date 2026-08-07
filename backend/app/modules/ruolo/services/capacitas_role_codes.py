from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from app.modules.ruolo.enums import CodiceTributo


CAPACITAS_ROLE_KIND_ORDINARY = "ordinary_role"
CAPACITAS_ROLE_KIND_AGGREGATED_NOTICE = "aggregated_notice"
CAPACITAS_ROLE_KIND_REGULATION_VIOLATION = "regulation_violation"
CAPACITAS_ROLE_KIND_AGENZIA_ENTRATE = "agenzia_entrate"
CAPACITAS_ROLE_KIND_TENANT_TAX_ADVANCE = "tenant_tax_advance"
CAPACITAS_ROLE_KIND_UNCLASSIFIED = "unclassified"

CAPACITAS_ORDINARY_ROLE_YEAR_MIN = 2000
CAPACITAS_ORDINARY_ROLE_YEAR_MAX = 2099

AGGREGATED_NOTICE_ISSUE_YEARS = {
    "2525": 2025,
    "2626": 2026,
}

SPECIAL_NOTICE_LABELS = {
    CAPACITAS_ROLE_KIND_AGGREGATED_NOTICE: "Avviso accorpato",
    CAPACITAS_ROLE_KIND_REGULATION_VIOLATION: "Violazione di regolamento",
    CAPACITAS_ROLE_KIND_AGENZIA_ENTRATE: "Agenzia delle Entrate",
    CAPACITAS_ROLE_KIND_TENANT_TAX_ADVANCE: "Anticipo tributi conduttore",
}


@dataclass(frozen=True)
class CapacitasRoleCodeClassification:
    raw_code: str
    code: str
    kind: str
    label: str
    is_ordinary_role: bool
    is_known_special: bool
    ordinary_year: int | None = None
    issue_year: int | None = None
    reference_year: int | None = None
    default_tribute_code: str | None = None
    allocation_mode: str | None = None
    requires_partitario_reconstruction: bool = False
    requires_manual_allocation: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CapacitasRoleCodeSplit:
    ordinary_years: list[int]
    special_codes: list[str]
    unclassified_codes: list[str]
    classifications: list[CapacitasRoleCodeClassification]


def normalize_capacitas_role_code(raw_code: object) -> str:
    return str(raw_code or "").strip()


def classify_capacitas_role_code(raw_code: object) -> CapacitasRoleCodeClassification:
    code = normalize_capacitas_role_code(raw_code)
    if code in AGGREGATED_NOTICE_ISSUE_YEARS:
        issue_year = AGGREGATED_NOTICE_ISSUE_YEARS[code]
        return CapacitasRoleCodeClassification(
            raw_code=code,
            code=code,
            kind=CAPACITAS_ROLE_KIND_AGGREGATED_NOTICE,
            label=SPECIAL_NOTICE_LABELS[CAPACITAS_ROLE_KIND_AGGREGATED_NOTICE],
            is_ordinary_role=False,
            is_known_special=True,
            issue_year=issue_year,
            allocation_mode="manual",
            requires_partitario_reconstruction=True,
            requires_manual_allocation=True,
        )
    if code == "7700":
        return CapacitasRoleCodeClassification(
            raw_code=code,
            code=code,
            kind=CAPACITAS_ROLE_KIND_REGULATION_VIOLATION,
            label=SPECIAL_NOTICE_LABELS[CAPACITAS_ROLE_KIND_REGULATION_VIOLATION],
            is_ordinary_role=False,
            is_known_special=True,
        )
    if code == "7890":
        return CapacitasRoleCodeClassification(
            raw_code=code,
            code=code,
            kind=CAPACITAS_ROLE_KIND_AGENZIA_ENTRATE,
            label=SPECIAL_NOTICE_LABELS[CAPACITAS_ROLE_KIND_AGENZIA_ENTRATE],
            is_ordinary_role=False,
            is_known_special=True,
        )
    if len(code) == 4 and code.startswith("99") and code[2:].isdigit():
        reference_year = 2000 + int(code[2:])
        return CapacitasRoleCodeClassification(
            raw_code=code,
            code=code,
            kind=CAPACITAS_ROLE_KIND_TENANT_TAX_ADVANCE,
            label=SPECIAL_NOTICE_LABELS[CAPACITAS_ROLE_KIND_TENANT_TAX_ADVANCE],
            is_ordinary_role=False,
            is_known_special=True,
            issue_year=reference_year,
            reference_year=reference_year,
            default_tribute_code=CodiceTributo.IRRIGAZIONE.value,
            allocation_mode="manual",
            requires_partitario_reconstruction=True,
            requires_manual_allocation=True,
        )
    if code.isdigit():
        year = int(code)
        if CAPACITAS_ORDINARY_ROLE_YEAR_MIN <= year <= CAPACITAS_ORDINARY_ROLE_YEAR_MAX:
            return CapacitasRoleCodeClassification(
                raw_code=code,
                code=code,
                kind=CAPACITAS_ROLE_KIND_ORDINARY,
                label="Ruolo ordinario",
                is_ordinary_role=True,
                is_known_special=False,
                ordinary_year=year,
            )
    return CapacitasRoleCodeClassification(
        raw_code=code,
        code=code,
        kind=CAPACITAS_ROLE_KIND_UNCLASSIFIED,
        label="Codice Capacitas non classificato",
        is_ordinary_role=False,
        is_known_special=False,
    )


def split_capacitas_role_codes(raw_codes: Iterable[object]) -> CapacitasRoleCodeSplit:
    classifications = [classify_capacitas_role_code(raw_code) for raw_code in raw_codes]
    ordinary_years = sorted(
        {
            classification.ordinary_year
            for classification in classifications
            if classification.ordinary_year is not None
        }
    )
    special_codes = sort_capacitas_role_codes(
        classification.code for classification in classifications if classification.is_known_special
    )
    unclassified_codes = sort_capacitas_role_codes(
        classification.code
        for classification in classifications
        if classification.kind == CAPACITAS_ROLE_KIND_UNCLASSIFIED and classification.code
    )
    return CapacitasRoleCodeSplit(
        ordinary_years=ordinary_years,
        special_codes=special_codes,
        unclassified_codes=unclassified_codes,
        classifications=classifications,
    )


def sort_capacitas_role_codes(raw_codes: Iterable[object]) -> list[str]:
    codes = {normalize_capacitas_role_code(raw_code) for raw_code in raw_codes}
    return sorted((code for code in codes if code), key=_capacitas_role_code_sort_key)


def _capacitas_role_code_sort_key(code: str) -> tuple[int, int | str]:
    return (0, int(code)) if code.isdigit() else (1, code)
