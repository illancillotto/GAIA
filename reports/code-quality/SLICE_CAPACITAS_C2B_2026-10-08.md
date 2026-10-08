# C2b — Capacitas Particelle Monitor Slice Report

## Ownership / baseline / target

Coordinator/root owns this report and new
`frontend/tests/unit/campaign-capacitas-particelle-monitor.test.tsx` only.
Registrya283cf27, worktree`GAIA-campaign-20261008-c2b-tests`, branch
`refactor/complexity-capacitas-particelle-monitor-tests`, HEAD39dbcc40,
merge-base main55a1b1d35911451e018b662c2acc450bf5994ea2. Dependency links
reuse existing installations; main dirty concurrent work untouched.
Runtime SHA256before/after
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`.
Target is monitor characterization, not authorized runtime refactoring.

## Behavioral invariants / characterization matrix

Real workspace and real usePolling; only public API/auth boundaries mocked.
Visibility getter and fake timers exercise actual effect dependencies/cleanup.
ProtectedPage/modal doubles are unrelated boundaries, not authorization proof.
Result JSON is declared dict/list/null by API, permitting malformed field
types for shape guards; accepted result fixtures retain all required display
fields. No private state, callback access, runtime export or impossible success
ID response. Mutating command handlers are outside this slice and not invoked.

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| pending/processing/queued_resume polling interval and terminal stop | No Particelle lifecycle tests | Yes | Three real timer cases14999+1ms and later45s | PASS |
| cancelling/cancelled/succeeded do not poll | None direct | Yes | Three status cases, cancelling Stop remains disabled | PASS |
| Manual active→succeeded/errors/failed completion notice | None direct | Yes | Three exact response transitions | PASS |
| Different response ID not previous tracked completion | None direct | Yes | Public list changes31→32, no false notice | PASS |
| Error/non-Error initial load and refresh recovery | None direct | Yes | Two failures, two visible notices, retry recovery | PASS |
| Silent failure/success retain manual error until explicit refresh | None direct | Yes | Timer and manual-error interleaving, row retention | PASS |
| Auth failures stop polling and recover on explicit load | None direct | Yes | Error and status401 recognized by classifier | PASS |
| Missing token at mount or later poll | Batch only Terreni coverage | Yes | No API dispatch, restore exact token, re-enable polling | PASS |
| Hidden visibility, single-flight deferred poll, unmount cleanup | None direct | Yes | Hidden ticks skipped, visible event dispatch, no overlap or post-unmount call | PASS |
| Shape guard null/array/object/wrong numeric fields | None direct | Yes | Six unknown result cases fall back to job diagnostic | PASS |
| Portal expiry warning distinct from GAIA auth | None direct | Yes | NOSessione, case-insensitive phrase and ordinary failure | PASS |
| Recent item order/max8 and immutable response | None direct | Yes | Ten API items, reversed bounded rows, execution metadata | PASS |

28new cases,19existing unchanged. `loadParticelleJobs`806–850 measured
31/31statements25/25brancharms4/4functions. No full-file100% inference from
that scoped band; presentation/status branches outside the matrix remain.

## Changes / metrics before-after / delta

Runtime unchanged, zero complexity delta. Local AST report
`/tmp/capacitas-c2b-complexity.json`/`.md`:principal472cognitive,
416cyclomatic,2631LOC,nesting2,params1;file3109LOC251callables,
1099cognitive/1174cyclomatic sums,useState31/useEffect2,24error20warning.
Existing before AST identical via unchanged source hash. No laundering,
baseline/tooling/config/scope/threshold edits or exceptions.

## Tests / coverage / ratchet

```bash
cd frontend
npm run test:unit -- tests/unit/campaign-capacitas-particelle-monitor.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=2
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-particelle-monitor.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=2 \
  --coverage.reportsDirectory=/tmp/capacitas-c2b-after
./node_modules/.bin/tsc -p /tmp/capacitas-c2b-test-tsconfig.json --noEmit
npm run typecheck
./node_modules/.bin/eslint tests/unit/campaign-capacitas-particelle-monitor.test.tsx
npm test
cd ..
make complexity-ratchet BASE_REF=main
```

Focused/confirmed47PASS0skip; smoke18PASS, runtime and explicit test-only
TypeScriptPASS, scopedESLint0errors0warnings, diffcheckPASS. Temporary test
tsconfig extends project with absolute Vitest/jest-dom types because normal
tsconfig excludes tests; no committed config change. RatchetPASSexit0/findings[]
in `/tmp/capacitas-c2b-ratchet.log`. No full suite/build/E2E per micro-slice.

Before batch-only coverage reproduced305/857statements263/929arms46/251
functions288/748lines,19testsPASS/coverageFAIL100. Actual combined after365/857
statements368/929arms61/251functions341/748lines, percentages42.59/39.61/
24.30/45.58; **full-file gateFAIL exit1** on all four100thresholds. Deltas
+60statements/+105arms/+15functions/+53lines. No sum of independent percent.
Logs`/tmp/capacitas-c2b-before.log`, `...coverage.log`, `...confirm.log`.

All attempts retained:initial46/47PASS failed due to assumed display phrase
`Pausa900ms`; actual metadata is `Fascia serale · 900ms · x2 · 2w`, corrected
test assertion only. First supplemental typecheck failed because parameterized
fixture tuples included an unused display label, corrected tuples; ESLint
first had unused waitFor warning, removed unused import. Confirmed47PASS and
explicit typecheck/lintPASS, no runtime fix or weakened behavior assertion.

## Classification / files / commit

**NO_CHANGE — CHARACTERIZATION_ONLY**. Two owned files only; source coherent
test-only commit authorized, exact SHA recorded after commit. Independent
review/integration required, no self-merge. Principal472 unchanged.

## Residual risks / next slice

Full-file coverage incomplete. Runtime refactoring remains held by policy and
pending GIS decision; defensive branch provenance does not grant exemptions.
No proof of complete real authorization, portal network behavior, or every
possible async interleaving. Next separately owned action: merge reviewed
test-only suites and derive remaining coverage ledger from actual cumulative
run, not extrapolation. Stop here; do not broaden commands or other monitors.
