# Capacitas C5A — Complexity Slice Report

## Ownership

Coordinator authorization: registry `47c8db71`. Test-only source slice; no
integration, governance, shared fixture, configuration or runtime ownership.

- Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261008-c5-tests`.
- Branch: `refactor/complexity-capacitas-incass-tests`.
- Preflight HEAD: `39dbcc40273cfca699b576b8445ccd378e822a46`.
- Authoritative merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Owned files: this report and
  `frontend/tests/unit/campaign-capacitas-incass.test.tsx` only.

Preflight `git status --short` was clean before creating the owned spec;
`git rev-parse HEAD` and `git merge-base HEAD main` established the snapshot
above. Existing runtime history was inspected without editing it. The existing
19-case batch spec remains byte-identical. The Coordinator explicitly authorized
a coherent C5A partial slice, not all of planned C5.

## Baseline and target callable

Runtime under characterization:
`frontend/src/components/elaborazioni/capacitas-workspace.tsx`.
Initial AST `/tmp/p2-capacitas-before.json` was checked against fresh
`/tmp/capacitas-c5-complexity.json`: both `files` and `callables` match exactly.
This slice does not reduce runtime complexity or claim to close its coverage.

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Main callable cognitive | 472 | 472 | 0 |
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

Tests render the real workspace, hooks, payload builders and job-visibility
helpers. Mocks are limited to API, GAIA token/auth-error classification,
ProtectedPage and the unrelated workspace modal boundary. Typed API fixtures
describe actual jobs, list jobs, credentials and harvest responses; no private
state access, hook mocks, source instrumentation or coverage suppression.

- Sync controls sanitize numeric text and preserve blank versus zero semantics.
  Exact payloads contain the existing optional credential, limit, throttle and
  five switches. The UI has **no subject-ID delimiter control** and does not
  submit `subject_ids`; the broader plan's assumption is not implemented here.
- Harvest controls live in Storico; returned totals remain visible there, but
  shared success/error status renders in Avvisi pagamenti. The tests preserve
  this existing cross-section behavior rather than correcting it.
- Creation and rerun await the monitor refresh. Deferred promises verify
  creation stays disabled while refresh is pending. Rerun disables its target
  during the API request, then list loading hides row commands until refresh
  completes; the tests assert these observable transitions, not private state.
- Deletion waits for API success, removes only the selected row, and does not
  reload the list. Other rows retain their own available command controls.
- Missing tokens prevent all four command dispatches. Error and non-Error
  rejections restore command availability, preserve other rows and permit retry.
- A normal refresh failure retains successful creation status alongside the
  monitor error. Auth expiry instead replaces that status with the existing
  monitor/session guidance; this proves UI behavior, not backend job execution.
- A later failed harvest retains the previous totals and previous success
  status alongside the new error. This is characterized, not fixed.

## Characterization test matrix

| Behavior | Existing test | Missing before | Added in C5A | Result |
| --- | --- | --- | --- | --- |
| Default/selected/sanitized sync payload and switches | Payload helper tests only | Real workspace dispatch | 4 cases, including blank/zero | PASS |
| Harvest default/selected/blank payload and zero/nonzero totals | None direct | UI-to-API integration and status location | 3 cases | PASS |
| Create busy state and create-before-refresh order | Batch suite covers Terreni, not inCASS | Sync and harvest commands | 2 deferred cases | PASS |
| Token disappears after mount | None for these commands | Sync and harvest guards | 2 cases | PASS |
| Creation Error/non-Error and retry | None direct | Both command paths | 4 cases | PASS |
| Successful create then refresh Error/non-Error | None direct | Status/error coexistence | 2 cases | PASS |
| Successful create then refresh auth expiry | None direct | Status replacement and monitor guidance | 1 case | PASS |
| Previous harvest totals survive later failure | None direct | Existing retention behavior | 1 case | PASS |
| Rerun target row, deferred refresh hides commands | None direct | Target selection and ordering | 1 case | PASS |
| Delete selected row only after API success | None direct | No-refresh row removal | 1 case | PASS |
| Rerun/delete Error/non-Error and retry | None direct | Row retention and recovery | 4 cases | PASS |
| Missing-token rerun/delete guards | None direct | No API dispatch | 2 cases | PASS |
| Polling timing/visibility/unmount, queue and detailed result guards | C5B not assigned | Remains missing here | Not added | NOT RUN / RESIDUAL |

Total: **27 new meaningful cases**; **46 PASS** together with the untouched
19-case batch suite. No skipped focused tests.

## Changes

Added a domain-specific inCASS spec, using direct labels, exact API payloads,
observable status/rows and deferred request boundaries instead of snapshots.
No runtime extraction or behavior change. List-job fixtures explicitly follow
the list contract without unused discarded properties or lint suppression.

## Tests and reproducible commands

Commands below run from the dedicated worktree (`cd frontend` for npm/tsc).
Logs and coverage artifacts are local `/tmp` evidence, not versioned assets.

| Command | Result | Evidence |
| --- | --- | --- |
| `npm run test:unit -- tests/unit/campaign-capacitas-incass.test.tsx tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=2` | 46 PASS | `/tmp/capacitas-c5-characterization.log` |
| `npm test` | 18 smoke PASS, 0 skipped | `/tmp/capacitas-c5-smoke.log` |
| `npm run typecheck` | PASS, exit 0 | `/tmp/capacitas-c5-typecheck.log` |
| `node_modules/.bin/tsc -p /tmp/capacitas-c5-test-tsconfig.json --noEmit` | Owned-test typecheck PASS, exit 0 | `/tmp/capacitas-c5-test-typecheck.log` |
| `npx next lint --file tests/unit/campaign-capacitas-incass.test.tsx` | PASS, no ESLint warnings/errors | `/tmp/capacitas-c5-lint.log` |
| `make complexity-ratchet BASE_REF=main` | PASS, 0 findings; authoritative baseline commit unchanged | `/tmp/capacitas-c5-ratchet.log` |
| `python3 tools/code_quality/complexity.py report frontend/src/components/elaborazioni/capacitas-workspace.tsx --json /tmp/capacitas-c5-complexity.json --markdown /tmp/capacitas-c5-complexity.md` | Fresh scoped AST, unchanged | `/tmp/capacitas-c5-complexity.log` |

Runtime tsconfig excludes tests; the separate test config extends the dedicated
worktree's `frontend/tsconfig.json`, sets `incremental: false`, includes only the
owned absolute spec path, sets `exclude: []`, and resolves absolute types for
`vitest/globals` and `@testing-library/jest-dom` from that worktree's node_modules.
It is temporary; repository configuration is unchanged.

Initial 25-case run: **23 PASS / 2 FAIL**, recorded in
`/tmp/capacitas-c5-focused.log`. Both failures were newly written harvest-error
tests querying immediately after navigation inside outer async `act`, while
React batched the section transition. Tests were corrected to obtain the real
control before that `act`; assertions were not weakened and runtime was not
changed. Two additional meaningful cases brought the final suite to 27.
One later strengthened assertion run had **45 PASS / 1 FAIL**: the new assertion
incorrectly expected a rerun row button during list refresh. The real UI hides
all rows behind its loading indicator. The test now verifies that indicator,
absence of row commands until refresh resolves, and restored commands afterward;
runtime is unchanged. This explained test-design failure was not suppressed.
An initial unused destructured fixture field lint warning was removed without
an ignore. Final lint and explicit test typecheck both pass.

## Coverage

Full-file V8 coverage includes exactly the real runtime workspace:

```sh
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-batch.test.tsx \
  --maxWorkers=2 --coverage.reportsDirectory=/tmp/capacitas-c5-before-coverage
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-incass.test.tsx \
  --maxWorkers=2 --coverage.reportsDirectory=/tmp/capacitas-c5-only-coverage
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-incass.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=2 \
  --coverage.reportsDirectory=/tmp/capacitas-c5-after-coverage
