# Capacitas C0 — Credential and Shell Characterization

## Ownership / baseline

Coordinator authorization registry `45e20c3f`; dedicated worktree
`/home/cbo/CursorProjects/GAIA-campaign-20261008-c0-tests`, branch
`refactor/complexity-capacitas-credentials-tests`.
Clean preflight HEAD `39dbcc40273cfca699b576b8445ccd378e822a46`; authoritative
merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Owned files only:

- `frontend/tests/unit/campaign-capacitas-credentials.test.tsx`
- `reports/code-quality/SLICE_CAPACITAS_C0_2026-10-08.md`

Plan reference `reports/code-quality/PLAN_CAPACITAS_COVERAGE_2026-10-08.md`.
Runtime, existing tests, shared hooks/components/API, config, governance,
baseline, thresholds and exclusions remained read-only. No C6/C7 overlap.

## Behavioral invariants

Real workspace and real `usePolling` execute. Only API lists/auth getter/error
classifier, ProtectedPage boundary and child settings modal are doubled.
No private closures, fabricated React state, new exports, ignores or runtime
instrumentation. All credentials use complete typed `CapacitasCredential`
fixtures; endpoint mocks return arrays, not undefined success responses.

- Four job forms default to the sole configured credential, even if inactive;
  activity affects the pool count, not option filtering or singleton selection.
- Zero/multiple credentials keep backend delegation until manually selected;
  inactive entries remain selectable. Harvest credential is a separate form
  and is not auto-selected by this credential-loading effect.
- Each job form owns its selection; navigation does not reset another form.
- Credential loading runs **only on mount**. Section changes, settings close
  and `initialSection` changes do not refresh it. There is no credential-refresh
  button/callback; tests do not invent one.
- `initialSection` rerender selects the new panel without discarding form state.
- Embedded workspace bypasses ProtectedPage; non-embedded passes module
  `catasto`, breadcrumb/title/description unchanged. Boundary prop verification
  is not an authentication/authorization implementation test.
- Settings open/close invokes the real parent state/controller and child
  callback contract, leaving workspace content and manual selection intact.
  The mocked child is not claimed as live settings content verification.
- Credential errors share Terreni's error state. A credential failure after
  monitor completion is visible; a later successful Terreni list clears an
  earlier failure. This observed ordering is characterized, not fixed.

The delayed credential-preservation case uses **React StrictMode's genuine
development effect replay**: first response populates real select options,
user chooses valid entries, second deferred response arrives and preserves all
four selections. This is not a production user-refresh scenario and does not
manufacture non-existent options or invoke internal callbacks.

## Characterization matrix

| Behavior | Existing coverage | Missing / added | Result |
| --- | --- | --- | --- |
| Empty pool and backend default in all four job forms | Terreni-only initial loading | Dedicated cross-form option/value checks | PASS |
| Sole active/inactive account and pool count | One active Terreni account | Both flags across four forms; harvest distinction | PASS |
| Multiple mixed/all-active/all-inactive accounts | Absent | Three pool matrices, options/order/enabled state/default | PASS |
| Independent selections and return to backend delegation | Terreni payload only | Four manual choices preserved through navigation | PASS |
| Delayed singleton after panel navigation | Absent | Deferred initial response, all forms updated | PASS |
| Deferred effect-replay preserves selections | Absent | Real StrictMode plus deferred second response | PASS |
| Credential Error/non-Error and shared error ordering | Absent | Two rejection cases plus delayed Terreni clear | PASS |
| Missing GAIA token | Existing batch dispatch guard | Mount blocks every list endpoint | PASS |
| Six distinct navigable panels | Absent | Actual panel content and absence of inactive panels | PASS |
| Changed `initialSection`, selection retention, no refetch | Absent | Rerender plus actual selected option | PASS |
| Embedded/non-embedded shell and settings open/close | Existing child unit tests only | Both parent contracts; selection/content retained | PASS |

17 new cases. Existing19 `campaign-capacitas-batch.test.tsx` cases are unchanged.
Combined focused suite: **36 PASS, 2 files, no skips**, exit0.

## Changes / metrics before, after, delta

New test file only; runtime not refactored. Fresh scoped AST report
`/tmp/capacitas-c0-complexity.json` matches `/tmp/p2-capacitas-before.json`
exactly for both `files` and `callables` objects.

| Runtime metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Main cognitive | 472 | 472 | 0 |
| Main cyclomatic | 416 | 416 | 0 |
| Main callable LOC / nesting / params | 2631 / 2 / 1 | 2631 / 2 / 1 | 0 |
| File effective LOC / callables | 3109 / 251 | 3109 / 251 | 0 |
| File cognitive sum / cyclomatic sum | 1099 / 1174 | 1099 / 1174 | 0 |
| File errors / warnings | 24 / 20 | 24 / 20 | 0 |

Classification: **NO_CHANGE / CHARACTERIZATION_ONLY**, not `IMPROVED`.
Nothing moved or transferred; largest callable remains cognitive472.

## Full-file coverage — expected gate FAIL

Fresh V8 baseline rerun uses existing19 batch tests on this exact checkout.
All three coverage runs include the **entire** Capacitas workspace with the
existing include mechanism, provider and100% thresholds unchanged.

