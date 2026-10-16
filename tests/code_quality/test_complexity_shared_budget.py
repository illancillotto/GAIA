"""R147: a baseline budget is lent once; a wholly added sharer is also checked as new."""

import subprocess

import pytest
import test_complexity_contracts as contracts

tool = contracts.tool


def git(root, *arguments):
    return subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def ratchet(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    monkeypatch.setattr(tool, "load_exceptions", lambda: [])
    git(tmp_path, "init", "-q")

    def run(name, old, new, *, source_commit=True, added=True, values=False):
        path = f"frontend/src/{name}" if not name.endswith(".py") else f"backend/app/{name}"
        source = tmp_path / path
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(old)
        git(tmp_path, "add", path)
        git(
            tmp_path,
            "-c",
            "user.name=F",
            "-c",
            "user.email=f@example.invalid",
            "commit",
            "-qm",
            name,
        )
        baseline = tool.baseline_from_report(tool.scan([path]))
        source.write_text(new)
        report = tool.scan([path])
        lines = tool.added_lines_since(baseline["source_commit"], [path]) if added else None
        if source_commit is not True:
            baseline["source_commit"] = source_commit
        code, findings = tool.compare(report, baseline, added_lines=lines)
        if values:
            return code, sorted((f["reason"], f.get("metric"), f["value"]) for f in findings)
        return code, {(f["reason"], f["symbol"], f.get("metric")) for f in findings}

    return run


def columns(*parts, shift=0):
    filler = "".join(f"const S{n} = {n};\n" for n in range(shift))
    return filler + "export const columns = [\n" + "".join(parts) + "];\n"


def ternary(count, var):
    return " ".join(f"r.{var}{n} ? {n} :" for n in range(count)) + " -1"


def fenced(body):
    return f"  // fence-sel\n  {{ k: 'x', render: (r) =>\n{body}  // fence-sel-end\n"


A_MULTI = "  { k: 'w', render: (r) =>\n    r.a ||\n    r.b ||\n    r.c ||\n    r.d },\n"
A_ONE = "  { k: 'w', render: (r) => r.a || r.b || r.c || r.d },\n"
SLOT = fenced("    r.v ? r.v :\n    null },\n")
TIED = fenced("    r.v\n    ?? 1 },\n")
CLOSE = "  { k: 'x', render: (r) => close() },\n"
OTHER_CLOSE = "  // other\n  { k: 'x', render: (r) => close() },\n"
HOT = "  { k: 'h', render: (r) =>\n    " + ternary(17, "h") + " },\n"
HOT_IMPROVED = "  { k: 'h', render: (r) =>\n    " + ternary(16, "h") + " },\n"
ADDED = "  { k: 'n', render: (r) =>\n    " + ternary(15, "n") + " && r.m },\n"
OLD = columns(A_MULTI, SLOT, CLOSE, OTHER_CLOSE, HOT)
NEW_CALLABLE = ("new_callable_violation", "render", "cyclomatic")


def test_added_callable_next_to_an_edited_hotspot_does_not_borrow_its_budget(ratchet):
    # ADV4b without a tie: the improved hotspot keeps its budget, the added
    # error-level callable guessed the same owner and is checked as new.
    new = columns(A_MULTI, SLOT, CLOSE, OTHER_CLOSE, HOT_IMPROVED, ADDED)
    assert ratchet("adv4b.tsx", OLD, new) == (1, {NEW_CALLABLE})


def test_the_proven_holder_is_not_checked_as_new(ratchet):
    # The improved hotspot is still above the error threshold; it holds the
    # budget by its first line, so only the added callable is reported, both
    # against the shared budget and as new.
    added = "  { k: 'n', render: (r) =>\n    " + ternary(19, "n") + " },\n"
    new = columns(A_MULTI, SLOT, CLOSE, OTHER_CLOSE, HOT_IMPROVED, added)
    assert ratchet("holder.tsx", OLD, new, values=True) == (
        1,
        [
            ("legacy_metric_regression", "cognitive", 19),
            ("legacy_metric_regression", "cyclomatic", 20),
            ("new_callable_violation", "cyclomatic", 20),
        ],
    )


@pytest.mark.parametrize("source_commit", ["", "0" * 40])
def test_shared_budget_needs_no_source_snapshot(ratchet, source_commit):
    new = columns(A_MULTI, SLOT, CLOSE, OTHER_CLOSE, HOT_IMPROVED, ADDED)
    assert ratchet("adv4b.tsx", OLD, new, source_commit=source_commit) == (1, {NEW_CALLABLE})


@pytest.mark.parametrize("shift", [4, 5, 7])
def test_added_callable_with_an_unrelated_tie_does_not_borrow(ratchet, shift):
    new = columns(A_ONE, TIED, CLOSE, OTHER_CLOSE, HOT_IMPROVED, ADDED, shift=shift)
    assert ratchet("adv4b_tie.tsx", OLD, new) == (1, {NEW_CALLABLE})


@pytest.mark.parametrize("shift", [3, 6, 8, 9])
def test_added_callable_with_an_unresolved_tie_never_passes(ratchet, shift):
    # Without contextual proof the tie is refused; once it is proven the
    # added callable must still be reported, never hidden.
    code, findings = ratchet(
        "adv4b_amb.tsx",
        OLD,
        columns(A_ONE, TIED, CLOSE, OTHER_CLOSE, HOT_IMPROVED, ADDED, shift=shift),
    )
    assert code == 2 or (code, NEW_CALLABLE in findings) == (1, True)


def test_without_added_lines_the_unique_holder_still_proves_the_owner(ratchet):
    # The improved hotspot's first line is the hotspot's own, so it holds the
    # budget even when no line is known to be added.
    new = columns(A_MULTI, SLOT, CLOSE, OTHER_CLOSE, HOT_IMPROVED, ADDED)
    assert ratchet("adv4b.tsx", OLD, new, added=False) == (1, {NEW_CALLABLE})


def test_without_added_lines_or_snapshot_the_guess_stands(ratchet):
    new = columns(A_MULTI, SLOT, CLOSE, OTHER_CLOSE, HOT_IMPROVED, ADDED)
    assert ratchet("adv4b.tsx", OLD, new, source_commit="", added=False) == (0, set())


BLOCK_HOT = "  { k: 'h', render: (r) => {\n    return " + ternary(17, "h") + ";\n  } },\n"


def test_added_callable_sharing_a_closing_line_does_not_borrow(ratchet):
    # The diff aligns the added callable's closing line with the hotspot's, so
    # it is not wholly added; the improved hotspot still holds the budget.
    improved = BLOCK_HOT.replace(ternary(17, "h"), ternary(16, "h"))
    added = "  { k: 'n', render: (r) => {\n    return " + ternary(15, "n") + " && r.m;\n  } },\n"
    old = columns(A_MULTI, SLOT, CLOSE, OTHER_CLOSE, BLOCK_HOT)
    new = columns(A_MULTI, SLOT, CLOSE, OTHER_CLOSE, improved, added)
    assert ratchet("closing.tsx", old, new) == (1, {NEW_CALLABLE})


def test_hotspot_copy_does_not_reuse_the_original_budget(ratchet):
    # Same structure, so the same fingerprint: the unchanged original still
    # holds the budget and the wholly added copy is a new callable.
    copy = HOT.replace("'h'", "'c'")
    assert ratchet("copy.tsx", OLD, columns(A_MULTI, SLOT, CLOSE, OTHER_CLOSE, HOT, copy)) == (
        1,
        {NEW_CALLABLE},
    )


def test_unchanged_hotspot_with_a_small_added_callable_passes(ratchet):
    small = "  { k: 'n', render: (r) =>\n    r.n ? 1 : 2 },\n"
    assert ratchet("small.tsx", OLD, columns(A_MULTI, SLOT, CLOSE, OTHER_CLOSE, HOT, small)) == (
        0,
        set(),
    )


ONE = "  { key: 'a', render: (r) => r.a ? 1 : 2 },\n"
LINES = "  { key: 'b', render: (r) => r.b },\n"


def test_edited_one_liner_keeps_its_ratchet_next_to_an_added_one(ratchet):
    # Both are wholly added and share the guess: the edited one still reports
    # its regression, the added one is also checked as new.
    edited = "  { key: 'a', render: (r) => r.a ? (r.x ? 1 : 3) : 2 },\n"
    added = "  { key: 'n', render: (r) => r.n },\n"
    old = columns(ONE, "  // keep\n", LINES)
    code, findings = ratchet("one.tsx", old, columns(edited, added, "  // keep\n", LINES))
    assert code == 1
    assert ("legacy_metric_regression", "render", "cyclomatic") in findings


def test_edited_hotspot_one_liner_keeps_its_ratchet_next_to_an_added_one(ratchet):
    hot = "  { key: 'a', render: (r) => " + ternary(16, "a") + " },\n"
    regressed = "  { key: 'a', render: (r) => " + ternary(17, "a") + " },\n"
    added = "  { key: 'n', render: (r) => r.n },\n"
    old = columns(hot, "  // keep\n", LINES)
    code, findings = ratchet("hot_one.tsx", old, columns(regressed, added, "  // keep\n", LINES))
    assert code == 1
    assert ("legacy_metric_regression", "render", "cyclomatic") in findings


def test_edited_small_callable_keeps_its_ratchet_next_to_an_added_one(ratchet):
    small = "  { key: 'a', render: (r) => {\n    return r.a ? 1 : 2;\n  } },\n"
    edited = "  { key: 'a', render: (r) => {\n    return r.a ? (r.x ? 1 : 3) : 2;\n  } },\n"
    added = "  { key: 'n', render: (r) => {\n    return r.n;\n  } },\n"
    old = columns(small, LINES)
    code, findings = ratchet("small_edit.tsx", old, columns(edited, added, LINES))
    assert code == 1
    assert ("legacy_metric_regression", "render", "cyclomatic") in findings


def test_edited_one_liner_sharing_its_guess_keeps_its_ratchet(ratchet):
    # The added one-liner sits on the old line, so both wholly added callables
    # resolve to the same owner and neither holds it: both are also checked as
    # new, and the edited one still reports its regression.
    edited = "  { key: 'a', render: (r) => r.a ? (r.x ? 1 : 3) : 2 },\n"
    added = "  { key: 'n', render: (r) => " + ternary(15, "n") + " },\n"
    code, findings = ratchet("pair.tsx", columns(ONE, LINES), columns(added, edited, LINES))
    assert code == 1
    assert ("legacy_metric_regression", "render", "cyclomatic") in findings
    assert NEW_CALLABLE in findings


def test_edited_one_liner_without_a_sharer_keeps_only_its_ratchet(ratchet):
    edited = "  { key: 'a', render: (r) => r.a ? (r.x ? 1 : 3) : 2 },\n"
    code, findings = ratchet("solo.tsx", columns(ONE, LINES), columns(edited, LINES))
    assert code == 1
    assert ("legacy_metric_regression", "render", "cyclomatic") in findings
    assert NEW_CALLABLE not in findings


TWIN_HOT = "  { key: 't', render: (r) => {\n    return " + ternary(17, "t") + ";\n  } },\n"


def test_added_callable_does_not_borrow_from_an_equivalent_twin_group(ratchet):
    # Without a snapshot the moved twins only resolve as an equivalent group;
    # the added callable guessed one of them and is checked as new.
    added = "  { key: 'n', render: (r) => {\n    return " + ternary(15, "n") + ";\n  } },\n"
    old = columns(TWIN_HOT, TWIN_HOT)
    new = columns(TWIN_HOT, TWIN_HOT, added, shift=2)
    assert ratchet("twins.tsx", old, new, source_commit="") == (1, {NEW_CALLABLE})


def test_moved_twins_alone_remain_equivalent(ratchet):
    old = columns(TWIN_HOT, TWIN_HOT)
    assert ratchet("twins_moved.tsx", old, columns(TWIN_HOT, TWIN_HOT, shift=2)) == (0, set())


SETTER = """class A:
    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, v):
        if v:
            self._x = v
"""


def test_added_decorated_callable_does_not_borrow_an_edited_setter_budget(ratchet):
    branches = "".join(f"        if v == {n}:\n            v = {n + 1}\n" for n in range(16))
    deleter = f"\n    @x.deleter\n    def x(self, v=0):\n{branches}        self._x = v\n"
    new = SETTER.replace("if v:", "if v and v > 0:") + deleter
    code, findings = ratchet("setter.py", SETTER, new)
    assert code == 1
    assert ("new_callable_violation", "A.x", "cyclomatic") in findings


def test_deleted_hotspot_replaced_by_one_added_callable_keeps_the_single_guess(ratchet):
    # A single user is not a double lend; this documented residual is unchanged.
    old = columns(A_MULTI, SLOT, CLOSE, OTHER_CLOSE, HOT)
    assert ratchet("deleted.tsx", old, columns(A_MULTI, SLOT, CLOSE, OTHER_CLOSE, ADDED)) == (
        0,
        set(),
    )


def test_deleted_neighbour_does_not_change_the_hotspot_ratchet(ratchet):
    regressed = "  { k: 'h', render: (r) =>\n    " + ternary(18, "h") + " },\n"
    old = columns(ONE, LINES, HOT)
    code, findings = ratchet("deleted_peer.tsx", old, columns(LINES, regressed))
    assert code == 1
    assert ("legacy_metric_regression", "render", "cyclomatic") in findings
    assert NEW_CALLABLE not in findings


def test_hotspot_moved_into_two_files_lends_its_budget_to_neither(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    monkeypatch.setattr(tool, "load_exceptions", lambda: [])
    git(tmp_path, "init", "-q")
    hotspot = "export const pick = (r) =>\n  " + ternary(17, "h") + ";\n"
    (tmp_path / "frontend/src").mkdir(parents=True)
    (tmp_path / "frontend/src/old.tsx").write_text(hotspot)
    git(tmp_path, "add", "frontend/src/old.tsx")
    git(tmp_path, "-c", "user.name=F", "-c", "user.email=f@example.invalid", "commit", "-qm", "o")
    baseline = tool.baseline_from_report(tool.scan(["frontend/src/old.tsx"]))
    (tmp_path / "frontend/src/old.tsx").unlink()
    paths = ["frontend/src/one.tsx", "frontend/src/two.tsx"]
    for path in paths:
        (tmp_path / path).write_text(hotspot.replace("pick", "choose"))
    report = tool.scan(paths)
    added = tool.added_lines_since(baseline["source_commit"], paths)
    code, findings = tool.compare(report, baseline, added_lines=added)
    assert code == 1
    assert {(f["reason"], f["path"]) for f in findings} == {
        ("new_callable_violation", path) for path in paths
    }


FUZZ_HOT = (
    "  // fence f1\n  { k: 'x', render: (r) =>\n    "
    + " ".join(f"r.a{n} ? {n} :" for n in range(9))
    + "\n    "
    + " ".join(f"r.a{n} ? {n} :" for n in range(9, 17))
    + " -1 },\n"
)


def test_review_fuzz_partial_copy_of_a_hotspot_is_never_hidden(ratchet):
    # R146 review fuzz (seed 6, twins mode): a copy of the hotspot is inserted
    # above it while a fenced sibling is edited. The unresolved tie is refused;
    # once resolved the copy must not share the surviving hotspot's budget.
    fence = "  // fence f0\n  { k: 'x', render: (r) =>\n"
    old = columns(fence + "    -1 },\n  // tail t0\n", FUZZ_HOT, shift=8)
    new = columns(FUZZ_HOT, fence + "    r.a0 ? 0 : -1 },\n  // tail t0\n", FUZZ_HOT, shift=6)
    code, findings = ratchet("partial.tsx", old, new)
    assert code == 2 or (code, NEW_CALLABLE in findings) == (1, True)


EFFECT_BODY = "".join(f"    if (a.k{n}) {{ run({n}); }}\n" for n in range(17))
EFFECT = "  useEffect(() => {\n    const map = ref.current;\n" + EFFECT_BODY + "  }, [a]);\n"
COMPONENT = "export function P({ a, b }) {\n  const ref = useRef(null);\n\n"


def small_effect(n):
    return f"  useEffect(() => {{\n    const map = ref.current;\n    run({n});\n  }}, [b]);\n\n"


@pytest.mark.parametrize("added", [1, 2])
def test_slid_first_line_of_an_added_effect_does_not_hold_the_budget(ratchet, added):
    # Real shape (MapContainer, c6413f9b): effects are inserted above an edited
    # hotspot effect with identical opening lines. The snapshot diff slides
    # the hotspot's first line onto the first added effect, which the
    # added-lines diff reports as added: it holds nothing, so the hotspot is
    # not checked as new while the small added effects are.
    old = COMPONENT + EFFECT + "}\n"
    effects = "".join(small_effect(n) for n in range(added))
    edited = EFFECT.replace("run(3); }", "run(3); log(); }")
    code, findings = ratchet("effects.tsx", old, COMPONENT + effects + edited + "}\n")
    assert (code, findings) == (1, {("legacy_metric_regression", "P", "loc")})
