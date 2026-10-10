import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
import test_complexity_contracts as contracts

tool = contracts.tool


def git(root, *arguments):
    process = subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, text=True, check=True
    )
    return process.stdout.strip()


@pytest.fixture
def source_case(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    monkeypatch.setattr(tool, "load_exceptions", lambda: [])
    path = "backend/app/handlers.py"
    source = tmp_path / path
    source.parent.mkdir(parents=True)
    prefix = "".join(f"PREFIX_{number} = {number}\n" for number in range(7))
    body = (
        "def same(value): return None\n\n"
        "def same(value): return None\n\n"
        'HANDLER_LABEL = "sync"\n\n'
        "def same(value):\n"
        "    result = value\n"
        "    if value:\n"
        "        result += 1\n"
        "    else:\n"
        "        result -= 1\n"
        "    return result\n"
        'NEXT_LABEL = "end"\n'
    )
    source.write_text(prefix + body)
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", path)
    git(
        tmp_path,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "immutable fixture",
    )
    baseline = tool.baseline_from_report(tool.scan([path]))
    original = prefix + body.replace("result = value\n", "result = value + 1\n")
    candidate = original.replace(prefix, "PREFIX_6 = 6\n")
    source.write_text(original)
    original_report = tool.scan([path])
    source.write_text(candidate)
    candidate_report = tool.scan([path])
    return source, baseline, original_report, candidate_report


def test_original_ambiguity_and_strict_regression_characterization(tool, source_case):
    source, baseline, original, candidate = source_case
    assert tool.compare(original, baseline) == (0, [])
    unavailable = copy.deepcopy(baseline)
    unavailable.pop("source_commit")
    code, findings = tool.compare(candidate, unavailable)
    assert code == 2
    assert findings == [
        {
            "reason": "ambiguous_identity",
            "path": "backend/app/handlers.py",
            "symbol": "same",
            "candidates": 3,
        }
    ]
    negative = copy.deepcopy(original)
    negative["callables"][-1]["cognitive"] += 1
    code, findings = tool.compare(negative, baseline)
    assert code == 1
    assert findings[0]["reason"] == "legacy_metric_regression"
    assert findings[0]["metric"] == "cognitive"
    assert source.exists()


def test_unchanged_boundary_proof_resolves_unique_source_owner(tool, source_case):
    _, baseline, _, candidate = source_case
    current = candidate["callables"][-1]
    owner = tool.source_provenance_owner(current, candidate, baseline)
    assert owner == baseline["callables"][-1]
    assert tool.compare(candidate, baseline) == (0, [])


def test_proven_owner_still_checks_below_threshold_regressions(tool, source_case):
    source, baseline, _, _ = source_case
    source.write_text(source.read_text().replace("if value:", "if value and value > 1:"))
    candidate = tool.scan(["backend/app/handlers.py"])
    code, findings = tool.compare(candidate, baseline)
    assert code == 1
    assert {finding["metric"] for finding in findings} == {"cyclomatic", "cognitive"}
    assert all(finding["reason"] == "legacy_metric_regression" for finding in findings)


@pytest.mark.parametrize(
    "damage",
    [
        "missing_source",
        "stale_current",
        "stale_baseline",
        "unknown_commit",
        "invalid_commit",
        "external_forgery",
    ],
)
def test_source_proof_rejects_unbound_records_and_bytes(tool, source_case, tmp_path, damage):
    source, baseline, _, candidate = source_case
    sources = None
    if damage == "missing_source":
        source.unlink()
    elif damage == "stale_current":
        candidate["callables"][-1]["fingerprint"] = "forged"
    elif damage == "stale_baseline":
        baseline["callables"][-1]["cognitive"] += 1
    elif damage == "unknown_commit":
        baseline["source_commit"] = "f" * 40
    elif damage == "invalid_commit":
        baseline["source_commit"] = "HEAD"
    else:
        exterior = tmp_path / "forged.py"
        exterior.write_text("def unrelated(): return 1\n")
        sources = {"backend/app/handlers.py": exterior}
    code, findings = tool.compare(candidate, baseline, source_paths=sources)
    assert code == 2
    assert findings[0]["reason"] == "ambiguous_identity"


def test_exterior_source_is_freshly_scanned_and_never_applied(tool, source_case, tmp_path):
    source, baseline, _, candidate = source_case
    exterior = tmp_path / "candidate.py"
    exterior.write_bytes(source.read_bytes())
    source.write_text("def replaced(): return 1\n")
    frozen = source.read_bytes()
    assert tool.compare(candidate, baseline)[0] == 2
    assert tool.compare(
        candidate, baseline, source_paths={"backend/app/handlers.py": exterior}
    ) == (0, [])
    assert source.read_bytes() == frozen


@pytest.mark.parametrize("path", ["../escape.py", "/outside.py"])
def test_source_proof_rejects_noncanonical_paths(tool, source_case, path):
    _, baseline, _, candidate = source_case
    current = {**candidate["callables"][-1], "path": path}
    assert tool.source_provenance_owner(current, candidate, baseline) is None


@pytest.mark.parametrize(
    "diff,before,after,expected",
    [
        ("", ["same"], ["same"], {1: 1}),
        ("", ["same"], ["different"], {}),
        ("@@ -1 +1 @@\n-old\n+new\n", ["old", "end"], ["new", "end"], {2: 2}),
        ("@@ -0,0 +1 @@\n+new\n", ["end"], ["new", "end"], {2: 1}),
        ("@@ -1 +0,0 @@\n-old\n", ["old", "end"], ["end"], {1: 2}),
        ("@@ -2 +2 @@\n-old\n+new\n", ["gap", "old"], ["changed", "new"], {}),
        ("@@ -9 +1 @@\n-old\n+new\n", ["old"], ["new"], {}),
        ("@@ -1 +1 @@\n-forged\n+new\n", ["old"], ["new"], {}),
    ],
)
def test_diff_mapping_validates_complete_snapshot_content(tool, diff, before, after, expected):
    assert tool.unchanged_source_lines(diff, before, after) == expected


@pytest.mark.parametrize("failure", ["diff_exit", "diff_stderr", "scanner_error"])
def test_source_proof_stops_on_git_or_scanner_failure(tool, source_case, monkeypatch, failure):
    _, baseline, _, candidate = source_case
    original_run = tool.subprocess.run
    if failure == "scanner_error":

        def reject(_):
            raise RuntimeError("snapshot scanner unavailable")

        monkeypatch.setattr(tool, "scan_python", reject)
    else:

        def run(arguments, **options):
            if arguments[1] == "diff":
                return subprocess.CompletedProcess(
                    arguments,
                    2 if failure == "diff_exit" else 1,
                    "",
                    "failure" if failure == "diff_stderr" else "",
                )
            return original_run(arguments, **options)

        monkeypatch.setattr(tool.subprocess, "run", run)
    assert tool.compare(candidate, baseline)[0] == 2


@pytest.mark.parametrize("rewrite", ["start", "end", "anchor_before", "anchor_after"])
def test_edited_boundaries_or_unique_context_cannot_prove_identity(tool, source_case, rewrite):
    source, baseline, _, _ = source_case
    replacements = {
        "start": ("def same(value):\n", "def same(other):\n"),
        "end": ("return result\n", "return result + 1\n"),
        "anchor_before": ('HANDLER_LABEL = "sync"', 'HANDLER_LABEL = "replaced"'),
        "anchor_after": ('NEXT_LABEL = "end"', 'NEXT_LABEL = "replaced"'),
    }
    before, after = replacements[rewrite]
    source.write_text(source.read_text().replace(before, after))
    report = tool.scan(["backend/app/handlers.py"])
    assert tool.source_provenance_owner(report["callables"][-1], report, baseline) is None


@pytest.mark.parametrize("duplicate", ["owner", "consumer"])
def test_source_proof_rejects_multiple_callable_spans(tool, source_case, monkeypatch, duplicate):
    _, baseline, _, report = source_case
    original_scan = tool.scan_python
    target = baseline if duplicate == "owner" else report
    target["callables"].append(copy.deepcopy(target["callables"][-1]))

    def scan(path):
        calls, metrics = original_scan(path)
        if path.name.startswith("before" if duplicate == "owner" else "after"):
            calls.append(copy.deepcopy(calls[-1]))
        return calls, metrics

    monkeypatch.setattr(tool, "scan_python", scan)
    assert tool.source_provenance_owner(report["callables"][-1], report, baseline) is None


def test_provenance_cannot_reuse_unique_fingerprint_reserved_for_a_sibling(
    tool, source_case, monkeypatch
):
    _, baseline, _, report = source_case
    sibling = copy.deepcopy(baseline["callables"][-1])
    sibling["line"], sibling["end_line"] = 50, 55
    report["callables"].append(sibling)
    original_scan = tool.scan_python

    def scan(path):
        calls, metrics = original_scan(path)
        if path.name.startswith("after"):
            calls.append(tool.CallableMetric(**{**sibling, "path": str(path)}))
        return calls, metrics

    monkeypatch.setattr(tool, "scan_python", scan)
    assert tool.source_provenance_owner(report["callables"][-2], report, baseline) is None


def test_reordered_identical_boundaries_without_unique_context_remain_unproven(tool, source_case):
    source, baseline, _, _ = source_case
    original = "def same(value):\n    return value\n\n"
    other = "def same(value):\n    return value + 1\n\n"
    source.write_text(original + other)
    git(tool.ROOT, "add", "backend/app/handlers.py")
    git(
        tool.ROOT,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "unanchored duplicates",
    )
    baseline = tool.baseline_from_report(tool.scan(["backend/app/handlers.py"]))
    source.write_text(other + original)
    report = tool.scan(["backend/app/handlers.py"])
    assert tool.source_provenance_owner(report["callables"][0], report, baseline) is None


@pytest.mark.parametrize("commit", [None, 17, {}, []])
def test_malformed_commit_preserves_ambiguity(tool, source_case, commit):
    _, baseline, _, report = source_case
    baseline["source_commit"] = commit
    assert tool.compare(report, baseline)[0] == 2


def test_duplicate_exact_fingerprint_claims_cannot_reuse_proven_owner(tool, source_case):
    source, baseline, _, _ = source_case
    immutable = git(tool.ROOT, "show", f"{baseline['source_commit']}:backend/app/handlers.py")
    handler = immutable[immutable.index("def same(value):\n") : immutable.index("NEXT_LABEL")]
    source.write_text(source.read_text() + handler + handler)
    report = tool.scan(["backend/app/handlers.py"])
    assert tool.source_provenance_owner(report["callables"][2], report, baseline) is None
    assert tool.compare(report, baseline)[0] == 2


def test_git_replace_cannot_change_immutable_source_bytes(tool, source_case):
    source, baseline, _, report = source_case
    candidate_bytes = source.read_bytes()
    base_commit = baseline["source_commit"]
    immutable = git(tool.ROOT, "show", f"{base_commit}:backend/app/handlers.py")
    source.write_text(
        immutable.replace('HANDLER_LABEL = "sync"', 'FORGED_LABEL = "replacement"').replace(
            'NEXT_LABEL = "end"', 'FORGED_END = "replacement"'
        )
        + "\n"
    )
    git(tool.ROOT, "add", "backend/app/handlers.py")
    git(
        tool.ROOT,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "replacement context",
    )
    replacement = git(tool.ROOT, "rev-parse", "HEAD")
    git(tool.ROOT, "replace", base_commit, replacement)
    source.write_bytes(candidate_bytes)
    assert tool.compare(report, baseline) == (0, [])


def test_source_proof_rejects_duplicate_spans_even_for_single_line_callable(tool):
    current = {"name": "same", "line": 2, "end_line": 2, "fingerprint": "current"}
    old = {**current, "fingerprint": "before"}
    assert tool.unique_mapped_callable(current, {2: 2}, [old, dict(old)], [current]) is None


def test_source_identity_proof_obeys_other_resolver_claims(tool, source_case, monkeypatch):
    _, baseline, _, report = source_case
    original = tool.resolve_baseline_callable

    def resolve(current, *arguments):
        if current is report["callables"][0]:
            return baseline["callables"][-1], None, False
        return original(current, *arguments)

    monkeypatch.setattr(tool, "resolve_baseline_callable", resolve)
    assert tool.source_provenance_owner(report["callables"][-1], report, baseline) is None


def test_native_cli_bound_sources_preserve_zero_one_two_exits(tool, source_case, tmp_path):
    source, baseline, _, _ = source_case
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline))
    script = (
        "import importlib.util, sys; from pathlib import Path; "
        f"spec=importlib.util.spec_from_file_location('cli_fixture', {str(Path(tool.__file__))!r}); "
        "module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; "
        f"spec.loader.exec_module(module); module.ROOT=Path({str(tmp_path)!r}); "
        "module.load_exceptions=lambda: []; "
        f"sys.exit(module.main(['check','--baseline',{str(baseline_path)!r},"
        "'backend/app/handlers.py']))"
    )

    def run():
        return subprocess.run(
            [sys.executable, "-c", script], cwd=tmp_path, text=True, capture_output=True
        )

    process = run()
    assert process.returncode == 0, process.stdout + process.stderr
    original_bytes = source.read_bytes()
    source.write_text(source.read_text().replace("if value:", "if value and value > 1:"))
    process = run()
    assert process.returncode == 1
    assert "legacy_metric_regression" in process.stdout
    source.write_bytes(original_bytes)
    baseline["source_commit"] = None
    baseline_path.write_text(json.dumps(baseline))
    process = run()
    assert process.returncode == 2
    assert "ambiguous_identity" in process.stdout


