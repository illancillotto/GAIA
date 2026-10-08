# Capacitas C4 — Complexity Slice Report

## Ownership

Agent `integration_r3`, assigned C4 test-only Storico monitor/results by the
Coordinator, registry integration `08c97b74`. Exclusive ownership:

- `frontend/tests/unit/campaign-capacitas-storico-monitor.test.tsx`
- `reports/code-quality/SLICE_CAPACITAS_C4_2026-10-08.md`

Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261008-c4-tests`;
branch `refactor/complexity-capacitas-storico-monitor-tests`.
Preflight clean HEAD `39dbcc40273cfca699b576b8445ccd378e822a46`;
`git merge-base HEAD main` gives authoritative
`55a1b1d35911451e018b662c2acc450bf5994ea2`.
Successive campaign commits are inherited from the clean integration worktree,
not from the dirty main checkout. No concurrent changes were imported.

Runtime, existing batch tests, baseline, shared configuration and governance
are read-only. No integration, baseline repair, threshold change, exclusion,
ignore, export, private-state injection or runtime refactoring is authorized.
Plan: `reports/code-quality/PLAN_CAPACITAS_COVERAGE_2026-10-08.md`.

## Baseline and target callable

Fresh scoped AST scan before/after of
`frontend/src/components/elaborazioni/capacitas-workspace.tsx`:

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Main cognitive | 472 | 472 | 0 |
| Main cyclomatic | 416 | 416 | 0 |
| Main callable LOC | 2631 | 2631 | 0 |
| Main nesting / params | 2 / 1 | 2 / 1 | 0 |
| File effective LOC | 3109 | 3109 | 0 |
| File cognitive sum | 1099 | 1099 | 0 |
| File cyclomatic sum | 1174 | 1174 | 0 |
| Callables | 251 | 251 | 0 |
| Error / warning | 24 / 20 | 24 / 20 | 0 |
| useState / useEffect | 31 / 2 | 31 / 2 | 0 |

The `files` and `callables` objects in both fresh reports are deep-equal,
including fingerprints and locations. No complexity reduction is claimed.

## Behavioral invariants and characterization tests

Tests mount the real workspace with `embedded initialSection="storico"`.
The actual `usePolling` hook and real `ApiError`/`isAuthError` classifier execute.
Inputs are typed complete jobs/results or values legitimately permitted by
unknown JSON fields. API responses, token retrieval, ProtectedPage and the
unrelated settings modal are the only mocked module boundaries.
Fake timers, document visibility and deferred promises exercise asynchronous
behavior; no setters, private callbacks, source rewriting or workspace mock.
The ProtectedPage double does not prove production authorization.

| Behavior | Existing test | Missing before C4 | Added | Result |
| --- | --- | --- | --- | --- |
| Explicit loading to empty; busy refresh; exact token | Batch suite covers Terreni, not Storico | Storico contract | Deferred initial list | PASS |
| API job order, resume explanation, dates/errors, deletion disabled for active states | None direct | Storico monitor rendering | Ordered mixed-status jobs | PASS |
| Pending/processing/queued_resume to terminal; timer stops; no silent manual feedback | Real hook separately tested, no workspace proof | Storico lifecycle | Three status cases with real polling | PASS |
| Hidden ticks skipped; visible immediate refresh; single-flight pending list | None direct | Race-sensitive monitor | Visibility events and deferred list | PASS |
| Unmount cancels future timers/events even after dispatched list | Terreni-specific only | Storico cleanup | Unmount during pending tick | PASS |
| Missing initial/later token; retain rows; manual restoration | None direct | Auth state transitions | Token changes and real refresh | PASS |
| Authentic 401/403 stops monitor and explicit recovery | None direct | Error classifier path | Real ApiError status cases | PASS |
| Explicit Error/non-Error refresh failures; silent failures/success retain existing error | None direct | Refresh feedback distinction | Failure and subsequent refresh sequences | PASS |
| Rerun exact ID, selected busy state, create-before-list ordering | None direct | Rerun mutation | Two deferred requests and distinct jobs | PASS |
| Rerun Error/non-Error retains rows, no list on failure, retry clears error | None direct | Rerun failure paths | Two error cases and successful retry | PASS |
| Delete exact ID removes only target, releases busy, never lists again | None direct | Deletion mutation | Deferred delete and two distinct jobs | PASS |
| Delete Error/non-Error retains target; retry clears error | None direct | Deletion failures | Error cases and successful retry | PASS |
| Lost token before rerun/delete makes no request | None direct | Command guard | Both visible controls | PASS |
| Unknown result JSON null/array/object/wrong required counters rejected safely | None direct | Shape guard | Seven permitted JSON cases | PASS |
| Report totals, item order/status styles, nullable IDs, error/message/dash and empty-error precedence | None direct | Result rendering | Four distinct outcome rows | PASS |
| Explicit progress 0/42; computed 33/100/0; invalid payload fallback | None direct | Monitor progress | Six result/payload cases | PASS |
| First valid terminal API result stored; valid first job overrides; later invalid/empty preserves stored result | None direct | Result precedence across refreshes | Ordered five-stage response sequence | PASS |
| Deleting terminal job leaves stored report visible | None direct | Report state independent of rows | Delete sole terminal job | PASS |

37 new cases; the existing19 batch cases are untouched. Initial test execution
failed before collection because a hoisted API mock referenced an imported
classifier before initialization. The mock now dynamically imports the actual
API core inside its factory; no assertion/branch was removed. The subsequent
new-spec run passed37 cases, and the combined run passed56 cases.

## Changes

Only a new characterization spec and this report. No runtime responsibility,
dependency, state, React lifecycle, API payload or service boundary changes.
No redundant private-guard tests were manufactured to meet a number.

## Coverage

Fresh baseline runs the unchanged19 batch tests. Fresh after runs all56 cases
from batch+C4, with identical full-file coverage include and unchanged100%
thresholds. Both execute all selected tests successfully but exit1 for coverage.

| Raw full-file counter | Before | After | Added covered | Percentage before → after |
| --- | ---: | ---: | ---: | --- |
| Statements | 305 / 857 | 387 / 857 | 82 | 35.58% → 45.15% |
| Branch arms | 263 / 929 | 388 / 929 | 125 | 28.31% → 41.76% |
| Functions | 46 / 251 | 66 / 251 | 20 | 18.32% → 26.29% |
| Lines | 288 / 748 | 360 / 748 | 72 | 38.50% → 48.12% |

**Full-file coverage FAIL100 remains.** These are not all integrated campaign
specs and not repository coverage. Denominators unchanged; source last mapped
line3268 of3270. No tail censoring, adjusted gate, baseline update or coverage
exclusion. Runtime refactoring remains blocked pending full-file compliance.

The following source-band counters use statement start lines and the containing
branch line, retaining all branch arms rather than discarding unlocated arms:

| C4 responsibility / source lines | Statements before → after | Branch arms before → after |
| --- | --- | --- |
| History result guard474–487 | 0/3 → 3/3 | 0/9 → 9/9 |
| History loader852–904 | 19/36 → 36/36 | 11/32 → 32/32 |
| History rerun/delete1184–1217 | 0/25 → 25/25 | 0/8 → 8/8 |
| History monitor2030–2129 | 0/8 → 8/8 | 0/32 → 31/32 |
| History report2130–2213 | 0/2 → 2/2 | 0/23 → 23/23 |

Residual monitor arm is the `?? 0` fallback at2056 after `Array.isArray(items)`.
A normal immutable JSON array has numeric `length`, so this defensive arm is
not reached by the legitimate API fixture. No getter/proxy/mutation trick or
runtime defense removal was used. Other workspace sections remain outside C4.
These source-band figures are explanatory, not an alternative coverage gate.

## Tests and ratchet

| Command | Result | Evidence |
| --- | --- | --- |
| New spec `npm run test:unit -- tests/unit/campaign-capacitas-storico-monitor.test.tsx --maxWorkers=1` | 37 PASS | `/tmp/capacitas-c4-second-tests.log` |
| Batch+C4 `npm run test:unit -- tests/unit/campaign-capacitas-storico-monitor.test.tsx tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=1` | 56 PASS | `/tmp/capacitas-c4-focused-tests.log`; final repeat `/tmp/capacitas-c4-final-tests.log` |
| `npm run typecheck` | PASS | `/tmp/capacitas-c4-typecheck.log` |
| `npx tsc --noEmit -p /tmp/capacitas-c4-tsconfig.json` | PASS, includes new spec | `/tmp/capacitas-c4-spec-typecheck.log` |
| `npx eslint tests/unit/campaign-capacitas-storico-monitor.test.tsx` | PASS, no diagnostics | `/tmp/capacitas-c4-eslint.log`; final repeat `/tmp/capacitas-c4-final-eslint.log` |
| `npm test` | 18 PASS, zero skips | `/tmp/capacitas-c4-smoke.log` |
| `make complexity-ratchet BASE_REF=main` | PASS, findings[] | `/tmp/capacitas-c4-ratchet.log`; repeat including report `/tmp/capacitas-c4-final-ratchet.log` |
| `git diff --check` | PASS | Worktree check |

Repository tsconfig excludes tests. The extra temporary config extends it and
includes the owned spec, runtime and next-env with actual Vitest/jest-dom types;
no repository configuration change. Full build/E2E and repository suites are
integration gates, not run or claimed PASS by this test-only agent.

Coverage reproduction from the worktree frontend:

```bash
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- \
  tests/unit/campaign-capacitas-storico-monitor.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/capacitas-c4-after-coverage
