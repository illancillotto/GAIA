"""R109: a wholly added callback must not inherit an owner proven to survive elsewhere."""

import subprocess

import pytest
import test_complexity_contracts as contracts

tool = contracts.tool

PAGE = """export function Page({ setSearch, setDay, focus }: Props) {
  return (
    <div>
      <button onClick={() => setSearch("")}>a</button>
      <button onClick={() => setSearch("")}>b</button>
      <button onClick={() => { if (focus) { setDay(1); } else { setDay(2); } }}>c</button>
    </div>
  );
}
"""

ADDED_RENDERER = """const renderFocus = (focus: boolean, setDay: (v: number) => void) => <button onClick={() => {
  if (focus) { setDay(3); } else if (!focus) { setDay(4); }
}}>f</button>;
"""

REWRITTEN_DAY_PAGE = PAGE.replace(
    "{ if (focus) { setDay(1); } else { setDay(2); } }",
    "{ if (focus) { setDay(1); } else if (!focus) { setDay(2); } else { setDay(5); } }",
)

COLUMNS = """export const columns = [
  { key: 'a', render: (r) => r.a },
  { key: 'b', render: (r) => r.b },
];
"""

BLOCK_COLUMNS = """export const columns = [
  { key: 'a', render: (r) => {
    return r.a;
  } },
  { key: 'b', render: (r) => {
    return r.b;
  } },
];
"""

TWO_LINE_COLUMNS = """export const columns = [
  { key: 'a', render: (r) =>
    r.a },
  { key: 'b', render: (r) =>
    r.b },
  { key: 'c', render: (r) =>
    r.c ? 1 : 2 },
];
"""

DELETION_COLUMNS = """export const columns = [
  { key: 'a', render: (r) => {
    return r.a;
  } },
  { key: 'b', render: (r) => {
    return r.b;
  } },
  { key: 'c', render: (r) => {
    if (r.q) return 1;
    return r.c;
  } },
];
"""

HANDLERS = """export function A() { const h = () => 1; return h; }
export function B() {
  const h = () => 2;
  return h;
}
"""

RENAMED_ANCESTOR = """export function P() {
  const x = list.map(
    (v) => v,
  );
  return x;
}
export function Q() {
  const x = list.map(
    (v) => v,
  );
  return x;
}
export function R() {
  const z = list.map(
    (v) => v,
  );
  return z;
}
"""

SETTER = """class A:
    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, v):
        self._x = v
"""

DECORATED = """class A:
    def m(self): return 1
    def m(self): return 1
    @staticmethod
    def m(self): return 1
"""

REDEFINED = """def f(x): return x
def f(x): return x
def f(x):
    if x:
        return 1
    return x
"""