def test_real_single_line_boundary_is_not_a_provenance_identity(tool, source_case):
    source, _, _, _ = source_case
    text = source.read_text()
    start = text.index("def same(value):\n")
    end = text.index("NEXT_LABEL")
    source.write_text(text[:start] + "def same(value): return value\n" + text[end:])
    git(tool.ROOT, "add", "backend/app/handlers.py")
    git(
        tool.ROOT,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "one-line owner",
    )
    baseline = tool.baseline_from_report(tool.scan(["backend/app/handlers.py"]))
    report = tool.scan(["backend/app/handlers.py"])
    assert tool.source_provenance_owner(report["callables"][-1], report, baseline) is None


def test_fresh_javascript_source_snapshots_prove_anonymous_handler_identity(tool, source_case):
    _, _, _, _ = source_case
    path = "frontend/src/handlers.tsx"
    source = tool.ROOT / path
    source.parent.mkdir(parents=True)
    prefix = "".join(f"const PREFIX_{number} = {number};\n" for number in range(7))
    body = (
        "<button onClick={() => null}>CloseA</button>;\n"
        "<button onClick={() => undefined}>CloseB</button>;\n"
        '\nconst LABEL = "sync-unique";\n'
        "<button onClick={() => {\n"
        "    const value = 1;\n"
        "    const result = value;\n"
        "    if (value) {\n"
        "        return result;\n"
        "    }\n"
        "    return null;\n"
        "}}>SyncUnique</button>;\n"
        'const NEXT = "end-unique";\n'
    )
    source.write_text(prefix + body)
    git(tool.ROOT, "add", path)
    git(
        tool.ROOT,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "anonymous handler source",
    )
    baseline = tool.baseline_from_report(tool.scan([path]))
    source.write_text("const PREFIX_6 = 6;\n" + body.replace("value = 1", "value = 2"))
    report = tool.scan([path])
    assert not report["parse_errors"]
    assert (
        tool.source_provenance_owner(report["callables"][-1], report, baseline)
        == baseline["callables"][-1]
    )
    assert tool.compare(report, baseline) == (0, [])
    source.write_text(source.read_text().replace("if (value)", "if (value && value > 1)"))
    report = tool.scan([path])
    code, findings = tool.compare(report, baseline)
    assert code == 1
    assert all(finding["reason"] == "legacy_metric_regression" for finding in findings)


