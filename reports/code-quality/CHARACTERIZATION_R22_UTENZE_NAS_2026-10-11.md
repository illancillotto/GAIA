# R22 — Utenze detail NAS command characterization (ANALYZE ONLY)

Date: 2026-10-11. Status: ANALYSIS_READY_FOR_COORDINATOR_ADMISSION;
runtime BLOCKED_COVERAGE. Global campaign ACTIVE/INCOMPLETE. No runtime ACCEPT,
complexity improvement, coverage PASS or application-suite completion claimed.

## Allocation and custody

Registry read first from integration:
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R22_UTENZE_NAS_2026-10-11.md`.
Dedicated reused clean tree:
`/home/cbo/CursorProjects/GAIA-campaign-20261010-r21-capacitas-job-actions`;
branch `characterize/complexity-r22-utenze-nas`;
HEAD `31436fc89e73d35fc4e6e7969441a7d8ba427bb2`;
merge-base main `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Initial status empty. All repository commands used this dedicated tree, except
reading the registry from its explicitly assigned integration tree.

Only this new report and private evidence were written. Runtime, existing specs,
configuration, baseline, R21/main/evidence and shared tooling remain read-only.
Checkpoint and repository complexity skills/rules were read. PROGRESS was read
with focus on the latest accepted R21 state; a combined documentation read
produced truncated output, so older historical diary entries are not claimed as
fully reviewed. No tests, typecheck, lint, full report, ratchet, build, Graphify,
install, cleanup, commit, push, import, or agent spawn were executed.

| Immutable item | SHA-256 |
| --- | --- |
| `frontend/src/app/utenze/[id]/page.tsx` | `b0f822daf809b0744b912f0f159a2e833c556dda289466b6ed45329a79e3d6b1` |
| Existing `frontend/tests/unit/campaign-utenze-detail-page.test.tsx` | `79ef301017ee78985d71b468300eba3239e901c9773eb56f60a033cd6ad13f98` |
| Frozen native `20261010-r21-integrated/integrated-complexity.json` | `c0cb68725d35a348e7902e642c7afb078881cbc4b1acc7c544da7f90b6512e66` |

Source and existing spec equal integration31436 byte-for-byte. Source also equals
Git bytes at frozen report source commit
`509a3913a2664c036c8aa34650a1765d6517dc3f`.
Recent runtime history: `737fffca`, `069eea98`, `254d908a`.
Private evidence directory:
`/home/cbo/.cache/gaia-campaign/20261011-r22-utenze-nas-author/`.
`analysis-evidence.json` freezes custody/native summary/source census;
`source-ast-census.json` is a single-source native AST census, not a gate replay.
Initial raw equality checks were false because scanner records have an empty
path and empty violations, while integrated records bind paths and annotate
thresholds. A read-only diagnostic established zero differences across all176
ordered identity/fingerprint/span/metric tuples; no scanner failure or native
retry occurred. These raw comparison results remain disclosed in evidence.

## Metrics — unchanged frozen native report

Official global: 1673 files, 20322 callables, 1925 errors, 2741 warnings,
4666 records. No fresh global report was generated.

| Callable / source span | Cognitive | Cyclomatic | Effective LOC | Nesting |
| --- | ---: | ---: | ---: | ---: |
| `DetailContent`, 214–2206 | 391 | 304 | 1908 | 2 |
| `loadNasImportStatus:useCallback[0]<callback>`, 496–514 | 3 | 3 | 19 | 1 |
| `handleImportFromNas`, 597–614 | 3 | 3 | 17 | 1 |
| `handleLoadNasCandidates`, 616–630 | 6 | 5 | 15 | 1 |
| `handleSaveNasPath`, 632–656 | 6 | 6 | 23 | 1 |
| `reloadSubject`, 397–400 | 0 | 1 | 4 | 0 |
| NAS effect, 889–894 | 1 | 2 | 6 | 1 |
| Candidate `find` callback, 638 | 0 | 1 | 1 | 0 |

Four command/status callables total18 cognitive,17 cyclomatic,13 decisions
(sum(cyclomatic−1)),74 effective LOC. This is a census, not an extraction credit
or a promised reduction of the enclosing391. Inline quick-import visibility,
JSX, subject hydration and effect dependencies remain part of the parent.

