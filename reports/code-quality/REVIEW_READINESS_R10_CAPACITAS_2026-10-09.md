# R10 Capacitas — Independent Readiness Review

## Scope and provenance

The original complete campaign attachment was read locally. Its global
objective remains **ACTIVE / INCOMPLETE**; this is one highest-hotspot readiness
review, not an alternative easier target or a campaign completion claim.

Authoritative ownership is
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R10_CAPACITAS_2026-10-09.md` in the
integration checkout. Reviewer checkout:
`/home/cbo/CursorProjects/GAIA-campaign-20261009-r10-capacitas-review`, branch
`review/complexity-r10-capacitas`, clean starting HEAD
`10784e761ded91383f9c8aa70ee02b25e18872cc`.

Only this report is owned. Runtime, tests, baseline, configuration, tooling,
main, concurrent work and existing worktrees remain read-only. No commit or
integration is authorized here. External scaffolding is under
`/home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/reviewer/`, created through
`apply_patch`; generated proof outputs are outside the checkout. The ignored
`frontend/node_modules` symlink points to the matching installed main dependency
tree; no dependency or library was modified.

Checkpoint skill, root AGENTS, repository complexity skill and its workflow,
constraints, quality-ratchet, metrics and validation documents apply. Versioned
C12, defensive provenance and modal reachability reports orient the review.
Old `/tmp` artifacts were lost; their historical results are **not** fresh proof.

## Fresh original baseline

Runtime `frontend/src/components/elaborazioni/capacitas-workspace.tsx` SHA256:
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`.

The unchanged versioned AST engine ran independently on the original source:

| Metric | Fresh original |
| --- | ---: |
| Principal cognitive / cyclomatic / LOC | 472 / 416 / 2631 |
| Principal nesting / parameters | 2 / 1 |
| File cognitive / cyclomatic sums | 1099 / 1174 |
| File decisions, sum(cyclomatic - 1) | 923 |
| File callable count / effective LOC | 251 / 3109 |
| File useState / useEffect / useReducer | 31 / 2 / 0 |

Command:

```text
node tools/code_quality/js_ast_metrics.mjs frontend/src/components/elaborazioni/capacitas-workspace.tsx > /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/reviewer/original-ast.json
```

Coordinator subsequently transferred the heavy focused slot after author's
original union ended. Fresh independent unchanged-source replay: **312 PASS /16
specs, 0 skip, 37.16 seconds**, statements857/857, functions251/251,
lines748/748, branches906/929 (97.52%). Coverage command exits **1** on the
unchanged100% branch threshold. Full-file gate remains FAIL, not a waiver.
`original-replay-ledger.json` verifies all23 missing source-arm coordinates and
their exact identity with author's newly generated ledger. No fresh ratchet,
build or browser PASS is claimed.

```text
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/reviewer/original-coverage
```

## Installed library and fresh genuine-input oracle

Installed SheetJS is **0.20.3**, independently checked in package metadata and
loaded module. Both installed entry points were exercised, without substitution:

| Entry point | SHA256 |
| --- | --- |
| `xlsx.mjs` | `1a0fb062ee9781b13f6687371b202aaefc53b6ce55b530c027e01f9c087b77db` |
| `xlsx.js` | `fd159f1e2d694e12cd0709c1ec1b63c6e1f045d2c4ce857a346f9b965798cbfa` |

The ESM source hash matches versioned provenance. `make_json_row` at 27487
uses an object when header is omitted. `sheet_to_json` at 27531 initializes a
fresh array, appends only `out[outi++] = row.row`, then sets length to `outi`.
Actual options are exactly `{ defval: null, raw: false }`; header, blankrows
and skipHidden are omitted. Hence a successful call returns dense non-null
object rows, or throws; skipped sheet rows do not create holes. Type overloads
alone would not establish that contract. An upgrade or changed options requires
reverification; this is not a generic promise about every SheetJS invocation.

