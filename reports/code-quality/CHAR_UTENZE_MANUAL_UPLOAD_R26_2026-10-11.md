# R26 Utenze manual upload — analysis and admission proposal

## Initial ownership and analysis stop condition

Coordinator registered ownership before agent activation. Author worktree:
`/home/cbo/CursorProjects/GAIA-campaign-20261010-r21-capacitas-job-actions`, branch
`characterize/complexity-r26-utenze-manual-upload`. ANALYZE ONLY currently owns
this new report and small private evidence under
`~/.cache/gaia-campaign/20261011-r26-utenze-upload/`.

Runtime `frontend/src/app/utenze/[id]/page.tsx` and all existing tests remain
READ-ONLY. Proposed new
`frontend/tests/unit/campaign-utenze-manual-upload-r26.test.tsx` is NOT admitted
or created. Stop for Coordinator approval before tests, native gates, runtime,
Graphify or publication. No commit, installation or cleanup performed.

One responsibility: real mounted manual document selection, per-item metadata,
sequential upload and modal lifecycle. Excludes deletion, classification,
subject forms, NAS candidate/import commands and runtime extraction. This
characterization is a prerequisite toward the highest remaining hotspot, not
a complexity improvement or a replacement for original full-file coverage.

## Preflight and immutable custody

Read checkpoint skill, authoritative global-goal attachment, root AGENTS,
project complexity skill and quality workflow/constraints. Repository preflight:

- `git status --short`: empty.
- `git rev-parse HEAD`: `de76117a6ad9405fd013c3c7114d18625c2b8620`.
- `git merge-base HEAD main`: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Owned runtime `git diff`/status: empty; recent source log starts `737fffca`,
  `069eea98`, `254d908a`, `e8a43f08`; no campaign runtime modification proposed.
- Main binary diff SHA256:
  `9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`.
- Main short-status SHA256:
  `0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`.
