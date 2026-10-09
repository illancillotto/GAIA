# R10 Capacitas — original readiness and measured design

## Phase, ownership and preserved source

**NO_CHANGE — ORIGINAL_CHARACTERIZATION_ONLY.** The global campaign remains
ACTIVE/INCOMPLETE. Coordinator separately authorized one new original rendered
test file after readiness/design review. No runtime, baseline, threshold,
exclusion, package, configuration, tooling or commit is authorized by this
report. Coordinator owns phase approval and integration. Author repository
writes are this report and that one new spec; disposable evidence lives outside
the worktree. The final characterization results appear below; the earlier
312-test original measurement remains preserved as the before evidence.

Authority: integration checkout's
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R10_CAPACITAS_2026-10-09.md` and
external `coordinator/READINESS_DESIGN_FEEDBACK.md`. The initial inline policy
prototype is superseded by the externally evaluated adjacent domain policy.

- Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261009-r10-capacitas`.
- Branch: `refactor/complexity-r10-capacitas`.
- Clean preflight HEAD: `10784e761ded91383f9c8aa70ee02b25e18872cc`.
- Main merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Original runtime SHA256:
  `d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`.
- Baseline SHA256:
  `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
- Runtime, all sixteen existing specs and production tooling remain unchanged.
  The existing 312 tests are retained; no inherited `/tmp` log is evidence.
- Checkpoint and project complexity instructions apply throughout. Historical
  C12, modal reachability and defensive provenance reports provide orientation;
  the measurements below were rerun against the current original source.

Evidence prefix, private directory permissions0700:
`/home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/`.
`preflight.json` and `checkpoint.md` preserve recovery context. Coverage session
86417 completed; TypeScript sessions80512/44655/51892 completed. No background
service, browser or active author test process remains. Coordinator transferred
the focused coverage slot to the reviewer after the original run finished.

## Fresh original measurement

Commands run from the dedicated worktree, coverage from `frontend/`:

```sh
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/original-coverage
python3 tools/code_quality/complexity.py report \
  frontend/src/components/elaborazioni/capacitas-workspace.tsx \
  --json /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/original-complexity.json \
  --markdown /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/original-complexity.md