`original-oracle.mjs` selects the five private reader/header/cell declarations
through TypeScript AST, validates the whole runtime hash, freezes their exact
original source and transpiles that extraction. It uses unmodified installed
ESM/CJS SheetJS to serialize and parse real CSV/XLSX bytes. File-boundary objects
provide the actual reader's text/arrayBuffer interface; they are not parser
mocks. All **56** outcomes pass: 14 fixtures x 2 formats x 2 library entries.
Every successful row has its own array index and is a non-null object.

Fixture matrix: ordinary import, alias priority, normalized header collisions,
duplicate raw headers, interior blank rows, note-only skipped rows, header-only,
empty, missing columns, compressed invalid-row numbering, history collision,
history one-column/null conversion, history empty and history missing columns.

Specific preserved outputs:

- Alias-list priority wins over worksheet column order: comune over frazione
  and localita, particella over mappale, sub over subalterno.
- Different raw headers normalizing to the same key use the **last** raw key:
  `COMUNE` then ` Comune ` reads the second cell.
- Exact duplicate raw headers are suffixed by SheetJS; `comune,comune` leaves
  canonical comune reading the **first** cell. These are different contracts.
- Empty physical rows disappear before reader iteration. A malformed fourth
  physical row after an interior blank raises original `Riga 3 non valida`, not
  a newly "corrected" physical row number.
- Terreni output always constructs string comune/sezione/foglio/particella/sub
  and computed label; history intentionally converts empty identifiers to null.

Command `node /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/reviewer/original-oracle.mjs`
exits 0. Exact source and observations live in `frozen-original-readers.ts`,
`frozen-original-updaters.json`, `original-oracle-results.json`. This is a
function/library equivalence oracle, **not rendered UI coverage**.

## Complete residual-arm classification

Branch IDs are coverage-artifact-specific; original expressions/lines identify
the candidates. Below are all 21 conditional arms, separately from the two
unknown modal arms. No arm has been removed by this review.

| Line / arm | Original fallback | Classification and current proof |
| --- | --- | --- |
| 258 | normalized value nullish to empty | JS_CONSTRUCTION: every callsite supplies Object.keys strings, including empty strings; no other private callsite |
| 281 | Terreni extension pop nullish | JS_CONSTRUCTION: File.name is string; split on dot always returns at least one string |
| 291 | Terreni first object nullish | SHEETJS_CONTRACT: nonempty dense successful object output |
| 293 | Terreni first object nullish again | SHEETJS_CONTRACT: same unchanged output, no yield or mutation |
| 313 | Terreni indexed object nullish | SHEETJS_CONTRACT: bounds-checked dense iteration |
| 314 | selected comune mapping nullish | JS_CONSTRUCTION: selected alias is in the Set built from the same keys as Map; raw values are strings |
| 315 | selected foglio mapping nullish | JS_CONSTRUCTION: same Map/Set invariant |
| 316 | selected particella mapping nullish | JS_CONSTRUCTION: same Map/Set invariant |
| 317 | selected optional sezione mapping nullish | JS_CONSTRUCTION: when optional key exists it has a string mapping; absent-key branch stays meaningful |
| 318 | selected optional sub mapping nullish | JS_CONSTRUCTION: same optional-key distinction |
| 378 | history extension pop nullish | JS_CONSTRUCTION: same genuine string split invariant |
| 388 | history first object nullish | SHEETJS_CONTRACT: nonempty dense successful object output |
| 390 | history first object nullish again | SHEETJS_CONTRACT: same unchanged output |
| 403 | history indexed object nullish | SHEETJS_CONTRACT: bounds-checked dense iteration |
| 404 | selected subject_id mapping nullish | JS_CONSTRUCTION: same Map/Set invariant, absent optional key still meaningful |
| 405 | selected idxana mapping nullish | JS_CONSTRUCTION: same invariant |
| 2056 | array length nullish | JS_CONSTRUCTION: successful Array.isArray on synchronous plain API JSON guarantees defined length; preserve outer Array.isArray/null decisions |
| 2482 comune | preview key comune nullish | BUILDER_CONSTRUCTION: mandatory validated normalized string |
| 2482 sub | preview key sub nullish | BUILDER_CONSTRUCTION: optional sub constructed as string, including empty |
| 2483 | preview label nullish | BUILDER_CONSTRUCTION: computed string on every pushed item |
| 2484 | preview comune nullish | BUILDER_CONSTRUCTION: same validated string |
| 3166 | selected updater null arm | UNKNOWN: no fresh or versioned genuine null witness for this synchronous event; defense MUST remain semantically |
| 3206 | started updater null arm | UNKNOWN: same; synchronous token check does not prove all React replay/rebasing schedules |

