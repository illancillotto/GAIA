import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/code_quality/complexity.py"


def run_tool(*args):
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def baseline(path: Path, source: Path) -> Path:
    out = run_tool("baseline", "--baseline", str(path), str(source))
    assert out.returncode == 0, out.stdout + out.stderr
    return path


def callback_source(prefix=""):
    return prefix + """
import { useCallback, useEffect } from 'react';

export function Comp({ rows, enabled, onClick }: { rows: number[]; enabled: boolean; onClick: () => void }) {
  const mapped = rows.map((row) => {
    if (row > 10) return row * 2;
    return row + 1;
  });
  const filtered = rows.filter((row) => {
    if (!enabled) return false;
    return row > 0;
  });
  const nested = rows.map((row) => rows.filter((child) => child > row));
  const handler = () => {
    if (enabled) onClick();
  };
  const cb = useCallback(() => {
    if (enabled) return mapped.length;
    return filtered.length + nested.length;
  }, [enabled, mapped.length, filtered.length, nested.length]);
  useEffect(() => {
    if (enabled) cb();
  }, [enabled, cb]);
  return <button onClick={handler}>{mapped.length}</button>;
}
"""


def test_anonymous_callbacks_survive_line_shift_without_ambiguous_identity(tmp_path):
    source = tmp_path / "frontend/src/Comp.tsx"
    write(source, callback_source())
    base = baseline(tmp_path / "baseline.json", source)
    write(source, callback_source("\n\nconst harmless = 1;\n\n"))
    out = run_tool("check", "--baseline", str(base), str(source))
    assert out.returncode == 0, out.stdout + out.stderr
    assert "ambiguous_identity" not in out.stdout


def test_callback_legacy_regression_still_fails(tmp_path):
    source = tmp_path / "frontend/src/Comp.tsx"
    write(source, callback_source())
    base = baseline(tmp_path / "baseline.json", source)
    write(source, callback_source().replace("if (row > 10) return row * 2;", "if (row > 10) { if (row > 20) return row * 3; return row * 2; }"))
    out = run_tool("check", "--baseline", str(base), str(source))
    assert out.returncode == 1, out.stdout + out.stderr
    assert "legacy_metric_regression" in out.stdout


def test_truly_indistinguishable_regressed_callbacks_exit_2():
    import importlib.util

    spec = importlib.util.spec_from_file_location("gaia_complexity", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    base_call = {
        "path": "frontend/src/Comp.tsx",
        "name": "callback<callback>",
        "kind": "arrow_function",
        "line": 10,
        "end_line": 10,
        "cyclomatic": 1,
        "cognitive": 0,
        "loc": 1,
        "nesting": 0,
        "params": 0,
        "fingerprint": "same-fingerprint",
        "violations": [],
    }
    current_call = {**base_call, "cyclomatic": 2, "cognitive": 1, "nesting": 1}
    other_base_call = {**base_call, "line": 20, "end_line": 20}
    current_call = {**current_call, "line": 15, "end_line": 15}
    other_current_call = dict(current_call)
    baseline_data = {
        "schema_version": 1,
        "engines": {},
        "scope": {},
        "files": {"frontend/src/Comp.tsx": {"callables": 2}},
        "callables": [dict(base_call), other_base_call],
    }
    report = {
        "parse_errors": [],
        "exception_errors": [],
        "callables": [dict(current_call), other_current_call],
        "violations": [],
    }

    code, findings = module.compare(report, baseline_data)
    assert code == 2
    assert findings[0]["reason"] == "ambiguous_identity"


def test_callback_debt_laundering_by_wrapper_or_rename_fails(tmp_path):
    source = tmp_path / "frontend/src/Comp.tsx"
    write(source, """
export function Comp({ rows }: { rows: number[] }) {
  const expensive = rows.map((row) => {
    if (row > 1) {
      if (row > 2) {
        if (row > 3) return row;
      }
    }
    return 0;
  });
  return <div>{expensive.length}</div>;
}
""")
    base = baseline(tmp_path / "baseline.json", source)
    write(source, """
export function Comp({ rows }: { rows: number[] }) {
  const renamedWrapper = (row: number) => {
    if (row > 1) {
      if (row > 2) {
        if (row > 3) return row;
      }
    }
    return 0;
  };
  const expensive = rows.map((row) => renamedWrapper(row));
  return <div>{expensive.length}</div>;
}
""")
    out = run_tool("check", "--baseline", str(base), str(source))
    assert out.returncode in {1, 2}, out.stdout + out.stderr
    assert "new_callable_violation" in out.stdout or "ambiguous" in out.stdout or "legacy_metric_regression" in out.stdout