- Baseline SHA256:
  `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
- Runtime SHA256:
  `b0f822daf809b0744b912f0f159a2e833c556dda289466b6ed45329a79e3d6b1`.
- Original detail spec SHA256:
  `79ef301017ee78985d71b468300eba3239e901c9773eb56f60a033cd6ad13f98`.
- Immutable NAS R22 spec SHA256:
  `8f2258e4cb65b2242ac65fc39a1407fad9a6a48457060387ef7392e39c0ed6d9`.
- Immutable preview R23 spec SHA256:
  `1fbcb0d529097bd4775daf09b661306dfd959d4bf57dd869dd11d2247c6d99b5`.
- Vitest config SHA256:
  `01e2dab469c1a961df5d2aa70efcb79e2e6a732be47808f5640a80d77ad61c68`.

Main concurrent work preserved. No baseline, scope, threshold, ignore or config
change. Last storage observation: root approximately 3.5 GiB available, separate
`/dev/shm` approximately 274 MiB; no destructive action or heavy run.

## Baseline and target callable

Read existing authoritative native JSON only:
`~/.cache/gaia-campaign/20261011-r24-integrated/complexity.json`.
Schema uses `files[path]` and flat `callables` entries keyed by `path`/`name`.
No scanner run and no October 7 baseline used.

| Callable | Lines | Cognitive | Cyclomatic | LOC | Nesting | Params |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| DetailContent | 214–2206 | 391 | 304 | 1908 | 2 | 1 |
| handleManualUpload | 658–685 | 8 | 7 | 27 | 1 | 0 |
| handleManualFilesSelection | 715–728 | 3 | 3 | 12 | 1 | 1 |
| handleManualDrop | 730–735 | 1 | 2 | 6 | 0 | 1 |
| handleManualItemChange | 737–741 | 1 | 2 | 5 | 0 | 2 |
| handleManualItemRemove | 743–745 | 0 | 1 | 3 | 0 | 1 |

Whole file: 176 callables, cognitive sum729/max391, cyclomatic sum723/max304,
effective LOC2118, official28useState/10useEffect. Three file error findings
remain. Nested callable sums are overlapping measures, not independent physical
decisions. Before/after metrics unchanged for this analysis.

Historical root R23 union: original21 + NAS45 + preview55 =121PASS. Full original
page remains 370/576 statements,408/610 branch arms,80/176 functions,364/536
lines; original full-file100 FAIL. This is historical evidence, not a fresh
R26 gate. Runtime remains BLOCKED_COVERAGE. No regional100 claim can authorize
runtime changes.

## Source-backed behavioral invariants

1. Public entry points are edit-only `Inserisci file` in Scheda (L1759) and
   header fallback `Nessun dato rilevato nel NAS, importa manualmente` when NAS
   import is unavailable (L1069). Read-only exposes neither. Module/session
   authorization lives in the real `UtenzeModulePage` wrapper.
2. Selection L715–728 accepts FileList/null; null/empty does nothing. Each
   occurrence produces a new UUID-backed item with docType `altro`, notes `""`;
   functional append preserves previous list and selection order. There is
   **NO deduplication**, extension/MIME/size filtering or name normalization.
   Selecting/dropping the same File again retains separate editable items.
3. Native hidden input has `multiple`, no `accept`, and resets its value to
   `""` after change (L1263–1272). Drop prevents default/stops propagation,
   clears drag highlight and feeds files/null. Drag enter/over set highlight;
   leave clears it. Click/Enter/space activate native input; other keys do not.
4. Per-row category and notes update by item ID; removal affects only that ID
   and remaining visual indices renumber. Display size is actual bytes divided
   by1024², toFixed(2). Notes are not trimmed.
5. Empty submit sets literal validation error, without busy/API/reload/status
   or clearing an existing success. Nonempty submit sets busy and clears both
   save messages, then awaits each upload in captured list order with exact
   `(token,subjectId,file,docType,notes || undefined)` arguments.
6. Success awaits reloadSubject then explicit loadNasImportStatus, resets list,
   closes modal and reports captured singular/plural count; upload API return
   payload is ignored. Reload hydration also schedules the subject-driven NAS
   effect (L887), so two status requests may overlap when new subject identity
   arrives. Same object reload does not trigger another subject effect.
7. First rejected upload stops later items; previous successes persist without
   rollback/reload/status. Current list/modal remain; retry submits all retained
   items, including prior successful items. Reload failure likewise retains
   list/modal after successful uploads. Error and opaque rejection have exact
   error/fallback strings. Finally always clears upload busy.
8. loadNasImportStatus catches its own errors into NAS fallback status; status
   rejection does not reject successful upload orchestration. Explicit status
   completion governs upload completion, while a later effect status can still
   overwrite visible NAS information.
9. Busy disables native remove/category/notes/cancel/submit. Drop target only
   receives CSS `pointer-events-none opacity-60`; tabIndex and keyboard handler
   remain, hidden input itself is not disabled. Do not fake a pointer event
   through CSS/overlay: any busy selection test must use a real focused public
   keyboard control/native file input path, preserving captured-list behavior.
10. Cancel clears list/closes; closing also clears list by effect L377–381.
    Backdrop/non-Escape key do not close. Escape listener removes/reinstalls by
    actual effect dependencies, closes manual modal even while upload pending,
    and gives existing preview precedence. Unmount removes the listener.
11. Escape during upload does not abort requests. Original closure retains list,
    token and subject ID; late completion can close/reset a reopened modal/list.
    No generation guard, abort, dedup or partial-retry improvement is permitted.
12. Manual upload has **no polling loop**. Tests must observe actual effects and
    deferred API requests, not invent polling timers. Unrelated shell heartbeat
    is not upload behavior and must not be mistaken for status refresh.

## Initial proposed real mounted characterization matrix

Every row is currently missing in existing manual-upload tests. Existing121
remain immutable; NAS/preview shared behaviors are covered independently but do
not establish manual-upload arguments or transitions. `Added` and `Result`
remain NOT ADMITTED/NOT RUN. Counts below are proposed, not executed tests.

| Behavior / public scenario | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Read-only lacks both manual entry points; enable-edit exposes them | Original edit/NAS visibility only | Manual access assertion | Not admitted | Not run |
| NAS unavailable header and Inserisci file open same empty modal | NAS visibility only | Open/lifecycle | Not admitted | Not run |
| NAS eligible header absent but Inserisci file opens | NAS visibility only | Manual fallback-independent access | Not admitted | Not run |
| Linked/unlinked NAS explanatory text and existing document panel | Preview fixtures only | Manual modal branch | Not admitted | Not run |
| Empty submit literal validation, enabled controls, zero boundaries | None | Full transition | Not admitted | Not run |
| Native multiple input appends File objects in given order/default metadata | None | Full transition | Not admitted | Not run |
| Reselect same File after input reset retains two independently editable rows | None | No-dedup invariant | Not admitted | Not run |
| Repeated selection/drop same name/lastModified retain independent items | None | UUID ownership externally observable | Not admitted | Not run |
| Native empty/canceled file selection leaves existing list | None | Null/empty guards reachable via input | Not admitted | Not run |
| Enter/space activate chooser; unrelated key does not | None | Public keyboard | Not admitted | Not run |
| Real drop appends; drag enter/over/leave/drop highlight and propagation | None | Public drop semantics | Not admitted | Not run |
| Drop with no files leaves list and clears highlight | None | Empty native transfer | Not admitted | Not run |
| Change category/notes only selected row, preserving other defaults | None | Per-ID update | Not admitted | Not run |
| Remove middle/last row and visual renumber; no premature upload | None | Per-ID remove | Not admitted | Not run |
| Real empty/binary/arbitrary-extension file accepted and correct size shown | None | No client filtering | Not admitted | Not run |
| One upload exact token/id/File/category, empty notes→undefined, singular success | None | Command mapping | Not admitted | Not run |
| Nonempty/whitespace notes preserved verbatim, all category options available | None | Command mapping | Not admitted | Not run |
| Multiple deferred uploads strictly sequential, immutable File identity/order | None | Await ordering | Not admitted | Not run |
| Busy native controls disabled, preventing duplicate submit/removal/edit | None | Actual control state | Not admitted | Not run |
| Real focused keyboard input while busy, if browser path reachable | None | Captured list excludes newly appended items | Not admitted | Not run |
| Uploads→reload→explicit/effect status, reverse completion observable | NAS analogous only | Manual command ordering | Not admitted | Not run |
| Same-object reload triggers explicit status only | NAS analogous only | Manual orchestration | Not admitted | Not run |
| Success closes/reset; reopen empty; singular/plural messages exact | None | Completion state | Not admitted | Not run |
| Error/opaque first-upload rejection retains list and busy clears | None | Failure split | Not admitted | Not run |
| Error/opaque second rejection stops third; retry reuploads first | None | Partial failure semantics | Not admitted | Not run |
| Error/opaque reload rejection retains list after successful upload | None | Failure boundary | Not admitted | Not run |
| Explicit/effect status errors absorbed while upload success remains | NAS analogous only | Manual-specific success | Not admitted | Not run |
| Valid retry clears previous error immediately; empty validation keeps success | None | Shared message semantics | Not admitted | Not run |
| Cancel/Escape reset list, backdrop/non-Escape keep it, reopen fresh | Preview analogous only | Manual modal lifecycle | Not admitted | Not run |
| Escape during pending upload then reopen/add; late success clears new list | None | Race preserved | Not admitted | Not run |
| Escape during pending upload then late failure does not reopen modal | None | Race failure | Not admitted | Not run |
| Same mounted route change while pending preserves captured upload id | NAS analogous only | Upload captured closure | Not admitted | Not run |
| Listener added/removed with same identity on close/unmount | Preview analogous only | Manual-specific cleanup | Not admitted | Not run |

## Proposed harness and native gate admission

Mount the actual default `UtenzeSubjectDetailPage`; real manual JSX, state,
handlers, child components and UUID generator remain unmocked. Only actual
external API/auth boundaries and Next navigation context are candidates for
mocking. Typed complete DTOs, real File objects, native input/drop events and
deferred API promises; no compiled handler extraction, direct DetailContent
access, fake callback/state probes, impossible DTO casts or coverage counters.

Primary route uses supported production `?embedded=1` to avoid unrelated shell
heartbeat/search while retaining real session/module wrapper and domain page.
Person fixture retains real ANPR child (complete API fixture at that boundary);
company fixture verifies modal subject-independent behavior. Existing tests
keep their original harness unchanged. Nonembedded case can retain real shell
if Coordinator admits complete auth/API/navigation fixture requirements.

Use DOM-scoped selectors: modal title ancestor, actual labelled category/notes,
row ancestor of filename and public drop target aria-label. Native input scoped
to modal `input[type=file]`; no application component mocks to manufacture
branches. Listener spies observe real browser methods and restore afterwards.
No hidden-row pointer activation through modal overlay.

After explicit admission, serial focused new-spec tests then immutable121 union,
fresh exact-page V8 coverage with unchanged100 four-dimensional thresholds,
project/new-spec types and scoped lint. Reuse native command pattern from
`~/.cache/gaia-campaign/20261011-r23-integrated/verify.py`, adapting only worktree,
new spec and evidence output. Escape literal `src/app/utenze/\[id\]/page.tsx`
for coverage include. Full100 still expected to FAIL; record actual numerator,
denominator, skipped counts and failure cause without suppressing gate. First
unexpected failure freezes source/output and stops, no retries or unrelated fix.

Coordinator alone owns native heavy token, scanner/ratchet/Graphify/integration
decisions. This proposal runs none. Graphify code refresh not necessary while
runtime boundaries remain unchanged; documentation graph is Coordinator-owned.

## Classification, residual risks and next decision

Current classification ANALYZE_ONLY / NO_CHANGE; no runtime or test change,
no improvement credit. Original whole-file coverage remains BLOCKED_COVERAGE;
fresh native checks not run. Global historicalFAIL30 and frozen R25FAIL14 are
distinct and not touched here. No aggregate reduction claimed.

Risks: source-backed legacy partial retry repeats successful documents, Escape
does not cancel, pending success can discard reopened selection, busy pointer
CSS does not prove disabled keyboard input, NAS statuses race without generation
guards. These must be characterized, never silently repaired in this campaign.

Requested next decision: admit the NEW manual-upload mounted spec only, plus
bounded original characterization gates under the serial native token. Runtime
stays immutable until full original100 and separate runtime slice admission.

## Subsequent Coordinator admission — draft tests only

Coordinator registry recorded admission BEFORE author reactivation. The author
now owns ONLY the new manual-upload spec, this report and private evidence.
Runtime, all three existing specs, dependencies, baseline and config remain
immutable. Native tests/types/lint/report/ratchet/Graphify/build/commit/cleanup
are still NOT admitted to the author. Root holds/releases the native token;
that does not authorize the author to run any gate.

The initial matrix above preserves the original proposal. Its 33 rows are now
implemented as a **DRAFT, NOT RUN** spec: 28 plain definitions plus 10
parameterized definitions expanding to21 cases, expected **49 new cases**.
Immutable union expected **170 cases across4 specs** (21+45+55+49). No PASS
claim is made for this draft; no runtime change or IMPROVED credit.

Frozen draft spec SHA256:
`329bc2674013b6e7901b26134bf495eafa90857dbb5d7db24b81056ec7f8585b`.
Original page remains
`b0f822daf809b0744b912f0f159a2e833c556dda289466b6ed45329a79e3d6b1`.
Latest status contains exactly these two NEW untracked files: spec and report.
All original spec/config/baseline hashes above rechecked exact after writing.

Harness mounts actual default page, wrapper, all internal domain components and
UUID helper. Mocks only API/auth/Next navigation boundaries. Production embedded
route is used. Default complete company DTO makes same-object/status-order
tests independent of unrelated ANPR hydration; a separate complete person case
retains the real ANPR child and its typed API status. No application component,
React state/effect, UUID or uploaded File is mocked. Assertions additionally
verify strict File reference identity, not just equivalent filenames.

DOM boundary simulation uses real File objects with conventional Testing Library
native change/drop dispatch (`target.files` array/null and transfer files array).
No runtime DTO cast, compiled handler or invented state is introduced. Busy
selection uses real focused drop-target keyboard activation of the native
non-disabled input, never synthetic pointer-through-overlay. Drag propagation
observation is on window, outside the React root, so it observes actual native
stopPropagation rather than an earlier native ancestor callback.

A read-only static correction attempt had a failed apply_patch precondition for
an already-correct NAS path literal. Targeted inspection proved the desired
`/refreshed/path` was already present; no file change or native test failure
occurred. The diagnostic is retained in the private checkpoint, not hidden as
a successful command.

## Fresh original evidence supplied by Coordinator

Root independently executed original union before admission: **121PASS/3 specs,
zero skips/todos**, coverage native exit1 solely four unchanged100 thresholds.
Exact coverage remains370/576statements408/610arms80/176functions364/536lines.
Raw characterization auditor exit0, original input SHA/custody all1673 runtime
and protected main exact. Evidence:
`~/.cache/gaia-campaign/20261011-r26-utenze-original/`.

These are Coordinator-provided original results, NOT author-executed new-spec
results. Runtime remains BLOCKED_COVERAGE; test draft does not waive full100.

## Exact proposed commands — NOT executed

CWD for all commands below:
`/home/cbo/CursorProjects/GAIA-campaign-20261010-r21-capacitas-job-actions/frontend`.
Coordinator must first explicitly assign serial native execution and prepare
the private output directory; no command below has run in this author phase.

Focused, expected49PASS/1 spec/no skips:

```bash
./node_modules/.bin/vitest run \
  tests/unit/campaign-utenze-manual-upload-r26.test.tsx \
  --maxWorkers=1 --no-file-parallelism --reporter=default --reporter=json \
  --outputFile.json=/home/cbo/.cache/gaia-campaign/20261011-r26-utenze-upload/focused.json