def test_comparison_reads_one_snapshot_despite_anchor_context_race(tool, source_case, monkeypatch):
    source, _, _, _ = source_case
    original = git(tool.ROOT, "show", "HEAD:backend/app/handlers.py") + "\n"
    second = (
        'SECOND_LABEL = "sync-second"\n\n'
        "def same(value):\n"
        "    result = value * 2\n"
        "    if value:\n"
        "        result += 1\n"
        "    else:\n"
        "        result -= 1\n"
        "    return result\n"
        'SECOND_END = "end-second"\n'
    )
    source.write_text(original + second)
    git(tool.ROOT, "add", "backend/app/handlers.py")
    git(
        tool.ROOT,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "two ambiguous handlers",
    )
    baseline = tool.baseline_from_report(tool.scan(["backend/app/handlers.py"]))
    prefix = "".join(f"PREFIX_{number} = {number}\n" for number in range(7))
    text = (original + second).replace(prefix, "PREFIX_6 = 6\n")
    text = text.replace("result = value\n", "result = value + 1\n")
    text = text.replace("result = value * 2\n", "result = value * 3\n")
    source.write_text(text)
    report = tool.scan(["backend/app/handlers.py"])
    base = tool.call_index(baseline)
    from collections import defaultdict

    by_fingerprint = defaultdict(list)
    for key, call in base.items():
        by_fingerprint[call["fingerprint"]].append((key, call))
    for current in report["callables"][-2:]:
        assert tool.resolve_baseline_callable(current, report, base, by_fingerprint)[1] is not None
    before = source.read_bytes()
    changed_anchors = text.replace('HANDLER_LABEL = "sync"', 'HANDLER_LABEL = "racing"')
    changed_anchors = changed_anchors.replace(
        'SECOND_LABEL = "sync-second"', 'SECOND_LABEL = "racing-second"'
    )
    source.write_text(changed_anchors)
    assert [
        tool.source_callable_signature(call)
        for call in tool.scan(["backend/app/handlers.py"])["callables"]
    ] == [tool.source_callable_signature(call) for call in report["callables"]]
    original_read = Path.read_bytes
    reads = []

    def read(path):
        if path == source:
            reads.append(path)
            return before if len(reads) == 1 else changed_anchors.encode()
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    assert tool.compare(report, baseline) == (0, [])
    assert len(reads) == 1
    assert tool.compare(report, baseline)[0] == 2
    assert len(reads) == 2


