#!/usr/bin/env python3
"""Deterministic GAIA complexity scanner and differential gate.

Local-first tool for GAIA Code Complexity. It uses Python's stdlib AST for
Python and a real Babel parser AST helper for JS/TS/JSX/TSX.
"""
from __future__ import annotations

import argparse
import ast
import dataclasses
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 2
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE = ROOT / "config/code-quality/complexity-baseline.json"
DEFAULT_EXCEPTIONS = ROOT / "config/code-quality/complexity-exceptions.json"
DEFAULT_REPORT_JSON = ROOT / "reports/code-quality/complexity-report.json"
DEFAULT_REPORT_MD = ROOT / "reports/code-quality/complexity-report.md"
JS_AST_HELPER = ROOT / "tools/code_quality/js_ast_metrics.mjs"
INCLUDE = ["backend/app/**/*.py", "frontend/src/**/*.js", "frontend/src/**/*.jsx", "frontend/src/**/*.ts", "frontend/src/**/*.tsx", "modules/elaborazioni/worker/**/*.py"]
EXCLUDE = [
    "**/__pycache__/**", "**/.pytest_cache/**", "**/.ruff_cache/**", "**/.next/**", "**/node_modules/**",
    "**/coverage/**", "**/htmlcov/**", "**/graphify-out/**", "backend/alembic/versions/*.py",
    "**/*.min.js", "**/*.d.ts", "**/fixtures/**", "**/__snapshots__/**",
]
CALLABLE_THRESHOLDS = {
    "cyclomatic": {"warning": 10, "error": 15},
    "cognitive": {"warning": 15, "error": 25},
    "loc": {"warning": 50, "error": 80},
    "nesting": {"warning": 4, "error": 5},
    "params": {"warning": 5, "error": 7},
}
FILE_THRESHOLDS = {
    "loc": {"warning": 500, "error": 800},
    "useState": {"warning": 10, "error": 20},
    "useEffect": {"warning": 5, "error": 8},
}
PRIMARY = ("cyclomatic", "cognitive", "loc", "nesting", "params")

@dataclasses.dataclass
class CallableMetric:
    path: str
    name: str
    kind: str
    line: int
    end_line: int
    cyclomatic: int
    cognitive: int
    loc: int
    nesting: int
    params: int
    fingerprint: str
    violations: list[dict[str, Any]]

    def key(self) -> str:
        return f"{self.path}::{self.name}"

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        # Test fixtures may live outside the repo. Keep stable POSIX absolute paths
        # instead of failing; real checkout scans still produce repo-relative paths.
        return resolved.as_posix()


def run_git(args: list[str], check: bool = True) -> str:
    p = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return p.stdout.strip()


def source_commit() -> str:
    return run_git(["rev-parse", "HEAD"], check=False) or "unknown"


def provenance() -> dict[str, Any]:
    return {
        "tool": rel(Path(__file__)),
        "repo_root": ROOT.as_posix(),
        "source_commit": source_commit(),
    }


