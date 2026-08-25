import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/code_quality/complexity.py"


def run_tool(*args, cwd=ROOT):
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_new_code_under_threshold_passes_without_baseline(tmp_path):
    p = tmp_path / "backend/app/ok.py"
    write(p, "def ok(x):\n    return x + 1\n")
    r = run_tool("check", str(p))
    assert r.returncode == 0, r.stdout + r.stderr


def test_new_code_above_threshold_fails_without_baseline(tmp_path):
    p = tmp_path / "backend/app/bad.py"
    write(p, "def bad(x):\n" + "\n".join([f"    if x == {i}:\n        x += {i}" for i in range(20)]) + "\n    return x\n")
    r = run_tool("check", str(p))
    assert r.returncode == 1
    assert "new_violation_no_baseline" in r.stdout or "new_callable_violation" in r.stdout


def test_new_file_above_file_loc_threshold_fails(tmp_path):
    p = tmp_path / "backend/app/large_declarative.py"
    write(p, "\n".join(f"VALUE_{i} = {i}" for i in range(800)) + "\n")

    r = run_tool("check", "--baseline", str(tmp_path / "missing.json"), str(p))

    assert r.returncode == 1
    assert '"scope": "file"' in r.stdout
    assert '"metric": "loc"' in r.stdout


def test_legacy_invariant_passes_and_worse_fails(tmp_path):
    p = tmp_path / "backend/app/legacy.py"
    write(p, "def legacy(x):\n    if x:\n        return 1\n    return 0\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0
    assert run_tool("check", "--baseline", str(baseline), str(p)).returncode == 0
    write(p, "def legacy(x):\n    if x:\n        if x > 2:\n            return 2\n        return 1\n    return 0\n")
    r = run_tool("check", "--baseline", str(baseline), str(p))
    assert r.returncode == 1
    assert "legacy_metric_regression" in r.stdout


def test_legacy_improved_passes(tmp_path):
    p = tmp_path / "backend/app/legacy.py"
    write(p, "def legacy(x):\n    if x:\n        if x > 2:\n            return 2\n        return 1\n    return 0\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0
    write(p, "def legacy(x):\n    if x > 2:\n        return 2\n    return 0\n")
    assert run_tool("check", "--baseline", str(baseline), str(p)).returncode == 0


def test_legacy_file_level_debt_cannot_worsen(tmp_path):
    p = tmp_path / "backend/app/large_legacy.py"
    write(p, "\n".join(f"VALUE_{i} = {i}" for i in range(500)) + "\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0

    with p.open("a") as source:
        source.write("EXTRA_VALUE = 1\n")
    r = run_tool("check", "--baseline", str(baseline), str(p))

    assert r.returncode == 1
    assert "legacy_file_metric_regression" in r.stdout


def test_python_async_nested_and_match(tmp_path):
    p = tmp_path / "backend/app/py_shapes.py"
    write(p, "async def outer(x):\n    def inner(y):\n        match y:\n            case 1:\n                return 1\n            case _:\n                return 0\n    return inner(x)\n")
    r = run_tool("report", "--json", str(tmp_path / "r.json"), "--markdown", str(tmp_path / "r.md"), str(p))
    assert r.returncode == 0
    data = json.loads((tmp_path / "r.json").read_text())
    names = {c["name"] for c in data["callables"]}
    assert {"outer", "outer.inner"} <= names


def test_js_tsx_arrow_callback_component_hooks(tmp_path):
    p = tmp_path / "frontend/src/Comp.tsx"
    write(p, "import { useEffect, useState } from 'react';\nexport const Comp = () => {\n const [x,setX] = useState(0);\n useEffect(() => { if (x) setX(x+1); }, [x]);\n const cb = (v: number) => { if (v > 1) { return v; } return 0; };\n return <button>{cb(x)}</button>;\n}\n")
    r = run_tool("report", "--json", str(tmp_path / "r.json"), "--markdown", str(tmp_path / "r.md"), str(p))
    assert r.returncode == 0
    data = json.loads((tmp_path / "r.json").read_text())
    file_metrics = next(iter(data["files"].values()))
    assert file_metrics["useState"] == 1
    assert "complexity_density" in file_metrics
    assert "cyclomatic_sum" in file_metrics
    assert any(c["kind"] == "react_component" for c in data["callables"])


def test_valid_expired_and_broad_exceptions(tmp_path):
    exc = tmp_path / "exceptions.json"
    exc.write_text(json.dumps({"exceptions": [
        {"path": "backend/app/foo.py", "metric": "cognitive", "reason": "declarative mapping", "owner": "qa", "introduced_at": "2026-08-18", "expires_at": "2099-01-01"},
        {"path": "frontend/src/**", "metric": "*", "reason": "too broad", "owner": "qa", "introduced_at": "2026-08-18", "expires_at": "2099-01-01"},
        {"path": "backend/app/bar.py", "metric": "loc", "reason": "old", "owner": "qa", "introduced_at": "2020-01-01", "expires_at": "2020-01-02"}
    ]}))
    r = run_tool("validate-exceptions", "--exceptions", str(exc))
    assert r.returncode == 2
    assert "too broad" in r.stdout and "expired" in r.stdout


def test_missing_and_corrupt_baseline_exit_codes(tmp_path):
    p = tmp_path / "backend/app/ok.py"
    write(p, "def ok():\n    return 1\n")
    assert run_tool("baseline-verify", "--baseline", str(tmp_path / "missing.json"), str(p)).returncode == 2
    corrupt = tmp_path / "corrupt.json"; corrupt.write_text("{")
    r = run_tool("check", "--baseline", str(corrupt), str(p))
    assert r.returncode == 2
    assert "invalid JSON" in r.stderr


def test_baseline_update_rejects_regressions(tmp_path):
    p = tmp_path / "backend/app/legacy.py"
    write(p, "def legacy(x):\n    if x:\n        return 1\n    return 0\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0
    write(p, "def legacy(x):\n" + "\n".join([f"    if x == {i}:\n        x += {i}" for i in range(18)]) + "\n    return x\n")
    r = run_tool("baseline", "--baseline", str(baseline), str(p))
    assert r.returncode == 1
    assert "baseline_update_rejected" in r.stderr


def test_merge_base_baseline_rejects_coordinated_regression(tmp_path):
    p = tmp_path / "backend/app/legacy.py"
    write(p, "def legacy(x):\n    if x:\n        return 1\n    return 0\n")
    merge_base_baseline = tmp_path / "merge-base-baseline.json"
    assert run_tool("baseline", "--baseline", str(merge_base_baseline), str(p)).returncode == 0

    write(p, "def legacy(x):\n    if x:\n        if x > 2:\n            return 2\n        return 1\n    return 0\n")
    coordinated_baseline = tmp_path / "coordinated-baseline.json"
    assert run_tool("baseline", "--baseline", str(coordinated_baseline), str(p)).returncode == 0
    assert run_tool("check", "--baseline", str(coordinated_baseline), str(p)).returncode == 0

    guarded = run_tool("check", "--baseline", str(merge_base_baseline), str(p))
    assert guarded.returncode == 1
    assert "legacy_metric_regression" in guarded.stdout


def test_file_deleted_does_not_fail(tmp_path):
    p = tmp_path / "backend/app/delete_me.py"
    write(p, "def gone():\n    return 1\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0
    p.unlink()
    assert run_tool("check", "--baseline", str(baseline), str(tmp_path / "backend/app")).returncode == 0


def test_rename_with_same_fingerprint_passes(tmp_path):
    p = tmp_path / "backend/app/a.py"
    write(p, "def same(x):\n    if x:\n        return 1\n    return 0\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0
    q = tmp_path / "backend/app/b.py"; shutil.move(p, q)
    assert run_tool("check", "--baseline", str(baseline), str(q)).returncode == 0


def test_new_file_reusing_existing_fingerprint_is_not_a_rename(tmp_path):
    source = "def same(x):\n    return x\n"
    app = tmp_path / "backend/app"
    write(app / "a.py", source)
    write(app / "c.py", source)
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(app)).returncode == 0

    write(app / "b.py", source)
    result = run_tool("check", "--baseline", str(baseline), str(app))

    assert result.returncode == 0, result.stdout + result.stderr


def test_ambiguous_fingerprint_exit_2(tmp_path):
    p = tmp_path / "backend/app/a.py"
    write(p, "def same(x):\n    return x\n")
    q0 = tmp_path / "backend/app/c.py"
    write(q0, "def same(x):\n    return x\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(tmp_path / "backend/app")).returncode == 0
    p.unlink(); q0.unlink()
    q = tmp_path / "backend/app/b.py"; write(q, "def same(x):\n    return x\n")
    r = run_tool("check", "--baseline", str(baseline), str(q))
    assert r.returncode == 2
    assert "ambiguous_fingerprint" in r.stdout


def test_changed_merge_base_unavailable_exit_2():
    r = run_tool("changed", "--base-ref", "refs/heads/does-not-exist")
    assert r.returncode == 2
    assert "merge-base unavailable" in r.stderr


def test_ratchet_merge_base_unavailable_exit_2():
    r = run_tool("ratchet", "--base-ref", "refs/heads/does-not-exist")
    assert r.returncode == 2
    assert "merge-base unavailable" in r.stderr


def _set_engine_version(path: Path, name="old-js-engine"):
    data = json.loads(path.read_text())
    data["engines"]["javascript"]["name"] = name
    path.write_text(json.dumps(data))


def test_engine_changed_without_flag_exit_2(tmp_path):
    p = tmp_path / "backend/app/legacy.py"
    write(p, "def legacy(x):\n    if x:\n        return 1\n    return 0\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0
    _set_engine_version(baseline)
    r = run_tool("baseline", "--baseline", str(baseline), str(p))
    assert r.returncode == 2
    assert "engine_migration_requires_approval" in r.stderr


def test_engine_changed_with_flag_valid_migration_exit_0(tmp_path):
    p = tmp_path / "backend/app/legacy.py"
    write(p, "def legacy(x):\n    if x:\n        return 1\n    return 0\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0
    _set_engine_version(baseline)
    r = run_tool("baseline", "--allow-engine-migration", "--baseline", str(baseline), str(p))
    assert r.returncode == 0, r.stdout + r.stderr


def test_engine_migration_source_regression_still_fails(tmp_path):
    p = tmp_path / "backend/app/legacy.py"
    write(p, "def legacy(x):\n    if x:\n        return 1\n    return 0\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0
    _set_engine_version(baseline)
    write(p, "def legacy(x):\n" + "\n".join([f"    if x == {i}:\n        x += {i}" for i in range(18)]) + "\n    return x\n")
    r = run_tool("baseline", "--allow-engine-migration", "--baseline", str(baseline), str(p))
    assert r.returncode == 1
    assert "legacy_metric_regression" in r.stderr


def test_engine_migration_new_violation_still_fails(tmp_path):
    p = tmp_path / "backend/app/ok.py"
    write(p, "def ok():\n    return 1\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0
    _set_engine_version(baseline)
    q = tmp_path / "backend/app/bad.py"
    write(q, "def bad(x):\n" + "\n".join([f"    if x == {i}:\n        x += {i}" for i in range(20)]) + "\n    return x\n")
    r = run_tool("baseline", "--allow-engine-migration", "--baseline", str(baseline), str(tmp_path / "backend/app"))
    assert r.returncode == 1
    assert "new_callable_violation" in r.stderr


def test_engine_migration_exclusion_expansion_fails(tmp_path):
    p = tmp_path / "backend/app/legacy.py"
    write(p, "def legacy(x):\n    if x:\n        return 1\n    return 0\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0
    data = json.loads(baseline.read_text())
    data["engines"]["javascript"]["name"] = "old-js-engine"
    data["scope"]["exclude"].append("backend/app/**")
    baseline.write_text(json.dumps(data))
    r = run_tool("baseline", "--allow-engine-migration", "--baseline", str(baseline), str(p))
    assert r.returncode in {1, 2}
    assert "baseline_scope_exclude_changed" in r.stderr


def test_baseline_scope_change_fails_without_engine_migration(tmp_path):
    p = tmp_path / "backend/app/legacy.py"
    write(p, "def legacy(x):\n    return x\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0
    data = json.loads(baseline.read_text())
    data["scope"]["exclude"].append("backend/app/private/**")
    baseline.write_text(json.dumps(data))

    r = run_tool("baseline", "--baseline", str(baseline), str(p))

    assert r.returncode == 2
    assert "baseline_scope_exclude_changed" in r.stderr


def test_engine_migration_ambiguous_matching_exit_2(tmp_path):
    p = tmp_path / "backend/app/a.py"
    q = tmp_path / "backend/app/c.py"
    write(p, "def same(x):\n    return x\n")
    write(q, "def same(x):\n    return x\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(tmp_path / "backend/app")).returncode == 0
    _set_engine_version(baseline)
    p.unlink(); q.unlink()
    r = tmp_path / "backend/app/b.py"
    write(r, "def same(x):\n    return x\n")
    out = run_tool("baseline", "--allow-engine-migration", "--baseline", str(baseline), str(r))
    assert out.returncode == 2
    assert "ambiguous_fingerprint" in out.stderr


def test_baseline_entry_removed_but_callable_present_fails(tmp_path):
    p = tmp_path / "backend/app/rem.py"
    write(p, "def rem(x):\n    if x:\n        return 1\n    return 0\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0
    data = json.loads(baseline.read_text())
    data["callables"] = []
    baseline.write_text(json.dumps(data))
    r = run_tool("check", "--baseline", str(baseline), str(p))
    assert r.returncode == 2
    assert "baseline_callable_count_mismatch" in r.stdout


def test_baseline_entry_removed_for_deleted_callable_passes(tmp_path):
    p = tmp_path / "backend/app/rem.py"
    write(p, "def rem(x):\n    if x:\n        return 1\n    return 0\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0
    p.unlink()
    assert run_tool("check", "--baseline", str(baseline), str(tmp_path / "backend/app")).returncode == 0


def test_manual_baseline_deletion_fails(tmp_path):
    p = tmp_path / "backend/app/manual.py"
    write(p, "def manual(x):\n    return x\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(p)).returncode == 0
    data = json.loads(baseline.read_text())
    data["callables"].pop()
    baseline.write_text(json.dumps(data))
    r = run_tool("baseline", "--baseline", str(baseline), str(p))
    assert r.returncode == 2
    assert "baseline_callable_count_mismatch" in r.stderr
