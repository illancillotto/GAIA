# Capacitas — Independent characterization integration 3

## Ownership and snapshot

Exclusive report ownership authorized in registry `cf9bb483`. Integration
worktree `GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`; preflight clean HEAD
`17e6047d932316ed99a937e33d840904762cc021`, empty staging area. Merge-base main
remains `55a1b1d35911451e018b662c2acc450bf5994ea2`; frozen R3 runtime
`0b1a0d37` unchanged. Main dirty/concurrent work is untouched. Coordinator
owns its separate documents; this agent stages only this report and approved
source test/report pairs. C5b is explicitly outside this integration scope.

## Review and integration

| Slice | Source commit | Integrated commit | Source tests | Cumulative tests | Ratchet |
|---|---|---|---:|---:|---|
| C5a inCASS commands | `72cc29fa2a59f92edea5750545a76c539dc987b2` | `6e6313ba` | 46 PASS | 182 PASS | PASS, 0 findings |
| C2b Particelle monitor | `34ee63925ab851ed1f392f52a052ebd0a5821385` | `67fce218` | 47 PASS | 210 PASS | PASS, 0 findings |
| C4 Storico monitor | `e9577559bd001a459d00282083ac9241bc295d8e` | `b3b16c46` | 56 PASS | 247 PASS | PASS, 0 findings |

Final focused cases247 PASS/11specs, zero skip; C5a27/C2b28/C437 new cases
plus155 from Integration2. All three sequential ratchets PASS/0, exit0.
Every source contains only its exclusive new spec and slice report. Independent
source focused tests run before integration; source worktrees clean and runtime
hash identical. Before each cherry-pick the staged area is checked empty, then
after integration cumulative focused tests and authoritative main ratchet run
sequentially. No code/config/protected files are modified.

## Behavioral review matrix

| Slice responsibility | Public behavior characterized | Review |
|---|---|---|
| C5a payload | Default/chosen credential, sanitized numeric inputs, blank/zero semantics, all sync/harvest flags, no fabricated subject IDs | PASS |
| C5a create/harvest | Exact token/payload, returned totals, zero eligible outcome, totals retained across sections and later failure | PASS |
| C5a async/error | Busy through create then refresh, duplicate prevention, token loss, Error/non-Error retry, refresh failure versus session-expiry status precedence | PASS |
| C5a row commands | Correct rerun/delete IDs, per-row busy, list-loading hides actions, ordered refresh, only target removed, errors/token loss retain rows | PASS |
| C2b monitor | Active statuses poll at15s, cancelling/terminal do not, tracked completion versus replacement ID, silent versus manual errors | PASS |
| C2b lifecycle | Auth/token loss freezes polling, explicit recovery, hidden-tab skip, visible single-flight refresh, pending call dedup and unmount cleanup | PASS |
| C2b result | Persisted null/array/object/wrong field shapes diagnostic fallback; portal expiry distinct from GAIA auth; recent items reversed/max8 without mutation | PASS |
| C4 monitor/lifecycle | Exact token, loading/order/status/deletion gating,15s polling, real ApiError401/403 classifier, hidden/visible single-flight, pending call/unmount cleanup | PASS |
| C4 commands/results | Ordered rerun/refresh and target delete, failure/retry/token guards, diagnostic JSON validation, progress/counters/nullable rows and latest/stored result precedence | PASS |

Real workspace, public React actions/effects and existing payload helper run;
API/auth/protected/modal boundary mocks explicitly export exercised functions.
No missing-export error masquerades as a business failure. C4 runs actual
`ApiError`/`isAuthError` from API core, with its corrected async mock-factory
import; the source's original precollection hoisting failure remains documented.
C2b and C4 persisted result
fixtures match the public backend job schema (`result_json: dict | list | None`,
status string); invalid numeric fields test the actual guard on unknown JSON,
not a fabricated parser output. A list replacing a previously active job ID is
valid list evolution, unlike the impossible command response IDs rejected in
Integration2. Public controls, timers and visibility events model lifecycle;
no private closures, setter captures, direct disabled-handler invocation,
runtime exports, ignore/config/baseline edits or synthetic coverage bypass.

## Coverage and preservation baseline

Fresh before coverage on integration reproduces Integration2 with all eight
actual specs:155 PASS/zero skip, coverage command exit1 for unchanged full-file
100% thresholds. Raw counters678/857 statements,640/929 branch arms,
172/251 functions,609/748 lines. Coverage gate **FAIL**, not compliant.
Before evidence `/tmp/gaia-capacitas-integration3-before-coverage/coverage-final.json`
and `/tmp/gaia-capacitas-integration3-before-coverage.log`.
Current combined C5a+C2b checkpoint executes all ten integrated specs together:
210 PASS, zero skip, but coverage command exit1/100% gate FAIL. Raw counters
795/857 statements (92.76%),720/929 arms (77.50%),227/251 functions (90.43%),
700/748 lines (93.58%). Gains from before:+117 statements,+80 arms,+55 functions,
+91 lines. Remaining62 statements,209 arms,24 functions,48 lines. Evidence
`/tmp/gaia-capacitas-integration3-c2b-coverage/coverage-final.json`, corresponding
`.log`, read-only `/tmp/gaia-capacitas-integration3-interim-counters.json`.
Istanbul `getLineCoverage` produces unique-line counters. This is actual combined
execution, not added independent percentages. C4 later requires another genuine
cumulative measurement. Runtime refactor remains held.

