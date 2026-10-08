# C2a — Capacitas Particelle Commands Complexity Slice Report

## Ownership

Coordinator/root owns only the new Particelle commands spec and this report.
Dedicated worktree `GAIA-campaign-20261008-c2a-tests`, branch
`refactor/complexity-capacitas-particelle-commands-tests`. Preventive registry
2cf57eaf. Clean source preflight39dbcc40273cfca699b576b8445ccd378e822a46;
merge-base main55a1b1d35911451e018b662c2acc450bf5994ea2. Main dirty concurrent
work is not copied, changed or committed. No runtime ownership granted.

## Baseline and target callable

Runtime SHA256 before/after
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`.
Existing19 batch tests unchanged. Before coverage reproduced in
`/tmp/capacitas-c2a-before`:305/857 statements263/929 branch arms,
46/251 functions288/748 lines. Tests19PASS, coverage gateFAIL exit1.
Full-file100% is not bypassed; this is test-only characterization.

## Behavioral invariants and characterization tests

Real workspace, public accessible controls and typed API response fixtures.
API/token mocks only at actual boundaries. No private closure/state access,
runtime exports, whole-workspace doubles, impossible mocks or exclusions.
The ProtectedPage double does not prove real authorization. Successful speed
and stop responses retain the requested canonical job ID, matching backend
route contracts. Unrelated rows exercise non-matching mapper branches. No
actual external portal calls are made.

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Create default flags, pending→success→refresh ordering | Batch does not create Particelle | Yes | Deferred create with exact payload, disabled button and subsequent list | PASS |
| Credential/limit/flags/speed/workers and reverse toggles | None direct | Yes | Two input/action cases with complete API payload and message | PASS |
| Rerun row-specific busy state and response-before-refresh | None direct | Yes | Deferred rerun and deferred list; untouched row stays enabled | PASS |
| Delete only requested row, no re-fetch | None direct | Yes | Deferred deletion, surviving ID and exact call count | PASS |
| Standard/double speed returned-ID mapping | None direct | Yes | Both bool payloads, two rows and deferred updated result | PASS |
| Stop processing→cancelling and repeated-stop disabled | None direct | Yes | Deferred stop, matching row and unaffected second row | PASS |
| Session token disappears before each command | None direct | Yes | Five UI actions no-op, no mutation or re-fetch | PASS |
| Error/non-Error mutation rejection for all commands | None direct | Yes | Ten cases retain rows, render both notices and restore controls | PASS |
| Create succeeded but refresh fails | None direct | Yes | Preserve create confirmation, show refresh failure, restore control | PASS |

Command band981–1073 now59/59 statements,30/30 arms,11/11 functions
(all previously0). This narrow band is **not** a full-file coverage claim.
Particelle monitor polling, result-shape guards and broad presentation remain
outside this single coherent slice.

## Changes

Added24 meaningful cases in a new exclusive spec. No runtime/test original,
API/query/DB/schema/transaction/auth changes. No runtime refactor performed.

## Metric before / after / delta

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive | 472 | 472 | 0 |
| Principal cyclomatic | 416 | 416 | 0 |
| Principal LOC / nesting / params | 2631/2/1 | 2631/2/1 | 0 |
| File effective LOC | 3109 | 3109 | 0 |
| File cognitive / cyclomatic sums | 1099/1174 | 1099/1174 | 0 |
| useState / useEffect | 31/2 | 31/2 | 0 |
| File error / warning | 24/20 | 24/20 | 0 |

Local report `/tmp/capacitas-c2a-complexity.json`, Markdown same stem:
251callables44findings. Runtime byte-identical, no complexity improvement.

## Tests and coverage

Reproducible from worktree/frontend:

```bash
npm run test:unit -- tests/unit/campaign-capacitas-particelle-commands.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=2
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-particelle-commands.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=2 \
  --coverage.reportsDirectory=/tmp/capacitas-c2a-after
npm run typecheck
./node_modules/.bin/tsc -p /tmp/capacitas-c2a-test-tsconfig.json --noEmit
./node_modules/.bin/eslint tests/unit/campaign-capacitas-particelle-commands.test.tsx
npm test
```

Combined43PASS0skip after independent review correction.
Coverage tests43PASS, **threshold gateFAIL exit1**; statements414/857(48.30%),
arms381/929(41.01%),functions88/251(35.05%),lines375/748(50.13%). Deltas from
before:+109statements/+118arms/+42functions/+87lines. Percentages are from
actual combined execution, not sums across independently measured suites.
Runtime and explicit new-spec typecheckPASS; normal tsconfig excludes tests,
so disposable supplemental config is necessary and not a committed change.
Scoped ESLintPASS, smoke18PASS, diffcheckPASS. No full suite/build/E2E run
per micro-slice; no such PASS asserted.

All attempts retained: initial new-test run13/26PASS(32/45combined) failed
because errors appear twice (hero and section), and only double-speed button
changes its label to `...` while Standard remains named and disabled. Corrected
test assumptions, not runtime; final45PASS. Supplemental typecheck initially
failed14 queries using unsupported `ByRoleOptions.exact`; string names are
already exact by default, so removed invalid options and reran45PASS/typecheck.
Root-directory ESLint emitted a pages-location warning; correct frontend-scoped
invocationPASS without config changes. Logs `/tmp/capacitas-c2a-*.log`.

Independent review rejected the two successful speed/stop mocks returning
job99 for a request targeting31: backend routes serialize the requested ID,
so these fixtures were impossible under the actual API contract. Removed
both cases, rather than manufacturing another response for coverage; valid
two-row cases already characterize preservation of unrelated rows. Original
8eec9bc2 remains recorded but is not approved for integration. Reran final
43tests and coverage plus explicit typecheck/lint; command-band coverage
unchanged. Evidence `/tmp/capacitas-c2a-reviewed.log` and coverage directory
`/tmp/capacitas-c2a-reviewed`. Authorized source follow-up removes only these
invalid cases and corrects this report; exact commit supplied separately.

## Ratchet

`make complexity-ratchet BASE_REF=main` PASS exit0/findings[]; log
`/tmp/capacitas-c2a-ratchet.log`. Local AST report command:
`python3 tools/code_quality/complexity.py report frontend/src/components/elaborazioni/capacitas-workspace.tsx --json /tmp/capacitas-c2a-complexity.json --markdown /tmp/capacitas-c2a-complexity.md`.
Protected config/baseline/tooling diff empty. Global30 historical divergences
remain separate provenance, neither repaired nor attributed to these tests.

## Classification / files changed / commit

**NO_CHANGE — CHARACTERIZATION_ONLY**. Exactly two owned files: this report
and `frontend/tests/unit/campaign-capacitas-particelle-commands.test.tsx`.
Source coherent test-only commit authorized; its exact SHA is recorded by the
Coordinator after commit. Independent review/integration required, not self-merged.

## Residual risks and recommended next slice

Full-file coverage is incomplete; cognitive472 hotspot remains blocked for
runtime refactoring. GIS risk decision is pending and not accepted here.
Recommended separately owned next slice: Particelle monitor lifecycle and
result guards, or existing planned Storico/inCASS sections; no continuation
inside this commands ownership. Do not fabricate races or remove defenses
solely for coverage. Stop after independent review.
