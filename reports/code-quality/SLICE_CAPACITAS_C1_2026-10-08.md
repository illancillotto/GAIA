# Capacitas C1 — Terreni monitor/actions characterization

## Ownership and preflight

Coordinator authorization registry `a31d9beb`. Dedicated worktree
`GAIA-campaign-20261008-c1-tests`, branch
`refactor/complexity-capacitas-terreni-tests`; initial HEAD
`39dbcc40273cfca699b576b8445ccd378e822a46`, merge-base main
`55a1b1d35911451e018b662c2acc450bf5994ea2`.
Initial status included a Coordinator-prepared untracked `.venv` dependency
symlink; this agent neither deletes nor commits it. Runtime/scoped existing
test diffs clean. Recent Capacitas runtime commits31d1cec5/073d3898/17526b29
remain untouched. Own only new Terreni spec and this report.

Read checkpoint/project skill, code-quality policy/references and
`PLAN_CAPACITAS_COVERAGE_2026-10-08.md`. Runtime, existing19 batch tests,
shared files, config, complexity tooling/baseline and ignored-branch scope
are read-only. No integration or GIS runtime work is performed.

## Baseline / target callable / metric delta

Fresh targeted scanner objects before and after are exactly equal:

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| ElaborazioniCapacitasWorkspace cognitive | 472 | 472 | 0 |
| Main cyclomatic / callable LOC | 416 / 2631 | 416 / 2631 | 0 / 0 |
| Main nesting / params | 2 / 1 | 2 / 1 | 0 / 0 |
| Effective file LOC / callable count | 3109 / 251 | 3109 / 251 | 0 / 0 |
| Cognitive / cyclomatic sums | 1099 / 1174 | 1099 / 1174 | 0 / 0 |
| useState / useEffect | 31 / 2 | 31 / 2 | 0 / 0 |
| Error / warning / findings | 24 / 20 / 44 | 24 / 20 / 44 | 0 / 0 / 0 |

Artifacts `/tmp/capacitas-c1-{before,after}-metrics.{json,md}`.
This is characterization, not a complexity refactor.

## Behavioral invariants and test boundaries

Render the real embedded workspace, real Terreni completion/error modals,
real stat/table rendering and real `usePolling`. Mock API/token/auth,
ProtectedPage and unrelated settings-modal boundaries only. Visibility is
controlled through its browser getter; fake time advances real polling.
All job/result fixtures are local and typed; delete API success returns void,
not an invented response payload. No exported private closures/setters,
fake React state, mocked polling or production instrumentation.

- Silent pending→succeeded/completed_with_errors/failed transitions open the
  report once. A second active job retains polling; already-terminal job is
  not announced again after close. Manual refresh does not open this notice.
- Manual refresh shows loading and disables its button; silent refresh does
  not. Silent ordinary errors stay silent, silent success retains an existing
  manual error, explicit success clears it. Session recovery clears the error
  but retains the existing instructional status message.
- Auth Error/non-Error or token loss stops polling, not backend jobs. Explicit
  restored-token refresh resumes it. Hidden ticks skip, visibility restores
  polling, slow requests do not overlap, unmount removes timers/listeners.
- Rerun awaits its command before refreshing; busy spans command and refresh.
  Delete retains its row until successful await, removes only the target and
  does not refetch. Both preserve rows/action recovery on errors; missing
  token does not dispatch. Other rows keep their action availability.
- Report counters, status/date fallbacks and optional speed/worker/throttle
  display preserve current output. Error details include only failed items,
  label/search-key and diagnostic fallbacks, with header/footer close actions.
- Open modals prefer current job data from the list; removal falls back to
  the original selected snapshot. Refresh can legitimately replace a failed
  result with empty/null data while the error modal remains open.

## Characterization matrix

