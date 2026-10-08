# Capacitas C11 — Complexity Slice Report

## Ownership and snapshot

Coordinator assignment under ACTIVE registry `1d0945bb`, agent `integration_r3`.
Own only new `frontend/tests/unit/campaign-capacitas-terreni-residual.test.tsx`
and this report. Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261008-c11-tests`;
branch `refactor/complexity-capacitas-terreni-residual-tests`.
Clean preflight HEAD `ae440459e08d5cca43a39a34290adf0dfbbe0639`, merge-base main
`55a1b1d35911451e018b662c2acc450bf5994ea2`.
No concurrent work imported. Existing tests, runtime, shared/config/baseline,
governance and integration remain read-only. GIS UNKNOWN runtime hold remains.

Read Integration4 and its39-arm ledger before selecting the two assigned public
transitions. Skills checkpoint/complexity/Graphify remain active; targeted logs
in `/tmp`. This is not an authorization for runtime cleanup or a coverage waiver.

## Baseline and target callable

Fresh scoped AST before/after for
`frontend/src/components/elaborazioni/capacitas-workspace.tsx` has deep-identical
`files` and `callables` objects, including fingerprints and positions:

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| ElaborazioniCapacitasWorkspace cognitive | 472 | 472 | 0 |
| Main cyclomatic / callable LOC | 416 / 2631 | 416 / 2631 | 0 |
| Main nesting / params | 2 / 1 | 2 / 1 | 0 |
| File cognitive / cyclomatic sum | 1099 / 1174 | 1099 / 1174 | 0 |
| File effective LOC / callables | 3109 / 251 | 3109 / 251 | 0 |
| File error / warning | 24 / 20 | 24 / 20 | 0 |
| useState / useEffect | 31 / 2 | 31 / 2 | 0 |

Reports `/tmp/capacitas-c11-{before,after}-complexity.json` and `.md`.
No complexity reduction or responsibility extraction is claimed.

## Behavioral invariants and characterization matrix

| Behavior | Existing test | Missing | Added | Result |
|---|---|---|---|---|
| Errors modal preserves original real job snapshot after target genuinely disappears from refreshed list | C1 refreshes the same job with empty/null result | Actual nonmatching refreshed job, fallback at681 | Open real Errori control on81; deferred refresh returns only82; assert81 absent from monitor,82 present, original label/key/diagnostic and modal job81 still visible; close removes modal only | PASS |
| Parallel worker control submits1→2→1 without changing unrelated payload flags/items | Batch tests default1 and one toggle to2 | Toggle back from2 to1 at2389 and exact three submitted payloads | Real CSV upload and three submissions; actual toggle labels/help text, exact API arguments and feedback, refreshed monitor rows91/92/93 | PASS |

Two coherent new tests, not a broad render matrix. Both mount the actual
workspace `embedded initialSection="terreni"`; real UI handlers/effects/hooks
execute. API calls/token getter are normal boundary doubles; ProtectedPage and
the unrelated settings modal are mocked. The actual API core error classifier
is dynamically imported, not replaced. No workspace/usePolling mock, private
setter/callback invocation, runtime export, ignored arm or fabricated parser.
File.text is a browser I/O boundary returning the actual supplied CSV content;
the workspace's own CSV parser/normalization runs unchanged.

All job/result fixtures satisfy their complete typed contracts. Create returns
a new pending job with its submitted payload; the subsequent list contains
those exact created jobs/IDs, rather than impossible response IDs or missing
newly created records. The disappearing-modal case returns a legitimately
different list via the public refresh API. The test proves actual DOM rows
changed before checking fallback, not merely that the row is hidden by loading.
Snapshots tested are UI state preserved from the original public response;
there is no private-state injection.

## Tests and initial failures

First focused execution failed2 cases due an incorrect test selector assuming
the panel title was an accessible heading. The intermediate retry had the same
selector issue. Correcting monitor lookup to actual rendered title then exposed
two accessible Chiudi controls; focused run1PASS/1FAIL. The final selector chooses
the real text-labeled bottom close button, preserving every behavioral assertion.
The first union coverage attempt also failed2cases/294PASS and is not PASS evidence.
No runtime modification or assertion deletion fixes these test-authoring errors.

Retained failure logs `/tmp/capacitas-c11-focused-tests.log`,
`/tmp/capacitas-c11-focused-final-tests.log`,
`/tmp/capacitas-c11-focused-corrected-tests.log` and
`/tmp/capacitas-c11-after-coverage.log`.

| Final command from frontend unless stated | Result | Log |
|---|---|---|
| `npm run test:unit -- tests/unit/campaign-capacitas-terreni-residual.test.tsx --maxWorkers=1` | 2PASS, no skips | `/tmp/capacitas-c11-source-final-focused.log` |
| `npm run test:unit -- 'tests/unit/campaign-capacitas-' --maxWorkers=1` | 296PASS/14specs, no skips | `/tmp/capacitas-c11-source-final-union.log` |
| `npm run typecheck` | PASS | `/tmp/capacitas-c11-typecheck.log` |
| `npx tsc --noEmit -p /tmp/capacitas-c11-tsconfig.json` | PASS, includes new spec explicitly | `/tmp/capacitas-c11-source-final-types.log` |
| `npx eslint tests/unit/campaign-capacitas-terreni-residual.test.tsx` | PASS, no diagnostics | `/tmp/capacitas-c11-source-final-eslint.log` |
| `npm test` | 18PASS, no skips | `/tmp/capacitas-c11-smoke.log` |
| Root `make complexity-ratchet BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python` | PASS, findings[] | `/tmp/capacitas-c11-source-final-ratchet.log` |
| `git diff --check` | PASS | Worktree check |

Standard tsconfig excludes tests. Temporary test-inclusive config extends the
real config, includes the owned spec and runtime, disables incremental, supplies
absolute installed Vitest/jest-dom type paths; no repository config changes.
Fullsuite/build/E2E/live services remain Coordinator integration gates and are
not run or claimed PASS by C11.

## Actual union coverage before/after

Fresh before executes all13 already-integrated matching specs294PASS/no skips.
Fresh after executes actual union with the new spec,14specs296PASS/no skips.
Same full-file include, unchanged100% thresholds, no sum of source percentages.
Both coverage commands **exit1 / FAIL100**, despite all selected tests passing.

| Counter | Before | After | Covered delta | After % |
|---|---:|---:|---:|---:|
| Statements | 857/857 | 857/857 | 0 | 100 |
| Branch arms | 890/929 | 892/929 | +2 | 96.01 |
| Functions | 251/251 | 251/251 | 0 | 100 |
| Lines | 748/748 | 748/748 | 0 | 100 |

Raw V8 arrays prove precisely the two assigned arms newly execute:

| Source expression | Branch id:arm | Before group counts | After group counts |
|---|---|---|---|
|681 `find(...) ?? terreniJobErrorsModal` |83:1 |[7,0] |[10,1] |
|2389 `parallel_workers > 1 ? 1 : 2` |320:0 |[0,1] |[1,2] |

IDs belong to these artifacts only. Before39missing arms become37 across31source
lines; the residual count equals929−892. All zero arms retained, including arms
with partial end-column metadata. No unreachable exemption or removed defense.
Coverage JSON and comparison preserve all929arms and unchanged denominators.
Residual source lines258,281,291,293,313–318,378,388,390,403–405,1550,1633,1649,
1663,1667,1671,2056,2482–2484,3166,3206,3214,3217,3220 remain outside this slice.
Branch coverage100% is not achieved; runtime refactoring remains unauthorized.

Reproduce from frontend:

```bash
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/capacitas-c11-source-final-coverage
```

Before log/JSON `/tmp/capacitas-c11-before-coverage.log` and
`/tmp/capacitas-c11-before-coverage/coverage-final.json`.
After log/JSON `/tmp/capacitas-c11-source-final-coverage.log` and
`/tmp/capacitas-c11-source-final-coverage/coverage-final.json`.
Read-only raw comparison `/tmp/capacitas-c11-source-final-comparison.json`.
JSON SHA256 before `73d7428789813d7c1268b61f75b4926b45bebb570a57306360fdb2d853173170`;
after `71486e18f53d61354e746940e9458a46bf018c72993b98de8108102e43790e8f`.
Later matching specs change the actual union; do not reuse these counts unexecuted.

## Integrity, Graphify and ratchet

Protected hashes identical in `/tmp/capacitas-c11-protected-{before,after}.sha256`:
runtime `d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`,
existing batch `4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`,
baseline `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
Tracked diff against preflight empty for runtime, existing tests, configuration,
packages/Makefile. Only two authorized new files staged/committed; no baseline
repair, inflation, scope/threshold/ignore/tooling change. Dirty main untouched.