def test_comparison_context_keeps_refusal_and_consumed_owner(tool, source_case, monkeypatch):
    source, baseline, _, report = source_case
    current = report["callables"][-1]
    context = {"source_paths": None, "added_lines": None, "snapshots": {}, "owners": set()}
    owner = tool.source_provenance_owner(current, report, baseline, context=context)
    assert owner == baseline["callables"][-1]
    assert tool.source_provenance_owner(current, report, baseline, context=context) is None
    context = {"snapshots": {}, "owners": set()}
    original = source.read_bytes()
    source.write_text("def malformed(")
    assert tool.source_provenance_owner(current, report, baseline, context=context) is None
    source.write_bytes(original)
    assert tool.source_provenance_owner(current, report, baseline, context=context) is None


def test_invalid_source_after_scan_preserves_original_ambiguity(tool, source_case):
    source, baseline, _, report = source_case
    source.write_text("def broken(")
    assert tool.compare(report, baseline)[0] == 2


def test_nonuniform_boundary_context_and_hunk_payload_fail_closed(tool):
    assert tool.source_anchor({1: 1, 2: 3}, ["unique", "end"], ["unique", "end"], 2, -1) is None
    assert (
        tool.unchanged_source_lines(
            "@@ -1 +1 @@\n-old\n+new\nmalformed\n", ["old", "end"], ["new", "end"]
        )
        == {}
    )
