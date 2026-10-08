# Capacitas — Independent characterization integration 4

## Ownership and snapshot

Registry `91d1fbca` authorizes exclusive Integration4 report and two approved
test-only cherry-picks. Worktree `GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`; clean preflight HEAD
`e4fe1063d7286a32e9231446de9b5d1371ac605a`, staging empty. Merge-base main
`55a1b1d35911451e018b662c2acc450bf5994ea2`; frozen R3 runtime unchanged.
Main dirty/concurrent work untouched; Coordinator documents are separately owned.
No runtime, existing tests, configuration, tooling or baseline edits authorized.

## Independent review and sequential integration

| Slice | Source commit | Integrated commit | Source tests | Cumulative tests | Ratchet |
|---|---|---|---:|---:|---|
| C5b inCASS monitor | `d145971b213c96f515cdb152e87a35cfd31d79c6` | `a79b36d1` | 64 PASS | 292 PASS | PASS, 0 findings |
| C9 actual no-sheet workbook | `65de921a6bd5695a75d0f18051d28951e2887065` | `8a12533a` | 21 PASS | 294 PASS | PASS, 0 findings |

Actual final focused run294 PASS/13specs, zero skip. Cases comprise247 inherited,
45 new C5b and2 new C9. Both authoritative sequential ratchets PASS/0, exit0.
Sources were clean and contain precisely their exclusive new spec and report.
Real source-focused tests run independently before cherry-pick. Each integration
requires staged area empty, cumulative focused tests and authoritative
`make complexity-ratchet BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python`
before the next slice. No ownership overlap, conflict or runtime layering change.

## Behavioral matrix and validity review

| Responsibility | Public behavior verified | Review |
|---|---|---|
| C5b polling | Empty/initial loading; active/terminal status gating; exact API limit300; interval20s at100 jobs versus45s at101, boundary crossing reschedules | PASS |
| C5b lifecycle | Hidden ticks skip, visibility triggers real single-flight refresh, pending ticks cannot overlap, unmount clears timer/listener even while request awaits | PASS |
| C5b race | Manual refresh lies outside polling single-flight; a later-settled manual response overwrites newer poll rows and re-enables active monitor | PASS, existing race disclosed |
| C5b errors/auth | Error/non-Error initial/manual/silent paths, retained manual error until manual success, token/auth freezes automatic refresh and explicit recovery | PASS |
| C5b queue | Collapsed priority for running/resume jobs, pending retains API order,15/16 expansion boundary, expanded API order and refreshed collapse order | PASS |
| C5b results | Persisted unknown JSON guards, counters/payment outcomes, nullable/optional fields, progress and first15 preview | PASS |
| C9 Terreni upload | Actual no-sheet binary triggers empty-batch notice, filename retained, parsed rows cleared, dispatch disabled, file input restored | PASS |
| C9 Storico upload | Actual no-sheet binary in file mode triggers empty-file notice, zero ready rows, import disabled and no request | PASS |

The real workspace/usePolling and public actions/effects execute; doubles stay
at actual API/auth/protected/modal/browser boundaries. C5b's classifier is a
boundary double, not a claim of independently testing actual authorization.
Its JSON fixtures match persisted public dict/list/null contracts; malformed
accepted items are not fabricated to force a crash. No setter/private closure,
runtime export, impossible command response ID or ignored branch is introduced.

C9 builds actual OOXML with installed SheetJS0.20.3, reads/writes the real ZIP
with CFB APIs, replaces only workbook.xml's `<sheets>` collection with
`<sheets/>`, and reserializes actual bytes. Precondition proves the unmocked
SheetJS parser accepts those bytes with `SheetNames=[]`; then the workspace
reads the same real bytes through File.arrayBuffer and its real parser. This
is a malformed user upload, not a valid supported Excel claim. No XLSX.read,
sheet_to_json or private parser output is mocked. The two missing-sheet guards
are genuinely reachable; neither is removed to claim coverage.

Source initial failures remain in individual reports: C9 ZIP path probe and
incorrect filename-clearing expectation; C5b assertion/construction iterations.
Integration itself does not fix runtime races or weaken existing tests.

## Fresh full-file before evidence

Actual integration before run executes all eleven integrated matching specs,
247 PASS/zero skip. Unchanged V8 full-workspace include and four100% thresholds
yield exit1, coverage **FAIL**:846/857 statements,810/929 branch arms,
244/251 functions,743/748 lines. Not full-file compliance.
Evidence `/tmp/gaia-capacitas-integration4-before-coverage/coverage-final.json`
and corresponding `.log`. Final counters must use actual combined execution,
never addition of percentages from source reports.

## Actual final full-file union and residual ledger

Fresh final V8 run executes all thirteen actual integrated specs together:
294 cases PASS/zero skip. All thresholds and denominators unchanged; command
still **exit1, coverage gate FAIL** because branches are below100%.

| Metric | Before covered/total | Final covered/total | Covered delta | Final % |
|---|---:|---:|---:|---:|
| Statements | 846/857 | 857/857 | +11 | 100 |
| Branch arms | 810/929 | 890/929 | +80 | 95.80 |
| Functions | 244/251 | 251/251 | +7 | 100 |
| Lines | 743/748 | 748/748 | +5 | 100 |

Remaining statement/function/line locations: **none**. Remaining branch arms:
**39 across33 branch-source lines**. Runtime full-file100% is **not achieved**;
statement/function100% does not waive branch policy.