Totals: **15** JS/builder construction arms + **6** version/options-dependent
SheetJS arms + **2** unknown modal arms = **23** inherited missing arms.

Preview-state inventory is exhaustive: initial empty list at 579; successful
reader result assignment at 1082; clearing on upload error at 1086 and UI clears
at 2261/2299. No API job payload populates this preview. `slice().map()` retains
builder objects. History monitor's API JSON is not the preview construction
proof. No fake private setter, built-in monkeypatch, parser fabrication or
accessor-bearing fake API JSON is accepted as coverage.

Meaningful guards must remain: no-sheet guards 285/382, empty-data checks,
column validation, stringifyImportCell null handling, optional column branches,
row validation/skipping, outer payload Array.isArray and UI presence conditions.
Versioned empty-workbook tests use actual malformed-but-parser-accepted OOXML;
no-sheet is reachable, not a SheetJS density counterexample.

## Modal invariants and characterization matrix

All seven state writers were independently inventoried. State initializes null;
Risolvi replaces it with a fresh object, radio updates selection, close sets
null, start sets busy/error, then one completion sets success or error. No
effect, section change or list setter clears it.

Versioned native keyboard witnesses and C12 characterize **reachable** null
arms at 3214/3217/3220. Old volatile browser proofs are not rerun or counted as
fresh official coverage here. These three guards are NECESSARY. Neither the
two UNKNOWN synchronous guards nor any late-response guard is authorized as
dead code. A shared domain policy may centralize the invariant but must retain
null unchanged for **every** event.

| Public transition | Behavior that must remain |
| --- | --- |
| Open/select | Fresh row object; first candidate/empty selection; radio changes only selectedFrazioneId |
| Missing token | No busy change and no API request |
| Begin | Functional update; busy true, error null; retain selection, row and success |
| Pending radio change | Radios remain enabled; request keeps original captured fraction while current selection can change |
| Success | Current modal gets busy false/success true; original captured row removed even if current modal is null/replaced; retain existing error/selection |
| Unsuccessful result | Current modal gets busy false/error `result.error ?? "Errore sync"`; empty string remains empty; retain success/selection/row |
| Rejection | Current modal gets busy false/error from Error.message or `"Errore"`; retain other fields |
| Background keyboard replacement | Pending original request updates replacement modal, not a request-owned modal; preserving this existing behavior is intentional |
| Replacement close then old completion | Stay null for success, failure and rejection; success still filters captured original row |
| Close/reopen | Reopening builds clean new state; no newly added stale-result suppression |
| Rapid events/StrictMode | Keep functional updater queue semantics, repeatable evaluation and original captured render closure |

The five original updater arrow expressions are frozen directly from AST.
Independent extracted-function checks pass for each null/object outcome and
retained row identity. Separate accessor-read probes establish that on null,
selected candidate.frazione_id, unsuccessful result.error and rejected Error.message are **not evaluated**;
on a non-null state they are evaluated inside the updater. These symbolic
laziness probes are not API fixtures, React execution or reachability evidence.

## Proposed design boundary

The author's proposed closed typed domain event policy is conditionally
reasonable: selected/started/synchronized/unsuccessful/rejected events with
correlated payloads and five concrete domain patch factories, behind one
nullable-state invariant. It can eliminate four repeated decisions while
preserving every semantic null defense. It is not accepted merely because
moving callback branches lowers the principal metric.