Whole file:176 callables, cognitive sum729/max391, cyclomatic sum723/max304,
547 decisions, density0.685552, effective LOC2118,22 imports/dependencies,
2231 physical lines. Official hooks:useState28/useEffect10/useReducer0;
file errors:LOC2118, useState28, useEffect10. A small independent Babel traversal
counts actual call-expression hooks: file useState50, DetailContent49;
useEffect10/useCallback3/useRef1/useDeferredValue1 in both. The official scanner
uses a textual `useState(` pattern and omits generic calls; the AST census is
supplemental and does not redefine official metrics, thresholds or baseline.

## Cohesive scope and behavior to preserve

Only NAS status/import/candidate/path commands and their public controls.
Upload, preview, deletion, classification, visura, personal-data saving, ANPR,
document grouping/pagination and other tabs' domain logic are outside scope.
Cross-effects are recorded only where they change NAS observations.

1. Initial subject GET sets `subject`; NAS status is requested only after a
   truthy subject through the effect depending on `[loadNasImportStatus,subject]`.
   Callback identity depends on token/id. There is no cancellation or request
   generation guard. Status loading leaves the old status visible, then replaces
   it. Failure resolves to can_import=false/missing=true/null folder/zero counts;
   Error.message or literal `Verifica NAS non disponibile`, without saveError.
2. Import immediately marks importing and clears saveError/saveMessage, then
   calls `importUtenzeSubjectFromNas(token,id)`, awaits subject GET and explicitly
   awaits status. It never submits selected path or candidate metadata. Subject
   replacement additionally schedules the NAS effect. Success literal uses
   import result folder name and created/updated counts. Import rejection stops
   before reload/status; reload rejection leaves the completed server import
   observable only as saveError and prevents explicit status. Status rejection
   is absorbed, so import success can coexist with unavailable-status UI.
3. A new subject object resets edit mode/confirmation and selected path to
   `subject.nas_folder_path || ""`; it does not clear candidates/status/shared
   messages or busy flags. Reload returning the same reference need not trigger
   the subject effect. Distinct fresh fixture objects are required to test the
   effect-driven extra request rather than accidentally suppress it.
4. Candidates command clears saveError but retains saveMessage/previous options
   while busy. On success it replaces options, preserves API order, and selects
   the first path only if the command's captured selected path is falsy and the
   first returned path truthy. No sorting or review/confidence filter occurs.
   Empty results replace the list but do not clear an existing input. Failure
   retains list/path and uses Error.message or the candidate fallback literal.
5. Saving a falsy path sets `Seleziona una cartella NAS da salvare.` and returns
   before API/busy/message clearing. A whitespace-only path is truthy and sent
   verbatim. Candidate lookup is exact and first-match. Letter is
   `candidate?.letter ?? subject?.nas_folder_letter ?? null`: empty string is
   retained, null candidate letter falls back; custom path retains subject
   letter rather than deriving a directory letter. Save submits exactly the two
   NAS keys to update API, sets subject directly from response (no reload GET),
   awaits explicit status and reports `Percorso NAS salvato sulla scheda soggetto.`.
   It also schedules effect status if response object differs. Update failure
   preserves edit/input/options; status failure is absorbed after persisted save.
6. Quick import is Boolean(can_import && (pending ??0)>0). In read-only mode the
   header import exists only for quick eligibility. In edit mode header import
   exists for can_import even with zero/negative pending. Scheda status-card
   quick button has the count and exists in either mode when eligible. Header
   remains available on other tabs; status card/override/shared save messages
   are confined to Scheda. `missing_in_nas` alone does not gate import.
7. Import buttons disable for importing OR loading-status, with `Aggiornamento...`
   only while importing. Candidate search disables for read-only OR its own busy
   and says `Ricerca cartelle...`; path save disables for read-only OR its own
   busy and says `Salvataggio...`. Input/radios depend only on edit mode, so remain
   editable while candidate/search/save/import is pending. The command busy
   flags do not form a cross-command lock; terminating edit is also available.
8. Candidate failure fallback is `Errore caricamento cartelle NAS candidate`;
   import fallback `Errore import documenti da NAS`; path update fallback
   `Errore salvataggio percorso NAS`. Non-Error values are not String-converted.
   All finally blocks release their own boolean even on rejection.