def git(root, *arguments):
    return subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def ratchet(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    monkeypatch.setattr(tool, "load_exceptions", lambda: [])
    git(tmp_path, "init", "-q")

    def run(name, old, new, *, source_commit=True):
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
        added = tool.added_lines_since(baseline["source_commit"], [path])
        if source_commit is not True:
            baseline["source_commit"] = source_commit
        code, findings = tool.compare(report, baseline, added_lines=added)
        return code, {(f["reason"], f["symbol"], f.get("metric")) for f in findings}, report

    return run


def test_wholly_added_callback_does_not_take_a_proven_surviving_owner(ratchet):
    code, findings, report = ratchet("Page.tsx", PAGE, ADDED_RENDERER + PAGE)
    added = next(c for c in report["callables"] if c["name"] == "Program<anonymous>")
    assert (added["line"], added["end_line"]) == (1, 3)
    assert (code, findings) == (0, set())


@pytest.mark.parametrize("source_commit", ["", "0" * 40])
def test_without_a_verifiable_source_snapshot_the_positional_guess_stands(ratchet, source_commit):
    code, findings, _ = ratchet(
        "Page.tsx", PAGE, ADDED_RENDERER + PAGE, source_commit=source_commit
    )
    assert code == 1
    assert ("legacy_metric_regression", "Program<anonymous>", "cyclomatic") in findings


def test_wholly_added_callback_still_reports_new_error_violation(ratchet):
    branches = " ".join(f"else if (focus === {n}) {{ setDay({n}); }}" for n in range(20))
    renderer = (
        "const renderFocus = (focus: number, setDay: (v: number) => void) => "
        "<button onClick={() => {\n"
        f"  if (focus) {{ setDay(3); }} {branches}\n"
        "}}>f</button>;\n"
    )
    code, findings, _ = ratchet("Page.tsx", PAGE, renderer + PAGE)
    assert code == 1
    assert {reason for reason, _, _ in findings} == {"new_callable_violation"}


@pytest.mark.parametrize(
    ("name", "old", "new", "symbol"),
    [
        ("rewrite.tsx", PAGE, REWRITTEN_DAY_PAGE, "Program<anonymous>"),
        (
            "one_liner.tsx",
            COLUMNS,
            COLUMNS.replace("(r) => r.a }", "(r) => (r.a && r.x) || (r.y ? r.z : r.w) }"),
            "render",
        ),
        (
            "insertion.tsx",
            BLOCK_COLUMNS,
            BLOCK_COLUMNS.replace(
                "  { key: 'a', render: (r) => {\n    return r.a;\n  } },\n",
                "  { key: 'a', render: (row) => { if (row.a && row.x) "
                "{ return row.y ? row.z : row.w; }\n    return row.q; } },\n"
                "  { key: 'n', render: (r) => {\n    return r.n;\n  } },\n",
            ),
            "render",
        ),
        (
            "lookalike.tsx",
            TWO_LINE_COLUMNS,
            TWO_LINE_COLUMNS.replace(
                "(r) =>\n    r.a }", "(r) => (r.a && r.x) ||\n    (r.y ? r.z : r.w) }"
            ).replace("r.c ? 1 : 2 }", "r.c }"),
            "render",
        ),
        (
            "deletion.tsx",
            DELETION_COLUMNS,
            DELETION_COLUMNS.replace(
                "(r) => {\n    return r.a;\n  } }",
                "(row) => { if (row.k) { return 0; }\n"
                "    return row.a && row.x ? row.y : row.z;\n  }, }",
            ).replace("    if (r.q) return 1;\n", ""),
            "render",
        ),
        (
            "handlers.tsx",
            HANDLERS,
            HANDLERS.replace("const h = () => 2;", "const h = (x) => (x && x.a) || (x ? 3 : 4);"),
            "h",
        ),
        (
            "ancestor.tsx",
            RENAMED_ANCESTOR,
            RENAMED_ANCESTOR.replace("    (v) => v,\n", "    (v) => (v && v.a ? 1 : 2),\n", 1)
            .replace("const z", "const x")
            .replace("return z", "return x"),
            "x:list.map[0]<callback>",
        ),
        (
            "setter.py",
            SETTER,
            SETTER.replace(
                "    def x(self, v):\n        self._x = v\n",
                "    def x(self, value):\n        self._x = value if value and value > 0 "
                "else (0 if value is None else -value)\n",
            ),
            "A.x",
        ),
        (
            "decorated.py",
            DECORATED,
            DECORATED.replace(
                "def m(self): return 1\n", "def m(self): return 1 if self else 2\n", 1
            ).replace("    @staticmethod\n", ""),
            "A.m",
        ),
        (
            "redefined.py",
            REDEFINED,
            REDEFINED.replace(
                "def f(x): return x\n", "def f(x): return x if x > 0 else -x\n", 1
            ).replace("    if x:\n        return 1\n", ""),
            "f",
        ),
    ],
)
def test_rewritten_legacy_callable_keeps_its_regression(ratchet, name, old, new, symbol):
    code, findings, _ = ratchet(name, old, new)
    assert code == 1
    assert ("legacy_metric_regression", symbol, "cyclomatic") in findings


def test_unreadable_source_snapshot_keeps_the_guess_when_first_requested(tool, ratchet):
    _, _, report = ratchet("Page.tsx", PAGE, ADDED_RENDERER + PAGE)
    current = next(c for c in report["callables"] if c["name"] == "Program<anonymous>")
    owner = {**current, "line": 4, "end_line": 4, "fingerprint": "other"}
    baseline = {"source_commit": "0" * 40, "callables": [owner]}
    context = {
        "source_paths": None,
        "added_lines": {current["path"]: {1, 2, 3}},
        "snapshots": {},
        "owners": set(),
    }
    assert tool.unheld_source_owner(current, owner, report, baseline, context) is owner


TWIN = "  { key: 'a', render: (r) => {\n    return r.v;\n  } },\n"
OTHER_TWIN = "  { key: 'b', render: (r) => {\n    return r.w;\n  } },\n"
HOTSPOT = (
    "  { key: 'z', render: (r) => {\n    if (r.a) { if (r.b) { return 1; } }\n"
    "    if (r.c && r.d) return 2;\n    return r.e ? 3 : 4;\n  } },\n"
)
REWRITE = (
    "  { key: 'c', render: (row) => { if (row.p && row.q) { return row.w; }\n"
    "    return row.y ? row.k : row.j; }, },\n"
)


def columns(*parts):
    return "export const columns = [\n" + "".join(parts) + "];\n"


@pytest.mark.parametrize(
    "new",
    [
        columns(REWRITE, TWIN),
        columns(REWRITE, TWIN, "  // filler\n"),
        columns("  // filler\n", REWRITE, TWIN),
    ],
)
def test_identical_twins_are_not_proven_individually(ratchet, new):
    # Only one of two identical twins survives; which one is a diff tie-break,
    # so the guess is kept instead of jumping to the bigger hotspot.
    code, findings, _ = ratchet("twins.tsx", columns(TWIN, HOTSPOT, TWIN), new)
    assert code == 1
    assert ("legacy_metric_regression", "render", "cyclomatic") in findings


def branchy(key, prefix, count, tail):
    lines = "".join(f"    if ({prefix}.b{n}) return {n};\n" for n in range(count))
    return f"  {{ key: '{key}', render: ({prefix}) => {{\n{lines}    return {tail};\n  }} }},\n"


def test_no_unaccounted_callable_leaves_the_insertion_new(ratchet):
    code, findings, _ = ratchet("eliminated.tsx", columns(TWIN, TWIN), columns(TWIN, REWRITE, TWIN))
    assert (code, findings) == (0, set())


def test_single_unaccounted_callable_is_the_owner_by_elimination(ratchet):
    small = branchy("y", "r", 1, 0)
    code, findings, _ = ratchet(
        "eliminated_owner.tsx", columns(TWIN, small), columns(REWRITE, TWIN)
    )
    assert code == 1
    assert ("legacy_metric_regression", "render", "cyclomatic") in findings


def test_eliminated_callable_still_claimed_by_a_survivor_lends_nothing(ratchet):
    hotspot = branchy("z", "r", 19, 0)
    added = branchy("c", "row", 15, -1)
    code, findings, _ = ratchet(
        "claimed.tsx",
        columns(TWIN, TWIN, hotspot),
        columns(TWIN, added, TWIN, hotspot.replace("return 0;", "return 99;")),
    )
    assert code == 1
    assert {reason for reason, _, _ in findings} & {
        "legacy_metric_regression",
        "new_callable_violation",
    }


def test_a_budget_still_claimed_by_a_sibling_guess_is_not_lent(ratchet):
    # The second rewrite's own guess is the vanished hotspot, so the first
    # rewrite may not borrow that budget and keeps its original guess.
    second = REWRITE.replace("'c'", "'d'").replace("row.p && row.q", "row.p && row.q && row.z")
    code, findings, _ = ratchet(
        "lent_once.tsx", columns(TWIN, TWIN, HOTSPOT), columns(TWIN, REWRITE, TWIN, second)
    )
    assert code == 1
    assert ("legacy_metric_regression", "render", "cyclomatic") in findings


def test_several_unaccounted_callables_leave_the_rewrite_new(ratchet):
    # Policy chosen for R109: without a proof, no nearest-line guess among
    # several vanished callables; absolute thresholds still apply.
    ternary = OTHER_TWIN.replace("return r.w;", "return r.w ? 1 : 0;")
    # The nearest unaccounted candidate is the small ternary, so a nearest-line
    # re-guess would report a regression; the policy leaves the rewrite new.
    code, findings, _ = ratchet(
        "several.tsx", columns(TWIN, ternary, HOTSPOT, TWIN), columns(REWRITE, TWIN, TWIN)
    )
    assert (code, findings) == (0, set())


def test_same_fingerprint_with_different_text_keeps_the_guess(ratchet):
    code, findings, _ = ratchet(
        "lookalike_twin.tsx", columns(TWIN, HOTSPOT, OTHER_TWIN), columns(REWRITE, TWIN)
    )
    assert code == 1
    assert ("legacy_metric_regression", "render", "cyclomatic") in findings