node /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/audit-original.mjs
```

Actual original union: **312 PASS, sixteen specs, zero skip, 36.86s**. The
coverage command exits1 because its unchanged100% branch gate fails. This is
the reproduced original gap, not a new regression or a coverage waiver.

| Metric | Actual original result |
| --- | --- |
| Statements | 857/857,100% |
| Functions | 251/251,100% |
| Lines | 748/748,100% |
| Branch arms | 906/929,97.52%;23 zero arms on22 source lines |
| Main callable | cognitive472;cyclomatic416;effectiveLOC2631;nesting2;params1 |
| File | cognitive1099;cyclomatic1174;effectiveLOC3109;251 callables |
| Aggregate decision count | sum(cyclomatic−1)=923, including every nested callback |
| Findings | 24error+20warning=44;31useState/2useEffect |

Coverage artifact `original-coverage/coverage-final.json` SHA256
`8104bbdd948b963bb2c4d259ce4eb424a098ae0e98494322f2b55e2196d64721`.
`original-ledger.json` contains every zero-arm raw range, original source line,
aggregate metrics and SHA256 of each of the sixteen specs. There are no
unlocated zero arms. Branch IDs below are specific to this fresh artifact;
line/column spellings follow Istanbul's1-based line/0-based column convention.

## Exhaustive original zero-arm classification

| Branch:arm | Arm start | Expression/responsibility | Classification and exact premise |
| --- | --- | --- | --- |
|16:1|258:25|`value ?? ""`|CONSTRUCTION_UNREACHABLE: private normalizer receives only `Object.keys` strings at every callsite |
|19:1|281:58|extension `pop() ?? ""`|CONSTRUCTION_UNREACHABLE: nonempty string separator returns a nonempty split array, whose final value is a string |
|23:1|291:41|Terreni first row `?? {}`|LIBRARY_CONTRACT_UNREACHABLE: nonzero length, actualSheetJS0.20.3 dense object output/options |
|24:1|293:46|Terreni first row `?? {}`|Same library premise; repeated construction does not introduce mutation |
|27:1|313:34|Terreni indexed row `?? {}`|Same dense output contract; bounded synchronous iteration |
|28:1|314:74|commune Map lookup fallback|CONSTRUCTION_UNREACHABLE: selected alias belongs to normalized keys used to populate Map; raw value string |
|29:1|315:74|foglio Map lookup fallback|Same selected-key/Map invariant |
|30:1|316:82|particella Map lookup fallback|Same selected-key/Map invariant |
|32:1|317:89|sezione Map lookup fallback|Same invariant only after the meaningful optional-key guard succeeds |
|34:1|318:77|sub Map lookup fallback|Same invariant only after the meaningful optional-key guard succeeds |
|41:1|378:58|Storico extension fallback|Same standard string/split/pop premise as281 |
|45:1|388:41|Storico first row fallback|Same currentSheetJS0.20.3 dense object contract/options |
|46:1|390:46|Storico first row fallback|Same library premise |
|49:1|403:34|Storico indexed row fallback|Same dense output/bounded iteration premise |
|51:1|404:96|subject identifier Map fallback|Same Map invariant; absent optional identifier branch remains meaningful |
|53:1|405:86|idxana Map fallback|Same Map invariant; absent optional identifier branch remains meaningful |
|285:1|2056:82|array length `?? 0`|CONSTRUCTION_UNREACHABLE: same plainAPI-JSON array synchronously reread after `Array.isArray`; length always defined |
|333:1|2483:83|preview label `?? "—"`|CONSTRUCTION_UNREACHABLE: all local preview items come from reader's string label construction |
|334:1|2484:46|preview commune `?? "—"`|CONSTRUCTION_UNREACHABLE: reader normalizes strings and validates mandatory commune nonempty |
|337:1|2482:51|preview commune key fallback|Same exclusive local preview provenance |
|338:1|2482:103|preview sub key fallback|Same reader construction; optional sub is a string including empty |
|426:1|3166:104|selection nullable updater|UNKNOWN_REACHABILITY: preserve its null behavior; ordinary live UI does not prove all React scheduling cases |
|434:1|3206:94|begin nullable updater|UNKNOWN_REACHABILITY: preserve its null behavior; synchronous dispatch does not prove universal unreachability |

Fifteen candidates are standard-language/construction conditions and six
depend on the installed library contract. The latter must be revalidated on
anySheetJS upgrade or change to `header`, `raw`, `defval` or row handling.
None is demonstrated by invented parser rows, monkeypatched builtins,
accessor-bearing API fixtures or private React state manipulation.

Fresh reviewer oracle independently checks realCSV/XLSX fixtures on bothESM
andCommonJSSheetJS0.20.3:56 reader outcomes, density and selected-key behavior.
Its library source hashes match the historical inspected artifacts:
ESM`1a0fb062ee9781b13f6687371b202aaefc53b6ce55b530c027e01f9c087b77db`,
CommonJS`fd159f1e2d694e12cd0709c1ec1b63c6e1f045d2c4ce857a346f9b965798cbfa`.
This is independently reported oracle evidence, not author-rendered coverage.
The fresh reader/source proof remains conditional on these exact libraries and
actual options; finite fixtures alone do not prove all future library inputs.

Author independently inspected the currentESM functions at27487/27531 and
CommonJS27371/27415: omittedheader leaves mode0; each `make_json_row` creates
`{}`; accepted rows are appended only through `out[outi++]=row.row`; final
length isouti. Missing sheets/ref return an empty array, and unknown cell types
throw instead of creating a null/hole. Blank/hidden skips never incrementouti.
These exact implementation facts prove density/non-null objects with the actual
`{defval:null,raw:false}` options; they do not rely solely on the oracle fixtures.

The separate reachable null guards3214/3217/3220 are covered by the original
fresh union and remain essential. C12's six publicUI cases retain late success,
unsuccessful response and rejection after replacement+close and replacement
remaining open. Their historical nativeTab/Enter proof is versioned narrative;
the lost browser files were not reused or falsely claimed rerun here.

## Original behavior and test matrix

| Contract | Existing original evidence | Remaining original characterization proposal |
| --- | --- | --- |
| Normalize/trim headers and cells; choose alias priority, not column order | batch/storico-input specs; fresh library oracle | RealCSV/XLSX normalized collision vs exact duplicate headers; compare preview and submitted payload |
| Dense rows, blank-row omission and validation indices | batch/empty-workbook/storico-input specs; real fixture oracle | Preserve compressed reader index: blank physical row before invalid row yields original `Riga 3` |
| Preserve first sheet selection and genuine no-sheet behavior | batch/storico-input/empty-workbook specs | Retain all existing missing-sheet/empty/optional-column cases |
| All preview entries are normalized reader constructions | batch preview-limit/full-payload test | Assert optional empty sub/sezione and derived string label on actual upload |
| Initial null; open fresh row; select only fraction; close sets null | anomalie and modal-race specs | Rapid real radio selection then immediate submit/close/reopen sequence using enabled DOM controls |
| Token guard precedes busy updater/API; begin clears only error | anomalie token-loss and deferred-busy cases | Retain exact token/payload/fetchflag and no dispatch when token unavailable |
| Busy blocks close/duplicate submit, leaves radio enabled | anomalie deferred radio test | Preserve request's captured fraction while current selected radio changes |
| Success sets busyfalse/successtrue, filters captured original row | anomalie plus modal-race | Two overlapping A/B requests settled in both orders; retain original closure/filter identity |
| Unsuccessful response sets busyfalse/error only, retaining success | anomalie error cases plus modal-race | A-success/B-failure overlap retains success with later error on current modal |
| Rejection uses original `instanceof Error` semantics and formatting | anomalie Error/nonError cases plus modal-race | Mixed rejection/success overlap retains the previously written error rather than normalizing state |
| Every updater retains null; formats error only when nonnull | original race cases; reviewer exact-updater oracle | Direct domain-policy null cases after implementation, with accessor probes confined to pure laziness checks |
| Pending requests update current replacement modal; captured ID stays old | six modal-race tests, unchanged original UI/API | Two-request close/reopen permutations; do not add request ownership or fix the race in this slice |

The separately authorized original characterization spec is
`frontend/tests/unit/campaign-capacitas-resolution-state-r10.test.tsx`.
It now executes the unchanged real component, coherent typedAPI boundaries
and public enabled controls, especially the two-request mixed-outcome sequences
absent fromC12's single-request replacement cases. All312 existing tests remain
intact, with no skips and exactUI→API→UI assertions. Direct policy coverage is
required after that new module actually exists and receives its own authorization;
extracted-function/property probes are supplementary proof, never claimed
original component branch coverage or modal reachability witnesses.

## Measured external design

The accepted-for-evaluation external design is a private adjacent module with
five correlated domain events: `selected`, `started`, `synchronized`,
`unsuccessful`, `rejected`. It owns a closed typed event/payload map, five
event-specific partial state changes and one null-first domain transition.
It is not a reusable null transformer: input events and state are tied to
fraction resolution, with no user-supplied callback or generic state type.

Exact candidate files under the author evidence prefix:
`candidate-fraction-resolution.ts` and `candidate-workspace-adjacent.tsx`.
`prototype-policy.mjs` reconstructs both from the frozen original source;
it fails on ambiguous replacement sites. All candidate changes are external.
Potential future production module name is
`frontend/src/components/elaborazioni/capacitas-fraction-resolution.ts`.

Every existing functional updater retains its original scheduling site. The
shared transition first returns null unchanged, then spreads the existing
state and invokes the typed event factory. The selected event passes the
candidate object, so `candidate.frazione_id` is read only after the null guard.
Likewise result.error and rejectedError.message remain lazily evaluated after
that guard. There is no eager error formatting, second dispatch, optional
generic payload, broad cast, effect change or move of theAPI/request flow.

The event patches preserve exactly the original fields:

| Event | Fields changed; all others retained |
| --- | --- |
|selected|selectedFrazioneId only |
|started|busytrue,errornull only |
|synchronized|busyfalse,successtrue only |
|unsuccessful|busyfalse,error=result.error??originalfallback only |
|rejected|busyfalse,error=originalinstanceofError/message/fallback only |

Open/close writers, first candidate fallback, renderedUI guards, token checks,
request payload, captured `resolveModal.particella.id`, old completion ordering
and anomaly filters stay in the workspace verbatim. The shared nullable
transition preserves both UNKNOWN synchronous guards and all three genuinely
reachable asynchronous guards. A real late-response null witness exercises
the policy's shared guard; this does not turn the two synchronous events into
proven unreachable code or remove their null semantics.

The separate twenty-one proven reader/preview fallback cleanups remove only
their redundant alternative values. Map lookups retain optional-key guards;
non-null assertions encode proven lookup/density/extension invariants without
runtime wrappers. The plain JSON array length uses the already-proven array
directly. Header normalization, alias order, dense row indices, stringification,
throw messages, item order, optional values and missing-sheet returns remain.

The unchanged `tools/code_quality/js_ast_metrics.mjs` measured every callable,
including all five factory callbacks and all surviving workspace callbacks.

| Metric | Original | Adjacent workspace | Policy module | Combined candidate |
| --- | ---: | ---: | ---: | ---: |
| Cognitive sum |1099|1019|3|1022,−77 |
| Cyclomatic sum |1174|1120|9|1129,−45 |
| Decisions sum(cyclomatic−1) |923|869|3|872,−51 |
| Callables |251|251|6|257,+6 |
| Effective fileLOC |3109|3105|35|3140,+31 declared |
| Main cognitive/cyclomatic/LOC |472/416/2631|455/404/2625|not applicable|−17/−12/−6 |
| Error/warning findings |24/20|22/19|0/0|22/19,−2error/−1warning |

The policy-only experiment separately measured main460/409/2625 and aggregate
1059cognitive/898decisions. Thus the event policy itself removes repeated
decisions before adding the twenty-one independent construction cleanups.
The policy module has no error/warning threshold violation. Its callbacks:

| Callable | Cognitive | Cyclomatic | LOC | Nesting | Params |
| --- | ---: | ---: | ---: | ---: | ---: |
|selected|0|1|1|0|1|
|started|0|1|1|0|0|
|synchronized|0|1|1|0|0|
|unsuccessful|1|2|1|0|1|
|rejected|1|2|1|0|1|
|transitionFractionResolution|1|2|8|1|3|

This is real domain decision deduplication with a new testable state contract,
not relocation of the old five guarded branches. Nevertheless3140 combined
effectiveLOC and six additional callables are explicit structural costs. The
main remains extreme at455cognitive: this slice is progress against the worst
hotspot, not elimination of it or achievement of the global campaign target.

External TypeScript check passes against real project/compiler types:

```sh
frontend/node_modules/.bin/tsc \
  -p /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/prototype-tsconfig.json \
  --noEmit