API adapters are unchanged: import POST `/utenze/subjects/{id}/import-from-nas`
with bearer token, no body; candidates GET `.../nas-candidates?limit=20` by adapter
implicit default; status GET `.../nas-import-status`. Mounted page mocks assert
literal function arguments (token/id, no extra candidate options), not copied
URL-building logic. API transport tests remain separate evidence.

### Request order, stale results and races

Guaranteed import partial order: import resolves before reload invocation;
reload resolves before explicit status invocation; explicit status settles before
success message and importing=false. Additional effect request follows subject
commit; relative scheduling of the explicit request versus effect cannot be
certified by static reading. Path update resolves before explicit status; there
is no subject reload in that command. For a fresh returned object, two status
calls are expected after each successful subject replacement; a mounted native
run must establish the actual trace before freezing exact ordering assertions.
Do not invent a total order, remove duplicate calls or accept any-order assertions
as evidence of total order preservation.

Any status response may overwrite a newer result; one request's finally clears
loading while a second is pending. Controlled tests should hold both requests,
resolve the later one first, then assert the earlier result wins when it resolves.
For path save, once saving=false and the remaining status request is outstanding,
quick import can become enabled if the first response was eligible: preserve the
boolean lifecycle rather than imposing a request counter.

Candidate results use the initiating render's path: if it was empty and the user
enters `/typed/during-search` before resolution, the first returned candidate can
overwrite that edit. If captured path was nonempty then cleared while pending,
results do not auto-select. Path editing during update is overwritten by returned
subject hydration. Old candidates survive subject replacement and can carry a
stale letter into a later save. Late subject/status responses after route id
change are unguarded; existing old subject/status can remain while the new GET is
pending. Do not fix these races under characterization. Use mounted route-prop
rerender with mutable navigation mock to observe them; do not unmount/remount and
call it a same-instance race test.

## Existing evidence and missing mounted-control matrix

Existing immutable page spec mounts the real page, checks auth/load/edit/person
saving and one Error-valued NAS status fallback. It does not mock or invoke NAS
import/candidates/path controls. `api-utenze.test.ts` exercises adapters only;
`utenze-subjects-document-refresh.test.tsx` covers another component's import
flow, not DetailContent/status duplication/path commands. A targeted search
across frontend tests found no path-save/candidate-control tests. These are
source observations, not executed test results. Historical36.28% statements /
37.54% branches are NOT current coverage measurements.

All cases below require real mounted page controls and independent typed fixtures;
none use copied runtime algorithms, extracted functions or source-string checks.

