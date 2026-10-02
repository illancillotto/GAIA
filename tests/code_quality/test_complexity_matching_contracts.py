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
