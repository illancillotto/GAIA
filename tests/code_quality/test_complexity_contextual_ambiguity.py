"""R146: an identity tie is resolved only by the existing contextual source proof."""

import subprocess
from collections import defaultdict

import pytest
import test_complexity_contracts as contracts

tool = contracts.tool

PATH = "frontend/src/Screen.tsx"

BASE = (
    "export function Screen(props) {\n"
    "  return (\n"
    "    <section>\n"
    "      <button\n"
    "        disabled={\n"
    "          props.a ||\n"
    "          props.b ||\n"
    "          props.c ||\n"
    "          props.d\n"
    "        }\n"
    "      >Act</button>\n"
    '      <input name="selection"\n'
    "        onChange={() =>\n"
    "          choose(value ? value : null)\n"
    "        }\n"
    '        className="selection-control"\n'
    "      />\n"
    '      <button title="first-close"\n'
    "        onClick={() => close()\n"
    "        }\n"
    "      >Close</button>\n"
    '      <aside title="other-close">\n'
    "        <button onClick={() => close()}>Other close</button>\n"
    "      </aside>\n"
    "    </section>\n"
    "  );\n"
    "}\n"
)
MULTI = (
    "        disabled={\n"
    "          props.a ||\n"
    "          props.b ||\n"
    "          props.c ||\n"
    "          props.d\n"
    "        }\n"
)
SINGLE = "        disabled={props.a || props.b || props.c || props.d}\n"
SHIFT = "".join(f"const SHIFT_{number} = {number};\n" for number in range(8))
# Stale baseline: lines shifted and the handler body changed, as on main.
MAIN = SHIFT + BASE.replace("choose(value ? value : null)", "choose(value)")
# The slice collapses the expression above: the nearest-span guess becomes a tie.
SLICE = MAIN.replace(MULTI, SINGLE)
TIED = 16
COPY = "      <input onChange={() =>\n          choose(value)\n        } />\n"
ORIGINAL_COPY = (
    "      <input onChange={() =>\n          choose(value ? value : null)\n        } />\n"
)
END = "    </section>\n"
REGRESSION = "choose(value && other ? value : null)"

TWINS = (
    "export function Twins() {\n"
    "  return (\n"
    "    <section>\n"
    '      <input name="first"\n'
    "        onChange={() =>\n"
    "          choose(value)\n"
    "        }\n"
    '        className="first-control"\n'
    "      />\n"
    '      <input name="second"\n'
    "        onChange={() =>\n"
    "          choose(value)\n"
    "        }\n"
    '        className="second-control"\n'
    "      />\n"
    "    </section>\n"
    "  );\n"
    "}\n"
)
SECOND = '        onChange={() =>\n          choose(value)\n        }\n        className="second'

# The fenced slot sits at equal distance from two identical close() twins.
BETWEEN = (
    "export function Between() {\n"
    "  return (\n"
    "    <section>\n"
    "      <button onClick={() => close()}>A</button>\n"
    '      <input name="selection"\n'
    "        onChange={() =>\n"
    "          choose(value ? value : null)\n"
    "        }\n"
    "      /><button onClick={() => close()}>B</button>\n"
    "    </section>\n"
    "  );\n"
    "}\n"
)