| Group | Genuinely missing stimuli | Literal public assertion / API evidence |
| --- | --- | --- |
| S1 | Initial subject pending, then status pending | No status before subject resolution; exact `(campaign-token,subject-1)` after it; page remains visible |
| S2 | Status can_import true/false × pending2/0/negative; null pending as boundary API input if admitted | Read-only header and `Aggiorna documenti (2)` presence; enable edit to observe header with zero; false eligibility hides both |
| S3 | Deferred status refresh with previous eligible result | Existing button disabled until status settles; old status message retained while pending |
| S4 | Error and non-Error status failures | Original Error text or `Verifica NAS non disponibile`, zero counts, `Non disponibile`, no quick button; subject still shown |
| S5 | Switch to `Letture contatori`, return Scheda | Header quick control persists; status-card/override disappear and return |
| I1 | Header versus counted-card import | Exact import token/id, no path argument; both buttons show disabled `Aggiornamento...` |
| I2 | Import deferred, reload deferred, then two statuses deferred | No reload before import resolution; no explicit status before reload resolution; two post-replacement calls; freeze observed total trace; busy persists until explicit request settles |
| I3 | Successful import with created2/updated1/folderRossi_Mario | `Import NAS completato da Rossi_Mario: 2 documenti creati, 1 aggiornati.`; refreshed subject visible and edit mode ends |
| I4 | Import rejects Error/string | Literal error/fallback; no reload or additional status; importing releases and retry control available |
| I5 | Import succeeds but reload rejects Error/string | Reload error/fallback, no success, no extra subject-effect/explicit status; old subject retained |
| I6 | Reload succeeds, explicit/effect status failure permutations | Import success alongside status failure; distinguish completion while other status pending |
| C1 | Read-only/confirmed edit and delayed search | Search/path-save initially disabled; input readonly; search says `Ricerca cartelle...`; save/input not disabled by candidate busy |
| C2 | Empty captured path, two distinct ordered candidates | First path selected; radio checked; DOM order equals response; exact candidates API two args; no update/import/status from search alone |
| C3 | Existing selected custom path; empty list; first empty path boundary | Preserve input; no implicit first selection; list replaced; empty list literal visible |
| C4 | Radio select second candidate versus typed path | Exact radio/input value; typing does not call API; unmatched path leaves all radios unchecked |
| C5 | Repeat search rejects Error/string after prior success | Previous options/input remain; literal failure/fallback; busy releases; prior success message remains |
| C6 | Change input while deferred search pending, empty/nonempty captured path | First result overwrites newly typed path for empty captured value; cleared nonempty captured value stays empty |
| P1 | Empty path save (also after prior successful message) | `Seleziona una cartella NAS da salvare.`; update not called; old success retained; no saving busy |
| P2 | Whitespace-only typed path | Exact `{nas_folder_path:"   ",nas_folder_letter:null}`; no trim/validation assumed |
| P3 | Match second candidate with letterR / empty-string / null | Exact path and respective letterR / "" / subject letter; first exact duplicate match if supplied |
| P4 | Custom path with subject letterS versus null | Exact `{nas_folder_path:"/custom/path",nas_folder_letter:"S"}` or null; no candidate-derived directory letter |
| P5 | Deferred update; fresh response path differs | `Salvataggio...` disabled; input remains editable until response; returned subject path wins, read-only resumes; no reload GET; two statuses; success literal |
| P6 | Update rejects Error/string | Literal error/fallback; selected path/edit mode/options preserved; no extra status and busy released |
| P7 | Update success with rejected status | Path success literal coexists with unavailable status; subject persisted, no update retry |
| R1 | Two status calls resolved in reverse order | Last-arriving old response overwrites new message/count; loading false while another pending is observable via button enabled state |
| R2 | Candidate search alongside save/import | Distinct busy labels/control states, no fabricated mutual exclusion; response hydration resets path but leaves candidates |
| R3 | Subject id change with old requests pending | New API calls use subject-2; late old subject/status can overwrite; record precise native schedule before golden assertions |
| M1 | Establish success, candidate failure/search, empty save, next import/save | Candidate command/empty guard retain success; import/nonempty save clear both messages at start |

Cases with noncanonical API boundary values must be explicitly labeled boundary
fixtures, never normal data. Duplicate/missing first path cases are optional
only within this same responsibility; no feature behavior should be inferred.
Core matrices use valid typed API shapes. Unreachable `subject?.` fallbacks are
not to be forced by synthetic function invocation merely to obtain coverage.

## Admission and small native measurement plan — NOT EXECUTED

Coordinator must separately admit ONLY a new
`frontend/tests/unit/campaign-utenze-nas-r22.test.tsx`; runtime remains read-only.
Author owns no heavy slot now. Root must budget disk/serial native allocation
before any command below. First failure stops with immutable evidence; no retry
without root decision. No build, dependency copy or coverage HTML output.

1. Write original tests mounting `UtenzeSubjectDetailPage` through the real module
   gate; typed subject/status/candidate fixtures, mock API boundary only. Existing
   page spec stays byte-exact. Use DOM click/change/radio/edit confirmation,
   deferred promises with awaited `act`, precise request argument/call counts and
   per-invocation event traces. Drain requests/cleanup per test; no sleeps or
   direct handler access. Stub unrelated child UI only as existing page tests do.
   New role queries use exact string names or anchored regex, not unsupported
   `{exact:true}`. Existing spec contains that option; do not modify it, and do
   not claim current native type failure without running an allocated check.
2. Serial small execution of original existing + new spec, e.g. from frontend:

   ```sh
   ./node_modules/.bin/vitest run tests/unit/campaign-utenze-detail-page.test.tsx tests/unit/campaign-utenze-nas-r22.test.tsx --maxWorkers=1 --no-file-parallelism
   ```

   Freeze tests/source/hash/counts/log and actual effect-versus-explicit event
   order. Repeated-reference subject tests must not conceal fresh-object effects.
   Native observed races and total ordering must be recorded before treating
   projected assertions as verified invariants.
