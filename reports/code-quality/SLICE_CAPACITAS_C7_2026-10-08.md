# Capacitas C7 — Anomaly list and fraction resolution characterization

## Ownership and preflight

Coordinator expressly assigned this test-only responsibility after reserving
the worktree `GAIA-campaign-20261008-c7-tests`, branch
`refactor/complexity-capacitas-anomalie-tests`. Starting clean HEAD
`39dbcc40273cfca699b576b8445ccd378e822a46`; merge-base main
`55a1b1d35911451e018b662c2acc450bf5994ea2`.

Owned files exclusively:

- `frontend/tests/unit/campaign-capacitas-anomalie.test.tsx`.
- This report `reports/code-quality/SLICE_CAPACITAS_C7_2026-10-08.md`.

All runtime, existing tests, shared helpers, configs, baseline, governance,
C0/C6 ownership, main and integration remain read-only. No runtime change,
new export, instrumentation, ignore, exclusion, threshold, baseline repair or
sync. Existing 19 Terreni batch tests are byte-identical and run alongside C7.
Checkpoint and complexity skills/project references applied; closure plan
`PLAN_CAPACITAS_COVERAGE_2026-10-08.md` reviewed before implementation.

## Responsibility and behavioral invariants

User action → state transition → API boundary → real rendered UI, restricted
to manual anomaly loading and fraction-resolution dialog.

- Anomalies are not automatically loaded on mount. Manual refresh uses the
  current token, disables duplicate refresh while pending, clears its prior
  error and replaces the list only after a successful response. Failed refresh
  preserves loaded rows. Missing token returns silently.
- Rendering preserves API order, count text, nullable name/date fallback,
  optional subalterno, invalid dates, candidate counts, first-choice selection
  and empty CCO/status arrays. Current plural literal `particellae` is
  characterized, not silently corrected as a feature.
- Changing a candidate dispatches exactly its `frazione_id`, selected
  anomaly UUID and `fetch_certificati: true`. No credential or details flag
  is injected. Success removes only that target from local rows, without
  another list request; final-item success restores the empty queue.
- False results retain the row. `error ?? "Errore sync"` preserves explicit
  empty-string semantics. Thrown Error displays its message; non-Error uses
  the existing generic error. Auth ApiError is treated as an ordinary Error
  in these two commands, with no invented monitor-style auth recovery.
- Token loss after mount/before resolution causes no dispatch/busy transition;
  explicit token restoration permits the next genuine user action.
- During pending resolution, close/synchronize are disabled, but radios are
  still enabled by current UI. Changing a radio does not change the already
  captured payload. On failed completion, the later selected radio remains
  and a subsequent retry dispatches it. On rejection, close is enabled and
  reopening resets errors/selection.

## Test matrix

| Behavior | Existing test | Added C7 evidence | Result |
|---|---|---|---|
| Manual initial/empty list and no resolve action | No direct workspace case | No autoload; exact token; empty queue | PASS |
| Single/multiple rows, API order, name/sub/date fallback | No direct case | Ordered rows, null/invalid/valid timestamps, current plural | PASS |
| Candidate content/default radio, CCO/status fallbacks | No direct case | Both candidates, exact counts/labels, first selection | PASS |
| Empty candidates cannot submit | No direct case | Disabled control and no API call | PASS |
| Exact selected resolve payload and target-only removal | No direct case | Two rows, choose second fraction, retain other; no refresh | PASS |
| Last-item success and success dialog reset | No direct case | Empty queue and hidden sync action | PASS |
| False result error/null/empty string | No direct case | Three public UI cases, preserve row/reopen | PASS |
| Resolution Error/non-Error/auth rejection and retry | No direct case | Three cases with current fallback and exact retry payload | PASS |
| List Error/non-Error/auth rejection and recovery | No direct case | Three cases, preserve old rows, clear on next pending request | PASS |
| Lost/restored token at list/resolve action | No direct case | No request while absent; selection retained; restored token sent | PASS |
| Deferred list busy/duplicate clicks | No direct case | Old rows retained until resolve, one dispatched request | PASS |
| Deferred resolve busy-close and candidate-change race | No direct case | Close remains disabled; captured first payload/later retry | PASS |
| Deferred rejection then close/reopen | No direct case | Error displayed, busy released, selection/error reset | PASS |
| Existing Terreni batch behavior | 19 existing cases | Unmodified suite rerun together | PASS |

C7 adds **20 meaningful cases**; existing 19 unchanged. Focused combined
execution **39 PASS / two files, zero skipped**, and smoke **18 PASS**.

## Mocking and reachability audit

Real `ElaborazioniCapacitasWorkspace`, domain components, React state/effects
and `usePolling` run unchanged. Mocks are limited to token getter, API
functions/error classifier, ProtectedPage boundary and unrelated settings
workspace modal. Real ApiError class is used; typed anomaly/resolve fixtures
match endpoint contracts. Empty job responses disable timers naturally;
this slice does not claim monitor polling coverage or authentication proof.

No entire-workspace mock, setter capture, private closure access, helper
export, context mutation, patched String/Array/Map, fake sparse parser output,
CSS-overlay background click, manually invoked disabled control handler or
impossible response used for coverage. Disabled button clicks use ordinary
DOM events and verify no request. Candidate changes while pending use an
actually enabled radio in the visible dialog. Deferred promises model API
timing; they are settled before cleanup.

## Test iterations and failures

First C7-only run: **19 PASS / 1 FAIL**, a test-selector error, not runtime
regression. Non-Error fallback has both notice title and description `Errore`,
so `findByText` was ambiguous. Corrected to `findAllByText` and explicitly
asserted two matching nodes for that case, one for the other cases. Final
combined run 39 PASS; no assertion removal, skipped case or hidden retry.
Original log `/tmp/capacitas-c7-first-tests.log` retained.