```

Immutable union, expected170PASS/4 specs/no skips:

```bash
./node_modules/.bin/vitest run \
  tests/unit/campaign-utenze-detail-page.test.tsx \
  tests/unit/campaign-utenze-nas-r22.test.tsx \
  tests/unit/campaign-utenze-preview-r23.test.tsx \
  tests/unit/campaign-utenze-manual-upload-r26.test.tsx \
  --maxWorkers=1 --no-file-parallelism --reporter=default --reporter=json \
  --outputFile.json=/home/cbo/.cache/gaia-campaign/20261011-r26-utenze-upload/union.json
```

Exact original full-file coverage, unchanged100 thresholds; expected tests170
PASS, coverage100 likely still FAIL/native1 (must inspect actual failure):

```bash
VITEST_COVERAGE_INCLUDE='src/app/utenze/\[id\]/page.tsx' \
./node_modules/.bin/vitest run \
  tests/unit/campaign-utenze-detail-page.test.tsx \
  tests/unit/campaign-utenze-nas-r22.test.tsx \
  tests/unit/campaign-utenze-preview-r23.test.tsx \
  tests/unit/campaign-utenze-manual-upload-r26.test.tsx \
  --maxWorkers=1 --no-file-parallelism --reporter=default --reporter=json \
  --coverage --coverage.reporter=text --coverage.reporter=json \
  --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261011-r26-utenze-upload/coverage \
  --outputFile.json=/home/cbo/.cache/gaia-campaign/20261011-r26-utenze-upload/coverage-tests.json
