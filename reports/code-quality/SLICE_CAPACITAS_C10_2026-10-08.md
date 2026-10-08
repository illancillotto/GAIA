# Capacitas C10 — Complexity Slice Report

## Ownership and snapshot

Coordinator registry `1d0945bb`: TEST-ONLY Particelle presentation residuals.
Exclusive ownership of this report and
`frontend/tests/unit/campaign-capacitas-particelle-presentation.test.tsx`.
Runtime, existing tests, configuration, baseline and governance remain read-only.
Runtime hold `GISUNKNOWN` remains effective.

- Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261008-c10-tests`.
- Branch: `refactor/complexity-capacitas-particelle-presentation-tests`.
- Clean preflight HEAD: `ae440459e08d5cca43a39a34290adf0dfbbe0639`.
- Merge-base main: `55a1b1d35911451e018b662c2acc450bf5994ea2`.

Preflight `git status --short`, `git rev-parse HEAD`, `git merge-base HEAD main`,
`git diff` and runtime path history were checked. Integration4 and its residual
ledger identify the exact 11 assigned missing branch arms; its prior figures
are freshly reproduced below, not reused as unexecuted evidence. No other
worktree or concurrent main work is edited.

## Baseline and target callable

Read-only runtime: `frontend/src/components/elaborazioni/capacitas-workspace.tsx`.
Fresh AST before `/tmp/capacitas-c10-before.json` and after
`/tmp/capacitas-c10-after.json` have exactly identical `files` and `callables`.

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Main cognitive | 472 | 472 | 0 |
| Main cyclomatic | 416 | 416 | 0 |
| Main callable LOC | 2631 | 2631 | 0 |
| Main nesting / parameters | 2 / 1 | 2 / 1 | 0 |
| File effective LOC | 3109 | 3109 | 0 |
| File callables | 251 | 251 | 0 |
| File cognitive / cyclomatic sums | 1099 / 1174 | 1099 / 1174 | 0 |
| File useState / useEffect | 31 / 2 | 31 / 2 | 0 |
| Error / warning findings | 24 / 20 | 24 / 20 | 0 |

## Behavioral invariants and characterization tests

The real workspace and hooks run. Mocks cover only API, token/auth-error,
ProtectedPage and unrelated settings-modal boundaries. Complete typed jobs
have positive coherent IDs. Accepted typed results supply genuine recent-item
outcomes consistent with processed/success/failed/skipped counters. Null, object
and array unknown results follow the declared public `result_json` contract.
No private handler, setter, export, impossible successful command response,
ignore, shared fixture or runtime manipulation is introduced.

| Behavior | Existing test | Missing before | Added | Result |
| --- | --- | --- | --- | --- |
| Active result current_label omitted/null | C2b checks label-present presentation | False separator arm1550 | 2 cases: exact2/4, no dangling separator,50% width, metadata/controls | PASS |
| Active invalid result with persisted diagnostic | C2b malformed guard cases primarily done rows | Diagnostic branch1633 | 3 cases: null/dict/list, diagnostic visible, no result progress/table/speed, Stop available | PASS |
| Completed valid result and progress counter section | C2b lifecycle primarily null results | Accepted done-result arms1649/1663/1667 | Four terminal cases with exact percentages/counters and control partition | PASS |
| Status-specific progress colors | No direct done-valid-result matrix | Six arms1671 | succeeded green, completed_with_errors amber, cancelled slate, failed rose | PASS |
| Valid result takes precedence over diagnostic | Existing done-error fallback only | Result/error precedence | Error-bearing terminal fixtures show counters, not job diagnostic | PASS |
| Mixed active/completed rendering | Prior command/lifecycle coverage does not prove full terminal matrix | Distinct sections/control availability | 1 case: active first, Completati heading,4done rows, matching colors | PASS |

**10 new cases PASS**, no skipped tests. No command dispatch is performed;
button availability and representation are asserted through public UI only.
No initial failing test or assertion weakening was needed.

## Changes

One focused test spec plus this report. Runtime relationships, effects, state,
authorization, API, transactions and portal behavior are untouched. Terminal
cases include skipped items and partial cancellation/failure to avoid treating
every completed-state row as100% success.

## Tests and reproducible commands

Commands run in this worktree; npm/tsc from `frontend/`, others from root.

| Command | Result | Evidence |
| --- | --- | --- |
| `npm run test:unit -- tests/unit/campaign-capacitas-particelle-presentation.test.tsx --maxWorkers=1` | 10 PASS,0skip | `/tmp/capacitas-c10-focused.log` |
| `npm run test:unit -- 'tests/unit/campaign-capacitas-' --maxWorkers=1` | Actual14-spec union304 PASS,0skip | `/tmp/capacitas-c10-union-tests.log` |
| `npm run typecheck` | PASS,exit0 | `/tmp/capacitas-c10-typecheck.log` |
| `node_modules/.bin/tsc -p /tmp/capacitas-c10-test-tsconfig.json --noEmit` | New-spec explicit types PASS | `/tmp/capacitas-c10-test-typecheck.log` |
| `npx next lint --file tests/unit/campaign-capacitas-particelle-presentation.test.tsx` | PASS,0errors/0warnings | `/tmp/capacitas-c10-lint.log` |
| `npm test` | 18 smoke PASS,0skip | `/tmp/capacitas-c10-smoke.log` |
| `make complexity-ratchet BASE_REF=main` | PASS,0findings | `/tmp/capacitas-c10-ratchet.log` |

Temporary test config extends this worktree's absolute frontend tsconfig,
sets `incremental:false`, includes only the owned absolute spec, sets
`exclude:[]`, and resolves absolute Vitest/jest-dom types from its node_modules.
This is necessary because normal tsconfig excludes tests; no repository
configuration is edited. Next lint's existing deprecation notice is not an
ESLint warning. One evidence-hash command initially tried the wrong baseline
path under reports; it exited1 with file-not-found, did not alter anything,
and was corrected to `config/code-quality/complexity-baseline.json`.

Fresh AST reports use this read-only command with `before` then `after` names:

```sh
python3 tools/code_quality/complexity.py report \
  frontend/src/components/elaborazioni/capacitas-workspace.tsx \
  --json /tmp/capacitas-c10-before.json --markdown /tmp/capacitas-c10-before.md
