# Capacitas C5B — Complexity Slice Report

## Ownership

Coordinator registry authorization `17e6047d`: **TEST-ONLY**, inCASS monitor,
polling, queue visibility and result presentation. C5A commands and C4 Storico
remain separate ownership. No runtime/config/tooling/shared-file authorization.

- Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261008-c5b-tests`.
- Branch: `refactor/complexity-capacitas-incass-monitor-tests`.
- Preflight HEAD: `39dbcc40273cfca699b576b8445ccd378e822a46`.
- Authoritative merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Owned files: `frontend/tests/unit/campaign-capacitas-incass-monitor.test.tsx`
  and this report only.

`git status --short` was clean; `git rev-parse HEAD`, `git merge-base HEAD main`,
`git diff` and runtime path history were checked before writing the spec. The
latest runtime-path commit is `31d1cec5b2dce890748fbf6223a342e37de1055b`.
This worktree does **not** contain C5A's source commit; coverage deltas below
are against a freshly rerun batch-only baseline, not C5A's combined figures.
No sibling spec is copied or integrated by this agent.

## Baseline and target callable

Runtime under characterization:
`frontend/src/components/elaborazioni/capacitas-workspace.tsx`.
Fresh before and after AST reports are `/tmp/capacitas-c5b-before.json` and
`/tmp/capacitas-c5b-after.json`; their complete `files` and `callables` objects
match exactly, also matching the authoritative runtime's earlier AST evidence.

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| ElaborazioniCapacitasWorkspace cognitive | 472 | 472 | 0 |
| Main callable cyclomatic | 416 | 416 | 0 |
| Main callable LOC | 2631 | 2631 | 0 |
| Main callable nesting | 2 | 2 | 0 |
| Main callable parameters | 1 | 1 | 0 |
| File effective LOC | 3109 | 3109 | 0 |
| File callable count | 251 | 251 | 0 |
| File cognitive sum | 1099 | 1099 | 0 |
| File cyclomatic sum | 1174 | 1174 | 0 |
| File useState | 31 | 31 | 0 |
| File useEffect | 2 | 2 | 0 |
| Error findings | 24 | 24 | 0 |
| Warning findings | 20 | 20 | 0 |

## Behavioral invariants

Tests mount the real workspace, real `usePolling` and real visibility/shape
helpers. Only API calls, GAIA token/auth-error classification, ProtectedPage and
the unrelated settings modal boundary are mocked. All jobs have positive,
unique IDs within each response and complete typed list-job contracts; result
and item fixtures follow real API types. Malformed result objects/arrays/null
are explicitly permitted by `result_json`, not manufactured private state.

- Initial and manual list reads use the existing token and `{ limit: 300 }`.
  Initial loading disables manual refresh; empty/terminal-only queues do not
  schedule automatic requests.
- `pending`, `processing`, `queued_resume` enable polling and disable deletion.
  Resume status displays its existing restart guidance. The three terminal
  statuses stop polling and permit deletion; commands are not invoked here.
- Exactly 100 listed jobs use 20 seconds, 101 use 45 seconds. Crossing either
  boundary replaces the real interval rather than retaining its previous rate.
- Hidden-document ticks do nothing; visible-tab events refetch immediately.
  Slow polling requests suppress later ticks and visibility refetches until
  they settle. Unmount removes timer/listener-driven requests, including after
  settlement of an already in-flight API promise; **no abort claim** is made.
- **Manual refresh is outside polling single-flight.** A deferred manual call
  overlaps a polling call; the late manual response overwrites the newer
  terminal response and can resume polling from older active rows. This is an
  existing race, deliberately characterized and not fixed in test-only work.
- Silent success updates rows without a completion message or loading screen.
  Manual refresh announces terminal transitions only for previously tracked
  active IDs, never a different ID. Silent non-auth failures retain rows and
  suppress errors; a previous explicit error persists through silent success
  until manual success clears it.
- Missing tokens and classified auth failures freeze automatic requests,
  retain any existing rows and show session guidance. Merely restoring a token
  does not resume timers; a successful manual refresh restores polling. The
  previous `Rientra in GAIA...` status message can remain after successful manual
  recovery, while its session error clears: preserved, not repaired.
- Collapsed queues prioritize `processing`/`queued_resume`, then preserve the
  remaining API order, including pending rows, capped at 15. Expanded queues
  preserve the original API order and expansion across refreshes. Re-collapsing
  restores prioritized ordering; exactly 15 jobs have no expand control.
- Rejected top-level result shapes show persisted job errors instead of
  counters. Accepted shapes show aggregate/payment values, optional-zero and
  nullable-display fallbacks, outcome tones and per-item errors. Valid results
  take precedence over `error_detail`.
- The backend list serializer retains at most **15** preview items and supplies
  `total_items`; the UI table displays at most **12**. The truncation test uses
  this real 15-item list contract, not an impossible oversized list preview,
  and preserves the existing text `Anteprima dei primi 15 soggetti su 20.`

## Characterization test matrix

The existing 19-case batch suite exercises Terreni, not these inCASS workspace
behaviors. Pure helper tests do not prove its monitor/UI integration.

| Behavior | Existing direct test | Missing before | Added in C5B | Result |
| --- | --- | --- | --- | --- |
| Empty initial list/limit/no timer | None | Workspace monitor contract | 1 | PASS |
| Deferred initial loading/manual-refresh disabled | None | First-response lifecycle | 1 | PASS |
| Active statuses, delete availability and resume note | None | Three real status integrations | 3 | PASS |
| Terminal statuses disable polling | None | Three terminal integrations | 3 | PASS |
| Exact 100/101 polling boundaries | None | Timing and total-list threshold | 2 | PASS |
| Live threshold rescheduling both directions | None | Hook dependency behavior | 1 | PASS |
| Hidden/visible lifecycle | None | Real document event/timer behavior | 1 | PASS |
| Slow request single-flight across tick/visibility | None | Real hook concurrency | 1 | PASS |
| Unmount with request outstanding | None | Timer/listener cleanup | 1 | PASS |
| Manual/poll overlap and late response ordering | None | Existing race semantics | 1 | PASS |
| Silent terminal transition/no message | None | Automatic terminal lifecycle | 1 | PASS |
| Manual tracked-ID terminal announcements | None | Success/error/failed terminal paths | 3 | PASS |
| Unrelated terminal ID does not announce | None | Reference-set matching | 1 | PASS |
| Initial Error/non-Error manual recovery | None | Explicit load failures | 2 | PASS |
| Silent Error/non-Error retry without error UI | None | Background failure policy | 2 | PASS |
| Manual error retained through silent recovery | None | Explicit/silent distinction | 1 | PASS |
| Missing token at mount and later login | None | Fail-closed/manual recovery | 1 | PASS |
| Token vanishes during polling | None | Stop/resume retaining rows | 1 | PASS |
| Initial and polling API auth expiry | None | Classified auth failure recovery | 2 | PASS |
| Collapsed/expanded ordering across refresh | Helper tests only | Actual UI ordering/selection | 1 | PASS |
| 15/16 expand-control boundary | Helper tests only | Actual control availability | 2 | PASS |
| Eight invalid top-level result shapes | None | Guard rejection and fallback UI | 8 | PASS |
| Invalid result without error detail | None | Safe row without result section | 1 | PASS |
| Empty valid success/processing result | None | Progress and optional-zero counters | 2 | PASS |
| Full aggregate and three item outcomes | None | Counters, statuses, nullables and precedence | 1 | PASS |
| Genuine 15-item preview/20-item total | None | UI cap and truncation message | 1 | PASS |

**45 new tests; 64 PASS** with the unchanged 19 batch cases. No skipped tests.
The first 44-case focused run passed completely; the added manual/poll race case
also passed on first execution. No runtime repair, failed-assertion weakening,
lint suppressions or test-only exports were needed.

## Changes

One domain-specific test file with typed fixtures, fake browser timers and
observable UI/API assertions. Fake timers advance real hook intervals; the hook
is never mocked. Deferred responses cover actual request boundaries and
ordering. No create/harvest/rerun/delete dispatch belongs to this spec.

## Tests and reproducible commands

Run npm/tsc commands from this worktree's `frontend/`, other commands from its
root. Complete logs are bounded local `/tmp` artifacts, not committed assets.

| Command | Result | Evidence |
| --- | --- | --- |
| `npm run test:unit -- tests/unit/campaign-capacitas-incass-monitor.test.tsx --maxWorkers=2` | Initial 44 PASS | `/tmp/capacitas-c5b-first-focused.log` |
| `npm run test:unit -- tests/unit/campaign-capacitas-incass-monitor.test.tsx tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=2` | Final 64 PASS | `/tmp/capacitas-c5b-characterization.log` |
| `npm test` | 18 smoke PASS, 0 skipped | `/tmp/capacitas-c5b-smoke.log` |
| `npm run typecheck` | PASS, exit 0 | `/tmp/capacitas-c5b-typecheck.log` |
| `node_modules/.bin/tsc -p /tmp/capacitas-c5b-test-tsconfig.json --noEmit` | Explicit new-spec typecheck PASS | `/tmp/capacitas-c5b-test-typecheck.log` |
| `npx next lint --file tests/unit/campaign-capacitas-incass-monitor.test.tsx` | PASS, no ESLint warnings/errors | `/tmp/capacitas-c5b-lint.log` |
| `make complexity-ratchet BASE_REF=main` | PASS, 0 findings | `/tmp/capacitas-c5b-ratchet.log` |

Runtime tsconfig excludes tests. Temporary explicit-test config extends the
absolute dedicated-worktree `frontend/tsconfig.json`, disables incremental
output, includes only this spec, sets `exclude: []`, and loads absolute
`vitest/globals` and `@testing-library/jest-dom` types from its node_modules.
No repository configuration changes are required.

Fresh before/after AST command, using `before` and then `after` respectively:

```sh
python3 tools/code_quality/complexity.py report \
  frontend/src/components/elaborazioni/capacitas-workspace.tsx \
  --json /tmp/capacitas-c5b-before.json --markdown /tmp/capacitas-c5b-before.md