3. Once allocated, original small full-file coverage measurement (no config
   edits, no threshold overrides), writing only small text/JSON evidence:

   ```sh
   VITEST_COVERAGE_INCLUDE='src/app/utenze/\[id\]/page.tsx' ./node_modules/.bin/vitest run tests/unit/campaign-utenze-detail-page.test.tsx tests/unit/campaign-utenze-nas-r22.test.tsx --maxWorkers=1 --no-file-parallelism --coverage --coverage.reporter=text --coverage.reporter=json --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261011-r22-utenze-nas-author/coverage-original
   ```

   Verify JSON contains exactly the intended `[id]/page.tsx` full runtime file,
   nonempty positive statement/function/branch/line denominators, and all four
   dimensions. Escaped bracket glob must be validated by actual resulting keys;
   empty output is INVALID evidence. Exit nonzero from100 thresholds is expected
   if whole-page gaps remain and is a STOP, never an authorization to weaken gates.
4. Convert genuine native uncovered statement/function/branch locations to a
   compact gap matrix. Separate NAS cases actually closed from untouched
   upload/preview/deletion/visura/domain UI gaps; do not use36% as the current
   gap. Tests above are one coherent missing responsibility, not a prediction
   of whole-page100. Remaining outside-scope gaps go to coordinator as a later
   separately admitted characterization responsibility, not this agent's scope.
5. Test-only publication, if root admits it, still requires independent frozen
   review, new-spec native types/lint, unchanged runtime/spec/config/baseline
   custody and allocated root integration gates. Runtime refactor stays blocked
   until genuine entire-file100 in all dimensions, zero missing/partial entries
   and real positive counts BEFORE change. Baseline/threshold/scope exclusions
   remain untouched. No runtime design or extracted hook is admitted here.

## Stop / handoff

Analysis finished; no new test written. Next action is Coordinator decision on
this exact new-spec matrix and serial small native allocation. No runtime change
accepted. Frozen source/native metric evidence supports readiness to characterize,
not refactor readiness. No Graphify refresh is delegated in this ANALYZE-only
allocation; coordinator retains governance/integration obligations. The original
full goal remains ACTIVE/INCOMPLETE and actual final application suites unverified.

## ORIGINAL existing-spec allocation — native measured baseline

Coordinator subsequently allocated this author ALONE EXCLUSIVE HEAVY for the
existing spec plus exact whole-file coverage. This appendix supersedes the
ANALYZE-only execution status above for this one command only. New spec creation,
runtime/config/types/lint/report/ratchet/build/install/cleanup remain unallocated.
The original analysis bytes are preserved privately as `analysis-report-frozen.md`
with original SHA-25654730b553eced70af94ef6bfe40b3456c3a41af8baf1a47fb6febf591f7e3121.

Preflight disk:448MiB available on shared disk,274MiB on `/dev/shm`.
HEAD/source/existing-spec hashes remained exact. Installed Vitest4.1.6 uses
picomatch and tinyglobby; both resolved the escaped include to exactly
`src/app/utenze/[id]/page.tsx` before the single execution. No threshold changes.

Executed from the dedicated tree's `frontend/`:

```sh
VITEST_COVERAGE_INCLUDE='src/app/utenze/\[id\]/page.tsx' ./node_modules/.bin/vitest run tests/unit/campaign-utenze-detail-page.test.tsx --maxWorkers=1 --no-file-parallelism --coverage --coverage.reporter=text --coverage.reporter=json --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261011-r22-utenze-nas-author/coverage-existing-original
```

Native result:1 spec/21 tests PASS,0 failed. Vitest duration2.64s.
Native exit1 solely for four unchanged global100% coverage thresholds;
this is the explicitly expected original legacy coverage gap, not a test failure.
No rerun or unexpected failure occurred. Raw JSON contains exactly one key:
`/home/cbo/CursorProjects/GAIA-campaign-20261010-r21-capacitas-job-actions/frontend/src/app/utenze/[id]/page.tsx`.
That entry's internal path matches; all denominator counters are positive.

| Dimension | Covered / total | Missing | Native percent | Required |
| --- | ---: | ---: | ---: | ---: |
| Statements | 209/576 | 367 | 36.28% | 100% |
| Branch arms | 229/610 | 381 | 37.54% | 100% |
| Functions | 36/176 | 140 | 20.45% | 100% |
| Lines | 208/536 | 328 | 38.8% | 100% |