def engine_versions() -> dict[str, Any]:
    node = subprocess.run(["node", "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.strip() if shutil_which("node") else "missing"
    babel = "missing"
    if shutil_which("node"):
        probe = subprocess.run(
            ["node", "-e", "try{console.log(require.resolve('@babel/parser',{paths:['./frontend/node_modules','./node_modules']}))}catch(e){process.exit(1)}"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if probe.returncode == 0:
            babel = "available"
    return {
        "python": {"name": "python-ast", "version": "1", "runtime": sys.version.split()[0]},
        "javascript": {"name": "babel-parser-ast", "version": "1", "runtime": node, "@babel/parser": babel},
    }


def shutil_which(cmd: str) -> str | None:
    from shutil import which
    return which(cmd)


def is_excluded(path: Path) -> bool:
    s = rel(path)
    return any(fnmatch.fnmatch(s, pat) for pat in EXCLUDE)


def iter_scope(paths: list[str] | None = None) -> list[Path]:
    if paths:
        out = []
        for p in paths:
            pp = (ROOT / p).resolve()
            if pp.is_dir():
                out.extend(x for x in pp.rglob("*") if x.is_file())
            elif pp.is_file():
                out.append(pp)
        return sorted({p for p in out if is_runtime(p) and not is_excluded(p)})
    files: list[Path] = []
    for pat in INCLUDE:
        files.extend(ROOT.glob(pat))
    return sorted({p for p in files if p.is_file() and not is_excluded(p)})


def is_runtime(p: Path) -> bool:
    s = p.as_posix()
    return (s.endswith(".py") and ("/backend/app/" in s or "/modules/elaborazioni/worker/" in s)) or bool(re.search(r"/frontend/src/.*\.(js|jsx|ts|tsx)$", s))


def effective_loc(lines: list[str], start: int, end: int) -> int:
    count = 0
    for line in lines[max(0, start - 1):end]:
        t = line.strip()
        if t and not t.startswith("#") and not t.startswith("//"):
            count += 1
    return count


def violation_dict(metric: str, value: int, thresholds: dict[str, int], scope: str = "callable") -> dict[str, Any] | None:
    sev = None
    if value >= thresholds["error"]:
        sev = "error"
    elif value >= thresholds["warning"]:
        sev = "warning"
    if not sev:
        return None
    return {"scope": scope, "metric": metric, "severity": sev, "threshold": thresholds[sev], "value": value}


class PyVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, source: str):
        self.path = rel(path)
        self.source = source
        self.lines = source.splitlines()
        self.stack: list[str] = []
        self.callables: list[CallableMetric] = []

    def visit_FunctionDef(self, node: ast.FunctionDef): self._function(node, "function")
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef): self._function(node, "async_function")

    def visit_ClassDef(self, node: ast.ClassDef):
        self.stack.append(node.name)
        for child in node.body: self.visit(child)
        self.stack.pop()

    def _function(self, node: ast.AST, kind: str):
        name = getattr(node, "name", "<lambda>")
        qn = ".".join([*self.stack, name]) if self.stack else name
        start = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", start)
        body = ast.get_source_segment(self.source, node) or ""
        cyclo, cog, nest = py_complexities(node)
        params = py_param_count(node)
        loc = effective_loc(self.lines, start, end)
        violations = []
        for metric, value in {"cyclomatic": cyclo, "cognitive": cog, "loc": loc, "nesting": nest, "params": params}.items():
            v = violation_dict(metric, value, CALLABLE_THRESHOLDS[metric])
            if v: violations.append(v)
        fp = hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()[:16]
        self.callables.append(CallableMetric(self.path, qn, kind, start, end, cyclo, cog, loc, nest, params, fp, violations))
        self.stack.append(name)
        for child in getattr(node, "body", []):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.visit(child)
        self.stack.pop()


def py_param_count(node: ast.AST) -> int:
    a = getattr(node, "args", None)
    if not a: return 0
    return len(a.posonlyargs) + len(a.args) + len(a.kwonlyargs) + bool(a.vararg) + bool(a.kwarg)


def py_complexities(node: ast.AST) -> tuple[int, int, int]:
    cyclo = 1
    cognitive = 0
    max_nesting = 0
    decision = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.ExceptHandler, ast.IfExp, ast.BoolOp, ast.Match)
    def walk(n: ast.AST, nesting: int = 0):
        nonlocal cyclo, cognitive, max_nesting
        inc_nest = isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.ExceptHandler, ast.Match))
        if isinstance(n, decision):
            cyclo += 1
            cognitive += 1 + nesting
            if isinstance(n, ast.BoolOp):
                cyclo += max(0, len(n.values) - 1)
                cognitive += max(0, len(n.values) - 1)
        if isinstance(n, ast.comprehension):
            cyclo += 1; cognitive += 1 + nesting
        if inc_nest:
            nesting += 1
            max_nesting = max(max_nesting, nesting)
        for c in ast.iter_child_nodes(n):
            if c is not node:
                walk(c, nesting)
    walk(node, 0)
    return cyclo, cognitive, max_nesting