```

Project types and new-spec lint, subject to separate admission:

```bash
npm run typecheck -- --incremental false
./node_modules/.bin/eslint tests/unit/campaign-utenze-manual-upload-r26.test.tsx --max-warnings=0
```

New-spec imported-source type harness should use the existing native
Coordinator pattern, not claim project typecheck includes tests automatically.
First unexpected gate failure: freeze logs/exits/source, STOP for Coordinator;
no silent retry, runtime fix, threshold modification or integration.

## Current stop

DRAFT_TESTS_READY_FOR_REVIEW, native NOT RUN, runtime BLOCKED_COVERAGE.
No publication/commit, no metric reduction, no global completion claim.
Await root static review and explicit bounded native admission.

## Coordinator static correction before first native run

Coordinator explicitly removed ONLY three unsupported `ByRoleOptions`
`exact: true` properties. String role-name matching is exact by default; same
selectors, assertions, cases and application behavior remain. The original
draft329bc267 remains historical evidence above, not the current input.

Current frozen spec SHA256:
`24878b60ce520369b94fc456c6ef28626a8bcc8511dc62085511cd825bd1e720`.
Author independently rechecked all page/three immutable-spec/config/baseline
hashes unchanged. Only new spec and report appear in author short status.

Independent static count: 28 plain tests plus10 parameterized definitions:
entry2, NAS path2, canceled selection2, chooser3, notes2, first-upload error2,
partial error2, reload error2, status error2, close2 =21 expanded cases; total49,
immutable union170/4 specs. No `.skip`, `.todo`, focused `.only` or fake coverage
fixture introduced.

Static async audit confirms:

- Company default avoids real ANPR `onStatusUpdated` hydration confounding
  subject-identity assertions. Separate person case mounts real ANPR and mocks
  only its external status/current-user boundary.
- Deferred first/second upload queues freeze File references/order until each
  real await resolves; subject/status call counts are captured after ready.
- Explicit status call follows reload continuation before committed subject
  effect; resolving explicit first releases upload while late effect remains
  capable of overwriting NAS display. No generation guard is assumed.
- Same-object reload retains reference identity, hence no additional subject
  effect. Real successful reload does reset edit mode, so `openManual` invokes
  public enable-edit confirmation again rather than assuming persisted edit.
- Route rerender changes params, not session-wrapper mount: token remains old;
  second upload/reload closes over old ID and File list. Storage token change
  tests captured token without remounting auth or fabricating a token prop.
- Escape clears current list but pending loop still holds the captured array;
  reopened busy keyboard selection can be cleared by late success. No direct
  runtime-handler or suppressed race introduced.
- Real key listener is observed after ready, with callback-reference identity
  on close/unmount. Module embedded route avoids unrelated shell listeners.

Root reported a separate Presenze partial-source type harness diagnostic:
18 GeoJSON namespace errors plus2 unsupported `exact: true` options. Root
corrected its verifier to include the COMPLETE parsed project roots, new spec
and Jest DOM typings; no ignored diagnostics or runtime/tooling policy change.
That separate harness failure is NOT evidence of an Utenze native test failure.
Any eventual Utenze new-spec type verification must use complete project roots,
not a reduced imported-source closure that omits ambient namespace declarations.

Native authority remains with separate Presenze reviewer; this author ran NO
native gate, made NO additional spec edit and remains stopped for Coordinator
focused-test admission. Current49 are still DRAFT/NOT RUN, runtime100 blocked.

## Subsequent Coordinator and independent native verification

The preceding draft status is historical. Root executed frozen corrected spec
24878b60:49focusedPASS,170union/4specPASS/no skip/todo, complete-project+new-spec
types0 (662project roots661runtime files0diagnostics), scoped new-spec lint0.
Raw single-page coverage437/576statements460/610branches109/176functions426/536
lines, versus fresh original121 baseline370/408/80/364 with same denominators.
Full100 native gate exits1 ONLY for unchanged four coverage thresholds; no test
failed, no baseline/config/threshold modified, runtime remains BLOCKED_COVERAGE.

Distinct reviewer in dedicated `GAIA-campaign-20261011-r26-utenze-review` tree
independently repeated49/170/coverage/types/lint/custody and actualmain55a ratchet
native0/findings[]. Explicit ACCEPT_CHARACTERIZATION_ONLY, report
`FINAL_REVIEW_UTENZE_MANUAL_UPLOAD_R26_2026-10-11.md` SHA637906a7. Source and
old three specs immutable; actual async dual-status, partial retry and captured
route traces preserved. No component/internal-handler mocks or synthetic credit.

Classification CHARACTERIZED_ONLY / NO_CHANGE complexity. Remaining139statements
150branch arms67functions110lines are not covered. Root may publish only exact
new spec and reports, never runtime or a100% waiver. Evidence directories:
`20261011-r26-utenze-characterization` and `20261011-r26-utenze-review` under
`~/.cache/gaia-campaign/`. No author native command, commit or cleanup occurred.