The percentages happen to match historical values, but these are now fresh native
measurements of this exact original source/spec. Statements/functions/branch
counters derive from raw JSON; line coverage is the maximum statement hit count
per statement-start line and matches native text208/536.296 branch-map entries
contain610 arms, so reporting296 as the branch denominator would be incorrect.

| NAS source region | Statements covered/total | Branch arms covered/total | Function observations |
| --- | ---: | ---: | --- |
| Status496–514 | 7/7 | 1/2 | callback18 hits; non-Error fallback remains uncovered |
| Import597–614 | 0/10 | 0/2 | handler0 hits |
| Candidates616–630 | 0/9 | 0/6 | handler0 hits |
| Save path632–656 | 0/15 | 0/7 | handler and candidate-find callback0 hits |
| NAS effect889–894 | 4/4 | 2/2 | callback37 hits |
| Quick eligibility961–964 | 1/1 | 1/4 | no separate function |
| Header import1059–1073 | 0/3 | 10/20 | three inline button callbacks0 hits |
| Status card1140–1170 | 0/1 | 8/14 | inline import callback0 hits |
| Override2042–2105 | 0/5 | 7/17 | search/input/save/map/radio callbacks0 hits |

These are location-based observations, not global attribution or promises about
future coverage. True eligibility, missing pending fallback and the three NAS
command bodies are still unexercised; matrix S1–M1 remains genuinely missing.
Import/candidate/path command bodies alone have34 missing statements and15 missing
branch arms. Whole-file missing367 statements/381 arms/140 functions/328 lines
also include out-of-scope responsibilities: document grouping helpers145–203,
ANPR/visura403–492, classification574–593, upload/delete659–711,
preview716–887, preview cleanup/Escape899–925, document filtering967–994,
manual-upload UI1210–1456, personal fields1515–1739, document controls1760–1949,
Catasto1981–2031, audit/metadata2112–2145. Genuine NAS tests cannot be claimed as
sufficient for full-file100; additional responsibility allocations belong to root.
No scope extension or synthetic execution is admitted to close those gaps here.

Private evidence retained:

- `original-native-command.json`: exact argv/cwd/include/reporters/threshold policy.
- `original-native.log`: complete native single-run output.
- `original-native-exit.json`: native exit1.
- `coverage-existing-original/coverage-final.json`: raw exact full-file counters/maps.
- `original-coverage-gaps.json`: exact key/hash, positive dimensions, all uncovered
  line ranges and function spans, NAS region counts and missing branch-arm locations;
  SHA-256 `02ba489519eedd2e549dd327bd3528d5a978029814566871d66e505548bc0302`.

STOP: ORIGINAL allocation complete, HEAVY RELEASED. No new test written.
Next action is root admission of the already documented genuine NAS test matrix,
with separately allocated serial execution. Runtime remains BLOCKED_COVERAGE;
whole original goal ACTIVE/INCOMPLETE, no runtime ACCEPT or reduction credit.

## Admitted implementation — frozen original NAS tests

Coordinator separately admitted the new NAS spec and serial native gates after
accepting the original diagnosis, without any runtime coverage waiver. This
appendix records that allocation. Earlier analysis/original appendices remain
byte-preserved as prefixes and private frozen copies; every attempt is retained.

ONLY added `frontend/tests/unit/campaign-utenze-nas-r22.test.tsx` plus this report.
New spec SHA-256:
`8f2258e4cb65b2242ac65fc39a1407fad9a6a48457060387ef7392e39c0ed6d9`.
45 new mounted tests; original immutable21 unchanged; union66 tests. No skipped
or weakened assertions. The tests mount the actual exported detail page and real
module session gate with API/auth/navigation boundaries mocked; unrelated layout
and child panels are stubbed, and actual95 imported runtime sources are included
in the separately checked new-spec TypeScript program.

### Behavior now demonstrated natively

- Status is requested only after subject resolution; pending status does not
  hide subject. Exact token/id arguments, fail-closed Error/non-Error results,
  folder/count UI, quick eligibility for positive/zero/negative pending and
  can_import=false, edit-mode header difference, null-pending boundary fallback,
  and independent missing_in_nas flag are asserted. Other tabs remove Scheda
  status/override while header action remains.