| Behavior | Existing test | Added C1 evidence | Result |
|---|---|---|---|
| Pending→three terminal statuses, notification once | Existing batch only timer cleanup | Three real15sec transition cases with another active job and repeated poll | PASS |
| Manual versus silent refresh | No direct cases | Deferred loading, no manual completion notice, silent error suppression and retained/cleared error contracts | PASS |
| Initial Error/non-Error monitor failure | No | Two failure cases, explicit list recovery | PASS |
| Auth Error/non-Error recovery | No | Two classified polling failures, stopped timer, restored-token refresh/resume | PASS |
| Token absent at mount/lost during polling | Existing batch loss before create | No monitor API until restoration, stop/resume sequence | PASS |
| Hidden tab, slow request overlap and unmount | Existing unmount only | Real visibility getter/timer/listener lifecycle, deferred polling | PASS |
| Rerun ordering/busy and refreshed state | No | Deferred command→deferred refresh, target/other-row buttons and exact token/id | PASS |
| Delete target/order/no refetch | No | Deferred void result, row retained then targeted removal | PASS |
| Command Error/non-Error retries | No | Four rerun/delete failure cases with row retained and retry clearing error | PASS |
| Command no-token guards | No | Two distinct buttons do not dispatch | PASS |
| Report/errors/filtering/close | No | Mixed successful/failed typed result, counters, labeled/key-only diagnostics and both close controls | PASS |
| Current-job versus selected snapshot | No | Open report refresh and selected row deletion | PASS |
| Open errors with empty/null refreshed result | No | Real API response refresh, no fake state | PASS |
| Status/date/options/processed counts | No | Nine statuses, valid/invalid/absent dates, default/explicit options and active report | PASS |
| Invalid/unavailable result payloads | No | Four public result_json values remain diagnostic rows, never enter invalid report | PASS |

28 new cases + unchanged19 original batch cases = **47 PASS, zero skips**.
Tests inspect observable request/UI ordering and data, not assertion-free
render matrices. Progress is the runtime's current processed/imported/linked
display; no nonexistent progress-percent contract is invented.

## Test execution and construction corrections

Fresh before: original19PASS, full-file coverage gate FAIL100% (expected).
Initial C1 spec run had **21 PASS / 7 FAIL**, caused by ambiguous new selectors:
terminal diagnostic appears in both row and report; both icon and footer
buttons have accessible name `Chiudi`. Corrected assertions check both visible
diagnostics and select actual footer text or header aria-label. Runtime and
existing tests stay unchanged; first failure log retained
`/tmp/capacitas-c1-focused.log`, not relabelled PASS.
The delete boundary double was also aligned to the declared Promise<void>
API contract. Corrected noncoverage focused run **47PASS**, exit0,
`/tmp/capacitas-c1-focused2.log`.

Final coverage run includes all47 cases, **47PASS**, but **exit1 for full-file
coverage thresholds**. It does not meet repository coverage compliance.
Artifact `/tmp/capacitas-c1-final2.log`, V8 JSON
`/tmp/capacitas-c1-final2-coverage/coverage-final.json`.
Earlier coverage logs remain `/tmp/capacitas-c1-{before,after,final}.log`.

## Honest full-file coverage before / after

Same857 statements/929 branch arms/251 functions/748 lines; all four100%
thresholds remain enforced, include/exclude/config unchanged:

| Counter | Before | After | Covered delta | Before % | After % |
|---|---:|---:|---:|---:|---:|
| Statements | 305/857 | 386/857 | +81 | 35.58 | 45.04 |
| Branch arms | 263/929 | 358/929 | +95 | 28.31 | 38.53 |
| Functions | 46/251 | 66/251 | +20 | 18.32 | 26.29 |
| Lines | 288/748 | 362/748 | +74 | 38.50 | 48.39 |

Remaining full-file gaps: **471 statements, 571 branch arms, 185 functions,
386 lines**. This branch began before sibling C6/C7 test integration, so the
cumulative claim is original19+C1 only, not an unexecuted sibling combination.

Assigned observed bands have no missing counter:

| Physical source band | Statements | Branch arms | Functions | Lines |
|---|---:|---:|---:|---:|
| Terreni completion/error modals117–245 | 11/11 | 27/27 | 6/6 | 10/10 |
| Terreni monitor loader754–806 | 33/33 | 27/27 | 5/5 | 32/32 |
| Rerun/delete948–981 | 25/25 | 8/8 | 4/4 | 21/21 |
| Terreni job table2497–2621 | 7/7 | 40/40 | 5/5 | 7/7 |

Band counters are diagnostic subdivisions, not coverage exclusions or a
substitute for complete file100%. Full JSON inspected; missing locations and
raw counts `/tmp/capacitas-c1-counters.json`, generated read-only from V8 JSON.
Other section/parser/invariant-sensitive gaps from the plan remain unresolved.

Command from frontend (all100% gates intentionally still fail):

```bash
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-batch.test.tsx \
  tests/unit/campaign-capacitas-terreni.test.tsx --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/capacitas-c1-final2-coverage
```

Before uses only unchanged batch spec and reports to
`/tmp/capacitas-c1-before-coverage`. No threshold override, private-code export,
new ignore, sparse impossible parser result or hidden runtime tail.

## Validation

- Focused Vitest: PASS47/zero skips, `/tmp/capacitas-c1-focused2.log`.
- Coverage run tests: PASS47; coverage gate **FAIL100%**, as above.
- Typecheck: PASS, `/tmp/capacitas-c1-typecheck-final2.log`.
- `npm test`: PASS18 smoke, `/tmp/capacitas-c1-smoke.log`.
- Scoped new-spec ESLint from frontend: PASS, `/tmp/capacitas-c1-lint-final3.log`.
- `make complexity-ratchet BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python`:
  PASS0/exit0, `/tmp/capacitas-c1-ratchet.log`.
- `git diff --check`: PASS.

No build/full repository suite/E2E/integration is run or claimed by this unit.
An extra lint invocation from repository root exited0 but emitted Next's
pages-directory diagnostic because of the wrong CWD; log
`/tmp/capacitas-c1-lint-final2.log` retained. The final correct frontend-CWD
check above emits no diagnostic; config/rules are not disabled or changed.
Graphify orientation dedicated frontend query could not find worktree graph,
`/tmp/capacitas-c1-graph.log`. No runtime responsibility/dependency changes;
no generated graph or generic root extraction is added.

## Preservation and classification

Runtime SHA256 remains
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`;
original19-suite SHA256 remains
`4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`.
Runtime, existing tests, frontend package/Vitest config, baseline/exceptions
and Python/Babel scanners compare byte-identically with HEAD. No suppression,
baseline inflation, threshold or scope edits, existing test weakening or
runtime complexity transfer.

**NO_CHANGE — CHARACTERIZATION_ONLY.** Readiness improves; runtime complexity
does not. Capacitas refactoring remains **BLOCKED_BY_FULL_FILE_COVERAGE**.

## Files changed / commit

- `frontend/tests/unit/campaign-capacitas-terreni.test.tsx`
- `reports/code-quality/SLICE_CAPACITAS_C1_2026-10-08.md`

Authorized coherent commit message:
`test(elaborazioni): characterize Capacitas Terreni monitor actions`.
Resolve exact slice SHA with
`git log -1 --format=%H -- reports/code-quality/SLICE_CAPACITAS_C1_2026-10-08.md`.

## Residual risks / next slice

API doubles cannot certify live portals, real authorization or all distributed
DB races. Other three monitors are not certified by Terreni tests. Relative
timers are real hook timers under fake time; this is not an E2E visibility
test. Fixed dates are display fixtures, not age-dependent search windows.
Existing retained status-message behavior is characterized, not corrected.

Stop READY_FOR_REVIEW after this test-only unit. Remaining coverage-plan
responsibilities need distinct ownership and combined independent measurement;
no runtime refactor is authorized by these local green bands.
