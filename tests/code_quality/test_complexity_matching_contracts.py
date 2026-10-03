import copy
from collections import defaultdict

import pytest
import test_complexity_contracts as contracts

tool = contracts.tool


def callable_metric(path, name, fingerprint, start, end=None):
    return {
        "path": path,
        "name": name,
        "fingerprint": fingerprint,
        "line": start,
        "end_line": end or start + 1,
        "cyclomatic": 1,
        "cognitive": 0,
        "loc": 2,
        "nesting": 0,
        "params": 1,
        "violations": [],
    }


def resolve(tool, current, old, current_calls=None, added=None):
    baseline = tool.call_index({"callables": old})
    by_fingerprint = defaultdict(list)
    for key, call in baseline.items():
        by_fingerprint[call["fingerprint"]].append((key, call))
    return tool.resolve_baseline_callable(
        current, {"callables": current_calls or [current]}, baseline, by_fingerprint, added
    )


def test_duplicate_identity_growth_uses_nearest_unique_span(tool):
    old = [callable_metric("a.py", "same", "fp", start) for start in [1, 30]]
    current = callable_metric("a.py", "same", "fp", 3)
    calls = [current, *copy.deepcopy(old)]
    assert resolve(tool, current, old, calls) == (old[0], None, False)


@pytest.mark.parametrize("added_start", [5, 10])
def test_added_duplicate_does_not_make_unchanged_siblings_ambiguous(tool, added_start):
    old = [callable_metric("a.py", "same", "fp", start) for start in [10, 20]]
    added_call = callable_metric("a.py", "same", "fp", added_start)
    survivor = callable_metric("a.py", "same", "fp", 15)
    other_survivor = callable_metric("a.py", "same", "fp", 25)
    calls = [added_call, survivor, other_survivor]
    added = {"a.py": {added_start, added_start + 1}}

    assert resolve(tool, survivor, old, calls, added) == (None, None, True)
    assert resolve(tool, added_call, old, calls, added) == (None, None, False)


@pytest.mark.parametrize("growth", [False, True])
def test_wholly_rewritten_duplicate_keeps_exact_legacy_checks_without_addition_proof(tool, growth):
    old = [callable_metric("a.py", "same", "fp", start) for start in [10, 20]]
    current = callable_metric("a.py", "same", "fp", 10)
    sibling = callable_metric("a.py", "same", "fp", 30)
    calls = [current, sibling]
    if growth:
        current["cognitive"] = 1
        sibling["loc"] = 3
        calls.append(callable_metric("a.py", "same", "fp", 40))
    assert resolve(tool, current, old, calls, {"a.py": {10, 11}}) == (old[0], None, False)


@pytest.mark.parametrize("change", ["missing_survivor", "regression", "partial_addition"])
def test_added_duplicate_cannot_hide_changed_or_missing_legacy_ownership(tool, change):
    old = [callable_metric("a.py", "same", "fp", start) for start in [10, 20]]
    added_call = callable_metric("a.py", "same", "fp", 5)
    survivor = callable_metric("a.py", "same", "fp", 15)
    other_survivor = callable_metric("a.py", "same", "fp", 25)
    calls = [added_call, survivor, other_survivor]
    added = {"a.py": {5, 6}}
    if change == "missing_survivor":
        calls.remove(other_survivor)
        calls.append(callable_metric("a.py", "same", "fp", 35))
        added["a.py"].update({35, 36})
    elif change == "regression":
        survivor["cognitive"] = 1
    else:
        added["a.py"] = {5}

    picked, error, equivalent = resolve(tool, survivor, old, calls, added)
    assert picked is None and not equivalent
    assert error["reason"] == "ambiguous_identity"


@pytest.mark.parametrize("added_start", [5, 10])
def test_added_duplicate_still_fails_for_new_error_level_violation(tool, added_start):
    old = [callable_metric("a.py", "same", "fp", start) for start in [10, 20]]
    added_call = callable_metric("a.py", "same", "fp", added_start)
    added_call["cyclomatic"] = 15
    added_call["violations"] = [
        {"metric": "cyclomatic", "severity": "error", "value": 15, "excepted": False}
    ]
    survivors = [callable_metric("a.py", "same", "fp", start) for start in [15, 25]]
    report = {
        "parse_errors": [],
        "exception_errors": [],
        "callables": [added_call, *survivors],
        "files": {},
    }
    baseline = {
        "schema_version": tool.SCHEMA_VERSION,
        "engines": {},
        "scope": {},
        "files": {},
        "callables": old,
    }
    code, findings = tool.compare(
        report, baseline, added_lines={"a.py": {added_start, added_start + 1}}
    )
    assert code == 1
    assert findings[0]["reason"] == "new_callable_violation"


