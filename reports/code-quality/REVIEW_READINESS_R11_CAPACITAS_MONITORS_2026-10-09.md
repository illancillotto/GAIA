# R11 Capacitas Monitors — Independent Readiness Review

## Ownership and snapshot

Global campaign remains **ACTIVE / INCOMPLETE**. Original attachment,
checkpoint skill, root AGENTS, repository complexity skill/workflow/constraints,
quality-ratchet, metrics and validation apply. This is one monitor lifecycle
readiness review, not global completion. Registry in integration:
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R11_CAPACITAS_MONITORS_2026-10-09.md`.

Reviewer worktree `GAIA-campaign-20261009-r11-capacitas-monitors-review`, branch
`review/complexity-r11-capacitas-monitors`, initial HEAD
`d2f222f9b48a2e8b728ad2801a240f2d9bdd0ba5`, merge-base/main
`55a1b1d35911451e018b662c2acc450bf5994ea2`, initially clean. Sole writable
repository path is this report. Runtime/tests/config/baseline/scanner unchanged;
no commit/integration authorized. Main concurrent work untouched.

External independent scaffolding/results:
`/home/cbo/.cache/gaia-campaign/20261009-r11-capacitas-monitors/reviewer/`.
Installed main node_modules symlink is ignored; no install/library change.
Vitest4.1.6, TypeScript5.8.3, Babel parser7.29.7. Graphify orientation dedicated
`make graphify-frontend-query` initially fails because review corpus has no graph;
same target against existing integration corpus succeeds. No generic root
extraction or graph modifications; Graphify is not numerical complexity proof.

## Fresh original baseline

Independent unchanged AST engine original workspace hash
`a409e88725f0c251df7e93560c909b4464d487f382ce8ceb74787c23b2c60b59`,
R10 fraction-policy hash
`0d635381b311c18477aeef375713cf336114329350bd74791a4d6da447c574eb`.

| Metric | Workspace | Combined with unchanged R10 policy |
| --- | ---: | ---: |
| Principal cognitive / cyclomatic / LOC | 455 / 404 / 2625 | same |
| Cognitive sum | 1019 | 1022 |
| Cyclomatic sum | 1120 | 1129 |
| Decisions sum(cyclomatic - 1) | 869 | 872 |
| Callable count / callable LOC | 251 / 4776 | 257 / 4789 |
| File LOC | 3105 | 3140 |
| useState / useEffect / useReducer | 31 / 2 / 0 | same |
| Error / warning | 22 / 19 | same |

Original loader cognitive/cyclomatic/LOC: Terreni21/15/47,
Particelle21/15/42, History25/18/46, inCASS21/15/42. Each nesting2/params1.

## Reconstructed behavioral contracts

All four synchronously read stored token before any loading/API work. Missing
token sets expiredtrue, exact family error, exact family resume message, then
returns without loadingtrue/false. Silent does not suppress expiry. Normal
requests set loadingtrue before list; successful list clears expired before
family application; normal success clears error after application. Ordinary
normal rejection classifies auth first, then instanceofError/message/fallback;
silent ordinary rejection does not read message or clear existing error. Auth
rejection performs expiry sequence and returns, but finally still releases
normal loading. `isAuthError` really accepts only ApiError401/403, not arbitrary
status401 dictionaries. inCASS list arguments exactly token,{limit:300}.

| Family | Successful application ordering and short-circuit contract |
| --- | --- |
| Terreni | Read current previous in-flight ref; only silent AND nonempty previous set scan FIRST matching terminal job in API order and open modal; then replace in-flight ref, then set jobs. Normal refresh never opens completion modal. |
| Particelle | Read previous ref, replace ref, set jobs; only normal AND nonempty previous AND matching terminal job set completion notice. |
| History | Read previous ref, replace ref, set jobs; scan FIRST terminal result passing actual result guard; repeat same guard before setting stored result; then normal tracked-terminal notice. Do not remove repeated guard. |
| inCASS | Read previous ref, replace ref, set jobs; normal tracked-terminal notice only. |

Terminal set is succeeded/completed_with_errors/failed. In-flight filter is
pending/processing/queued_resume, retaining order and duplicate ID semantics
of original filter/map/newSet. Never replace ID short-circuit with eager status
evaluation. History's displayed valid first job may override stored terminal
result; empty/nonvalid future lists retain previous report. Terreni open modal
follows current jobs, then falls back to snapshot after disappearance.

Refs are read when a response resolves, not captured at dispatch. No request
generation or cancellation check exists in these loaders. Polling prevents
poll-to-poll overlap only; manual refresh may overlap polling and old responses
may replace newer state or clear newer expiry. Preserve these races, not fix
them. Original usePolling callback latest-ref update, enabled/interval options,
effect declarations/dependencies, hidden/visible handling and cleanup remain
unchanged. Commands await list refresh before releasing their own busy state.

## Independent original replay

Coordinator transferred heavy coverage slot after author terminal original run.
Fresh reviewer command from frontend:

```text
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts ./node_modules/.bin/vitest run tests/unit/campaign-capacitas-*.test.ts* --maxWorkers=2 --coverage --coverage.reportsDirectory=<reviewer-evidence>/original-coverage --reporter=default
./node_modules/.bin/tsc --noEmit --incremental false
./node_modules/.bin/eslint src/components/elaborazioni/capacitas-workspace.tsx src/components/elaborazioni/capacitas-fraction-resolution.ts tests/unit/campaign-capacitas-*.test.ts*
```

338 tests /18specs **PASS**, zero skips,22.71s. Actual coverage-final maps:
workspace857/857statements,873/873branches,251/251functions,748lines100%;
R10policy9/9statements,6/6branches,6/6functions,8lines100%.
Combined866s879b257f756l100%. Typecheck/lint PASS. Process handles41022,
74755,83836 terminal exit0; do not repoll/restart. Frozen relevant runtime,
all Capacitas tests/config/baseline/scanner/package hashes unchanged afterward.
Independently compared author/reviewer raw statement/function/branch maps and
all hit-count arrays: identical for both files, modulo absolute path only.

## Characterization matrix

| Behavior | Existing test | Missing | Proposed added | Result |
| --- | --- | --- | --- | --- |
| Four normal/silent/token/auth/error contracts | Family monitor specs | Exact cross-family overlapping expiry chronology | Deferred real UI refresh+timer responses, both orders, with genuine ApiError401/403 | Original338PASS; new tests not authorized |
| Polling intervals/visibility/singleflight/cleanup | All four monitor specs, real usePolling | None for unchanged hook scope | Retain unchanged suites | PASS |
| Manual versus polling stale completion | inCASS monitor late-manual test | Terreni/Particelle/History cross-order outcomes | Two deferred list requests, assert actual rows/status/loading | Proposed |
| First terminal of multiple Terreni completions | Terreni single completion variants | Explicit multiple simultaneous tracked terminals/API order | Poll actual timer, completion modal ID; reverse API order | Proposed |
| Empty ref/unrelated terminal/silent notice suppression | Existing family cases | Explicit retained/ref consumption after overlap | Deferred original UI timelines | Proposed |
| History first-valid terminal/result retention | Storico monitor cases | Overlap stored-result chronology | Deferred ordered reports, invalid latest and empty refresh | Proposed |
| Helper lazy access/setter throws | No new helper exists yet | Direct unit cases for future authorized runtime | Typed helper tests, real guards, throwing callbacks; supplementary only | Not executed as implementation tests |

Source timing oracles supplement these rendered tests, never replace missing
characterization/coverage. No private React state, fake parser/polling or
fabricated API payload getters to obtain coverage.

## Adjacent prototype independent review

Author external adjacent workspace hash
`79b1fd78216077eeca77e2efd900dd50af5815b488d30e76a8fa5bcdf5db25a3`,
monitor helper hash
`98fa8f9eb5562ba9bba48e05074fd9f1f330febb76a61f301da4a8d7a512fc97`.
This is NOT applied runtime. Typed closed-family lifecycle removes repeated
token/loading/session/error/finally orchestration. Seven fields (not eight)
comprise coherent monitor ports: family,list,apply and four setters; no DB,
miscellaneous state, generic manager or untyped megaContext. Family-specific
application remains named closure, same hook state/setters/ref timing. Synchronous
list adapter retains inCASS arguments. Returning shared async promise rather
than introducing an extra async wrapper preserves settlement timing.

Independent AST counts ALL nested/new callbacks, including helper filter/map/
find/some. Combined with unchanged R10policy:
cognitive1022→902(-120),decisions872→788(-84),rawcyclomatic1129→1048(-81),
callables257→260(+3),callableLOC4789→4654(-135),
effectiveLOC3140→3150(+10). Principal455→391,404→360,2625→2534LOC;
workspace3105→3021LOC. Newhelper94LOC/10callables, refreshcog12/cyclo9/
LOC33/nest2/params2; all new helper callables below warning thresholds.
Combined error22→17,warning19→16. LOC growth disclosed; no simple transfer of
the original88cognitive into a helper. Familyapplycognitive5/5/9/5.

Independent extracted-source oracle uses actual source ApiError/isAuthError and
history-result guard, exact original/candidate loaders plus helper. 3920
single/overlap traces cover missing tokens, synchronous storage throws,
ordinary typed/untyped/auth401/403,
status-only401 nonauth, previous sets, list order, four silent combinations,
both completion orders, setters/ref/API/result guards and caller settlement
at12microticks per completion: PASS. No UI/reachability/coverage claim. Original
versus candidate protected source (everything except allocated loaders/helper
import/new family applications) identical modulo whitespace, including JSX,
commands/readers/hooks and R10 decisions.

## Rejected designs and gating risk

**Adjacent draft REJECTED for implementation as-is**: independent unchanged
scanner full-context comparator against merge-base55a yieldsFAIL4. Unchanged
R10 fraction-submit Programanonymous callback shifted3198→3116; line fallback
matches baseline3122 callback, reports cyclomatic2→4,cognitive1→3,LOC2→22,
nesting0→1. This is not an actual family behavior regression, but cannot be
waived or hidden: authoritative actual ratchet must still pass. Do not rename
legacy anonymous callbacks, pad blank lines, modify scanner or baseline.

Initial inline variant may preserve positioning but parent fileLOC3105→3106
violates current-file no-growth planning rule. Rejected, not waived.

## Selected inline variant — independent design approval

Author subsequently eliminates unnecessary single-use terminal-status wrapper
and keeps original direct private Set.has in history application. Cohesive
lifecycle/selectors remain local to the existing workspace, not another
monolith. Shared private refresh requires silent:boolean; all four wrappers
explicitly forward their retained silent=false defaults. No new inaccessible
default arm or test-driven export. This is a substantive semantic simplification,
not line padding/format compression/legacy-symbol renaming to repair matching.

Fresh independently parsed selected hash:
`2a2199ccd52b942fab54a1fff0878431b1ff6b7516bcaff2c03bd875b39e60f5`.
ParentfileLOC3105→3103; combined3140→3138(-2). Full workspace253callables,
899cognitive,1038rawcyclomatic,785decisions,4638callableLOC. With unchanged
fractionpolicy:259callables(+2),902cognitive(-120),1047rawcyclomatic(-82),
788decisions(-84),4651callableLOC(-138). Principal391/360/2534,
31state/2effect unchanged. Error17/warning16; all new helpers below thresholds.

Fresh independent unchanged-scanner full-context merge-base55a comparator
**PASS0**. It remains external design comparator, NOT implementation ratchet.
Independent3920trace/12microtick replay PASS including synchronous token throws
and outer caller rejection/settlement traces. Protected all-other-source
comparison PASS, history repeated guard retained. The earlier adjacentFAIL4
and initial-inlineLOC regression are retained as rejected evidence.

**APPROVED FOR ORIGINAL CHARACTERIZATION PHASE ONLY**, conditional on
Coordinator explicit allocation. Selected design offers genuine combined
decision/cognitive reduction with no transferred hotspot or threshold changes.
Actual runtime source, rendered transition tests, full-file coverage, ratchet,
review and final certification still required; prototype hashes/results do
not authorize automatic runtime edits or source commits.

## Classification and recommendation

Readiness-only **REORGANIZED_AND_CHARACTERIZED**, no runtime improvement claim.
Original replay and behavioral contracts proven; adjacent numeric reduction is
substantive but gate failure blocks that exact design. Selected inline design
independently approved for ORIGINAL rendered race characterization first.
Runtime edits/commit/fullfile100%/actual ratchet/source review/final
certification/integration remain separate phases. No final suite/build/browser
certification executed here. Highest callable455 remains extreme in actual
runtime; global debt/target completion is not achieved by readiness.

## Files and residual risks

Only this readiness report added, unstaged/uncommitted. Protected frozen hashes
PASS and working tree otherwise clean. Prototype proofs freeze independently;
new variations require new metrics/oracles/comparator. Supplementary scaffolding
does not prove DOM batching/render timing, native browser behavior, unreachable
throws or exhaustive concurrency; proposed real-UI deferred tests address actual
race-sensitive contracts before runtime authorization. Baseline inflation,
threshold changes, exclusions, ignore and unrelated refactors remain forbidden.
