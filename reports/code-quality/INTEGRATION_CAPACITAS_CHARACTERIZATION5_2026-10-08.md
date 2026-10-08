# Capacitas — Independent characterization integration 5

## Ownership and preflight

Registry `bcf46233` authorizes exclusive report ownership and sequential
approved test-only source cherry-picks. Worktree
`GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`; clean preflight HEAD
`638a46815bc50640a361958ef0ad32a2809eb4b2`, staging empty. Merge-base main
`55a1b1d35911451e018b662c2acc450bf5994ea2`, frontend tree
`a9b5957a07d4898f75a3d328f2967ef56b71ea36`. Dirty main remains untouched.
Runtime, old tests, baseline, tooling, thresholds and shared configuration
read-only. Coordinator does not write integration during cherry-pick operations.

## Fresh measured before

Actual before coverage executes all thirteen integrated matching specs:
294 tests PASS/zero skip. Same full-workspace V8 include and four100% gates,
857/857 statements,890/929 branch arms,251/251 functions,748/748 lines.
Coverage command exit1: **FAIL100** on branches95.80%, not compliant.
No guessed or percentage-summed counter. Evidence
`/tmp/gaia-capacitas-integration5-before-coverage/coverage-final.json`,
`/tmp/gaia-capacitas-integration5-before-coverage.log`.

Fresh scoped AST `/tmp/gaia-capacitas-integration5-before-complexity.json`:
principal472cognitive/416cyclomatic/2631LOC/nesting2/params1;
file1099cognitive/1174cyclomatic/3109effectiveLOC/251callables,
24error20warning44findings,31useState2useEffect. No runtime change.

