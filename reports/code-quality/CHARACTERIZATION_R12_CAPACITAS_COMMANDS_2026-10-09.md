# R12 Capacitas commands — ORIGINAL characterization

**READY_FOR_REVIEW**, test-only phase. Actual runtime is **NO_CHANGE**.
Global campaign remains **ACTIVE / INCOMPLETE**. No runtime implementation,
commit, staging, pick, push, merge or next hotspot is authorized or performed.

## Authority and frozen source

Coordinator `~/.cache/gaia-campaign/20261009-r12-capacitas/coordinator/CHARACTERIZATION_APPROVAL.md`
and integration ownership registry allocate only the new
`frontend/tests/unit/campaign-capacitas-command-lifecycle-r12.test.tsx` and this
report after readiness/candidate freeze. Both exact freeze hashes were sent
to Coordinator before any test write. Readiness remains immutable c56aab28;
exterior candidate remains immutable b69cbc44. Independent final readiness
report627332b0 supersedes its provisional a10d report by attributed terminal
evidence; the author frozen readiness was not rewritten.

Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261009-r11-capacitas-monitors`,
branch `refactor/complexity-r12-capacitas-commands`, HEAD
`f0b6e00e4f41d2fe54f504d4fe700613ae4b2c83`, main merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Runtime a232, unchanged fraction
policy, all nineteen previous Capacitas specs, config/packages/tooling/scanner/
baseline and all3506protected tracked paths remain byte-exact. The exterior
candidate was never applied to run these tests. No baseline synchronization,
scope exclusion, suppression or coverage waiver.

## Public UI behavior matrix

The new spec adds80cases across Terreni, Particelle, Storico and inCASS.
Each case mounts actual workspace rendering, uses native public buttons,
actual usePolling/timers/visibility handling, deferred ordinary API promises,
plain JSON jobs and genuine ApiError from runtime core. ProtectedPage and the
settings workspace modal use the same boundary isolation as existing specs.
No private React state, fake polling/parser, instrumentation, getter fixture,
unsupported command state or counter-oriented coverage case is introduced.

| New original responsibility | Cases | Assertions and preserved behavior |
| --- | ---: | --- |
|Rerun then deferred list Error/nonError/401/403 |16 |Exact command token/ID, no early list, selected busy before response, requested rather than returned ID confirmation, loading while refresh pending, original rows retained on rejection, ordinary/fallback message versus real expiry guidance, controls released, polling continues only for ordinary errors |
|Captured command token then fresh reload token change/loss |8 |Command uses token-A; reload reads token-B or expires without another API dispatch; refresh loading and final rows/status/error/controls reflect original outcomes |
|Authentic command ApiError401/403 on rerun/delete |16 |Command detail is ordinary visible Error, rows retained, no expiry/guidance or command-driven refresh, busy released; actual subsequent polling still executes |
|Two different-ID reruns, both completion orders |8 |Second dispatch replaces scalar busy ID; first completed command awaits its reload then clears all rerun busy while another API remains pending; both exact API IDs/tokens and ordered reload requests/last confirmation retained |
|Two different-ID deletes, both orders, newer success/Error |16 |Busy moves to newer ID; first settlement clears scalar busy early; successful deletion filters its ID, rejection retains its row, later success clears earlier error while later rejection preserves earlier success status; no list API |
|Delete crossing deferred manual or actual poll list, both orders |16 |Fresh list token/API signatures, manual loading hides rows versus silent poll retaining visible controls, current-row functional filtering preserves newly arrived row14; delete-first late response resurrects row11 and its fresh detail, no automatic delete reload |
|Total |80 |Meaningful timelines rather than branch quota |

The final allocation extends the readiness72case proposal with explicit
different-ID delete success/error outcomes and both rerun completion orders;
the approved public-UI responsibilities determine the count. Four initial
lists run once at mount; active row13 makes real polling reachable while failed
rows11/12 expose legal delete controls. Fresh list replaces13 with14 and changes
row11 detail, distinguishing filtering of current state from a captured list.
No synthetic click of a disabled delete control is used.

All families hide job rows during manual loading. Tests observe public loading,
disabled refresh and confirmations during pending reload, then released row
controls after settlement; they do not claim private busy observation while
rows are hidden. Original scalar busy race is directly observed after the first
reload completes while the second rerun API remains pending.

## Fresh final gates on original runtime

New-spec-only final run: **80PASS / 1spec / zero skips**,6.66s,exit0.
Complete final twenty-spec run: **476PASS / 20specs / zero skips**,61.57s,exit0.
JUnit independently contains476cases,20suites,0failure/0error/0skip.
This is a fresh run of unchanged actual source, not readiness/R11 replay claims.

Explicit full-file coverage includes BOTH workspace and fraction policy:

| Complete file | Statements | Branches | Functions | Lines |
| --- | ---: | ---: | ---: | ---: |
|Workspace |789/789 |818/818 |253/253 |684/684 |
|Fraction policy |9/9 |6/6 |6/6 |8/8 |
|Union |798/798 |824/824 |259/259 |692/692 |

All four dimensions100%,0missing/0skipped. Raw Istanbul JSON has exactly two
complete files; `audit-characterization.cjs` verifies each dimension and saves
`characterization-final-audit.json`, including all19old-spec hashes and protected
path comparison. Full100% existed before these tests; new cases add behavioral
evidence rather than change coverage scope or thresholds.

Fresh project TypeScript exit0. Explicit external test config extends the real
project config/options, includes actual src, next-env, new spec and setup-vitest,
and overrides the project tests exclusion; final exit0. It does not claim
explicit typechecking of every old spec. Fresh ESLint on actual workspace,
fraction policy and all20specs with max-warnings0:exit0,0errors/0warnings.
Tracked/staged diff empty; diff-check and untracked new-spec whitespace check
exit0. Test file and report remain untracked/uncommitted.

## Attempts retained and limits

Spec initial attempt80PASS6.26s. Initial full run476/20/full100%66.06s also
passed. Explicit TypeScript attempt1 failed TS2688 because an external config
resolved vitest/globals relative to its cache directory; only that external
config now gives the real project's absolute vitest globals path. Attempt2
then found two TS2769 diagnostics: getByRole does not accept an `exact` option.
Removed those redundant options from new spec only; string role names already
match exactly by default, preserving assertions. Final explicit attempt3=0,
spec and full coverage rerun on the final file as recorded above. All logs/exits
retained separately, no failed result relabeled PASS; no application repair.

Residual gaps: this rendered matrix does not enumerate every crossed pair of
rerun/delete in the same family, same-ID rerun/delete, overlapping two pending
rerun reload responses, or every command failure combination. Source oracle in
frozen readiness supplements order/microticks but is not rendered coverage.
Rendered tests prove public settlement boundaries, not every individual React
microtick. Existing nineteen specs remain protection for other commands,
rendering, status guards and monitors. Independent original replay/review still
required; candidate runtime application and final certification need separate
Coordinator phase allocation. No claim of actual source IMPROVED is made.

Actual runtime metrics are unchanged from fresh readiness measurements:
combined cognitive926/decisions803/rawcyclomatic1062/callableLOC4677/fileLOC3131/
259callables/17errors16warnings; principal391cognitive/360cyclomatic/2527LOC,
31state2effects. Exterior reduced metrics remain planning evidence only.
Runtime structure did not change, so no frontend graph extraction is needed in
this test-only phase. No raw root Graphify or graph commit occurred.

## Commands and evidence

External evidence `E=/home/cbo/.cache/gaia-campaign/20261009-r12-capacitas/author`.
Executed from actual frontend cwd; logs and exits have corresponding names.

```bash
npm run test:unit -- tests/unit/campaign-capacitas-command-lifecycle-r12.test.tsx --maxWorkers=1
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts \
  npm run test:coverage -- tests/unit/campaign-capacitas- --maxWorkers=1 \
  --coverage.reportsDirectory="$E/characterization-coverage-final" \
  --reporter=default --reporter=junit --outputFile.junit="$E/characterization-junit-final.xml"