```

Logs `/tmp/capacitas-c4-{before,after}-coverage.log`; raw JSON
`/tmp/capacitas-c4-{before,after}-coverage/coverage-final.json`.
AST reports `/tmp/capacitas-c4-{before,after}-complexity.json` and `.md`.
Initial collection failure `/tmp/capacitas-c4-first-tests.log` is retained.

## Integrity and Graphify

Protected runtime, existing batch spec, baseline and Vitest configuration hashes
are identical in `/tmp/capacitas-c4-protected-{before,after}.hash`.
Runtime SHA256 `d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`;
existing batch SHA256 `4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`.
No runtime or existing-test diff. Baseline, thresholds and scope unchanged.

Dedicated frontend Graphify query attempted but cannot run in this fresh
worktree: missing local `frontend/src/graphify-out/graph.json`, Make exit2,
log `/tmp/capacitas-c4-graphify-query.log`. Not reported as PASS. Test-only C4
changes no component/service dependencies; no graph refresh required by runtime
impact and no generated graph files committed. Docs refresh is Coordinator-owned.

## Classification

`NO_CHANGE / CHARACTERIZATION_ONLY`. Behavior characterization and measurable
coverage increase, not a complexity improvement or refactoring readiness waiver.

## Files changed and commit

Only the two owned files listed above. Coherent source commit message:
`test(capacitas): characterize Storico monitor and results`.
Exact resulting SHA is delivered to Coordinator after the commit; no integration
is performed by this agent. Status `READY_FOR_REVIEW` is a test-only review state,
not an authorization to edit the Capacitas runtime.

## Residual risks and recommended next slice

Coverage still lacks many unrelated workflow sections and a defensive monitor
branch. Mocked endpoint boundaries cannot certify live backend ordering, actual
authentication enforcement or external portal availability. Cleanup proves no
future monitor dispatch, not cancellation of a request already sent. Existing
full-file coverage blockers are preserved, not fixed by runtime changes.

Stop after this coherent slice. Coordinator may review/integrate it and rerun all
owned Capacitas specs together to establish a cumulative full-file denominator.
Any next test responsibility needs new exclusive ownership; runtime work remains
unauthorized until the applicable coverage and campaign checkpoint gates pass.