Ledger derives from every entry of actual V8 `b` arrays and retains every zero
arm regardless of location. Branch group line uses `branchMap.line` (fallback
to branch location start); exact arm start/end/columns, containing location,
branch type/id and arm index are preserved in JSON. In this run **zero unlocated
arms**, determined by checking every arm; none discarded. Count sum39 equals
929−890. This is a measurement ledger, **not** an unreachable classification.
Some construction/library-sensitive paths have separately owned provenance;
the remaining paths require their own behavioral/reachability analysis.

| Branch source line | Uncovered arms | IDs (branch:arm) | Arms without start-line location |
|---|---:|---|---:|
| 258 | 1 | 16:1 | 0 |
| 281 | 1 | 19:1 | 0 |
| 291 | 1 | 23:1 | 0 |
| 293 | 1 | 24:1 | 0 |
| 313 | 1 | 27:1 | 0 |
| 314 | 1 | 28:1 | 0 |
| 315 | 1 | 29:1 | 0 |
| 316 | 1 | 30:1 | 0 |
| 317 | 1 | 32:1 | 0 |
| 318 | 1 | 34:1 | 0 |
| 378 | 1 | 41:1 | 0 |
| 388 | 1 | 45:1 | 0 |
| 390 | 1 | 46:1 | 0 |
| 403 | 1 | 49:1 | 0 |
| 404 | 1 | 51:1 | 0 |
| 405 | 1 | 53:1 | 0 |
| 681 | 1 | 83:1 | 0 |
| 1550 | 1 | 231:1 | 0 |
| 1633 | 1 | 249:0 | 0 |
| 1649 | 1 | 252:0 | 0 |
| 1663 | 1 | 254:0 | 0 |
| 1667 | 1 | 255:0 | 0 |
| 1671 | 6 | 256:0, 256:1, 257:0, 257:1, 258:0, 258:1 | 0 |
| 2056 | 1 | 285:1 | 0 |
| 2389 | 1 | 320:0 | 0 |
| 2482 | 2 | 337:1, 338:1 | 0 |
| 2483 | 1 | 333:1 | 0 |
| 2484 | 1 | 334:1 | 0 |
| 3166 | 1 | 426:1 | 0 |
| 3206 | 1 | 434:1 | 0 |
| 3214 | 1 | 436:1 | 0 |
| 3217 | 1 | 437:1 | 0 |
| 3220 | 1 | 439:1 | 0 |

Artifacts `/tmp/gaia-capacitas-integration4-final-coverage/coverage-final.json`,
`/tmp/gaia-capacitas-integration4-final-coverage.log`,
`/tmp/gaia-capacitas-integration4-residual-ledger.json` and `.md`.
Reproducible read-only extractor `/tmp/gaia-capacitas-integration4-ledger.cjs`;
unique line counts use Istanbul `getLineCoverage`, not overlapping statement sums.
Coverage JSON before SHA256
`b3aef35485071fe9e045bc687d6f5e8fdc8b3ab6a3472ac56dbd3ef8fd3ded9f`;
final SHA256`35d107523af9661d656d472e6b779baa596d58ce8adc7788c833a274b60bd121`.

Reproduce on frozen frontend source `8a12533a06a9d4a35ed5d74ddd93209ab59aa8e2`,
frontend tree `a9b5957a07d4898f75a3d328f2967ef56b71ea36`:

```bash
cd frontend
npm run test:unit -- 'tests/unit/campaign-capacitas-' --maxWorkers=1
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/gaia-capacitas-integration4-final-coverage
```

Later new matching specs change this filter's union; do not reuse frozen counts
for a larger unexecuted future suite.

## Preservation and metrics

Runtime SHA256 unchanged
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`;
existing batch SHA256 unchanged
`4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`;
baseline SHA256 unchanged
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
Diff against preflight empty for runtime trees/config/code-quality/tooling/
Makefile/frontend packages and Vitest config. No scope/threshold/ignore change.
Runtime metrics stay principal472cognitive/416cyclomatic/2631LOC/nesting2/params1;
file1099cognitive/1174cyclomatic/3109effectiveLOC/251callables/24error/20warning,
31useState/2useEffect. No complexity delta or laundering claim.

## Validation and limits

Independent source logs `/tmp/gaia-capacitas-integration4-{c5b,c9}-source.log`.
Sequential integrated focused/ratchet logs use `-integrated.log`/`-ratchet.log`.
Temporary test-inclusive configuration
`/tmp/gaia-capacitas-integration4-test-tsconfig.json` explicitly includes both
new specs with absolute Vitest/jest-dom types; standard tsconfig excludes tests.
Final integrated C5b/C9 explicit new-spec types and scoped lint PASS, logs
`/tmp/gaia-capacitas-integration4-final-{types,lint}.log`; unchanged Next16
deprecation notice only. Diff check PASS. Fresh final AST report
`/tmp/gaia-capacitas-integration4-final-complexity.json` remains identical.
Dedicated Graphify frontend query `ElaborazioniCapacitasWorkspace` PASS82nodes,
orientation only, `/tmp/gaia-capacitas-integration4-graph-query.log`. No runtime
relationship change requires a code graph refresh; Coordinator owns docs graph.

No fullsuite/build/E2E/live portal certification is claimed for micro-slices;
final frontend-wide checks are Coordinator-owned after the source freeze.
Global baseline provenance remains separate, not absorbed/reclassified here.

## Classification and stop

**NO_CHANGE — CHARACTERIZATION_ONLY**. Final focused tests, counters, residual
ledger and sequential ratchets complete. Stop after C5b/C9 reviewed integration;
no runtimewave acceptance, ignore/exemption, baseline inflation or claim that
this characterization closes the global complexity campaign.