```

## Actual union coverage and delta

Before executes the actual13-spec/294-test union before the new spec exists.
After executes the actual14-spec/304-test union; no independent percentage
addition and no inherited test is edited. All tests PASS with zero skip in
both runs. Scope, denominators and all four100% thresholds remain unchanged.

```sh
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/capacitas-c10-before-coverage
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/capacitas-c10-after-coverage
```

| Counter | Before | After | Covered delta | Percentage-point delta |
| --- | ---: | ---: | ---: | ---: |
| Statements | 857/857,100% | 857/857,100% | 0 | 0 |
| Branch arms | 890/929,95.80% | 901/929,96.98% | +11 | +1.18 |
| Functions | 251/251,100% | 251/251,100% | 0 | 0 |
| Lines | 748/748,100% | 748/748,100% | 0 | 0 |

Both coverage commands **exit1 / full-file gate FAIL**, solely because branches
remain below100%. Runtime refactoring is not authorized by statement100%.
Logs `/tmp/capacitas-c10-{before,after}-coverage.log`, raw counters in each
directory's `coverage-final.json`; unique statement-start line coverage uses
the maximum statement hit per line, matching the printed V8 totals.

All11 assigned previously-zero arms now have genuine hits:
No previously-covered branch arm loses coverage in the actual union.

| Source line | Closed branch:arm | After hits |
| --- | --- | --- |
| 1550 | 231:1 | 3 |
| 1633 | 249:0 | 3 |
| 1649 | 252:0 | 8 |
| 1663 | 254:0 | 8 |
| 1667 | 255:0 | 8 |
| 1671 | 256:0 /256:1 | 2 /6 |
| 1671 | 257:0 /257:1 | 2 /4 |
| 1671 | 258:0 /258:1 | 2 /2 |

There are **28 remaining arms**, with no statement/function/line residue.
Read-only ledger `/tmp/capacitas-c10-residual-ledger.json` preserves branch IDs,
arm indexes, source lines, exact locations and counters; none discarded.
Remaining source lines:258,281,291,293,313,314,315,316,317,318,378,388,390,403,
404,405,681,2056,2389,2482(two arms),2483,2484,3166,3206,3214,3217,3220.
No remaining Particelle presentation arm belongs to this assignment.

## Ratchet and preservation

`BASE_REF=main` remains authoritative, baseline commit
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Gate reports no findings, exit0;
inherited campaign changes are also in its comparison. No baseline inflation,
threshold change, ignore/exclusion or runtime change. Global historical
divergences remain independently owned provenance issues.

SHA256 before/after:

- Runtime: `d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`.
- Existing batch: `4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`.
- Baseline: `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.

## Classification

**NO_CHANGE — CHARACTERIZATION_ONLY**: measured11-arm coverage gain, zero
complexity change. Not `IMPROVED`; no complexity laundering. Main cognitive472
and full-file branch-policy blocker remain unchanged.

## Files changed and commit

Only the two owned new files enter the authorized source commit
`test(capacitas): cover Particelle presentation residuals`.
Exact source SHA is returned separately after commit and is reproducible via
`git log -1 --format=%H -- frontend/tests/unit/campaign-capacitas-particelle-presentation.test.tsx`.
No integration/cherry-pick is performed by this agent.

## Graphify, residual risks and next slice

Orientation via dedicated `make graphify-frontend-query` attempted; exit2,
worktree-local graph absent, `/tmp/capacitas-c10-graphify.log`. No raw-root
extraction, graph modification or credential disclosure. Runtime relationships
unchanged; report outside platform/domain docs corpora, no refresh required.

Complete backend/frontend/worker suites, build and E2E are not run by this
test-only presentation agent. API-boundary mocks are not a proof of actual
authorization/portal behavior. Remaining28branch arms require their existing
owners or new scoped authorization, including defensive provenance and async
modal transitions; do not fabricate impossible states or exclusions.

Integration should review this two-file commit, execute the actual union with
other independently reviewed slices, and measure its real V8 counters. Stop
at `READY_FOR_REVIEW`; runtime hold remains in force.