- Both header and status-card import controls submit only token/id, never the
  unsaved selected path. Deferred import keeps both busy controls disabled and
  prevents premature reload. Genuine fresh-object reload makes two status calls
  in addition to initial status; hydrated input resets and edit mode terminates.
  Literal created2/updated1 success, Error/non-Error import failures, successful
  server import followed by Error/non-Error reload failure, swallowed status
  failures, and same-reference reload's absence of extra effect are tested.
- Deferred mounted trace proves exactly `[import,reload,status-1,status-2]`.
  Resolving status-2 first changes UI but leaves importing active and success
  absent; resolving status-1 then overwrites the newer result and publishes
  success. This native completion observation identifies status-1 as the awaited
  explicit request and status-2 as the subject effect; no any-order assertions.
- Candidate search asserts two-argument API call, busy/read-only control states,
  independent save/import/input controls, API order without score/review sorting,
  first selection, exact radio/typed input selection, existing path preservation,
  empty replacement list, empty-first-path boundary, Error/non-Error failures
  retaining old options/path, and both captured-value races during deferred
  search. Empty captured value overwrites a newly typed path; captured nonempty
  value does not select after input is cleared.
- Path save asserts empty guard/no API, candidate versus second-candidate letter,
  candidate empty-string/null fallback, unmatched custom path with subject/null
  letter, whitespace-only boundary payload sent verbatim, exact two-key update
  arguments, deferred independent controls, response hydration overwriting an
  edited input while retaining options, no reload GET, Error/non-Error update
  failure retaining edit state, and success despite both status failures.
- Deferred path trace proves `[update,status-1,status-2]`. Both requests initially
  disable header import while old status remains visible. Resolving status-1
  publishes path success and enables import despite still-pending status-2;
  status-2 later replaces the status/count. This preserves the current boolean
  loading lifecycle, with no invented request counter.
- Shared-message tests prove candidates and empty guard retain prior success,
  while nonempty save/import clear prior success/error immediately. Candidate
  search and path save can overlap; later subject hydration wins input while
  preserving returned candidate options. Route rerender retains the mounted
  instance: new requests use subject-2, but late subject-1 status overwrites UI;
  subsequent public import still addresses subject-2.

Fixtures are independent API data, not copied runtime orchestration. Null pending,
empty first path and whitespace path cases are explicitly labeled boundary data;
core scenarios use valid typed API objects. No test invokes handlers directly,
extracts compiled functions, inspects source strings, calculates fake coverage,
or alters production code to make behavior reachable. Exact role names use
supported string matching; the old spec is not type-edited.

This is a coherent command responsibility, not every proposed optional case.
Duplicate-path candidate data was omitted before the first native run to avoid
manufacturing duplicate React keys. Late old subject GET overwriting a newer
subject was analyzed but not claimed as tested; the mounted route test covers
late old status. Individual mixed success/failure permutations of both duplicate
status requests are not all separately enumerated; actual reverse resolutions,
explicit-first completion and both-failed outcomes are covered.

### Actual native gates — first attempts only

Pre-test disk427MiB; before native55a364MiB; final361MiB, tmpfs274MiB.
No dependency copies, HTML reports, build, install or cleanup.

| Gate | Exact evidence stem under private author directory | Actual result |
| --- | --- | --- |
| New spec + immutable old spec, one worker | `new-union-attempt1` | exit0;2 specs66/66PASS;5.97s |
| Same union + exact full-file coverage/text+JSON | `new-coverage-attempt1` |66/66PASS; exit1 ONLY unchanged four100 thresholds;9.04s |
| Real project TypeScript | `project-types-attempt1` | `npm run typecheck -- --incremental false`; exit0 |
| Real new-spec imported TypeScript program | `new-spec-types-attempt1` | private `type-r22-new-spec.cjs`;95 actual runtime sources,0 diagnostics;exit0 |
| Scoped new-spec lint | `new-spec-lint-attempt1` | `eslint tests/unit/campaign-utenze-nas-r22.test.tsx --max-warnings=0`;exit0 |
| Actual global native merge-base ratchet | `native55a-attempt1` | `python3 -B tools/code_quality/complexity.py ratchet --base-ref 55a1b1d35911451e018b662c2acc450bf5994ea2`;exit0/findings[] |