@pytest.mark.parametrize("wholly_added", [False, True])
def test_duplicate_identity_growth_never_guesses_overlapping_spans(tool, wholly_added):
    old = [callable_metric("a.py", "same", "fp", start) for start in [1, 10]]
    current = callable_metric("a.py", "same", "fp", 1, 20)
    calls = [current, *copy.deepcopy(old)]
    added = {"a.py": set(range(1, 21))} if wholly_added else None
    picked, error, equivalent = resolve(tool, current, old, calls, added)
    assert picked is None and not equivalent
    assert (error is None) == wholly_added
    if error:
        assert error["reason"] == "ambiguous_identity"


def test_changed_duplicate_identity_uses_nearest_unreserved_span(tool):
    old = [
        callable_metric("a.py", "same", fingerprint, start)
        for fingerprint, start in [("first", 1), ("second", 30)]
    ]
    current = callable_metric("a.py", "same", "changed", 3)
    assert resolve(tool, current, old) == (old[0], None, False)


def test_same_path_renamed_symbol_keeps_unique_fingerprint_owner(tool):
    old = [callable_metric("a.py", "previous", "fp", 1)]
    current = callable_metric("a.py", "renamed", "fp", 3)
    assert resolve(tool, current, old) == (old[0], None, False)


def test_renamed_duplicate_group_with_same_metrics_is_equivalent(tool):
    old = [callable_metric("a.py", "previous", "fp", start) for start in [1, 10]]
    calls = [callable_metric("a.py", "renamed", "fp", start) for start in [3, 15]]
    assert resolve(tool, calls[0], old, calls) == (None, None, True)


def test_renamed_duplicate_group_growth_uses_nearest_span(tool):
    old = [callable_metric("a.py", "previous", "fp", start) for start in [1, 30]]
    current = callable_metric("a.py", "renamed", "fp", 3)
    assert resolve(tool, current, old) == (old[0], None, False)


@pytest.mark.parametrize("wholly_added", [False, True])
def test_renamed_duplicate_group_growth_rejects_ambiguous_ownership(tool, wholly_added):
    old = [callable_metric("a.py", "previous", "fp", start) for start in [1, 10]]
    current = callable_metric("a.py", "renamed", "fp", 1, 20)
    added = {"a.py": set(range(1, 21))} if wholly_added else None
    picked, error, equivalent = resolve(tool, current, old, added=added)
    assert picked is None and not equivalent
    assert (error is None) == wholly_added
    if error:
        assert error["reason"] == "ambiguous_fingerprint"


def test_moved_duplicate_group_with_same_metrics_is_equivalent(tool):
    old = [
        callable_metric(path, "same", "fp", start) for path, start in [("a.py", 1), ("b.py", 10)]
    ]
    calls = [callable_metric("new.py", "same", "fp", start) for start in [3, 15]]
    assert resolve(tool, calls[0], old, calls) == (None, None, True)


def test_moved_duplicate_group_uses_nearest_unique_span(tool):
    old = [
        callable_metric(path, "same", "fp", start) for path, start in [("a.py", 1), ("b.py", 30)]
    ]
    current = callable_metric("new.py", "same", "fp", 3)
    assert resolve(tool, current, old) == (old[0], None, False)


@pytest.mark.parametrize("wholly_added", [False, True])
def test_moved_duplicate_group_never_guesses_overlapping_spans(tool, wholly_added):
    old = [
        callable_metric(path, "same", "fp", start) for path, start in [("a.py", 1), ("b.py", 10)]
    ]
    current = callable_metric("new.py", "same", "fp", 1, 20)
    added = {"new.py": set(range(1, 21))} if wholly_added else None
    picked, error, equivalent = resolve(tool, current, old, added=added)
    assert picked is None and not equivalent
    assert (error is None) == wholly_added
    if error:
        assert error["reason"] == "ambiguous_fingerprint"