Required checks before approval:

1. Concrete event-payload types enforce correlation without arbitrary patches,
   optional catch-all fields or casts that accept unrelated payloads.
2. Return null before table lookup/factory evaluation. Do not eagerly format
   errors at dispatch, and preserve the exact field changes in the matrix.
3. Keep original inline functional updater scheduling, getStoredAccessToken,
   try/await/catch, result.ok branch, request payload/closure and setAnomalie.
   Do not switch to a new reducer queue, capture latest mutable refs, add tokens,
   cancellation or race fixes.
4. Factories, table dispatch, every nested callback and full modified-file
   aggregations count in measurements. A generic null wrapper, redistributed
   unchanged decisions or principal-only improvement is rejected.
5. Reader cleanup may remove only the 21 proven fallback arms, after explicit
   approval. Retain alias precedence, density-dependent bounds and errors;
   stronger local construction types must not alter API interfaces.
6. Fresh original UI characterization first, then actual candidate complete-file
   100% statement/branch/function/line, ratchet PASS0 against authoritative base,
   no baseline/scope/threshold/matcher/config/tooling edits, independent replay.

No candidate runtime is approved by this report. Initial inline prototype
increased legacy file LOC3109→3137 and is rejected; formatting compression or
ratchet changes cannot fix that. The first selected:string design also passed
an eagerly read candidate field, failing the original laziness requirement;
it was superseded before the independent candidate comparison. Its initial
probe used a stale string payload against the already revised object policy
and failed with missing selection. That was a harness/version mismatch, not a
runtime failure; the corrected object-policy comparison below is authoritative.

Coordinator explicitly allowed external adjacent domain policy evaluation.
Fresh independent AST measurements on `candidate-workspace-adjacent.tsx` and
`candidate-fraction-resolution.ts`, counting every new and nested callable:

| Metric | Original | Adjacent candidate combined | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive / cyclomatic / LOC | 472 /416 /2631 | 455 /404 /2625 | -17 /-12 /-6 |
| Combined cognitive | 1099 | 1022 | -77 |
| Combined cyclomatic | 1174 | 1129 | -45 |
| Combined decisions | 923 | 872 | -51 |
| Combined callable count | 251 | 257 | +6 |
| Parent file effective LOC | 3109 | 3105 | -4 |
| Combined file effective LOC | 3109 | 3140 | +31 |
| Combined callable LOC | 4782 | 4789 | +7 |

The35-effective-line adjacent policy has6callables, cognitive3/cyclomatic9,
decisions3; it carries no extreme debt. Combined LOC growth is explicit rather
than hidden. Its responsibility is a closed five-event fraction resolution
state policy; a private domain module with direct pure-transition tests can be
legitimate here, unlike an arbitrary move of the whole JSX/closure or generic
null wrapper. Genuine repeated decisions are removed in both originals and
callsite enclosing metrics; all callback metrics remain counted. The existing
principal remains455, so this does not solve the extreme hotspot globally.

Latest selected payload is the entire `CapacitasFrazioneCandidate`; factory
reads frazione_id only after the shared null guard. Policy imports API types
only. `candidate-review.mjs` freshly compares60original/candidate outcomes:
fiveevents x3states x4unsuccessful-error variants, including null, replacement
state and preexisting success/error. All values and selected-field read timing
match. Candidate workspace SHA256
`13253c2a0b1402b169c96b2b53ced6383c9a997c4ac6b79d6bf9505214b541f1`;
policy SHA256
`a248c96ae56d8f3d00f40153a333f8a7c746d6e9cc889ea3395d4b9f05152d9a`.
Two additional candidate probes confirm lazy result.error/Error.message reads:
zero reads on null, one read on non-null, preserving empty string. Candidate
reader extraction independently passes the same56genuineCSV/XLSX outcomes in
both installed library entries, with exact expected values and errors. This
small proof does not demonstrate rendered race/UI equivalence or actual
candidate full-file coverage. Typed literal callsites are correlated;
the generic type can admit unions at future callers, so this is a private
closed-callsite policy, not an arbitrary exported event API guarantee.