python3 /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/compare-prototype.py
```

The external comparison imports the unchanged production scanner, loads the
exact merge-base baseline fromGit, overlays candidate callable records into
full baseline context, and supplies actual diff-added line sets. Adjacent
candidate result: **exit0, empty findings** in `prototype-comparison.json`.
No matching rule or threshold is changed. This is an in-memory design
comparison, **not** a production implementation ratchet or certification.
The authoritative `make complexity-ratchet BASE_REF=main` must run on actual
approved source before acceptance, independently repeated after source freeze.

Author exact-AST updater oracle `compare-state-policy.mjs` independently
executes the five unchanged updater functions against the candidate policy:
**637 comparisons PASS**,13 payload variants×49 states. This includes null,
all busy/success boolean combinations, several retained selection/error values,
empty/null/undefined failure errors, realErrors and nonError rejections. Three
separate lazy-access probes check candidate.frazione_id, result.error and
Error.message:zero reads on null, exactlyone per nonnull updater evaluation,
matching original. `state-policy-oracle.json` retains the exact result. This
is pure supplemental equivalence evidence, not renderedUI coverage, asynchronous
ordering proof or a witness for either UNKNOWN synchronous guard.

Reviewer independently inspected those exact candidate hashes:
workspace`13253c2a0b1402b169c96b2b53ced6383c9a997c4ac6b79d6bf9505214b541f1`,
policy`a248c96ae56d8f3d00f40153a333f8a7c746d6e9cc889ea3395d4b9f05152d9a`.
Fresh `reviewer/candidate-review-results.json` reports60 state comparisons
equivalent, selected-field timing equivalent with zero differences, two lazy
error probes and56 actualSheetJS reader comparisons equivalent. These fresh
results supplement the author's checks; phase acceptance remains pending the
reviewer's complete report and Coordinator decision.

The initial inline prototype is rejected: original file3109→3137LOC violates
the legacy file gate. Its external full matching also returns exit2 ambiguous
`Program<anonymous>` identity87 candidates. This failure is retained and not
renamed green or absorbed into a baseline. Adjacent module evaluation was
separately permitted by Coordinator because it owns a genuine typed domain
policy and combined decisions decrease. Inline compression, arbitrary source
relocation and scope shrink were not used to make the gate pass.

Two initial external typecheck attempts failed only because a file outside
the repository could not resolve inheritedvitest/globals or barexlsx. The
external tsconfig now resolves the project's existing types and modules;
the successful check exits0. Production tsconfig/dependencies are unchanged.

## Gate boundary, residual risks and phase request

Original full-file coverage remains **FAIL100**. Candidate full-file coverage
has not been run, and expected coverage from shared decisions is not an actual
coverage result. Ultimately both workspace and policy module require100%
statement/branch/function/line coverage with no ignores or exclusions.
No fullfrontend, build, E2E, globalcheck or baseline synchronization was run
by this author. No production services or old volatile browser logs were used.

Dedicated orientation command `make graphify-frontend-query Q="..."` failed
because the fresh worktree has no frontend graph. Read-only readiness changes
no runtime boundary, so no frontendGraphify refresh was claimed. A separately
approved new adjacent module/import requires the dedicated frontend target
and appropriate pruning/patch rules before final closure; Coordinator owns
shared governance/platform documentation Graphify maintenance.

Required next phase is a Coordinator decision on this exact measured candidate
and original characterization matrix after independent review. Approve tests
first, acquire genuine original behavioral evidence, then explicitly allocate
the two runtime paths if implementation is authorized. Preserve frozen hashes,
all old tests, null/race behavior, alias/library contracts and actual scanner.
Stop if event typing, state timing, library proof, complete coverage or identity
matching fails. No generic wrapper, fake reader rows, synchronous guard deletion,
baseline inflation, threshold increase or reduction to a safe subset qualifies.

This readiness report grants no runtime approval, completion claim or commit
authorization. Global strategic targets and historical findings remain open.

## Authorized original characterization — final result

Coordinator's external `coordinator/CHARACTERIZATION_APPROVAL.md` and the updated
integration ownership registry authorize only the named new rendered spec and
this report. Application runtime, existing tests and every production config,
baseline and scanner remain read-only. No policy module exists in the repository
and the new test imports only the unchanged original workspace.

Added **twelve meaningful original cases**, not attempts to force3166/3206.
All API/auth boundaries use coherent typed values; actual workspace React hooks,
state, polling hook, presentation components and public DOM handlers execute.
Only unrelated protected shell/settings modal boundaries are replaced. No
private setter, detached callback, impossible parser fixture, runtime
instrumentation or helper substitute appears in the owned spec.

| New cases | Original UI/API/state invariants actually asserted |
| --- | --- |
|Five failure variants×two completion orders=ten cases|Start Uras/FRA-B; replace with Terralba/FRA-D and start its request; change current radio toFRA-C while busy. Settle Uras success and Terralba failure in both orders. Current modal remainsTerralba withFRA-C; only capturedUras row is removed; Terralba failure retains success and Uras success retains error. Radio selection afterwards retains both fields. Close/reopen clears terminal fields and selects first candidate. |
|Failure variants|Provided error, null→`Errore sync`, empty→no error card, actualError message and nonError→`Errore`; corresponding expected notices remain alongside success rather than being normalized away. |
|One token-loss/selection case|Failure error survives radio selection and enabled synchronization with missing token; no second API call/busy transition. Restored token starts request, clears only error and capturesFRA-B. Enabled radio then changes toFRA-A while close stays disabled; successful completion retains currentFRA-A and removes capturedUras. |
|One two-request close/reopen case|Terralba request fails first, releasing current close while olderUras request still waits. Close then reopenTerralba resets error/success/selection; selectFRA-D. OlderUras success updates that freshly openedTerralba modal, retaining new identity/selection and removing onlyUras. |

The exact outgoing API calls, token values, fraction IDs and `fetch_certificati:
true` flag are asserted, including capturedFRA-B/FRA-D versus subsequently
displayedFRA-C. Completion of one request releasing the current busy flag while
another remains pending is existing behavior, deliberately characterized rather
than corrected. No request ownership, cancellation, generation check or state
normalization is introduced.

The live background row action uses focus plus `fireEvent.click`, matching the
existingC12 rendered boundary. This jsdom evidence demonstrates state/API
transitions, not nativeTab ordering, browserEnter activation or pointer access
through production overlays. Historical genuine keyboard races and their
three essential guards remain intact; no browser replay was claimed here.

| Executed gate | Result | Durable author artifact |
| --- | --- | --- |
|Owned original rendered spec|12PASS,1file,0skip,exit0,2.42s|`characterization-focused-attempt1.log`/`.exit`|
|Actual original old+new union|324PASS,17files,0skip,43.99s; coverageexit1|`characterization-original-coverage.log`/`.exit`|
|Full-file original coverage|857/857statements,251/251functions,748/748lines100%;906/929branches97.52% **FAIL100**|`characterization-original-coverage/coverage-final.json`|
|Explicit owned-test TypeScript|PASSexit0, imported actual runtime types checked, no shared config change|`characterization-tsconfig.json`, `characterization-typecheck.log`/`.exit`|
|Scoped owned-test Next lint|PASSexit0,noESLintwarnings/errors; existingNext16 command deprecation only|`characterization-lint.log`/`.exit`|
|Fresh runtime AST before/final equality|Exact `files` and `callables` equality PASS;472/416/2631 and all aggregates unchanged|`characterization-complexity.json`/`.md`/`.log`|
|Original hash/map/coverage preservation|All16oldspecSHA unchanged, runtimeSHA unchanged, maps identical,0newlycovered/0lostarms|`characterization-preservation.json`/`.log`|
|Protected diff/whitespace|PASS; only assigned new spec/report untracked; nothing staged|`git diff --quiet HEAD -- frontend/src ...`, `git diff --check`, `git status --short`|

Reproduction from `frontend/`:

```sh
npm run test:unit -- tests/unit/campaign-capacitas-resolution-state-r10.test.tsx --maxWorkers=1
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/characterization-original-coverage
node_modules/.bin/tsc \
  -p /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/author/characterization-tsconfig.json \
  --noEmit