Runtime SHA256
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`;
existing batch SHA256
`4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`;
baseline SHA256
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.

## Source review and gates

| Slice | Source | Integrated | Independent source tests | Cumulative integrated tests | Ratchet |
|---|---|---|---:|---:|---|
| C10 Particelle presentation | `c3d428f97e1dbb07a70d92c1e81a36d2a3d8f401` | `ffeafafd` | 29 PASS | 304 PASS / 14 specs | PASS / 0 findings |
| C11 Terreni residual | `bab83acdf1d9ab3b472c061516bdb9d927795b1f` | `df86527b` | 2 PASS | 306 PASS / 15 specs | PASS / 0 findings |

C10 source authorized explicitly by Coordinator before independent source
review/tests and cherry-pick. Both sources clean, exactly their new exclusive
spec/report, runtime hash identical. C11 exact READY source authorized by
Coordinator, also recorded in registry129fbccd, independently reviewed/tested
only after C10 completed its cumulative test/ratchet gates. No incomplete branch
cherry-picked. No overlap/conflict, runtime dependency, layering or import change.
Runtime acceptance is explicitly not authorized.

C10 review confirms real API-boundary/public-UI fixtures: consistent success/
failed/skipped counts and progress across succeeded/completed-with-errors/
cancelled/failed outcomes; omitted/null current label preserves exact counter
text without dangling separator; active persisted null/array/object results
render diagnostic safely; terminal result wins over error detail; mixed lists
retain active/completed section order and distinct controls/colors. No private
state injection, impossible command ID response or missing-export fake error.
Tests exercise real workspace effects/rendering, with API/auth/protected/modal
doubles only. No production authorization/live portal proof is inferred.

| Responsibility | C11 behavioral characterization | Review |
|---|---|---|
| Errors modal snapshot | Open actual Errori control for job81; deferred public refresh returns only82; actual monitor no longer has81, while original label/key/diagnostic and job81 modal remain; real close removes only modal | PASS |
| Parallel worker toggle | Real CSV File.text input, three real submissions with toggle1→2→1; exact payload, labels/help, feedback, API call counts and actual created job rows91/92/93 | PASS |

C11 imports the real API core error classifier. Its API fixtures match complete
typed contracts and valid counts; each create response is a pending job carrying
its actual submitted payload and the next list includes those exact jobs/IDs.
The real workspace CSV parser, handlers, hooks, effects and DOM execute.
Neither source invokes private setters/closures, fabricates impossible response
IDs/parser output, removes defenses or modifies existing tests.

## Actual final full-file union and residual ledger

Fresh actual fifteen-spec union: **306 tests PASS, zero skips**. Same full-file
V8 include and all four unchanged100% gates. Coverage command **exit1 / FAIL100**;
only branches remain below100%, not full-file compliance or runtime clearance.

| Metric | Before covered/total | Final covered/total | Covered delta | Final % |
|---|---:|---:|---:|---:|
| Statements | 857/857 | 857/857 | 0 | 100 |
| Branch arms | 890/929 | 903/929 | +13 | 97.20 |
| Functions | 251/251 | 251/251 | 0 | 100 |
| Lines | 748/748 | 748/748 | 0 | 100 |

Before and final statementMap/fnMap/branchMap objects compare exactly equal.
No lost covered branch arms. Newly covered source locations681,1550,1633,1649,
1663,1667,1671(six arms),2389. No remaining statement/function/line locations.
Residual **26 branch arms across25 source lines**, including every zero arm.
No arms without start-line location; partial/null end-column metadata remains
preserved in JSON. Count26 equals929−903; no threshold/exemption/scope change.

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
| 2056 | 1 | 285:1 | 0 |
| 2482 | 2 | 337:1, 338:1 | 0 |
| 2483 | 1 | 333:1 | 0 |
| 2484 | 1 | 334:1 | 0 |
| 3166 | 1 | 426:1 | 0 |
| 3206 | 1 | 434:1 | 0 |
| 3214 | 1 | 436:1 | 0 |
| 3217 | 1 | 437:1 | 0 |
| 3220 | 1 | 439:1 | 0 |

These are measurement facts, not newly proven unreachable classifications.
Separately owned `CAPACITAS_DEFENSIVE_BRANCH_PROVENANCE_2026-10-08.md` describes
21 conditional construction/library candidates; five modal-race guards remain
UNKNOWN. Integration grants neither coverage waivers nor guard removal.

Artifacts `/tmp/gaia-capacitas-integration5-final-coverage/coverage-final.json`,
`/tmp/gaia-capacitas-integration5-final-coverage.log`, corresponding `.exit`,
`/tmp/gaia-capacitas-integration5-residual-ledger.json` and `.md`.
Read-only extractor `/tmp/gaia-capacitas-integration5-ledger.cjs` retains branch
IDs/types/containing lines/exact locations and uses Istanbul getLineCoverage.
Coverage JSON SHA256 before
`35d107523af9661d656d472e6b779baa596d58ce8adc7788c833a274b60bd121`, final
`c5d4a38027b6876b7d0a7b76310edfd6876346bda707064e9f45f182e0a50fe1`.

## Frozen source and reproducibility

Final source `df86527b4fe979b507dde7dbdcbc443c574e1869`, frontend tree
`1ddc7041881a24259e30dd81491aafba44fdb104`.

```bash
cd frontend
npm run test:unit -- 'tests/unit/campaign-capacitas-' --maxWorkers=1
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/gaia-capacitas-integration5-final-coverage
```

Later matching specs change the union; do not reuse these frozen counts for
unexecuted source. Report-only commit does not change the frozen frontend tree.

## Validation, preservation and complexity

| Gate | Actual result | Artifact |
|---|---|---|
| C10 independent source batch + new spec | 29 PASS, zero skips | `/tmp/gaia-capacitas-integration5-c10-source.log` |
| C10 integrated cumulative tests | 304 PASS / 14 specs, zero skips | `/tmp/gaia-capacitas-integration5-c10-integrated.log` |
| C10 ratchet main | PASS0, exit0 | `/tmp/gaia-capacitas-integration5-c10-ratchet.log` |
| C11 independent source new spec | 2 PASS, zero skips | `/tmp/gaia-capacitas-integration5-c11-source.log` |
| C11 integrated cumulative tests | 306 PASS / 15 specs, zero skips | `/tmp/gaia-capacitas-integration5-c11-integrated.log` |
| C11 ratchet main | PASS0, exit0 | `/tmp/gaia-capacitas-integration5-c11-ratchet.log` |
| Actual final full-file coverage | Tests306 PASS; coverage FAIL100, exit1 | `/tmp/gaia-capacitas-integration5-final-coverage.log` |
| Explicit both-new-spec TypeScript | PASS, exit0 | `/tmp/gaia-capacitas-integration5-final-types.log` |
| Scoped both-new-spec lint | PASS, exit0; existing Next16 deprecation only | `/tmp/gaia-capacitas-integration5-final-lint.log` |
| Protected runtime/config/tooling/old-batch diff | Empty against638a4681 | `git diff --exit-code` |
| Diff whitespace | PASS | `git diff --check` |

Both ratchets use authoritative main baseline/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Diagnostic post-run JSON parsing
initially selected Make's shell `${BASE_REF...}` brace, causing SyntaxError;
corrected to the JSON opening line, independently verifies exact baseline and
empty finding arrays. No gate/source/test failure was bypassed or changed.

Fresh final AST `/tmp/gaia-capacitas-integration5-final-complexity.json` and `.md`
has exactly identical before/after files/callables objects, fingerprints/positions.
Main472cognitive416cyclomatic2631LOC/nesting2/params1; file1099cognitive/
1174cyclomatic3109LOC251callables24error20warning44findings31useState2useEffect:
**all deltas0**. No complexity reduction or runtime decomposition claimed.
Protected runtime/old-batch/baseline SHA256 above remain byte-identical.
No baseline inflation/repair, thresholds, exclusions, scope, ignore, tooling,
shared-config change, test weakening or imported dirty main work.

Historical globalcheck FAIL30 remains separately owned provenance, not run or
recertified in this task. Fullsuite/build/E2E/live stacks **NOT_RUN here**, remain
Coordinator/final-verifier gates. Existing R3 fullsuite evidence does not replace
fresh validation of these new tests. No architectural relationships change,
so no runtime Graphify refresh required; platform-docs graph refresh remains
Coordinator-owned under dedicated Make workflow.

## Classification, files and residual risk

**NO_CHANGE — CHARACTERIZATION_ONLY.** Twelve genuine new cases integrated,
thirteen previously uncovered arms characterized, no runtime reduction/acceptance.
Owned report only plus approved sequential new specs and their source reports:
`campaign-capacitas-particelle-presentation.test.tsx`,
`campaign-capacitas-terreni-residual.test.tsx`, `SLICE_CAPACITAS_C10_2026-10-08.md`,
`SLICE_CAPACITAS_C11_2026-10-08.md`. Report commit SHA delivered to Coordinator
after commit; not self-referentially written into its content.

Public UI/API-boundary fixtures prove current local behavior, not production
permissions/backend persistence/live portal concurrency or GIS UNKNOWN closure.
Full-file100% remains FAIL with26 residual arms; mission ACTIVE/INCOMPLETE.
Stop after report delivery. Recommended next action: independent frozen-source
verification and explicit Coordinator decision for conditional defensive paths
and modal race analysis, not an automatic runtime cleanup or coverage exemption.
