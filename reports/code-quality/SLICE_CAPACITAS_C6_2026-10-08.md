# Capacitas C6 — Certificati characterization slice

## Ownership and preflight

Coordinator registry authorization integration `45e20c3f`. Dedicated worktree
`GAIA-campaign-20261008-c6-tests`, branch
`refactor/complexity-capacitas-certificati-tests`; initial clean HEAD
`39dbcc40273cfca699b576b8445ccd378e822a46`, merge-base main
`55a1b1d35911451e018b662c2acc450bf5994ea2`.
Own only the new Certificati spec and this report. Runtime, original tests,
shared files, config/tooling, baseline, thresholds and exclusions are read-only.
Read project/checkpoint skills, code-quality references and
`PLAN_CAPACITAS_COVERAGE_2026-10-08.md` before implementation. Scoped runtime
diff clean; recent runtime history `31d1cec5`, `073d3898`, `17526b29` unchanged.

## Baseline and target callable

Fresh targeted scanner before/after confirms exact equality of runtime
callable and file metric objects:

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Main cognitive | 472 | 472 | 0 |
| Main cyclomatic | 416 | 416 | 0 |
| Main callable LOC | 2631 | 2631 | 0 |
| Main nesting / parameters | 2 / 1 | 2 / 1 | 0 / 0 |
| File effective LOC | 3109 | 3109 | 0 |
| File callable count | 251 | 251 | 0 |
| File cognitive / cyclomatic sum | 1099 / 1174 | 1099 / 1174 | 0 / 0 |
| File useState / useEffect | 31 / 2 | 31 / 2 | 0 / 0 |
| Errors / warnings / findings | 24 / 20 / 44 | 24 / 20 / 44 | 0 / 0 / 0 |

Artifacts `/tmp/capacitas-c6-{before,after}-metrics.{json,md}`.
This test-only responsibility closes reachable Certificati behavior
characterization, not the extreme Capacitas complexity or whole-file coverage.

## Behavioral invariants

Render the true embedded workspace with `initialSection="certificati"`.
Only API, token/auth classifier, ProtectedPage and workspace-modal boundaries
are mocked. Real stat rendering, state transitions and `usePolling` execute.
No private closure invocation, exported runtime helper, synthetic React state,
polling mock, parser fabrication or whole-workspace double.

- Explicit command reads the current token; no token means no dispatch and
  no clearing of previous results. Token restoration allows the next command.
- Default credential is `null`, even with one loaded account; explicit
  selection maps its numeric ID. Limit/throttle are exact number conversions.
- Busy/result/error updates happen before awaiting the API; a disabled
  command does not dispatch a duplicate. Fields remain editable, but edits
  affect only a later command, not the already-dispatched payload.
- Result updates occur on settlement; positive remaining-empty count selects
  warning tone, zero default tone, refetched count success tone.
- Auth classifier takes precedence for both Error and non-Error failures;
  ordinary Error preserves its message, non-Error uses the existing fallback.
  Finally releases busy; a retry clears prior error before awaiting.
- Loss of token after dispatch does not cancel or rewrite the pending request.
  An independent active Terreni monitor continues real polling while re-fetch
  awaits and its timer/listener is cleaned on unmount.

## Characterization test matrix

| Behavior | Existing test | Missing before C6 | Added | Result |
|---|---|---|---|---|
| Default payload, successful result and default/success tones | No | Certificati command/results | Exact token/null credential/100/300 and DOM stat classes | PASS |
| One credential remains auto-selected until explicit selection | No | Credential input mapping | Real option selection, numeric7/23/zero throttle, warning count3 | PASS |
| Previous result clearing and request/input ordering | No | Second command deferred lifecycle | Result gone before settle; duplicate click ignored; edits sent next time only | PASS |
| Auth Error and auth non-Error | No | Re-fetch auth branches | Two deferred rejects plus restored-token retry | PASS |
| Ordinary Error and non-Error fallback | No | Ordinary failure branches | Two deferred rejects; error clears on pending retry and result settles | PASS |
| Token disappears before next command | No | Guard preserves old result | No second API call until restored token | PASS |
| Token absent at mount | Terreni loss only | Certificati no-token initialization/dispatch | All list/API calls absent; explicit restored-token command works | PASS |
| Token disappears while awaiting | No | No cancellation/revalidation contract | Original payload/token settles into result | PASS |
| Real monitor polling independent of re-fetch | Existing Terreni cleanup | Busy re-fetch does not pause monitor | Pending typed job, real15sec interval, unmount45sec/listener cleanup | PASS |

11 new cases (one four-case failure matrix), original 19 batch cases unchanged;
combined **30 PASS, zero skips**. Fixtures return valid API result shapes;
pending Terreni job satisfies its complete public TypeScript type. API mock
exports are explicit, so missing-export exceptions cannot impersonate failures.
ProtectedPage double does not certify real authorization or remote API behavior.

## Execution and corrected test construction