Final genuine combined C4 run executes all eleven integrated specs:
247 PASS/zero skip, coverage gate **FAIL100**, exit1. Whole-file counters:

| Counter | Before | Final | Covered delta | Final % |
|---|---:|---:|---:|---:|
| Statements | 678/857 | 846/857 | +168 | 98.71 |
| Branch arms | 640/929 | 810/929 | +170 | 87.19 |
| Functions | 172/251 | 244/251 | +72 | 97.21 |
| Lines | 609/748 | 743/748 | +134 | 99.33 |

Remaining11 statements,119 branch arms,7 functions,5 lines. High statement
coverage does not substitute for missing branch coverage or full-file100%.
No defensive branch was fabricated or removed. Source C4 keeps its2056 fallback
after Array.isArray, rather than falsifying a payload to hit it. Final evidence
`/tmp/gaia-capacitas-integration3-final-coverage/coverage-final.json`, log
`/tmp/gaia-capacitas-integration3-final-coverage.log`, raw counters
`/tmp/gaia-capacitas-integration3-final-counters.json`. SHA256 before JSON:
`328964985a62d67cf7947efc9b4069ac26a7a99af03f23803e326466cfca225e`;
final JSON:`b3aef35485071fe9e045bc687d6f5e8fdc8b3ab6a3472ac56dbd3ef8fd3ded9f`.

Reproduce from integration frontend snapshot `b3b16c46` plus governance-only
concurrent commits (filter must not silently include later specs):

```bash
npm run test:unit -- 'tests/unit/campaign-capacitas-' --maxWorkers=1
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/gaia-capacitas-integration3-final-coverage
```

Runtime SHA256 remains
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`;
existing batch SHA256
`4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`;
baseline SHA256
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
Diff versus preflight is empty for runtime trees/config/tooling/Makefile and
frontend package/config files. Fresh scoped AST
`/tmp/gaia-capacitas-integration3-final-complexity.json` unchanged:
principal472 cognitive/416 cyclomatic/2631LOC/2nesting/1param;
file1099 cognitive/1174 cyclomatic/3109 effectiveLOC/251callables,
24error/20warning/44finding,31useState/2useEffect. All metric deltas0.

## Validation and limits

Source logs `/tmp/gaia-capacitas-integration3-{c5a,c2b}-source.log`.
Each integrated slice has corresponding `-integrated.log` and `-ratchet.log`;
command `make complexity-ratchet BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python`
must show baseline55a and empty findings before another integration.
Explicit test-inclusive temporary tsconfig
`/tmp/gaia-capacitas-integration3-test-tsconfig.json` avoids relying on the normal
project config that excludes tests. Integrated C5a explicit types/lint PASS;
Integrated C2b explicit types/lint also PASS.
`git diff --check` PASS.
Final explicit test-inclusive TS and scoped lint on all three new specs PASS,
logs `/tmp/gaia-capacitas-integration3-final-{types,lint}.log`. Existing Next16
deprecation notice is not a lint error. No repository config edit.

Dedicated Graphify frontend query `ElaborazioniCapacitasWorkspace` PASS/82nodes,
orientation only, log `/tmp/gaia-capacitas-integration3-graph-query.log`.
No runtime relationships changed requiring code refresh; documentation refresh
stays Coordinator-owned. No full-suite/build/E2E/live portal proof is claimed.
Individual source initial test-design failures remain documented, not erased.

Coordinator read-only global scan completed during this checkpoint, exit0:
1668files/20280callables,1938error/2749warning/4687findings. Its report
`files`/`callables` objects exactly match R3 integrated report: test-only
complexity delta0. Logs/artifacts `/tmp/gaia-capacitas-characterization-*`.
Global `complexity-check` remains FAIL30 (direct CLI exit1, make exit2);
Coordinator compared finding objects exactly to R3 independent check output,
unchanged. Historical divergence is not assigned to these test changes or
absorbed into baseline; authoritative per-change ratchet remains separate.

## Classification and stop

**NO_CHANGE — CHARACTERIZATION_ONLY**. No reduction/laundering claim.
All assigned sequential gates and genuine final coverage are complete.
Stop this ownership after C4; coverage gate remains FAIL, runtime held.
C5b requires separate authorization, not automatic
integration. Full-file100% policy, baseline provenance and GIS runtime-risk
hold remain unchanged; this checkpoint does not complete the global campaign.