## Runtime metrics before / after

Fresh scoped AST scans before and after test addition:

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Principal cognitive | 472 | 472 | 0 |
| Principal cyclomatic | 416 | 416 | 0 |
| Principal callable LOC | 2631 | 2631 | 0 |
| Principal nesting / parameters | 2 / 1 | 2 / 1 | 0 / 0 |
| Aggregate cognitive | 1099 | 1099 | 0 |
| Aggregate cyclomatic | 1174 | 1174 | 0 |
| Effective file LOC | 3109 | 3109 | 0 |
| Callables | 251 | 251 | 0 |
| Errors / warnings / findings | 24 / 20 / 44 | 24 / 20 / 44 | 0 |
| useState / useEffect | 31 / 2 | 31 / 2 | 0 / 0 |

Callable/file metric objects and AST fingerprints compare byte-equivalent
after JSON serialization. No reduction claim: **NO_CHANGE / CHARACTERIZATION_ONLY**.

## Full-file coverage — gate remains FAIL

Existing V8 scope/thresholds 100 unchanged. Before: existing batch 19 only;
after: C7+batch 39. Actual JSON counters, not rounded percentages:

| Counter | Before covered/total | After covered/total | New outcomes | Percent before→after |
|---|---:|---:|---:|---:|
| Statements | 305/857 | 342/857 | +37 | 35.58→39.90 |
| Branch arms | 263/929 | 313/929 | +50 | 28.31→33.69 |
| Functions | 46/251 | 63/251 | +17 | 18.32→25.09 |
| Lines | 288/748 | 315/748 | +27 | 38.50→42.11 |

Both coverage commands exit 1 solely for existing full-file 100 thresholds.
All their tests pass; neither coverage gate is called PASS. Remaining runtime
refactoring is **BLOCKED_BY_FULL_FILE_COVERAGE**, even if C7 behavior is tested.

Owned UI band 3035–3228 (partition by statement/function start or branch line):
statements 0/36→36/36, functions 0/17→17/17, branch arms 2/56→51/56.
The five missing arms are the `prev ? ... : null` null outcomes at 3166,
3206, 3214, 3217, 3220. Closing is disabled during a pending resolution; no
legitimate action was found to null the live dialog before these updaters.
They are **not declared dead/unreachable universally** and are not forced via
state manipulation/unmount tricks. No runtime removal/exclusion authorized.
Other sections and defensive parser branches remain in the full denominator.

Coverage JSONs `/tmp/capacitas-c7-{before,after}-coverage/coverage-final.json`;
logs `/tmp/capacitas-c7-{before,after}-coverage.log`. V8 source mappings and
raw missing branch keys were inspected directly; no new censoring/ignore.
Last mapped statement reaches line 3268 of 3270 in both reports, not a censored
early tail. Denominators 857/929/251 remain exactly unchanged.

## Commands and validation

From `frontend/`:

```bash
npm run test:unit -- tests/unit/campaign-capacitas-anomalie.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=1
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-batch.test.tsx \
  --maxWorkers=1 --coverage.reportsDirectory=/tmp/capacitas-c7-before-coverage
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-anomalie.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/capacitas-c7-after-coverage
npm run typecheck
npm test
node_modules/.bin/eslint tests/unit/campaign-capacitas-anomalie.test.tsx
```

From repository root:

```bash
backend/.venv/bin/python tools/code_quality/complexity.py report \
  frontend/src/components/elaborazioni/capacitas-workspace.tsx \
  --json /tmp/capacitas-c7-after-complexity.json \
  --markdown /tmp/capacitas-c7-after-complexity.md
make complexity-ratchet BASE_REF=main
git diff --check
```

Typecheck PASS; smoke 18 PASS; new test ESLint exit 0 / zero diagnostics;
diff check PASS. Ratchet **PASS, zero findings**, authoritative main55a.
Log `/tmp/capacitas-c7-ratchet.log`; no baseline update/repair.
Focused/coverage logs `/tmp/capacitas-c7-focused-tests.log`, before/after
coverage logs; `/tmp/capacitas-c7-{typecheck,smoke,eslint-final}.log` contain
the other gates. Metrics `/tmp/capacitas-c7-{before,after}-complexity.json`.
No full suite/build/E2E duplicate executed. Graphify orientation attempted
through dedicated frontend query, but fresh worktree has no local graph:
Make exits 2 with a missing-graph error, recorded `/tmp/capacitas-c7-graphify-query.log`.
Test-only change does not alter component/service relationships; no graph
regeneration/API extraction necessary and no graph-success claim.

## Integrity, commit and residual risks

Runtime SHA256 remains
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`;
batch suite SHA256 remains
`4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`.
Runtime/batch/baseline/V8-config Git-object hashes compare identical in
`/tmp/capacitas-c7-protected-{before,after}.hash`. Runtime/existing tests and
shared/config diff empty; only the two exclusively owned files added.

Authorized coherent test-only source commit will follow focused gate PASS
and report completion. No integration or governance edit. Resolve exact SHA
using `git log -1 --format=%H -- reports/code-quality/SLICE_CAPACITAS_C7_2026-10-08.md`.

Partial whole-file coverage remains substantial; browser accessibility,
external providers and real stack auth not certified by unit boundary mocks.
The existing anomaly commands' generic auth handling and current plural text
are preserved, not production fixes. Five modal defensive null arms remain
explicit; no claim to have solved all race interleavings.

Stop READY_FOR_REVIEW after this test-only unit. Coordinator may integrate
characterization independently, but cannot authorize runtime complexity
refactoring until combined closure evidence meets policy or an explicitly
separate defensive-provenance decision is made. Next responsibility requires
new ownership; no C0/C6/other monitor or parser work is started here.