Fresh baseline run executes the unchanged 19 cases: **19 PASS**, but full-file
coverage100% gate **FAIL**, exit1. `/tmp/capacitas-c6-before.log`.
Initial new-spec run had **9 PASS / 2 FAIL** because expected tone classes used
incorrect opacity suffixes. Runtime inspection demonstrated real stat classes;
only new assertions were corrected to the actual output. No production failure
was repaired and the first run is not called PASS. Evidence
`/tmp/capacitas-c6-focused.log`.

Corrected focused run **30 PASS / two files**, exit0,
`/tmp/capacitas-c6-focused2.log`. Combined coverage run again executes
**30 PASS / zero skip**, but retains exit1 for the honest100% threshold failure;
`/tmp/capacitas-c6-after.log`. No threshold or include/exclude gate changed.

## Full-file coverage before / after / delta

V8 JSON counters directly inspected, same857 statements/929 branch arms/
251 functions/748 lines, not merely rounded aggregate percentages:

| Counter | Before | After | Covered delta | Before % | After % |
|---|---:|---:|---:|---:|---:|
| Statements | 305/857 | 343/857 | +38 | 35.58 | 40.02 |
| Branch arms | 263/929 | 285/929 | +22 | 28.31 | 30.67 |
| Functions | 46/251 | 55/251 | +9 | 18.32 | 21.91 |
| Lines | 288/748 | 321/748 | +33 | 38.50 | 42.91 |

Certificati source-line band2917–3034 alone:

| Counter | Before | After |
|---|---:|---:|
| Statements | 0/21 | 21/21 |
| Branch arms | 1/18 | 18/18 |
| Functions | 0/9 | 9/9 |
| Lines | 0/17 | 17/17 |

No missing Certificati statement or branch outcome remains in that band.
This **does not** establish complete file100%. Remaining whole-file gaps:
514 statements, 644 branch arms, 196 functions, 427 lines. Other sections and
the planning ledger's invariant/library-sensitive parser branches remain
unresolved. No test-only claim that such guards are reachable/dead is added.
Coverage artifacts `/tmp/capacitas-c6-{before,after}-coverage/coverage-final.json`;
exact counters/missing locations `/tmp/capacitas-c6-coverage-counters.json`.

Commands from frontend, unchanged include mechanism and all four100% thresholds:

```bash
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-batch.test.tsx \
  --maxWorkers=1 --coverage.reportsDirectory=/tmp/capacitas-c6-before-coverage
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-batch.test.tsx \
  tests/unit/campaign-capacitas-certificati.test.tsx --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/capacitas-c6-after-coverage
```

## Validation and ratchet

- Focused two-spec Vitest: PASS30, `/tmp/capacitas-c6-focused2.log`.
- `npm run typecheck`: PASS, `/tmp/capacitas-c6-typecheck.log`.
- `npm test`: PASS18 smoke, `/tmp/capacitas-c6-smoke.log`.
- ESLint new spec: PASS, `/tmp/capacitas-c6-lint.log`.
- `git diff --check`: PASS.
- `make complexity-ratchet BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python`:
  PASS / zero findings / exit0, `/tmp/capacitas-c6-ratchet.log`.
- Full-file coverage gate: FAIL before and after, explicitly **not PASS**.

No full repository suite, build, E2E, integration or unrelated tests are run
by this test-only slice. No old suite result is reused as a new certification.
Graphify dedicated frontend query attempted for orientation but worktree graph
absent, `/tmp/capacitas-c6-graph-query.log`. No runtime boundaries/dependencies
changed; no root graph generation or shared/generated graph commit is needed.

## Preservation and classification

Runtime SHA256 stays
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`;
original batch-suite SHA256 stays
`4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`.
No existing runtime/test/config/baseline/exclusion is modified, no code moved.
Protected baseline/exceptions/scanner/Babel helper/frontend Vitest config and
package files independently compared byte-for-byte with HEAD and unchanged.

**NO_CHANGE — CHARACTERIZATION_ONLY.** Complexity metrics and runtime behavior
are identical. Test readiness improves, not complexity. Runtime refactoring
remains **BLOCKED_BY_FULL_FILE_COVERAGE**, despite C6 local band closure.

## Files changed / commit

- `frontend/tests/unit/campaign-capacitas-certificati.test.tsx`
- `reports/code-quality/SLICE_CAPACITAS_C6_2026-10-08.md`

Authorized test-only commit message:
`test(elaborazioni): characterize Capacitas certificati refetch`.
Resolve exact SHA using
`git log -1 --format=%H -- reports/code-quality/SLICE_CAPACITAS_C6_2026-10-08.md`.

## Residual risks and recommended next slice

API boundary characterization does not prove live portal behavior or real
authorization. C6's real polling test covers an active Terreni monitor while
Certificati awaits, not every other monitor's lifecycle. Deferred requests,
token changes and rejection paths are exercised through real observable actions,
not impossible state. New tests do not resolve whole-file parser/invariant gaps.

Stop after this test-only unit is ready for review. Another coverage-plan
responsibility needs distinct ownership/authorization; do not start a Capacitas
runtime refactor until full-file100% and all required gates are demonstrated.