def git(root, *arguments):
    return subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repository(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    monkeypatch.setattr(tool, "load_exceptions", lambda: [])
    source = tmp_path / PATH
    source.parent.mkdir(parents=True)
    git(tmp_path, "init", "-q")

    def commit(original):
        source.write_text(original)
        git(tmp_path, "add", PATH)
        git(
            tmp_path,
            "-c",
            "user.name=F",
            "-c",
            "user.email=f@example.invalid",
            "commit",
            "-qm",
            "b",
        )
        baseline = tool.baseline_from_report(tool.scan([PATH]))

        def run(text, *, added=False, source_commit=None):
            source.write_text(text)
            report = tool.scan([PATH])
            lines = tool.added_lines_since(baseline["source_commit"], [PATH]) if added else None
            if source_commit is not None:
                baseline["source_commit"] = source_commit
            code, findings = tool.compare(report, baseline, added_lines=lines)
            return code, findings, report

        return baseline, run

    return commit


@pytest.fixture
def case(repository):
    return repository(BASE)


def handler(report, start=None):
    return next(
        call
        for call in report["callables"]
        if call["name"] == "Program<anonymous>"
        and call["end_line"] > call["line"]
        and start in (None, call["line"])
    )


def first_pass(tool, current, report, baseline, added=None):
    base = tool.call_index(baseline)
    fingerprints = defaultdict(list)
    for identity, call in base.items():
        fingerprints[call["fingerprint"]].append((identity, call))
    return tool.resolve_baseline_callable(current, report, base, fingerprints, added)


def tied(tool, report, baseline, start=TIED):
    current = handler(report, start)
    _, ambiguity, _ = first_pass(tool, current, report, baseline)
    assert ambiguity["reason"] == "ambiguous_identity"
    return current


def context(added=None):
    return {"source_paths": None, "added_lines": added, "snapshots": {}, "owners": set()}


def contextual_proof(tool, current, report, baseline):
    path = current["path"]
    old_calls = [call for call in baseline["callables"] if call["path"] == path]
    new_calls = [call for call in report["callables"] if call["path"] == path]
    mapping, before, after = tool.validated_source_mapping(
        path, baseline["source_commit"], tool.ROOT / path, old_calls, new_calls
    )
    return tool.contextual_source_owner(current, mapping, before, after, old_calls, new_calls)


def baseline_call(baseline, line):
    return next(call for call in baseline["callables"] if call["line"] == line)


def rightful(baseline):
    return baseline_call(baseline, 13)


def summary(findings):
    return sorted(
        (f["reason"], f.get("symbol"), f.get("metric"), f.get("baseline"), f.get("value"))
        for f in findings
    )


def test_stale_main_state_already_resolves_through_the_contextual_correction(tool, case):
    baseline, run = case
    code, findings, report = run(MAIN)
    guessed, ambiguity, _ = first_pass(tool, handler(report), report, baseline)
    assert ambiguity is None and guessed["line"] == 23
    assert (code, findings) == (0, [])


def test_tie_is_resolved_to_the_contextually_proven_owner(tool, case):
    baseline, run = case
    code, findings, report = run(SLICE)
    current = tied(tool, report, baseline)
    _, ambiguity, _ = first_pass(tool, current, report, baseline)
    assert ambiguity["candidates"] == 3
    assert tool.source_provenance_owner(current, report, baseline) is None
    resolution = (None, ambiguity, False)
    assert tool.resolve_source_ambiguity(current, report, baseline, resolution, context()) == (
        rightful(baseline),
        None,
        False,
    )
    assert (code, findings) == (0, [])


def test_tie_resolution_does_not_depend_on_report_order(tool, case):
    baseline, run = case
    _, _, report = run(SLICE)
    reordered = {**report, "callables": list(reversed(report["callables"]))}
    assert tool.compare(reordered, baseline) == (0, [])


def test_real_regression_in_the_tied_callable_is_measured_against_the_rightful_owner(tool, case):
    baseline, run = case
    code, findings, report = run(SLICE.replace("choose(value)", REGRESSION))
    tied(tool, report, baseline)
    assert code == 1
    assert summary(findings) == [
        ("legacy_metric_regression", "Program<anonymous>", "cognitive", 1, 2),
        ("legacy_metric_regression", "Program<anonymous>", "cyclomatic", 2, 3),
        ("legacy_metric_regression", "Screen", "cognitive", 4, 5),
        ("legacy_metric_regression", "Screen", "cyclomatic", 5, 6),
    ]


@pytest.mark.parametrize(
    "damage",
    [
        ('className="selection-control"', 'className="changed"'),
        ('name="selection"', 'name="changed"'),
    ],
)
def test_broken_exterior_fence_keeps_the_ambiguity(tool, case, damage):
    baseline, run = case
    code, findings, report = run(SLICE.replace(*damage))
    current = tied(tool, report, baseline)
    assert contextual_proof(tool, current, report, baseline) is None
    assert code == 2
    assert findings[0]["reason"] == "ambiguous_identity"


def test_added_copy_inside_the_fenced_slot_keeps_the_ambiguity(tool, case):
    baseline, run = case
    inside = SLICE.replace(
        '        className="selection-control"\n',
        '        onBlur={() =>\n          choose(value)\n        }\n        className="selection-control"\n',
    )
    code, findings, report = run(inside)
    current = tied(tool, report, baseline)
    assert contextual_proof(tool, current, report, baseline) is None
    assert code == 2
    assert findings[0]["reason"] == "ambiguous_identity"


@pytest.mark.parametrize("added", [False, True])
def test_duplicate_slot_copy_outside_the_fence_still_fails_the_ratchet(tool, case, added):
    # The original slot is proven. The copy has no source slot: it keeps the
    # pre-existing nearest-span guess (a close() handler) and exceeds its loc.
    # The proven owner's budget is never lent to the copy a second time.
    baseline, run = case
    code, findings, report = run(SLICE.replace(END, COPY + END), added=added)
    current = tied(tool, report, baseline)
    resolution = (None, first_pass(tool, current, report, baseline)[1], False)
    owner, _, _ = tool.resolve_source_ambiguity(current, report, baseline, resolution, context())
    assert owner is rightful(baseline)
    assert code == 1
    assert summary(findings) == [("legacy_metric_regression", "Program<anonymous>", "loc", 1, 2)]


@pytest.mark.parametrize("commit", ["", "not-a-commit", "0" * 40])
def test_unverifiable_source_commit_keeps_the_ambiguity(tool, case, commit):
    baseline, run = case
    code, findings, report = run(SLICE, source_commit=commit)
    current = tied(tool, report, baseline)
    assert tool.contextual_ambiguity_owner(current, report, baseline, context()) is None
    assert code == 2
    assert findings[0]["reason"] == "ambiguous_identity"


def test_wholly_added_callable_never_gains_a_contextual_owner(tool, case):
    baseline, run = case
    _, _, report = run(SLICE)
    current = tied(tool, report, baseline)
    owner = tool.contextual_ambiguity_owner(current, report, baseline, context())
    assert owner is rightful(baseline)
    added = {PATH: set(range(current["line"], current["end_line"] + 1))}
    assert tool.contextual_ambiguity_owner(current, report, baseline, context(added)) is None


def test_owner_claimed_by_a_sibling_guess_is_not_lent(tool, case):
    baseline, run = case
    # Same line count, so the tie stays; the sibling guesses the rightful owner.
    sibling = "[() =>\n  1];\n"
    code, findings, report = run(SLICE.replace("const SHIFT_4 = 4;\nconst SHIFT_5 = 5;\n", sibling))
    assert first_pass(tool, handler(report, start=5), report, baseline)[0] is rightful(baseline)
    current = tied(tool, report, baseline)
    assert contextual_proof(tool, current, report, baseline) is rightful(baseline)
    assert tool.contextual_ambiguity_owner(current, report, baseline, context()) is None
    assert code == 2
    assert findings[0]["reason"] == "ambiguous_identity"


def test_added_renderer_guessing_the_owner_keeps_the_ambiguity(tool, case):
    baseline, run = case
    renderer = "const renderX = () => <i onClick={() => {\n  choose(value);\n}} />;\n"
    shifted = "const SHIFT_0 = 0;\nconst SHIFT_1 = 1;\nconst SHIFT_2 = 2;\n"
    code, findings, report = run(SLICE.replace(shifted, renderer), added=True)
    added = tool.added_lines_since(baseline["source_commit"], [PATH])
    guessed, _, _ = first_pass(tool, handler(report, start=1), report, baseline, added)
    assert guessed is rightful(baseline)
    current = tied(tool, report, baseline)
    assert contextual_proof(tool, current, report, baseline) is rightful(baseline)
    assert code == 2
    assert findings[0]["reason"] == "ambiguous_identity"


def test_owner_already_lent_in_this_comparison_is_not_lent_twice(tool, case):
    baseline, run = case
    _, _, report = run(SLICE)
    current = tied(tool, report, baseline)
    local = context()
    local["owners"].add(tool.callable_key(rightful(baseline)))
    assert tool.contextual_ambiguity_owner(current, report, baseline, local) is None
    fresh = context()
    assert tool.contextual_ambiguity_owner(current, report, baseline, fresh) is rightful(baseline)
    assert tool.contextual_ambiguity_owner(current, report, baseline, fresh) is None


def test_owner_reserved_by_its_surviving_fingerprint_is_never_lent(tool, repository):
    # The original handler text survives elsewhere, so its fingerprint reserves
    # the fenced owner; the tie between the close() twins stays a refusal.
    baseline, run = repository(BETWEEN)
    changed = BETWEEN.replace("choose(value ? value : null)", "choose(value)")
    code, findings, report = run(changed.replace(END, ORIGINAL_COPY + END))
    current = tied(tool, report, baseline, start=6)
    assert contextual_proof(tool, current, report, baseline) is baseline_call(baseline, 6)
    assert tool.contextual_ambiguity_owner(current, report, baseline, context()) is None
    assert code == 2
    assert findings[0]["reason"] == "ambiguous_identity"


def test_twin_tie_is_resolved_only_by_its_fence(tool, repository):
    baseline, run = repository(TWINS)
    spread = SECOND.replace("choose(value)", "choose(\n            value)")
    text = "".join(f"const S{n} = {n};\n" for n in range(3)) + TWINS.replace(SECOND, spread)
    code, findings, report = run(text)
    current = tied(tool, report, baseline, start=8)
    assert "fingerprint" in first_pass(tool, current, report, baseline)[1]
    first = baseline_call(baseline, 5)
    assert tool.contextual_ambiguity_owner(current, report, baseline, context()) is first
    assert code == 1
    assert summary(findings) == [
        ("legacy_metric_regression", "Program<anonymous>", "loc", 2, 3),
        ("legacy_metric_regression", "Twins", "loc", 18, 19),
    ]
    code, findings, _ = run(text.replace('className="first-control"', 'className="moved"'))
    assert code == 2
    assert findings[0]["reason"] == "ambiguous_identity"


def test_ambiguous_fingerprint_refusal_is_not_widened(tool, case):
    baseline, run = case
    _, _, report = run(SLICE)
    current = handler(report)
    refusal = {"reason": "ambiguous_fingerprint", "path": PATH, "symbol": current["name"]}
    resolution = (None, refusal, False)
    assert (
        tool.resolve_source_ambiguity(current, report, baseline, resolution, context())
        == resolution
    )