def scan_python(path: Path) -> tuple[list[CallableMetric], dict[str, Any]]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=rel(path))
    v = PyVisitor(path, src); v.visit(tree)
    imports = sum(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree))
    return v.callables, {"imports": imports, "loc": effective_loc(src.splitlines(), 1, len(src.splitlines()))}

def scan_js(path: Path) -> tuple[list[CallableMetric], dict[str, Any]]:
    if not shutil_which("node"):
        raise RuntimeError("node is required for JS/TS AST metrics")
    proc = subprocess.run(["node", str(JS_AST_HELPER), str(path)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"JS AST helper failed for {rel(path)}")
    payload = json.loads(proc.stdout)
    out: list[CallableMetric] = []
    for item in payload.get("callables", []):
        violations = []
        for metric, value in {"cyclomatic": item["cyclomatic"], "cognitive": item["cognitive"], "loc": item["loc"], "nesting": item["nesting"], "params": item["params"]}.items():
            v = violation_dict(metric, value, CALLABLE_THRESHOLDS[metric])
            if v: violations.append(v)
        out.append(CallableMetric(rel(path), item["name"], item["kind"], item["line"], item["end_line"], item["cyclomatic"], item["cognitive"], item["loc"], item["nesting"], item["params"], item["fingerprint"], violations))
    return out, payload.get("file_metrics", {})


def load_exceptions(path: Path = DEFAULT_EXCEPTIONS) -> list[dict[str, Any]]:
    if not path.exists(): return []
    data = json.loads(path.read_text())
    return data.get("exceptions", []) if isinstance(data, dict) else data


def validate_exceptions(excs: list[dict[str, Any]]) -> list[str]:
    errors = []
    today = datetime.now(timezone.utc).date().isoformat()
    for i, e in enumerate(excs):
        p = e.get("path") or e.get("pattern")
        if not p: errors.append(f"exception[{i}] missing path/pattern")
        if p in {"backend/app/**", "frontend/src/**", "modules/elaborazioni/worker/**"} or (p and p.endswith("/**")):
            errors.append(f"exception[{i}] too broad: {p}")
        for field in ("metric", "reason", "owner", "introduced_at"):
            if not e.get(field): errors.append(f"exception[{i}] missing {field}")
        exp = e.get("expires_at")
        if exp and exp < today: errors.append(f"exception[{i}] expired: {p}")
        if not exp and not e.get("no_expiry_reason"):
            errors.append(f"exception[{i}] missing expires_at or no_expiry_reason")
    return errors


def is_path_exception(path: str, violation: dict[str, Any], excs: list[dict[str, Any]]) -> bool:
    for e in excs:
        pat = e.get("path") or e.get("pattern")
        if pat and fnmatch.fnmatch(path, pat) and e.get("metric") in {violation["metric"], "*"}:
            return True
    return False


def is_exception(call: CallableMetric, violation: dict[str, Any], excs: list[dict[str, Any]]) -> bool:
    return is_path_exception(call.path, violation, excs)


def scan(paths: list[str] | None = None) -> dict[str, Any]:
    files = iter_scope(paths)
    all_calls: list[CallableMetric] = []
    file_metrics: dict[str, Any] = {}
    calls_by_path: dict[str, list[CallableMetric]] = defaultdict(list)
    parse_errors = []
    for p in files:
        try:
            if p.suffix == ".py": calls, fm = scan_python(p)
            else: calls, fm = scan_js(p)
            path_key = rel(p)
            all_calls.extend(calls)
            calls_by_path[path_key].extend(calls)
            file_metrics[path_key] = {**fm, "callables": len(calls)}
        except Exception as e:
            parse_errors.append({"path": rel(p), "error": str(e)})
    excs = load_exceptions()
    for c in all_calls:
        for v in c.violations:
            v["excepted"] = is_exception(c, v, excs)
    by_area = Counter("backend" if c.path.startswith("backend/") else "frontend" if c.path.startswith("frontend/") else "worker" for c in all_calls)
    callable_violations = [{"path": c.path, "symbol": c.name, "line": c.line, **v} for c in all_calls for v in c.violations if not v.get("excepted")]
    file_violations: list[dict[str, Any]] = []
    for path_key, metrics in file_metrics.items():
        calls = calls_by_path.get(path_key, [])
        cyclomatic_sum = sum(c.cyclomatic for c in calls)
        cognitive_sum = sum(c.cognitive for c in calls)
        loc = max(1, int(metrics.get("loc") or 1))
        metrics.update({
            "cyclomatic_sum": cyclomatic_sum,
            "cyclomatic_max": max((c.cyclomatic for c in calls), default=0),
            "cognitive_sum": cognitive_sum,
            "cognitive_max": max((c.cognitive for c in calls), default=0),
            "complexity_density": round((cyclomatic_sum + cognitive_sum) / loc, 6),
            "dependency_count": metrics.get("imports", 0),
        })
        metrics["violations"] = []
        for metric, thresholds in FILE_THRESHOLDS.items():
            value = int(metrics.get(metric, 0) or 0)
            violation = violation_dict(metric, value, thresholds, scope="file")
            if not violation:
                continue
            violation["excepted"] = is_path_exception(path_key, violation, excs)
            metrics["violations"].append(violation)
            if not violation["excepted"]:
                file_violations.append({"path": path_key, "symbol": "<file>", "line": 1, **violation})
    violations = callable_violations + file_violations
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": source_commit(),
        "provenance": provenance(),
        "engines": engine_versions(),
        "scope": {"include": INCLUDE, "exclude": EXCLUDE, "files": len(files)},
        "summary": {"files": len(files), "callables": len(all_calls), "callables_by_area": dict(by_area), "violations": len(violations), "errors": sum(1 for v in violations if v["severity"] == "error"), "warnings": sum(1 for v in violations if v["severity"] == "warning")},
        "files": file_metrics,
        "callables": [c.to_dict() for c in all_calls],
        "violations": violations,
        "parse_errors": parse_errors,
        "exception_errors": validate_exceptions(excs),
    }


