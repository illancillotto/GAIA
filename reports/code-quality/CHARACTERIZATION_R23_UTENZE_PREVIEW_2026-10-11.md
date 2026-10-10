# R23 — original Utenze document preview (ANALYZE ONLY)

Date2026-10-11. Classification CHARACTERIZATION_PLANNED. No runtime admission,
complexity improvement, coverage PASS or native R23 test result claimed.
Global original goal ACTIVE/INCOMPLETE; runtime BLOCKED_COVERAGE.

## Allocation, skills and fresh custody

Read FIRST the private R23 brief and integration registry
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R23_UTENZE_PREVIEW_2026-10-11.md`.
Dedicated clean reused tree:
`/home/cbo/CursorProjects/GAIA-campaign-20261010-r21-capacitas-job-actions`;
branch `characterize/complexity-r23-utenze-preview`;
HEAD `35d4121ecd8320271aab8cbcfc4d4f55e3aae4a1`;
main merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Initial working tree clean. All repository commands specified this tree, except
reading the explicitly assigned integration registry in its own tree.

Checkpoint and repository complexity skills/rules remain active from the prior
session; latest PROGRESS R22 accepted/integrated was read from this branch.
Only this NEW report and small private analysis artifacts are written. Runtime,
all existing tests/config/tooling/baseline and old R21/R22 evidence are read-only.
No test writing, tests/type/lint/report/ratchet/build/Graphify refresh, cleanup,
install, dependency/worktree copy, model/provider change, commit/push/import or
agent spawn. Free disk2160MiB/tmpfs274MiB at preflight; recovered headroom does
not imply admission of heavy gates or a full build.

| Protected item | SHA-256 |
| --- | --- |
| Original `[id]/page.tsx` | `b0f822daf809b0744b912f0f159a2e833c556dda289466b6ed45329a79e3d6b1` |
| `src/lib/document-preview.ts` | `4600f63d6e31fc037bfc5d064d66fcc1b9ae58243fdbbcf9571f6bfb9db1a866` |
| Original page21 spec | `79ef301017ee78985d71b468300eba3239e901c9773eb56f60a033cd6ad13f98` |
| NAS45 spec | `8f2258e4cb65b2242ac65fc39a1407fad9a6a48457060387ef7392e39c0ed6d9` |
| Existing format helper spec | `bed62f690b67c611a168c02369d4df83b669d98660d97db9666237295d69edd5` |
| Frozen R21 integrated native complexity report | `c0cb68725d35a348e7902e642c7afb078881cbc4b1acc7c544da7f90b6512e66` |
| Published R22 integrated raw full-file coverage | `07e94d8db84c9f4f3bb4d078a9db66387cc1d2504545c1681fe7102773412c6b` |

18 protected paths (runtime/helper/config/package/baseline and13 existing
Utenze/format specs) equal HEAD. Page/helper and original page/helper specs also
equal frozen native report source commit
`509a3913a2664c036c8aa34650a1765d6517dc3f`. NAS spec is protected at current35d
and was introduced after that frozen report. Page history737fffca/069eea98/
254d908a; format helper historyd6fe1d78/c4f72f06. No runtime edit since R22.

Native sources read:
`~/.cache/gaia-campaign/20261010-r21-integrated/integrated-complexity.json`;
`~/.cache/gaia-campaign/20261011-r22-integrated/coverage/coverage-final.json`
and `coverage-audit.json`. Private small evidence lives in
`~/.cache/gaia-campaign/20261011-r23-utenze-preview-author/analysis-evidence.json`:
full custody, exact metrics, published raw key/hash and region missing locations.
No historical percentage is substituted for that published native measurement.

Graphify orientation was performed by coordinator: dedicated frontend query
`openPreviewFromBlob` found no matching nodes. Earlier DetailContent orientation
is known; no additional graph edge is invented and no extraction/refresh runs.

## Scope and exact unchanged native metrics

ONE responsibility: actual page preview selection → download/blob → format
adapter → modal → objectURL/close/Escape/cleanup. Public document row/button/
keyboard and Catasto preview controls are in scope. Existing selectors can be
traversed naturally to reach those controls. Upload/classification/deletion,
NAS commands, visura requests, forms/domain changes and general list refactoring
are outside scope. The format helper is read-only and remains the real dispatcher
in any future tests; it must not be replaced by a copied test algorithm.

| Native callable / source span | Cognitive | Cyclomatic | LOC | Nesting |
| --- | ---: | ---: | ---: | ---: |
| `DetailContent`,214–2206 |391|304|1908|2|
| `closePreviewModal:useCallback[0]<callback>`,747–759 |1|2|13|1|
| `openPreviewFromBlob`,761–866 |18|17|98|1|
| `handlePreviewDocument`,868–874 |1|2|7|1|
| `handlePreviewCatastoDocument`,876–887 |0|1|12|0|
| Sheet map,836–847 |1|2|12|0|
| Row map,845 |1|2|1|0|
| Cell map,845 |1|2|1|0|
| URL cleanup effect,896–902 |1|2|7|1|
| Its returned cleanup,897–901 |1|2|5|1|
| Escape effect,904–926 |6|6|19|1|
| `handleKeyDown`,909–922 |3|4|12|1|
| Returned listener cleanup,925 |0|1|1|0|

Four primary preview callables sum20 cognitive/22 cyclomatic/18 decisions/
130 effective LOC. Nested callbacks are separately listed; sums are native
inventory, not promises about reducing enclosing391 or physical decision credit.
`openPreviewFromBlob` already has cyclomatic17 ERROR, LOC98 ERROR and cognitive18
WARNING. No metric was regenerated or changed in this analysis.

Whole page176 callables, cognitive729/max391, cyclomatic723/max304,
547 decisions, effective LOC2118,2231 physical lines,22 imports/dependencies,
official useState28/useEffect10/useReducer0. Supplemental AST50 file/49 component
state-call count from R22 remains distinct from the official textual hook count.
Format helper: getExtension1/2/4, isPdfFilename0/1/3, getDocumentPreviewKind9/9/23
(cognitive/cyclomatic/LOC); file34LOC/3callables/cognitive10/cyclomatic12, no
violations. All source bytes match the native report binding.

## Original invariants and public reachability

### Selection, guard and request order

Utenze document row has `role=button`/tabIndex0; click or keydown Enter/Space
launches preview. Nested Preview stops propagation before invoking the same
handler. The select stops click propagation and is not a preview action.
A document with `id:null` still has its row and Preview control, so the guard is
PUBLICLY REACHABLE: saveError becomes
`Il documento non ha un identificativo valido per la preview.`, with no download,
URL creation or preview modal. Do not classify that guard as impossible or remove
it to obtain coverage. Non-activation keys do not invoke download.

Valid document calls `downloadUtenzeDocumentBlob(token,document.id)` as an argument
BEFORE entering openPreviewFromBlob. Consequently download invocation precedes
any explicit revoke of an existing URL. No selected path, extension or filename
is sent to the API. Adapter GET is `/utenze/documents/{id}/download`, bearer token.
Catasto calls `downloadCatastoDocumentBlob(token,id)` (GET
`/catasto/documents/{id}/download`, bearer), also before open's revoke; there is no
Catasto invalid-id guard. Correlation row/Enter/Space/nested Preview all route to
that handler. Real visura card's `Visualizza visura` forwards latest document to
the same Catasto preview handler; no visura request need be triggered to test it.

Snapshot preserves filename, extension via nullish fallback, boolean is_pdf via
nullish filename fallback, type/classification via nullish default. Snapshot id
is null and paths empty regardless of original document; these internal fields
must not be probed through compiled handler extraction. Valid typed Utenze DTOs
provide is_pdf:boolean/doc_type:string/classification_source:string; Catasto
handler explicitly supplies derived extension/is_pdf and visura/catasto values.
Thus open's absent doc_type/classification default and null is_pdf fallback are
not reached by valid public DTOs. Keep such residual arms visible; do not delete
properties or fake an internal invocation merely to reach them. Metadata-mismatch
fixtures can still use valid types, e.g. filename.pdf/extension.png/is_pdf:false.

### Modal state, dispatch and conversion

Opening clears old URL/error/html/sheets/text, stores new preview document, sets
loading=true and kind=download. It does NOT clear shared saveError/saveMessage.
Awaited blob creates objectURL BEFORE dispatch/conversion. ObjectURL is stored
before any asynchronous DOCX/spreadsheet/text processing. The modal's header
Scarica appears as soon as that URL commits, even while conversion is loading or
has failed. Before blob resolution no Scarica/link exists. Loading literal is
`Caricamento anteprima...`; Chiudi remains available throughout.

Dispatch uses lowercased explicit extension or lowercase last-dot filename
extension; explicit empty string prevents filename fallback. getDocumentPreviewKind
prioritizes isPdf===true OR extension.pdf, then image, docx, spreadsheet, text,
otherwise download. isPdf=false does NOT veto an actual.pdf extension. Blob MIME
is not consulted. Case of filename/download attribute/title is preserved.

| Kind | Trigger examples | Literal rendered result / boundary |
| --- | --- | --- |
| PDF |.pdf/.PDF or is_pdf:true |iframe src=URL/title=original filename; header Scarica |
| Image |.jpg/.jpeg/.png/.gif/.webp/.bmp/.svg |actual Next Image, unoptimized, alt=filename/src=URL |
| DOCX |.docx |dynamic Mammoth import; blob.arrayBuffer; convertToHtml({arrayBuffer}); HTML result.value rendered |
| Spreadsheet |.xls/.xlsx |dynamic XLSX import; blob.arrayBuffer; read(buffer,{type:"array"}); first3 sheets in source order |
| Text |.txt/.csv/.log/.md/.json/.xml/.eml |blob.text(), literal pre text/whitespace, no HTML interpretation |
| Download |unknown/no extension, or explicit empty extension |`Anteprima inline non disponibile per questo formato.` and Scarica documento link |

DOCX empty value gives
`Nessun contenuto leggibile disponibile per questo file DOCX.`.
Spreadsheet sheet_to_json options are exactly header1/blankrowsfalse/defval"".
Only first25 rows of each first3 sheets are kept; each cell becomes String(cell??"").
UI substitutes `—` for empty strings, preserving literal "0" and "false". Empty
sheet shows `Foglio senza celle valorizzate.`; no sheets shows
`Nessun dato tabellare leggibile disponibile per questo file.`. CSV is TEXT, never
spreadsheet. Text empty string gives `File di testo vuoto.`; whitespace and "0"
are nonempty content.

Download/blob/arrayBuffer/conversion/text/URLcreate failures are caught with
Error.message or `Errore caricamento anteprima documento`; finally clears loading.
Error suppresses every inline renderer. If URL was already created before adapter
failure, header Scarica remains and that URL is not revoked until later lifecycle
cleanup. Failure before URL creation has no download link. No adapter failure
changes API routing or retries download.

### URL lifecycle and listener ordering — preserve duplicates

closePreviewModal explicitly revokes captured previewUrl if truthy, then sets
URL/document/error/content null or empty, loadingfalse and kinddownload. URL effect
cleanup ALSO revokes the old committed URL on dependency replacement/unmount.
Thus normal loaded Chiudi/Escape causes two revokes of the same URL: explicit
close followed by effect cleanup. Opening replacement while a URL is committed
similarly invokes the next download first, explicitly revokes old URL, clears it,
and effect cleanup revokes it again. Loaded unmount without explicit close has
one effect revoke. Closing while initial blob is pending has no URL to revoke.
These are source-derived expectations; freeze exact full native event traces
before promoting schedules to golden assertions. Immediate versus deferred blob
resolution can alter whether a null-URL intermediate commit occurs; no invented
static total order across React passive effects.

Keydown listener is absent when previewDocument and manual-upload modal are both
absent. With previewDocument, Escape closes preview and returns before the manual
branch. Other keys return without closing. URL change recreates close callback,
therefore listener removal/re-addition follows dependency changes. Cleanup removes
the exact registered callback on close/unmount/replacement. Do not assert only
that some callback was removed, or include unrelated component listener calls.
Testing manual-upload Escape or both modals' precedence would expand scope; its
uncovered arms remain explicit residuals.

Modal has no dialog role, autofocus, focus trap or inert/disabled underlying rows.
A focused document row can retain focus after Enter opens preview. Replacement
can therefore be exercised via still-focused public row keyboard activation;
focus/activeElement must be shown in the test rather than pretending an ordinary
pointer click penetrates the overlay. If native DOM/focus evidence cannot support
this interleaving, STOP/report the limitation; do not invoke handlers directly.
Backdrop has no close handler; closing must use Chiudi/Escape.

### Late responses and overlap — no race fixes

No request generation/cancellation/abort or stale-document check exists.

- Close-before-blob: late blob still creates/stores URL and clears loading while
  previewDocument remains null, so no modal reappears. URL survives hidden until
  dependency cleanup/new open/unmount. Test exact cleanup after draining the
  late promise; do not count a URL as revoked just because modal disappeared.
- Close-after-URL but before conversion: double revoke occurs, then late conversion
  still writes html/kind/content without reopening the closed modal.
- Close-before-first blob, open second document, resolve second then first: first
  late URL can replace second URL while second filename/document stays selected.
  Cleanup can revoke the second URL even though second UI remains. This is genuine
  old content/new filename mixing, not an invariant to repair in characterization.
- First conversion pending, close/open second, then resolve old conversion: old
  HTML/sheet/text and kind can overwrite second document's presentation while
  second URL and filename remain. Old finally can clear busy for a newer request.
- Late rejection after close stores error with no modal; after new open it can
  replace the newer preview's error and clear its loading. Failed old requests
  must not be silently discarded in expected assertions.

Exact native trace must distinguish download invocation, blob settlement,
URLcreate/revoke, adapter invocation/resolution and listener add/remove. Expected
content/link/title must use literal fixture labels; do not calculate expected
output by copying runtime transformations.

## Published native residual gap and existing evidence

R22 integrated existing66 PASS, whole-file still FAIL100:
statements253/57643.92%, arms273/61044.75%, functions49/17627.84%,
lines251/53646.82%; missing323/337/127/285. This is published native evidence,
NOT a new R23 execution. Raw has exactly one integration `[id]/page.tsx` key,
positive counters and zero skipped in the audit; source bytes equal current35d.

| Location region | Statements covered/total | Arms covered/total | Native function evidence |
| --- | ---: | ---: | --- |
| Close747–759 |1/11|0/2|close0 hits; covered declaration is not execution |
| Open761–866 |0/50|0/30|open and3 nested mapping callbacks0 |
| Document868–874 |0/4|0/2|handler0 |
| Catasto876–887 |0/1|0/0|handler0 |
| URL effect896–902 |3/4|1/2|effect and returned cleanup64 hits; truthy URL never exercised |
| Escape904–926 |3/13|3/10|effect64; key handler/registered cleanup0 |
| Modal1394–1493 |0/3|1/51|3 nested sheet/row/cell UI callbacks0 |
| Document controls1853–1936 |0/12|0/20|rows/keyboard/Preview and adjacent select/classification callbacks0 |
| Catasto controls2000–2038 |0/7|0/8|row/keyboard/Preview callbacks0 |

Four core location regions alone have65 missing statements and34 arms; function
invocations all0. UI/control region counts include adjacent declarations and
out-of-scope callbacks: do not claim every missing entry in those spans belongs
to preview. Raw V8 function body location for open begins764, whereas the native
complexity declaration span begins761; both are retained rather than matched by
an invented exact line. Precise missing spans/counts/arm locations live privately.

Old page21 and NAS45 specs stub visura preview child and never invoke preview;
new NAS scope is immutable. `document-preview.test.ts` has13 direct helper cases
for precedence/extensions/formats, but does not mount/download/convert/cleanup.
`utenze-subject-visura-card.test.tsx` asserts only forwarding onPreviewLatest,
not the page pipeline. API tests prove transport adapter boundaries separately;
other Catasto district preview tests exercise a different component. No existing
Mammoth/XLSX/objectURL Utenze page pipeline coverage was found by targeted search.

## Proposed genuine mounted missing-case matrix — no test written

Later owned optional spec ONLY
`frontend/tests/unit/campaign-utenze-preview-r23.test.tsx`, after separate root
admission. All cases mount actual authorized page and real format helper;
public API/browser/conversion boundaries may be mocked, runtime stays immutable.

| Group | Stimulus through public UI | Literal assertions / missing behavior |
| --- | --- | --- |
| P1 |Nested Preview, card click, focused card Enter/Space; nonactivation key |Exactly one Utenze token/id call; bubbling stopped for nested button; inert key0 calls; read-only still permits preview |
| P2 |Typed document with id:null |Exact guard text; no download/URL/modal; guard is reachable |
| P3 |Catasto row/nested Preview/Enter/Space; actual Visualizza visura |Exactly Catasto token/document-id; no Utenze download or visura request |
| P4 |Deferred blob |Filename modal/Caricamento anteprima.../Chiudi present; no Scarica/URLcreate before resolution; URLcreate receives exact Blob |
| F1 |PDF upper/lower case; .png override filename.pdf with is_pdffalse; is_pdftrue unknownextension |Literal iframe/title/src versus actual img/alt/src; original case/download filename retained |
| F2 |Extensionnull filenamefallback, empty-extension boundary suppressing fallback, no extension, unsupported .zip/MIMEpdf |Literal download fallback/link href/download; no iframe/image; MIME does not select format |
| F3 |DOCX nonempty adapter literalHTML and empty value |Exact convertToHtml buffer argument/order, rendered `<strong>` label and empty fallback, header URL/link retained |
| F4 |Four sheet names, first sheet26 rows, secondempty, third mixedcells, fourth sentinel |read exact buffer/{type:array}; sheet_to_json exact worksheet/options/3 calls; sheet order A/B/C, D absent; row25 present/26 absent; literal cells —/0/false/—/keep |
| F5 |Workbook no sheets and sheet with no rows |Distinct no-tabular-data versus empty-sheet literal; no fabricated extra cells |
| F6 |Text/CSV/EML, empty text, whitespace, literal <tag>& |Exact pre content/escaping and File di testo vuoto.; CSV not XLSX; arrayBuffer/adapters not called for text |
| E1 |Error/non-Error blob rejection |Exact error or fallback; loading released; no URL/Scarica; Chiudi works |
| E2 |Mammoth reject/arrayBuffer reject; XLSX read or sheet_to_json throw; text reject |Exact adapter/error literal; after-created URL still linked; no inline body; no API retry |
| E3 |URLcreate throws Error/non-Error |Preview error/no created link; subsequent public open clears old error |
| U1 |Loaded Chiudi then reopen same document; loaded Escape; loaded unmount |Freeze literal create/revoke sequence and double revoke; unmount single revoke; no reappearance; each new open resets content |
| U2 |Close initial pending blob, then late resolution/rejection, then unmount |No modal reopens; late successful URL cleanup observed; late error hidden; no synthetic cancellation |
| U3 |Close pending DOCX conversion after URL creation, then resolve |Two revokes; no modal after late content; next public preview does not retain old closed-state content unless actual race writes it later |
| U4 |Focused-row replacement with old committed URL |Prove retained activeElement; next download before explicit old revoke; observe cleanup duplicate and create nextURL; freeze full native order |
| R1 |Close A pending blob, open B, resolve B then A |B filename/title/download attr persists with late A URL; B URL cleanup; no discarded old response |
| R2 |A conversion pending, close/open B, then resolve/reject A |Literal old content/error/kind contamination and loading lifecycle, not normalized latest-wins |
| K1 |Non-Escape versus Escape; URL change; close/unmount |Exact keydown listener callback registration/removal identities; no lingering listener; no manual-upload branch expansion |
| K2 |Backdrop click and focus retention |Backdrop leaves modal open; keyboard activation explanation supported by actual DOM focus |

Core fixtures: complete typed Utenze document (id nullable, unique nas_path,
required smart/content/warning fields), complete Catasto document, actual Node
Blob from existing setup, unique URL outputs `blob:r23-A`/`blob:r23-B`, literal
conversion/workbook outputs. Keep preview fixtures at <=5 documents; no list
pagination/filter expansion merely to gather coverage. Retain real Next Image
for image DOM; stub unrelated ANPR/domain children. To test latest-visura preview,
retain actual visura card and avoid request/confirmation actions. Other variants
can use correlation controls without expanding the visura responsibility.

Existing setup replaces global Blob with NodeBlob (arrayBuffer/text/stream already
real). Prefer actual small Blob bodies. Spy only individual read methods for
pending/error interleavings; do not implement a custom fake Blob dispatcher.
Mammoth named convertToHtml and XLSX read/utils.sheet_to_json may be hoisted module
boundary mocks because dynamic imports use those packages. Return real-shaped
literal adapter results (`value`/`messages`, SheetNames/Sheets and rows), assert
literal expected DOM/calls independently. This tests orchestration and adapter
contract, not binary DOCX/XLSX parser correctness; no need for large archives.

Browser URL functions can be locally installed/stubbed if jsdom lacks them,
with original descriptors restored after cleanup. Do not replace all URL globals.
Filter window listener spies by keydown and preserve actual add/remove behavior;
restore spies after draining all deferred requests/unmount. No sleeps, fake timers,
direct event-handler calls, extracted compiled probes or source-string assertions.
Avoid selecting a background pointer target through overlay to manufacture
replacement; use focus/keyboard evidence or close/open interleaving instead.
Modal has no role=dialog, so scope through its visible Anteprima documento title
and actual DOM panel, not a test-only semantic wrapper. Duplicate filename text
must be scoped to modal versus row. Role options use supported string/regex
matching, never old unsupported `{exact:true}`.

## Feasible phased native plan — needs separate allocation

1. Coordinator reviews this frozen scope/matrix first. Admit ONLY new preview spec
   + report/private artifacts; author exclusively heavy after fresh disk check.
   No runtime/old-test/config/baseline change. Approximate45–60 genuine cases is a
   planning budget, not an actual test count or guaranteed full-file outcome.
2. First small serial run from dedicated frontend: new preview spec + old page21
   + NAS45, maxWorkers1/no-file-parallelism. Optionally retain existing13 helper
   cases if root allocates that union. Freeze exact source/spec/hash and native
   URL/listener/conversion traces before asserting total ordering. First unexpected
   native assertion/type/import failure STOP, save evidence, no auto correction
   or rerun. Root must decide any correction.
3. Exact entire original `[id]/page.tsx` coverage (not preview-region include):

   ```sh
   VITEST_COVERAGE_INCLUDE='src/app/utenze/\[id\]/page.tsx' ./node_modules/.bin/vitest run tests/unit/campaign-utenze-preview-r23.test.tsx tests/unit/campaign-utenze-detail-page.test.tsx tests/unit/campaign-utenze-nas-r22.test.tsx --maxWorkers=1 --no-file-parallelism --coverage --coverage.reporter=text --coverage.reporter=json --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261011-r23-utenze-preview-author/coverage-original-attempt1
   ```

   Validate escaped glob against installed resolver and raw JSON exactly one
   full-file key, all four positive denominator counters. Keep unchanged100
   thresholds. Expected residual FAIL100 is legacy gap, not an assertion failure
   or runtime waiver. Map native missing functions/lines/arms, including impossible
   valid-DTO defaults and manual Escape arms; do not fabricate execution to close
   them. Store small text/JSON only, no HTML/default report copies or broad suite.
4. After tests pass, real project nonincremental noEmit types and actual new-spec
   imported TypeScript program; scoped lint maxwarnings0. Only after these gates
   are green and fresh disk check, root may allocate/read-only native55a ratchet.
   Runtime stays unchanged, so frozen source-bound metrics are sufficient; no
   global-report regeneration or baseline update needed for this diagnosis.
5. Freeze all attempts/source/spec/report/config/baseline/old evidence custody;
   STOP/release. Distinct fresh independent review and root integration required
   for test-only acceptance/publication. Characterization never authorizes a
   runtime decomposition while whole-file100 remains unmet.

Current~2.1GiB headroom permits analysis, not automatic broad/final suites or
build. Small native phase should use existing dependencies and one worker, no
worktree/dependency copying and no cache cleanup. Stop on ENOSPC/unexplained
failure; preserve artifacts. Remaining NAS identifier display, upload/deletion/
classification/visura/ANPR/domain forms and unrelated list behavior stay under
root's later allocation; no scope expansion to inflate R23 coverage.

## Stop and handoff

Analysis complete. Only NEW R23 report/private evidence written, no new test or
heavy gate executed. Classification CHARACTERIZATION_PLANNED, runtime
BLOCKED_COVERAGE; global ACTIVE/INCOMPLETE, official metrics and strategic tail
unchanged. Next action: coordinator admission/rejection of this exact mounted
preview matrix and phased native budget. No runtime ACCEPT or IMPROVED claim.
Coordinator owns subsequent governance/Graphify/publication obligations.

## Admitted new-test-only phase — native first attempts frozen

Coordinator separately admitted ONLY new mounted preview spec, own report
amendment/private artifacts and serial native tests/coverage/types/lint. Frozen
analysis bytes were copied BEFORE amendment to `analysis-report-frozen.md`, still
SHA-256 `b565d6ba2ee1dcab34fd6f76bd4e25ed74a9f5ae4813864d6a26f1af34afcc55`.
This appendix supersedes the earlier ANALYZE execution status for this phase only.
No runtime, old test, config, baseline, tooling or scope changes were authorized
or made; no ratchet/global report/build/Graphify/install/cleanup/commit/import.

New `frontend/tests/unit/campaign-utenze-preview-r23.test.tsx` contains55 genuine
mounted cases, written using apply_patch without disable directives/comments.
SHA-256 `1fbcb0d529097bd4775daf09b661306dfd959d4bf57dd869dd11d2247c6d99b5`.
Same exact first-attempt bytes are privately retained as
`new-spec-attempt1.test.tsx`. All55 cases plus original21 and NAS45 passed twice:
121/121 across3 spec files, no failures/pending/todo/skipped tests. Planning45–60
was not treated as a quota or coverage acceptance threshold.

### Proven public behavior and boundary assertions

The actual exported page, real Utenze session gate, real document-preview helper,
real Next Image and real latest-visura card run. Only API/auth/navigation/browser
URL and Mammoth/XLSX conversion boundaries plus unrelated layout/domain children
are mocked. Real Node Blob from repository setup is used; selected read methods
are spied for literal buffers and failure/deferred interleavings. There is no
copied dispatcher, compiled handler invocation, source-string check, fake coverage,
runtime mutation or DTO property deletion to reach impossible defaults.

- Utenze row/nested Preview/Enter/Space each invoke exactly one token/id download;
  nested propagation does not duplicate it. Nonactivation key does not download.
  Read-only permits preview. Public id:null Preview produces the exact guard
  error with no URL/download/modal. Catasto row/nested/Enter/Space and actual
  Visualizza visura call Catasto token/id only, without requesting a new visura.
- Deferred real Blob shows filename/loading/Chiudi but no URL/Scarica until
  resolution; URLcreate receives that exact Blob. PDF extension/boolean precedence,
  casing/null fallback, valid metadata mismatch, actual image presentation,
  unsupported/empty-extension/no-extension download fallback and MIME independence
  are asserted through iframe/img/link/title/download attributes.
- DOCX asserts exact ArrayBuffer input to convertToHtml and literal safe HTML
  structure versus empty conversion message. XLS and XLSX assert literal
  read(buffer,{type:array}), sheet_to_json worksheet/options call order, first3
  sheets, first25 rows, omitted fourth/26th sentinels, empty workbook/sheet text,
  and independent literal cell outputs keep/0/false/—/—. No expected mapping
  algorithm is copied into tests. TXT/CSV/EML use real Blob.text and assert exact
  pre content/markup escaping, empty and whitespace semantics, no conversion.
- Error/non-Error download, ArrayBuffer, Mammoth and URLcreate failures, XLSX
  read/row-conversion and text read failures assert actual error/fallback, loading
  release, URL presence/absence, no inline renderer and no download retry.
  Created URLs remain downloadable through adapter failure and close revokes
  them twice. A new public open after URL failure clears old error.
- Loaded Chiudi/Escape demonstrate double revoke, clean reopen and single cleanup
  of the reopened URL on unmount. Loaded unmount alone revokes once. Closing
  before Blob resolution then resolving/rejecting keeps modal closed; late URL
  is revoked on unmount. Closing during DOCX conversion revokes twice and late
  HTML does not reopen the modal. Non-Escape/backdrop clicks leave it open.
- Focus-based replacement is PUBLICLY PROVEN: the actual row is focused before
  first Enter; document.activeElement remains that row after loaded modal, before
  and after second Enter. No pointer target is clicked through the overlay.
  The replacement download invocation precedes the explicit old revoke; cleanup
  duplicates revoke, then new URL is created. Exact API calls stay token/doc-A.
- Window keydown registration/removal identities are asserted at initial open,
  URL update, close and unmount. The old callback is removed before the new
  installed callback is later removed; no lingering extra registration occurs.
- Late old Blob replaces newer URL while newer filename/title/download filename
  stays selected. Late old DOCX conversion overwrites newer PDF kind/content
  while preserving the newer URL/filename. Old rejection clears newer loading
  and remains as error even after newer Blob succeeds. Assertions preserve those
  races rather than impose latest-wins or cancellation.

Adapter mocks test actual caller contract/orchestration, not binary DOCX/XLSX
parser correctness. Boundary fixture empty explicit extension is labeled in the
test; normal metadata remains complete and valid. Literal fixture expected
outputs are independently stated. No manual-upload/NAS/domain action is triggered.

### Actual native URL/listener traces

Eleven scenario traces were emitted by the first native run and frozen to
`native-traces-attempt1.json` BEFORE any promotion to a complete scheduling golden.
Tests assert literal arguments, URL call order/counts, synchronous download-before-
revoke and callback identities; they do not guess an entire passive-effect trace.
`native-traces-coverage-attempt1.json` separately records the required coverage
run. Their URL event sequences and native mock boundary-order tuples match
exactly across both executions; absolute invocation numbers differ naturally.
Per-scenario native invocationCallOrder includes download calls even when the
deferred API mock does not append a textual event. This distinguishes instrumented
boundary order from a subset of textual URL events, without fabricating calls.

| Native observation | Actual ordered boundary/URL evidence |
| --- | --- |
| Loaded Chiudi or Escape, reopen, unmount |downloadA/create1/revoke1/revoke1/downloadA/create2/revoke2|
| Loaded unmount |downloadA/create1/revoke1|
| Close pending Blob, late resolve, unmount |downloadA/create1/revoke1; no reopen|
| Close pending Blob, late reject |downloadA; no create/revoke/reopen|
| Close during DOCX conversion |downloadA/create1/Mammoth/revoke1/revoke1; no late URL recreation|
| Focused public replacement |downloadA/create1/downloadA/revoke1/revoke1/create2/revoke2|
| Late first Blob after second |downloadA/downloadB/createB/createA/revokeB/revokeA-on-unmount|
| Old conversion after new PDF |downloadA/createA/Mammoth/revokeA/revokeA/downloadB/createB/revokeB-on-unmount|
| Old error while new loading |downloadA/downloadB/createB/revokeB-on-unmount; stale error still visible|

Listener trace separately records native add/remove invocation orders; passing
identity assertions bind removals to the exact registered callbacks. No API or
component implementation was replaced to collect those observations.

### Native gates, commands and exits — no correction/retry

Preflight disk5700MiB; before first native run5392MiB; after coverage5386MiB;
after types5379MiB. tmpfs274MiB. Existing dependencies, one worker, serial gates,
JSON/default test reporters and text/JSON-only coverage; no HTML output.

| Gate | Exact private evidence stem | Native outcome |
| --- | --- | --- |
| New55 + immutable66 union |`new-union-attempt1`|3 files121/121PASS, exit0,8.89s|
| Same union + exact entire original page coverage |`new-coverage-attempt1`|121/121PASS; exit1 ONLY four unchanged100 thresholds;13.53s|
| Real project TypeScript |`project-types-attempt1`|npm run typecheck -- --incremental false;exit0|
| Explicit new-spec imported TypeScript program |`new-spec-types-attempt1`|95 actual runtime sources,0 diagnostics;exit0|
| Scoped new-spec lint |`new-spec-lint-attempt1`|eslint tests/unit/campaign-utenze-preview-r23.test.tsx --max-warnings=0;exit0|

Each stem retains exact argv/cwd/env, native log and exit JSON. Both Vitest runs
use maxWorkers1/no-file-parallelism/bail1, default+JSON test reporters, with actual
test JSON in `*-results.json`. The first unexpected failure stop rule was not
triggered; no code corrections or native retries followed the first execution.
Real new-spec TypeScript resolved coordinator's heterogeneous-tuple warning
with0 diagnostics; no speculative tuple correction or project-excluded test gate
was substituted. The new-spec program uses project options, next-env, actual new
spec and jest-dom Vitest types, no emit/incremental false, including real page
imports. Existing tests remain outside that separate new-spec program and are
protected byte-for-byte; project typecheck alone is not claimed as spec proof.

Installed tinyglobby/picomatch validated escaped `[id]` include before coverage.
Raw JSON has exactly one absolute full-file key:
`/home/cbo/CursorProjects/GAIA-campaign-20261010-r21-capacitas-job-actions/frontend/src/app/utenze/[id]/page.tsx`.
Internal path matches, positive full-file counters, all denominator maps unchanged,
zero skipped-map flags and no exclusions/config changes. Native result JSON marks
assertions passed; overall native command1 remains coverage FAIL100.

| Dimension | Original published R22 | R23 original runtime + new tests | Gain | Still missing | Required |
| --- | ---: | ---: | ---: | ---: | ---: |
| Statements |253/57643.92%|370/57664.23%|117|206|100%|
| Branch arms |273/61044.75%|408/61066.88%|135|202|100%|
| Functions |49/17627.84%|80/17645.45%|31|96|100%|
| Lines |251/53646.82%|364/53667.91%|113|172|100%|

Line counts use max statement hit per statement-start line and match native text;
296 branch-map entries contain610 arms. Incidental document/list/visura presentation
coverage from real typed fixtures is visible in the whole-file total; it is not
claimed as a separate responsibility characterized or a runtime improvement.

| Native preview region | Statements | Arms | Actual function hits |
| --- | ---: | ---: | --- |
| Close747–759 |11/11|2/2|19|
| Open761–866 |50/50|26/30|open61;sheet8/row52/cell60|
| Document868–874 |4/4|2/2|57|
| Catasto876–887 |1/1|0/0|5|
| URL cleanup896–902 |4/4|2/2|effect/cleanup186|
| Escape904–926 |11/13|7/10|effect254/key4/remove115|
| Modal1394–1493 |3/3|51/51|sheet7/row52/cell60|
| Document controls1853–1936 |7/12|14/20|includes adjacent out-of-scope select/classification|
| Catasto controls2000–2038 |7/7|5/8|includes nonactivation key and metadata fallback gaps|

### Residual gap remains genuine — no runtime waiver

Four open-preview arms remain at775(is_pdf nullish snapshot fallback),776(doc_type
default),777(classification_source default),809(is_pdf??null): both public typed
Utenze/Catasto flows supply those fields. They were not forced through deleted
DTO properties or extracted-handler probes. Source remains unchanged; no valid
public reachability proof is claimed for these defaults.

Escape misses statements919–920 and3 arms at914/919 belonging to manual-upload
listener/branch cases outside preview scope. Catasto control residuals are one
nonactivation key arm2008 plus subalterno/CF fallback presentation2020/2023;
all required Catasto activation routes are tested. Document control residuals
include adjacent select/classification and presentation paths outside commands.
No universal regional100 claim is made.

Exact whole-file residual is206 statements/202 arms/96 functions/172 lines,
including99 missing-line ranges. Private `new-coverage-gaps-attempt1.json` retains
every missing function span/arm location/count and before/after region matrix;
SHA-256 `95ed4e97492fd2bc19a5eedee9eb73501d431cbf7588d826a6fffae610eac3f6`.
Remaining source responsibilities include ANPR/visura403–492, personal-save
branches518/547–548, classification574–593, manual upload/deletion659–711,
manual queue/drop/files716–744, manual-upload modal1070/1210–1386,
personal fields1515–1739, select/classification/deletion1884–1949,
list expansion1981, audit/metadata2112–2145 and remaining helper/display branches.

Recommended NEXT characterization allocation (not started): one original manual
document-upload/queue responsibility, based on native659–683/716–744 and
1210–1386 gaps, keeping deletion/classification/ANPR/visura separate. It requires
its own ownership, public invariant/missing-case analysis and serial admission.
Do not expand this R23 slice or weaken full-file100 to close unrelated debt.

### Final freeze, classification and stop

Original page/helper, both old campaign specs, all13 existing Utenze/format specs,
config/package/baseline retain initial hashes and equal immutable35d HEAD. Earlier
analysis/evidence/custody bytes and native first attempts are preserved. Final
manifest/custody freezes actual commands, outcomes, source/spec/report/raw/gap/
trace hashes. Working tree has ONLY new preview spec and own report untracked;
tracked diff empty. No runtime acceptance/publication, source import or commit.

Classification CHARACTERIZED_ONLY / NO_CHANGE complexity. DetailContent391/304/
1908 and file729cognitive/723cyclomatic/2118LOC unchanged; no IMPROVED credit.
Runtime BLOCKED_COVERAGE until genuine whole-file100. Global original goal
ACTIVE/INCOMPLETE; strategic-tail reduction and final application suites unmet.

STOP: admitted native phase complete, HEAVY RELEASED. Root must allocate distinct
fresh independent review and any later ratchet/integration/governance/Graphify
publication gates. No unallocated heavy or next responsibility started.

## Separately admitted actual Make ratchet — native0, post-processing STOP

Coordinator allocated ONLY actual Make complexity-ratchet, new evidence, own
report amendment and custody. Same35d author branch; source/spec/config/baseline
unchanged. Previous CHARcf878df3... was preserved BEFORE amendment in
`implementation-report-pre-ratchet-frozen.md`. Preflight disk5491MiB/tmpfs274MiB;
exclusive author heavy, root/reviewer/R24 no competing native gate.

Executed exactly once from the dedicated repository tree:

```sh
make complexity-ratchet BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2 QUALITY_PYTHON=backend/.venv/bin/python
```

Actual native Make exit0, retained in `make-native55a-attempt1-exit.json`.
`make-native55a-attempt1-command.json` freezes argv/cwd/allocation;
`make-native55a-attempt1.log` retains the complete native stdout. Make echoes
`backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref ${BASE_REF:-origin/main}`
then a standalone JSON body whose visible base_ref and baseline_commit both are
`55a1b1d35911451e018b662c2acc450bf5994ea2` and whose final literal is
`"findings": []`. This was the actual requested Make target, not a replacement
direct scanner invocation, synthetic report or baseline update.

Post-processing then failed: my extraction code used text.find("{") and selected
the brace inside the Make echo's `${BASE_REF:-origin/main}`. json.raw_decode
therefore raised JSONDecodeError before it reached the actual standalone JSON.
The error is an author post-processing bug, not a native ratchet failure. Exact
algorithm/error/cause were preserved in
`make-native55a-postprocess-attempt1-failure.json`; no parsed result artifact was
created and full structured-body verification remains pending. Native exit0 and
visible exact findings[]/base fields are reported separately from that uncompleted
verification, without claiming the failed extractor passed.

Following this allocation's explicit instruction “STOP on unexpected fail, no
retry”, no extractor correction/retry or native gate rerun was performed. Only
bounded head/tail reading diagnosed the Make echo issue. Root must decide a
bounded post-processing-only extraction from the standalone JSON line; the native
gate does not need rerunning for this error. This STOP is not a runtime waiver,
application failure or permission to alter tests/source/config/baseline.

Final ratchet custody/manifest preserve every previous attempt and frozen prefix,
the exact55 new spec,18 protected paths and tracked-diff-empty/only2 owned
untracked state. No global report/build/Graphify/cleanup/commit/import.
Classification remains CHARACTERIZED_ONLY/NO_CHANGE; full coverage still FAIL100,
runtime BLOCKED_COVERAGE/global ACTIVE/INCOMPLETE. HEAVY RELEASED. Distinct review
remains required after root settles the post-processing verification.