Dedicated `make graphify-frontend-query` attempted: fresh worktree has no local
`frontend/src/graphify-out/graph.json`; Make exit2 in
`/tmp/capacitas-c11-graphify-query.log`. Not claimed PASS. No runtime relationship
change requires code graph refresh; docs graph maintenance stays Coordinator-owned.
The initially incorrect baseline hash path was corrected to the actual
`config/code-quality/complexity-baseline.json` before recording protected hashes.

## Classification, files changed and commit

**NO_CHANGE — CHARACTERIZATION_ONLY.** Two genuine UI branches characterized,
no complexity improvement, functional fix or runtime wave clearance.
Only new spec and this report. Authorized coherent source commit message:
`test(capacitas): characterize Terreni snapshot and worker toggle`.
Exact source SHA delivered after commit; agent does not integrate.
Status READY_FOR_REVIEW means test-only review, not full-file coverage compliance.

## Residual risks and recommended next slice

No production authorization, live Capacitas concurrency or backend persistence
claim follows from API boundary fixtures. These tests preserve current UI
behavior; they do not resolve the separate GISUNKNOWN decision or37residual arms.
Stop after this slice. Coordinator can independently review, integrate and
measure actual combined C10/C11 union under new ownership; no additional runtime
or test responsibility is implicitly authorized.