`protected-source.mjs` independently inverts exactly21 enumerated replacement
groups, validates each occurrence count, and reconstructs the **entire original
file byte-for-byte** from the adjacent candidate. Thus there is no unlisted
AST/source delta in38top-level declarations,80hook calls, the1resolutionAPI
call,601JSXelements/931attributes, unrelated helpers, effects/dependencies,
authentication, request/filter ordering or async closure capture. Only the
explicit policy import/type,21fallback candidates and5updater bodies differ.
The60state comparisons also assert object key order: original spread then
specific fields matches state spread then concrete patch; omitted fields are
retained. Each null guard executes before lookup/factory/field access.

Initial protected-source harness matched a label-cell string that also appears
in unrelated JSX and failed its uniqueness assertion. It was narrowed to the
specific consecutive preview label/comune cells; final whole-source identity
passes. No runtime edit or weakened protection resolved that harness failure.

Independent `compare-external.py` loads the **versioned merge-base** baseline
with `git show`, scans both external candidates with the unchanged engine,
retains baseline context for every other path and uses exact diff-added lines.
External comparator exit0/findings[] against55a1b1d3. This verifies actual
legacy-parent LOC and callback matching at design time. It is explicitly **not
an implementation ratchet**: no source was changed and no baseline regenerated.

The design is **CONDITIONALLY ACCEPTABLE FOR ORIGINAL CHARACTERIZATION**,
subject to Coordinator phase selection, queue/closure oracle, direct typed-event tests and actual
ratchet/full-file100% implementation gates. No new runtime ownership is implied.
Principal 472 is an
extreme hotspot even after a small safe slice: the global objective additionally
requires genuine decomposition and substantial global debt reduction, not merely
making this file's coverage green.

## Status, limits and next action

**NO_CHANGE — PROVENANCE_AND_CONDITIONAL_DESIGN_REVIEW.** All runtime bytes and
metrics are unchanged. Original library/reader/updater oracle and312tests PASS
are fresh; original full-file branch gate FAIL is freshly reproduced. No runtime/test source, existing test, baseline,
exclusion, private React state or service was modified. No new goal was created.

Coordinator decides characterization/runtime phases. Heavy original replay is
complete and the slot is released: independent312PASS/906of929branchFAIL,
exact23-arm ledger reproduced. The next original characterization should cover
two simultaneous A/Brequests, both settlement orders, mixed completion outcomes,
selection after start, replacement/open/close/reopen, original-row filtering,
and captured request payloads. Keep all existing tests and final gates.

Precise additional original tests worth authorizing: startA, select another
radio while busy and prove request stillA/originalfraction; keyboard-supported
replacementB/startB; settle A/B success/failure/rejection in both orders while
asserting current modal's retained row/selection and mixed success/error flags;
replaceB/close/reopenC beforeAsettles and prove AupdatesC while filtering onlyA;
nullish-versus-empty result.error, non-Error rejection and missing token. These
are public rendered transitions with typed API-boundary deferred responses,
not private updater calls or fabricated null witnesses for3166/3206. The future
small policy module also needs real direct pure-transition tests covering all
fiveevents fornull/fullstate, retained fields/key order and lazy reads. Coverage
of a shared genuine guard must come from legitimate tests, not an ignore or
React-state injection.

Do not run parallel duplicate coverage, whole frontend/build/E2E or
implement before authorization. Stop on unexplained differences or failures.

Report-only changes do not alter runtime structure, routes or module surfaces;
Graphify aggregation belongs to the Coordinator's governed docs refresh. No
code graph update or Graphify success is claimed here.

## Authorized original-characterization replay