Each stem has exact command JSON/native log/exit JSON. New-spec attempt1 bytes
are independently frozen as `new-spec-attempt1.test.tsx`. Project typecheck did
not skip application source; the new-spec program uses native TypeScript with
actual project options/imports, not a synthetic declaration-only approximation.
Its configured roots are next-env, the new spec and jest-dom's Vitest types;
old existing spec remains untouched and is outside this separate new-spec gate.
Native55a ran only after tests/types/lint were green and disk was checked;
actual baseline_commit equals the full55a hash. It saw264 changed paths including
the two untracked owned additions. No scope/threshold/baseline update or global
report was performed. Diff whitespace checks also included both untracked files
using `git diff --no-index --check /dev/null <owned-file>`.

### Genuine full-file residual coverage — still FAIL100

Raw `coverage-new-union-attempt1/coverage-final.json` contains exactly the same
single full `[id]/page.tsx` key and internal path as original. All denominators
remain positive and unchanged. Tests executed the original runtime, not a
candidate implementation. Native text and raw counters agree.

| Dimension | Original | With new NAS spec | Gain | Still missing | Required |
| --- | ---: | ---: | ---: | ---: | ---: |
| Statements |209/57636.28%|253/57643.92%|44|323|100%|
| Branch arms |229/61037.54%|273/61044.75%|44|337|100%|
| Functions |36/17620.45%|49/17627.84%|13|127|100%|
| Lines |208/53638.8%|251/53646.82%|43|285|100%|

| Region | Statements | Branch arms | Function hits |
| --- | ---: | ---: | --- |
| Status496–514 |7/7|2/2|106|
| Import597–614 |10/10|2/2|11|
| Candidates616–630 |9/9|6/6|23|
| Save path632–656 |15/15|7/7|handler20/find11|
| NAS effect889–894 |4/4|2/2|149|
| Quick eligibility961–964 |1/1|4/4|inline value|
| Header1059–1073 |2/3|20/20|NAS import2+8;manual-modal callback0|
| Status card1140–1170 |1/1|14/14|import1|
| Override2042–2105 |5/5|15/17|search23/input18/save20/map89/radio3|

Full native coverage of these command bodies is a diagnosis only, never a
substitute for full-file100. NAS display still has two missing identifier arms
at2095 (`partita_iva` and identifier-unavailable fallback); fixtures used canonical
codice_fiscale. Header callback1070 opens manual upload, which remains outside
this command scope and is not invoked to inflate coverage. Whole residual gap
also includes document-grouping helpers145–203, ANPR/visura403–492,
other personal-save branches518/547–548, classification574–593,
upload/delete659–711, preview716–887/cleanup/Escape899–925,
document-filter helpers956–994, manual-upload UI1210–1456,
personal fields1515–1739, document controls1760–1949,
Catasto1981–2031, audit/metadata2112–2145. Their precise145 uncovered-line ranges,
127 uncovered function spans and all337 missing arm locations/counts are retained
in `new-union-coverage-gaps.json` rather than concealed by percentages.
Gap artifact SHA-256:
`7463615973dc01c7f937f3508b5c735f933d9faedfe37ba799646f535eb400a2`.

### Final custody, classification and handoff

Final source hash b0f822... and existing spec79ef301... remain exact;
config/package and baseline equal immutable HEAD. Baseline SHA-256 remains
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
Working tree has ONLY the new spec and this report untracked; tracked diff empty.
Frozen prior native command/log/raw/gap evidence preserved; original analysis
and baseline report copies retain54730b... and01b926e8... respectively.
Final manifest/custody JSON records all artifact hashes, native gates and original
integrity checks. No source import/commit/push/publication or Graphify refresh.
Coordinator retains integration/governance/Graphify obligations after review.

Classification: CHARACTERIZED_ONLY / NO_CHANGE complexity. DetailContent391/304/
1908 and file729cognitive/723cyclomatic/2118LOC remain unchanged; no IMPROVED
credit. Runtime BLOCKED_COVERAGE until genuine entire-file100; no waiver.
Full original campaign ACTIVE/INCOMPLETE, final application suites unverified.

STOP: coherent NAS characterization and all delegated gates complete;
HEAVY RELEASED. Frozen spec/report now require distinct fresh independent review
and root integration/acceptance before test-only publication. Do not start
another responsibility or runtime refactor from this handoff.