./node_modules/.bin/tsc --noEmit --incremental false
./node_modules/.bin/tsc --noEmit -p "$E/characterization-tsconfig.json"
./node_modules/.bin/eslint --max-warnings=0 src/components/elaborazioni/capacitas-workspace.tsx \
  src/components/elaborazioni/capacitas-fraction-resolution.ts tests/unit/campaign-capacitas-*.test.ts*
cd ..
git diff --check
git diff --no-index --check /dev/null frontend/tests/unit/campaign-capacitas-command-lifecycle-r12.test.tsx
node "$E/audit-characterization.cjs"
```

Final logs: characterization-spec-final, characterization-coverage-final,
characterization-project-type, characterization-explicit-type-attempt3,
characterization-owned-lint-final. All corresponding .exit files0. Earlier
spec-attempt1/coverage/explicit-type/explicit-type-attempt2 logs retained.
All processes terminal; heavy author window **RELEASED**. No build/browser/
backend/worker or broad unrelated frontend suite was run.

| Frozen artifact | SHA256 |
| --- | --- |
|New ORIGINAL characterization spec |6ca512806be4ebf2e399e1df7da735ecd37986eb485f7ca3b0cea9a6ac90189d |
|Actual unchanged workspace |a23270634778b1243fb8ce2e01deef704ee0620a857b93b6a79591cd11c7474e |
|Unchanged fraction policy |0d635381b311c18477aeef375713cf336114329350bd74791a4d6da447c574eb |
|Frozen author readiness |c56aab28792a9dd6060bf3b6db6b670c64e6d2b4d38cc8475c8918e16f45e9d8 |
|Frozen exterior candidate |b69cbc44b3c219503c940304ce9c1b335faeb7f3703d7569267ba5104bac555d |

This report hash is delivered separately. Stop terminal **READY_FOR_REVIEW**,
with only previously authorized readiness plus the new spec/report untracked.
Next action is independently authorized original replay; no runtime edit yet.