```

| Full-file counter | Batch-only before | C5A-only | Batch + C5A after | Covered delta | Percentage-point delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| Statements | 305/857 (35.58%) | 311/857 (36.28%) | 421/857 (49.12%) | +116 | +13.54 |
| Branch arms | 263/929 (28.31%) | 175/929 (18.83%) | 345/929 (37.13%) | +82 | +8.82 |
| Functions | 46/251 (18.32%) | 73/251 (29.08%) | 102/251 (40.63%) | +56 | +22.31 |
| Lines | 288/748 (38.50%) | 282/748 (37.70%) | 380/748 (50.80%) | +92 | +12.30 |

All three runs have tests PASS (19, 27, 46 respectively), but **exit 1:
coverage gate FAIL against unchanged 100% thresholds on all four counters**.
This is not full-file coverage compliance. Counters come from each
`coverage-final.json`; line totals use unique statement start lines with the
maximum hit count per line. C5A-only is an independent coverage view, not an
additive delta. The combined final run also validates the final strengthened
rerun loading/command-availability assertion.

## Ratchet and provenance

`make complexity-ratchet BASE_REF=main` reports baseline commit
`55a1b1d35911451e018b662c2acc450bf5994ea2`, no new findings and exit 0. It includes
already integrated campaign changes inherited in HEAD; C5A itself changes only
tests and this report. No baseline, threshold, exclusion, tooling or shared
configuration was modified. The separate global provenance divergence is not
absorbed or reclassified by this slice.

Frozen SHA256 evidence:

- Runtime: `d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`.
- Existing batch spec: `4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`.

## Classification

**NO_CHANGE — CHARACTERIZATION_ONLY.** Real test/coverage gain, zero complexity
delta and no runtime or architecture change. Not `IMPROVED`; no complexity
laundering claim. The cognitive-472 refactor remains
**BLOCKED_BY_FULL_FILE_COVERAGE**.

## Files changed and commit

Only the two owned files above are included in the authorized source commit:
`test(capacitas): characterize inCASS command lifecycle`.
The exact source SHA is returned separately to the Coordinator, and can be
reproduced with `git log -1 --format=%H -- frontend/tests/unit/campaign-capacitas-incass.test.tsx`.
No integration or cherry-pick is performed by this agent.

## Residual risks and recommended next slice

Reserve **C5B** separately: inCASS 20s/45s polling with 100/101 jobs, active
states, hidden-document behavior, unmount cleanup, collapsed/expanded queue
ordering, detailed payment counter rendering, truncation and malformed/null
result-shape guards. C5A does not prove those behaviors, real authorization,
backend transactions or external portal execution.

The complete workspace still has substantial uncovered responsibilities outside
inCASS, including the coverage plan's candidate defensive branches. Do not
manufacture impossible states to hit them. No runtime complexity refactor is
authorized by this partial test evidence. Full suites, build, E2E and broader
coverage closure were not run by this test-only agent; the Coordinator owns
integration decisions. Runtime relationships did not change, so no code graph
refresh is necessary. No domain/platform docs corpus was modified.