| Counter | Before: batch19 | C0 alone17 | After: batch19+C0=36 | Incremental covered |
| --- | ---: | ---: | ---: | ---: |
| Statements | 305/857 (35.58%) | 229/857 (26.72%) | 343/857 (40.02%) | +38 |
| Branch arms | 263/929 (28.31%) | 179/929 (19.26%) | 313/929 (33.69%) | +50 |
| Functions | 46/251 (18.32%) | 33/251 (13.14%) | 63/251 (25.09%) | +17 |
| Lines | 288/748 (38.50%) | 219/748 (29.27%) | 321/748 (42.91%) | +33 |

After missing: **514 statements, 616 branch arms, 188 functions, 427 lines**.
Every full-file coverage invocation exits1 for the100% thresholds, while its
tests pass. This is not coverage compliance or permission to refactor runtime.
Other sections and defensive arms in the coverage plan remain unclosed.

The specifically assigned `loadCredentials` region722–752 changes from
13/15→15/15 statements,13/20→20/20 branch arms and5/5→5/5 functions.
This local region100% is **not** substituted for the full-file failure.

Coverage evidence SHA256:

- Before `/tmp/capacitas-c0-before-coverage/coverage-final.json`:
  `68ba2897f6fc66819046b293699ac22f1ac968e2fd43310637273a380c8a74de`.
- C0-only `/tmp/capacitas-c0-only-coverage/coverage-final.json`:
  `2e24f9ea5ec3b541f24ff169423736aaee46dcbbe0cde4a96725cf3ab481c577`.
- Cumulative `/tmp/capacitas-c0-after-coverage/coverage-final.json`:
  `4a09fda52206b71525631c964c89207b9f307bdc88c6a47fee18aa8bd5640663`.

## Tests / reproducible commands

From the dedicated frontend directory, bounded logs under `/tmp/capacitas-c0-*`:

```bash
npm run test:unit -- tests/unit/campaign-capacitas-credentials.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=2

VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-credentials.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=2 \
  --coverage.reportsDirectory=/tmp/capacitas-c0-after-coverage

npm run typecheck
npm test
npm run lint -- --file tests/unit/campaign-capacitas-credentials.test.tsx
node_modules/.bin/tsc -p /tmp/capacitas-c0-test-tsconfig.json --noEmit
```

| Verification | Result | Evidence |
| --- | --- | --- |
| Focused C0+batch unit suite | 36 PASS, exit0 | `characterization.log` |
| C0-only coverage tests | 17 PASS; coverage gate FAIL exit1 | `only-coverage.log` |
| Baseline coverage tests | 19 PASS; coverage gate FAIL exit1 | `before-coverage.log` |
| Combined coverage tests | 36 PASS; coverage gate FAIL exit1 | `after-coverage.log` |
| Repository frontend typecheck | PASS exit0 | `typecheck.log` |
| Supplemental new-test typecheck | PASS exit0 | `test-typecheck-final.log` |
| Existing source smoke | 18 PASS exit0 | `smoke.log` |
| New-test scoped ESLint | PASS exit0 | `lint-final.log` |
| Authoritative `make complexity-ratchet BASE_REF=main` | PASS,0 findings, exit0 | `ratchet.log` |
| Fresh runtime scoped AST | Identical metrics/file/callable structures | `complexity.json/.md/.log` |

The repository TypeScript configuration excludes tests. Supplemental temporary
config extends it and includes this new test explicitly, with absolute Vitest
and jest-dom type locations; no repository configuration was modified.
No full suites, build, E2E or unrelated tests were run.

## Initial failures / review

Initial new-test run13/16 PASS,3 failures retained in `focused.log`:
two error expectations incorrectly assumed immediate credential rejection could
not be cleared by concurrently successful Terreni loading; navigation absence
incorrectly matched the Certificati description also present in the nav.
Corrected only this new spec: deferred error ordering and panel-title selector,
then added a separate regression-sensitive shared-error ordering case.
Assertions keep their behavioral intent; no production change or weakened
timeout/skip. The intermediate16-case PASS is in `focused-final.log`; the final
17+19-case result is in `characterization.log` and coverage logs.

First supplemental TypeScript attempt failed TS2688 because a `/tmp` config
resolved inherited `vitest/globals` relative to `/tmp`. Only its temporary type
paths were corrected; the final test-specific check passes. Original attempt
retained in `test-typecheck.log`. ESLint emits the existing Next16 deprecation
notice but no lint warnings/errors.

Review confirms only API/auth/protected/modal boundary doubles, real React
effects/polling, actual valid DOM choices and distinct assertions. Baseline,
runtime and existing19-test file hashes remain unchanged. No Graphify code
refresh required: no runtime responsibility/dependency boundary changes.

## Commit / remaining risks / next slice

Authorized source commit message:
`test(capacitas): characterize credential selection and workspace shell`.
Commit includes only the two owned files; actual SHA returned to Coordinator.
Status **READY_FOR_REVIEW**, not integrated. No governance/status edit by agent.

Full-file100% remains unmet; native modal content and ProtectedPage auth are
outside the asserted boundary contract. StrictMode preservation represents
development replay, not a newly added refresh feature. Shared Terreni error
clearing is existing behavior, not a resolved bug.

Recommended next authorized slice: C1 Terreni monitor/report/actions, preserving
this characterization and cumulative reporting; C6/C7 can proceed in their
non-overlapping owned specs. Runtime refactor and defensive-arm reconciliation
still require separate ownership/approval. Stop after this test-only commit.
