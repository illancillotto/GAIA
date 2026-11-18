from __future__ import annotations

from itertools import permutations

import pytest

from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.search.service import _score, search_operational


def test_search_without_enabled_domains_returns_no_results():
    user = ApplicationUser(
        role=ApplicationUserRole.ADMIN.value,
        module_utenze=False,
        module_ruolo=False,
        module_catasto=False,
    )

    response = search_operational(None, user, "  Rossi   Mario  ")

    assert response.model_dump() == {
        "query": "Rossi Mario",
        "items": [],
        "total": 0,
        "modules": [],
    }


@pytest.mark.parametrize(
    ("query", "values", "expected"),
    [
        ("rossi", [], 40),
        ("rossi", [None, "", " \t\n"], 40),
        ("rossi", ["verdi"], 40),
        ("RoSsI", [" \tROSSI\n"], 100),
        ("rossi", ["ROSSI Mario"], 86),
        ("rossi", ["Mario Rossi"], 68),
        ("rossi mario", ["Mario Rossi"], 64),
        ("rossi mario", ["Rossi · Mario"], 64),
        ("rossi mario", ["Rossi Luigi"], 40),
        ("rossi mario", ["Mario Verdi"], 40),
        ("mario rossi", ["rossi mario bianchi"], 64),
        ("mario rossi", ["prefix mario rossi suffix"], 68),
        ("mario rossi", ["mario rossi suffix"], 86),
        ("mario rossi", ["mario rossi"], 100),
        ("rossi\t mario", ["Mario Rossi"], 64),
        ("rossi rossi", ["Rossi"], 64),
        (" rossi ", ["rossi"], 64),
        ("", [], 40),
        ("", [None, "  "], 40),
        ("", ["Rossi"], 86),
        ("  ", ["Rossi"], 64),
        ("È", [" è "], 100),
        ("STRASSE", ["Straße"], 40),
        ("İ", ["i\u0307"], 100),
        ("rossi mario", ["rossi", "mario"], 40),
    ],
)
def test_score_preserves_normalization_and_match_precedence(query, values, expected):
    assert _score(query, values) == expected


@pytest.mark.parametrize("values", list(permutations([None, "verdi", "Mario Rossi", "rossi"])))
def test_score_selects_best_value_independently_of_order(values):
    assert _score("rossi", iter(values)) == 100


def test_score_consumes_all_values_after_exact_match():
    consumed = []

    def values():
        for value in ["rossi", None, "verdi", "rossi mario"]:
            consumed.append(value)
            yield value

    assert _score("ROSSI", values()) == 100
    assert consumed == ["rossi", None, "verdi", "rossi mario"]


def test_score_propagates_iteration_error_after_exact_match():
    error = RuntimeError("late iteration failure")

    def values():
        yield "rossi"
        raise error

    with pytest.raises(RuntimeError) as caught:
        _score("rossi", values())
    assert caught.value is error


def test_score_normalizes_query_before_accessing_values():
    events = []
    error = RuntimeError("query normalization failure")

    class Query(str):
        def lower(self):
            events.append("query.lower")
            raise error

    class Values:
        def __iter__(self):
            events.append("values.iter")
            return iter([])

    with pytest.raises(RuntimeError) as caught:
        _score(Query("rossi"), Values())
    assert caught.value is error
    assert events == ["query.lower"]


@pytest.mark.parametrize("method", ["strip", "lower"])
def test_score_propagates_value_error_after_exact_match(method):
    error = RuntimeError(f"value.{method} failure")

    class Value(str):
        def strip(self):
            if method == "strip":
                raise error
            return self

        def lower(self):
            raise error

    with pytest.raises(RuntimeError) as caught:
        _score("rossi", ["rossi", Value("verdi")])
    assert caught.value is error