node_modules/.bin/next lint --file tests/unit/campaign-capacitas-resolution-state-r10.test.tsx
```

The external TypeScript config explicitly includes the owned spec and real
Vitest/jest-dom types, clears the inherited test exclusion and disables
incremental emission. No production config change or weaker typecheck is used.
The first focused/type/lint attempts pass; there is no hidden failing rendered
attempt. The unchanged100% full-file gate retains its expected original failure.

Owned spec SHA256
`3fa5efef566e73057614810c250c77b7dde2f0b1859d33ddeec2c3a0a1d7520a`.
Final original coverage SHA256
`5be80df7639ec526b3f3957d88b0b8c5857abb20a916b84b5b1eae8d8d47e95b`.
Final maps exactly match the earlier fresh original maps; all23zero-arm ranges
above remain identical. The added cases strengthen behavior protection without
artificial branch hits. The two synchronous arms remain UNKNOWN and untouched.

Focused session58585, type session63469, lint session55289 and union session96241
all completed. No author processes/services remain and the focused replay slot
is available for Coordinator transfer. No fullfrontend/build/browser, candidate
coverage, implementation ratchet, baseline synchronization, Graphify runtime
refresh, commit or integration ran in this characterization phase.

**Stop: original characterization complete, runtime still unchanged.** Next
is independent replay of the exact owned spec/source and Coordinator's explicit
decision on implementation and later pure-policy test ownership. The external
adjacent design remains a proposal; eventual runtime acceptance still requires
100%full-file coverage of both changed runtime files, genuine total debt
reduction and authoritative unchanged merge-base ratchetPASS0. The global
campaign remains ACTIVE/INCOMPLETE.
