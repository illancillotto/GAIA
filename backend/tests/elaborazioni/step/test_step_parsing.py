from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.modules.elaborazioni.step import parsing


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.405,12", Decimal("1405.12")),
        ("258,27", Decimal("258.27")),
        ("-217.4", Decimal("-217.40")),
        ("258.27", Decimal("258.27")),
        (1869.26, Decimal("1869.26")),
        (0, Decimal("0.00")),
        ("43", Decimal("43.00")),
        ("1.405", None),
        ("'-217.4", None),
        ("abc", None),
        ("", None),
        (None, None),
    ],
)
def test_amount_is_strict_and_never_coerces_missing_to_zero(raw, expected) -> None:
    assert parsing.amount(raw) == expected


def test_dates_integers_and_years() -> None:
    assert parsing.parse_date("16/11/2024") == date(2024, 11, 16)
    assert parsing.parse_date("2024-11-16") == date(2024, 11, 16)
    assert parsing.parse_date("29/06/204") is None
    assert parsing.parse_date(None) is None
    assert parsing.integer("12") == 12
    assert parsing.integer(3) == 3
    assert parsing.integer("x") is None
    assert parsing.integer(None) is None
    assert parsing.year("2019") == 2019
    assert parsing.year("2018-2019") is None
    assert parsing.year(None) is None
    assert parsing.text("  ") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Avv. N. 020190006018040 Not. 31/01/2021 ", ("020190006018040", "020190006018040")),
        ("Avv. n. 120180009615120 Not. 30/10/2024", ("120180009615120", "120180009615120")),
        ("Bollettazione n. 020230020619550 del 2023", ("020230020619550", "020230020619550")),
        ("Bollettazione. n. 020217800173725", ("020217800173725", "020217800173725")),
        ("Avv. N. 20210004064870 Not. 15/11/2022", ("20210004064870", None)),
        ("0120180003259580", ("0120180003259580", None)),
        (
            "Quota scarichi anno 2023 - Avv. PG13319 not. 28/11/2025",
            ("Quota scarichi anno 2023 - Avv. PG13319 not. 28/11/2025", None),
        ),
        ("", (None, None)),
    ],
)
def test_avviso_reference_recognizes_only_full_cnc_codes(raw, expected) -> None:
    assert parsing.avviso_reference(raw) == expected


def test_fingerprint_is_order_independent() -> None:
    assert parsing.fingerprint({"a": 1, "b": 2}) == parsing.fingerprint({"b": 2, "a": 1})