python3 tools/code_quality/complexity.py report \
  frontend/src/components/elaborazioni/capacitas-workspace.tsx \
  --json /tmp/capacitas-c5b-after.json --markdown /tmp/capacitas-c5b-after.md
```

Both exit 0, report 251 callables and 44 findings (24 error, 20 warning).

## Coverage

Fresh full-file statement/branch/function/line measurements use the unchanged
existing include mechanism, with all four thresholds remaining **100%**:

```sh
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-batch.test.tsx \
  --maxWorkers=2 --coverage.reportsDirectory=/tmp/capacitas-c5b-before-coverage
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-incass-monitor.test.tsx \
  --maxWorkers=2 --coverage.reportsDirectory=/tmp/capacitas-c5b-only-coverage
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-incass-monitor.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=2 \
  --coverage.reportsDirectory=/tmp/capacitas-c5b-after-coverage
```

| Full-file counter | Batch-only before | C5B-only | Batch + C5B after | Covered delta | Percentage-point delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| Statements | 305/857 (35.58%) | 243/857 (28.35%) | 353/857 (41.19%) | +48 | +5.61 |
| Branch arms | 263/929 (28.31%) | 219/929 (23.57%) | 391/929 (42.08%) | +128 | +13.77 |
| Functions | 46/251 (18.32%) | 26/251 (10.35%) | 57/251 (22.70%) | +11 | +4.38 |
| Lines | 288/748 (38.50%) | 233/748 (31.14%) | 331/748 (44.25%) | +43 | +5.75 |

All three runs have tests PASS (19, 45, 64 respectively), but **exit 1:
coverage gate FAIL** on all four unchanged thresholds. This is coverage growth,
not full-file compliance. Counters derive from each `coverage-final.json`;
line coverage uses unique statement start lines with maximum hit per line.
Independent C5B-only counts must not be added to another suite's coverage.

The combined run covers the inCASS top-level guard at physical lines489–526:
3/3 statements and 10/10 V8 branch arms; its monitor at903–946: 31/31 statements
and 25/25 branch arms. Rendering band2748–2916 reaches 9/11 statements and
85/87 branch arms: the two missing statements invoke rerun/delete, and missing
arms at2817/2830 display their busy labels, deliberately owned by C5A.
These local bands are descriptive evidence, **not** a narrowed coverage gate.
The real polling hook is exercised, but its own file is not included in these
workspace full-file coverage counters.

## Ratchet and provenance

Authoritative gate `make complexity-ratchet BASE_REF=main`: PASS, baseline commit
`55a1b1d35911451e018b662c2acc450bf5994ea2`, no findings. It also includes campaign
changes already inherited in this branch's HEAD; C5B adds only the owned test
and report. The 30 global baseline divergences remain a separate provenance
problem, not attributed to or absorbed by this slice.

Runtime and original batch suite remain byte-identical, SHA256:

- Runtime: `d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`.
- Batch spec: `4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`.

No baseline update, threshold/exclusion/ignore changes, shared-file edits,
runtime relocation or artificial counter reduction occurred.

## Classification

**NO_CHANGE — CHARACTERIZATION_ONLY.** Real branch/test coverage gains with
zero runtime complexity delta. Not `IMPROVED`; no reorganization or complexity
laundering. The cognitive-472 runtime refactor remains
**BLOCKED_BY_FULL_FILE_COVERAGE**.

## Files changed and commit

Only the two exclusively owned files are included in the source commit:
`test(capacitas): characterize inCASS monitor lifecycle`.
Its exact SHA is returned to the Coordinator independently and can be recovered
with `git log -1 --format=%H -- frontend/tests/unit/campaign-capacitas-incass-monitor.test.tsx`.
No cherry-pick/integration is performed by this agent.

## Graphify

Orientation attempted via
`make graphify-frontend-query Q="Capacitas workspace inCASS monitor polling and result rendering"`:
exit 2, missing worktree-local `frontend/src/graphify-out/graph.json`, recorded
in `/tmp/capacitas-c5b-graphify.log`. Target respected; no raw-root Graphify
execution or credential disclosure. Runtime relationships/structure are
unchanged; this report is outside domain/platform docs corpora. No graph
regeneration is required or authorized for this test-only slice.

## Residual risks and recommended next slice

- Have Integration verify C5A+C5B+the existing batch suite together, calculating
  a real union from V8 output instead of summing independent counters.
- The observed manual/poll overlap and late-response overwrite need an explicit
  separate runtime decision if correction is desired; this slice does not fix
  races or conceal their characterization. Token recovery's retained status
  message is likewise unchanged.
- Top-level result guards do not validate each item; no malformed accepted
  item is fabricated to force a crash. Real backend transactions, authorization
  and external portals are outside API-boundary tests.
- Other workspace responsibilities and the coverage plan's defensive-branch
  ledger remain uncovered. Stop rather than forge impossible records or
  exclude branches. Further test-only work needs new ownership.
- Build, E2E and complete frontend/backend/worker suites are not executed by
  this focused test-only agent; final integration gates remain Coordinator-owned.

Stop after the source commit and `READY_FOR_REVIEW` handoff; no runtime refactor
is authorized by these partial full-file coverage results.