def baseline_from_report(report: dict[str, Any]) -> dict[str, Any]:
    return {k: report[k] for k in ("schema_version", "generated_at", "source_commit", "provenance", "engines", "scope", "files", "callables")}


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc.msg} at line {exc.lineno} column {exc.colno}") from exc


def callable_key(c: dict[str, Any]) -> str:
    # Path + qualified name is the primary identity; source span and fingerprint
    # disambiguate repeated anonymous/callback symbols emitted by JS/TS ASTs.
    return f"{c['path']}::{c['name']}::{c.get('line', 0)}::{c.get('end_line', 0)}::{c.get('fingerprint', '')}"


def call_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {callable_key(c): c for c in data.get("callables", [])}


def baseline_integrity_errors(baseline: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if baseline.get("schema_version") != SCHEMA_VERSION:
        errors.append({"reason": "invalid_baseline_schema_version", "value": baseline.get("schema_version")})
    for key in ("engines", "scope", "files", "callables"):
        if key not in baseline:
            errors.append({"reason": "invalid_baseline_missing_key", "key": key})
    files = baseline.get("files", {}) if isinstance(baseline.get("files"), dict) else {}
    calls = baseline.get("callables", []) if isinstance(baseline.get("callables"), list) else []
    by_path = Counter(c.get("path") for c in calls)
    for path, metrics in files.items():
        expected = metrics.get("callables") if isinstance(metrics, dict) else None
        if expected is not None and by_path.get(path, 0) != expected:
            errors.append({"reason": "baseline_callable_count_mismatch", "path": path, "expected": expected, "actual": by_path.get(path, 0)})
    return errors


def scope_policy_errors(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    old_scope = old.get("scope", {}) if isinstance(old.get("scope"), dict) else {}
    new_scope = new.get("scope", {}) if isinstance(new.get("scope"), dict) else {}
    if set(old_scope.get("include", [])) != set(new_scope.get("include", [])):
        errors.append({"reason": "baseline_scope_include_changed", "old": old_scope.get("include", []), "new": new_scope.get("include", [])})
    if set(old_scope.get("exclude", [])) != set(new_scope.get("exclude", [])):
        errors.append({"reason": "baseline_scope_exclude_changed", "old": old_scope.get("exclude", []), "new": new_scope.get("exclude", [])})
    return errors


def comparable_engines(engines: dict[str, Any] | None) -> dict[str, Any]:
    comparable = json.loads(json.dumps(engines or {}))
    for engine in comparable.values():
        if isinstance(engine, dict):
            engine.pop("runtime", None)
    return comparable


def span_distance(a: dict[str, Any], b: dict[str, Any]) -> int:
    a_start = int(a.get("line") or 0); a_end = int(a.get("end_line") or a_start)
    b_start = int(b.get("line") or 0); b_end = int(b.get("end_line") or b_start)
    if a_start <= b_end and b_start <= a_end:
        return 0
    return min(abs(a_start - b_end), abs(b_start - a_end), abs(a_start - b_start), abs(a_end - b_end))


def metric_tuple(c: dict[str, Any]) -> tuple[int, ...]:
    return tuple(int(c.get(m, 0) or 0) for m in PRIMARY)


def unique_line_tiebreak(c: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    ranked = sorted(((span_distance(c, b), b) for b in candidates), key=lambda item: item[0])
    if len(ranked) == 1:
        return ranked[0][1]
    if ranked[0][0] < ranked[1][0]:
        return ranked[0][1]
    return None


def resolve_baseline_callable(c: dict[str, Any], report: dict[str, Any], base: dict[str, dict[str, Any]], base_by_fp: dict[str, list[tuple[str, dict[str, Any]]]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None, bool]:
    exact = base.get(callable_key(c))
    if exact:
        return exact, None, False

    same_identity = [bc for bc in base.values() if bc.get("path") == c.get("path") and bc.get("name") == c.get("name")]
    same_identity_fp = [bc for bc in same_identity if bc.get("fingerprint") == c.get("fingerprint")]
    if len(same_identity_fp) == 1:
        return same_identity_fp[0], None, False
    if len(same_identity_fp) > 1:
        current_same_fp = [rc for rc in report["callables"] if rc.get("path") == c.get("path") and rc.get("name") == c.get("name") and rc.get("fingerprint") == c.get("fingerprint")]
        base_metrics = sorted(metric_tuple(bc) for bc in same_identity_fp)
        current_metrics = sorted(metric_tuple(rc) for rc in current_same_fp)
        if len(current_same_fp) == len(same_identity_fp) and current_metrics == base_metrics:
            return None, None, True
        picked = unique_line_tiebreak(c, same_identity_fp)
        if picked:
            return picked, None, False
        return None, {"reason": "ambiguous_identity", "path": c["path"], "symbol": c["name"], "fingerprint": c.get("fingerprint")}, False

    if len(same_identity) == 1:
        return same_identity[0], None, False
    if same_identity:
        picked = unique_line_tiebreak(c, same_identity)
        if picked:
            return picked, None, False
        return None, {"reason": "ambiguous_identity", "path": c["path"], "symbol": c["name"], "candidates": len(same_identity)}, False

    same_path_fp = [bc for bc in base.values() if bc.get("path") == c.get("path") and bc.get("fingerprint") == c.get("fingerprint")]
    if len(same_path_fp) == 1:
        return same_path_fp[0], None, False
    if len(same_path_fp) > 1:
        current_same_path_fp = [rc for rc in report["callables"] if rc.get("path") == c.get("path") and rc.get("fingerprint") == c.get("fingerprint")]
        base_metrics = sorted(metric_tuple(bc) for bc in same_path_fp)
        current_metrics = sorted(metric_tuple(rc) for rc in current_same_path_fp)
        if len(current_same_path_fp) == len(same_path_fp) and current_metrics == base_metrics:
            return None, None, True
        picked = unique_line_tiebreak(c, same_path_fp)
        if picked:
            return picked, None, False
        return None, {"reason": "ambiguous_fingerprint", "path": c["path"], "symbol": c["name"]}, False

    if any(bc.get("path") == c.get("path") for bc in base.values()):
        return None, None, False

    matches = base_by_fp.get(c.get("fingerprint"), [])
    if len(matches) == 1:
        return matches[0][1], None, False
    if len(matches) > 1:
        match_calls = [m[1] for m in matches]
        current_same_fp = [rc for rc in report["callables"] if rc.get("fingerprint") == c.get("fingerprint")]
        base_metrics = sorted(metric_tuple(bc) for bc in match_calls)
        current_metrics = sorted(metric_tuple(rc) for rc in current_same_fp)
        if len(current_same_fp) == len(match_calls) and current_metrics == base_metrics:
            return None, None, True
        picked = unique_line_tiebreak(c, match_calls)
        if picked:
            return picked, None, False
        return None, {"reason": "ambiguous_fingerprint", "path": c["path"], "symbol": c["name"]}, False
    return None, None, False


def compare(report: dict[str, Any], baseline: dict[str, Any] | None, changed_only: set[str] | None = None) -> tuple[int, list[dict[str, Any]]]:
    if report.get("parse_errors") or report.get("exception_errors"):
        return 2, [{"reason": "configuration_error", "parse_errors": report.get("parse_errors"), "exception_errors": report.get("exception_errors")}]
    if baseline is None:
        errors = [v for v in report["violations"] if v["severity"] == "error"]
        return (1 if errors else 0), [{"reason": "new_violation_no_baseline", **v} for v in errors]
    integrity = baseline_integrity_errors(baseline)
    if integrity:
        return 2, integrity
    base = call_index(baseline); findings = []
    base_by_fp = defaultdict(list)
    for k, c in base.items(): base_by_fp[c.get("fingerprint")].append((k, c))
    for c in report["callables"]:
        if changed_only is not None and c["path"] not in changed_only: continue
        b, ambiguity, equivalent_group = resolve_baseline_callable(c, report, base, base_by_fp)
        if ambiguity:
            return 2, [ambiguity]
        if equivalent_group:
            continue
        if not b:
            for v in c.get("violations", []):
                if v["severity"] == "error" and not v.get("excepted"):
                    findings.append({"reason": "new_callable_violation", "path": c["path"], "symbol": c["name"], **v})
            continue
        for m in PRIMARY:
            if c[m] > b.get(m, 0):
                findings.append({"reason": "legacy_metric_regression", "path": c["path"], "symbol": c["name"], "metric": m, "baseline": b.get(m, 0), "value": c[m], "delta": c[m] - b.get(m, 0)})
    baseline_files = baseline.get("files", {})
    for path, metrics in report.get("files", {}).items():
        if changed_only is not None and path not in changed_only:
            continue
        base_metrics = baseline_files.get(path)
        if not base_metrics:
            for violation in metrics.get("violations", []):
                if violation["severity"] == "error" and not violation.get("excepted"):
                    findings.append({"reason": "new_file_violation", "path": path, **violation})
            continue
        for metric, thresholds in FILE_THRESHOLDS.items():
            baseline_value = int(base_metrics.get(metric, 0) or 0)
            value = int(metrics.get(metric, 0) or 0)
            if baseline_value >= thresholds["warning"] and value > baseline_value:
                findings.append({
                    "reason": "legacy_file_metric_regression",
                    "path": path,
                    "metric": metric,
                    "baseline": baseline_value,
                    "value": value,
                    "delta": value - baseline_value,
                })
    return (1 if findings else 0), findings


def merge_base(base_ref: str) -> str:
    mb = subprocess.run(["git", "merge-base", base_ref, "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if mb.returncode != 0 or not mb.stdout.strip():
        raise RuntimeError(f"merge-base unavailable for {base_ref}: {mb.stderr.strip()}")
    return mb.stdout.strip()


def changed_files(base_ref: str, merge_base_commit: str | None = None) -> set[str]:
    base = merge_base_commit or merge_base(base_ref)
    committed = run_git(["diff", "--name-only", f"{base}...HEAD"])
    worktree = run_git(["diff", "--name-only", "HEAD"])
    untracked = run_git(["ls-files", "--others", "--exclude-standard"])
    return {x for output in (committed, worktree, untracked) for x in output.splitlines() if x}


def baseline_at_merge_base(base_ref: str, baseline_path: Path) -> tuple[str, dict[str, Any]]:
    base = merge_base(base_ref)
    try:
        relative_path = baseline_path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"baseline path must be inside the repository: {baseline_path}") from exc
    result = subprocess.run(
        ["git", "show", f"{base}:{relative_path}"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"baseline unavailable at merge-base {base}: {relative_path}. "
            "Merge the reviewed baseline before enabling the blocking ratchet gate."
        )
    try:
        return base, json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"invalid baseline JSON at merge-base {base}: {exc.msg} "
            f"at line {exc.lineno} column {exc.colno}"
        ) from exc


def write_report(report: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True); md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    s = report["summary"]
    top = sorted(report["callables"], key=lambda c: (c["cognitive"], c["cyclomatic"], c["loc"]), reverse=True)[:20]
    md = ["# GAIA Complexity Report", "", f"- Commit: `{report['source_commit']}`", f"- Files: `{s['files']}`", f"- Callables: `{s['callables']}`", f"- Violations: `{s['violations']}` (`{s['errors']}` error, `{s['warnings']}` warning)", "", "## Top callable", "", "| Path | Symbol | Line | Cog | Cyc | LOC | Nest | Params |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for c in top:
        md.append(f"| `{c['path']}` | `{c['name']}` | {c['line']} | {c['cognitive']} | {c['cyclomatic']} | {c['loc']} | {c['nesting']} | {c['params']} |")
    md_path.write_text("\n".join(md) + "\n")


def cmd_report(args):
    r = scan(args.paths); write_report(r, Path(args.json), Path(args.markdown)); print(json.dumps(r["summary"], sort_keys=True)); return 2 if r["parse_errors"] or r["exception_errors"] else 0

def cmd_check(args):
    r = scan(args.paths)
    try:
        b = load_json(Path(args.baseline)) if Path(args.baseline).exists() else None
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    code, findings = compare(r, b)
    print(json.dumps({"summary": r["summary"], "findings": findings[:100]}, indent=2, sort_keys=True)); return code

def cmd_changed(args):
    try: changed = changed_files(args.base_ref)
    except Exception as e: print(str(e), file=sys.stderr); return 2
    r = scan(args.paths)
    try:
        b = load_json(Path(args.baseline)) if Path(args.baseline).exists() else None
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    code, findings = compare(r, b, changed_only=changed)
    print(json.dumps({"changed_files": sorted(changed), "findings": findings[:100]}, indent=2, sort_keys=True)); return code

def cmd_ratchet(args):
    try:
        base, baseline = baseline_at_merge_base(args.base_ref, Path(args.baseline))
        changed = changed_files(args.base_ref, merge_base_commit=base)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    report = scan(args.paths)
    scope_errors = scope_policy_errors(baseline, baseline_from_report(report))
    if scope_errors:
        print(json.dumps({"error": "ratchet_scope_changed", "findings": scope_errors[:100]}, indent=2), file=sys.stderr)
        return 2
    if comparable_engines(baseline.get("engines")) != comparable_engines(report.get("engines")):
        print(json.dumps({
            "error": "ratchet_engine_changed",
            "baseline_engines": comparable_engines(baseline.get("engines")),
            "current_engines": comparable_engines(report.get("engines")),
        }, indent=2), file=sys.stderr)
        return 2
    code, findings = compare(report, baseline, changed_only=changed)
    print(json.dumps({
        "base_ref": args.base_ref,
        "baseline_commit": base,
        "changed_files": sorted(changed),
        "findings": findings[:100],
    }, indent=2, sort_keys=True))
    return code

def cmd_baseline(args):
    r = scan(args.paths); newb = baseline_from_report(r); bp = Path(args.baseline)
    if bp.exists():
        try:
            old = load_json(bp)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        scope_errors = scope_policy_errors(old, newb)
        if scope_errors:
            print(json.dumps({"error": "baseline_update_rejected", "findings": scope_errors[:100]}, indent=2), file=sys.stderr)
            return 2
        if comparable_engines(old.get("engines")) != comparable_engines(newb.get("engines")):
            if not args.allow_engine_migration:
                print(json.dumps({"error": "engine_migration_requires_approval", "old_engines": old.get("engines"), "new_engines": newb.get("engines")}, indent=2), file=sys.stderr)
                return 2
        code, findings = compare(r, old)
        if code != 0:
            print(json.dumps({"error": "baseline_update_rejected", "findings": findings[:100]}, indent=2), file=sys.stderr); return code
    bp.parent.mkdir(parents=True, exist_ok=True); bp.write_text(json.dumps(newb, indent=2, sort_keys=True) + "\n")
    print(f"wrote {bp}"); return 0

def cmd_baseline_verify(args):
    bp = Path(args.baseline)
    if not bp.exists(): print(f"missing baseline {bp}", file=sys.stderr); return 2
    before = bp.read_text(); r = scan(args.paths); candidate = json.dumps(baseline_from_report(r), indent=2, sort_keys=True) + "\n"
    def norm(s: str) -> dict[str, Any]:
        try:
            d = json.loads(s)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in {bp}: {exc.msg} at line {exc.lineno} column {exc.colno}") from exc
        d.pop("generated_at", None)
        d.pop("source_commit", None)
        provenance = d.get("provenance")
        if isinstance(provenance, dict):
            provenance.pop("source_commit", None)
        engines = d.get("engines")
        if isinstance(engines, dict):
            for engine in engines.values():
                if isinstance(engine, dict):
                    engine.pop("runtime", None)
        return d
    try:
        ok = norm(before) == norm(candidate)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"baseline_reproducible_ignoring_timestamp_commit": ok}, sort_keys=True)); return 0 if ok else 1

def cmd_validate_exceptions(args):
    errors = validate_exceptions(load_exceptions(Path(args.exceptions)))
    print(json.dumps({"errors": errors}, indent=2)); return 2 if errors else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    def common(sp):
        sp.add_argument("--baseline", default=str(DEFAULT_BASELINE)); sp.add_argument("paths", nargs="*")
    sp = sub.add_parser("report"); common(sp); sp.add_argument("--json", default=str(DEFAULT_REPORT_JSON)); sp.add_argument("--markdown", default=str(DEFAULT_REPORT_MD)); sp.set_defaults(func=cmd_report)
    sp = sub.add_parser("check"); common(sp); sp.set_defaults(func=cmd_check)
    sp = sub.add_parser("changed"); common(sp); sp.add_argument("--base-ref", default="origin/main"); sp.set_defaults(func=cmd_changed)
    sp = sub.add_parser("ratchet"); common(sp); sp.add_argument("--base-ref", default="origin/main"); sp.set_defaults(func=cmd_ratchet)
    sp = sub.add_parser("baseline"); common(sp); sp.add_argument("--allow-engine-migration", action="store_true", help="rewrite baseline after an explicit metrics-engine migration approval"); sp.set_defaults(func=cmd_baseline)
    sp = sub.add_parser("baseline-verify"); common(sp); sp.set_defaults(func=cmd_baseline_verify)
    sp = sub.add_parser("validate-exceptions"); sp.add_argument("--exceptions", default=str(DEFAULT_EXCEPTIONS)); sp.set_defaults(func=cmd_validate_exceptions)
    args = p.parse_args(argv); return args.func(args)

if __name__ == "__main__": raise SystemExit(main())