Coordinator separately authorized cherry-picking characterization-only source
`fd26c39594d438e271ad885d725f1e182920a1e2` into this reviewer checkout. Preflight
checked clean tracked state, both target paths absent/untouched and exactly two
source-commit paths. Shared hook configuration was inspected: no core.hooksPath
override, a pre-commit hook calls scripts/update_docs.sh; cherry-pick did not run
that hook or create additional changes. Existing independent untracked report
was preserved. Authorized reviewer cherry-pick is
`f06b3ed730ca95eff9e5091bbc2c5dfcb6978746`; it contains only the new spec and
author readiness report. This is not a report commit or runtime integration.

New spec SHA256 is independently exact:
`3fa5efef566e73057614810c250c77b7dde2f0b1859d33ddeec2c3a0a1d7520a`.
All16original campaign specs retain their frozen pre-cherry-pick hashes.
Runtime retains `d5210072...a99935`, and all tracked differences from10784e76
are exactly the two authorized added paths. Main/concurrent work remains intact.

| Independent gate | Result |
| --- | --- |
| Actual old+new original union | 324PASS /17spec,0skip,54.31seconds |
| Full-file coverage | 857/857statements,251/251functions,748/748lines100%;906/929branches97.52%,exit1FAIL |
| Raw map/branch preservation | Exact statement/function/branch maps; same23zeroarms;0newcovered/0lost |
| Explicit new-spec TypeScript | PASSexit0; actual imported runtime/type graph; no incremental emission/shared config edits |
| New-spec Next lint | PASSexit0,noESLintwarnings/errors; existing Next lint deprecation only |
| Frozen original reader/updater oracle | PASS56actualSheetJSfixtures/fiveupdaters with lazy/null behavior |
| Existing adjacent-candidate differential | PASS60state/key-order/field-timing cases,2lazyfailure probes,56realreadercases |
| Existing protected-source proof | PASSexact21groupinversion/wholeoriginalsource identity |
| Hash and ownership preservation | PASS16oldspecs/newexacthash/runtimefrozen/onlyauthorizedcommitpaths |

Independent union executed from reviewer frontend with the same actual coverage
include and100%thresholds, using report directory
`/home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/reviewer/characterization-original-coverage`.
Log: `characterization-original-coverage.log`; raw counter/map comparison:
`characterization-ledger.json`, coverage JSON SHA256
`39f0beedcfc83383ed43fecb1f30dad999a76e4d9e45f30f53a75f1a681bb38e`.
The independently measured FAIL100is preserved and explained by the same23arms;
it is neither waived nor a candidate implementation PASS.

TypeScript uses reviewer-local external `characterization-tsconfig.json`
extending the unchanged frontend tsconfig, explicitly including the new spec
and real runtime imports, existing Vitest/jest-dom types, empty test exclusion
and incremental:false. Command `node_modules/.bin/tsc --noEmit -p` that external
config exits0. Command `node_modules/.bin/next lint --file
tests/unit/campaign-capacitas-resolution-state-r10.test.tsx` exits0. Logs are
`characterization-typecheck.log` and `characterization-lint.log`. Ordinary
runtime typecheck alone would not substitute for checking the new spec.

Independent source review accepts the12new characterization cases: ten mixed
completion permutations (fiveactualfailureforms x2orders), one missing-token /
selection / real-start error-clearing case, one close/reopen older-response
case. LiveDOM/API-boundary transitions verify retained replacement identity,
current selection versus captured request fraction, mixed success/error fields,
captured original filtering and cleanup/reopen defaults. No setter/private
closure invocation, SheetJS mock, built-in fabrication or test weakening is
present. Focus plus jsdom click characterizes supported replacement transitions;
nativeTab/Enter reachability still comes from the versioned browser witnesses,
not these jsdom mechanics. Cases are characterization, not extra branch hits.

The requested original characterization is **INDEPENDENTLY ACCEPTED**. Runtime
implementation approval remains a separate Coordinator decision with ownership
allocation and direct policy tests, actual candidate100%coverage/ratchet and
final gates required. Principal472 and global campaign objective remain
ACTIVE/INCOMPLETE. Heavy focused replay slot is released; reviewer stops here
without runtime/config/baseline edits, report commit or additional integration.
