# R23 independent final review — Utenze document preview

**ACCEPT_CHARACTERIZATION_ONLY** for the exact new 55-test preview spec. This is test-only acceptance: runtime remains **BLOCKED_COVERAGE**, classification **CHARACTERIZED_ONLY / NO_CHANGE complexity**, original campaign **ACTIVE/INCOMPLETE**. No runtime acceptance, full-file 100% waiver, IMPROVED designation or global completion.

## Allocation and immutable inputs

Reviewer tree `/home/cbo/CursorProjects/GAIA-campaign-20261011-r23-utenze-preview-review`, branch `review/complexity-r23-utenze-preview`, HEAD `35d4121ecd8320271aab8cbcfc4d4f55e3aae4a1`, merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`. Active R23 ownership registry and admission were read first. Reviewer held exclusive native heavy after author terminal/release; coordinator and R24 did not overlap those gates.

Only this NEW report and NEW private evidence under `/home/cbo/.cache/gaia-campaign/20261011-r23-utenze-preview-review/` were written. Application, helpers, all tests, configuration, baseline, policies and tooling were read-only. No source import, edit, commit, install, build, cleanup, dependency copy or agent creation.

| Frozen input | SHA-256 |
| --- | --- |
| Actual `frontend/src/app/utenze/[id]/page.tsx` | `b0f822daf809b0744b912f0f159a2e833c556dda289466b6ed45329a79e3d6b1` |
| Actual `frontend/src/lib/document-preview.ts` | `4600f63d6e31fc037bfc5d064d66fcc1b9ae58243fdbbcf9571f6bfb9db1a866` |
| Existing detail-page spec, 21 tests | `79ef301017ee78985d71b468300eba3239e901c9773eb56f60a033cd6ad13f98` |
| Existing NAS R22 spec, 45 tests | `8f2258e4cb65b2242ac65fc39a1407fad9a6a48457060387ef7392e39c0ed6d9` |
| NEW `campaign-utenze-preview-r23.test.tsx`, 55 tests | `1fbcb0d529097bd4775daf09b661306dfd959d4bf57dd869dd11d2247c6d99b5` |
| Author `CHARACTERIZATION_R23_UTENZE_PREVIEW_2026-10-11.md` | `e8b3d94874b5b953376110082d1aeda5c76380717fdfaf91f82309e4def16dbc` |
| Immutable merge-base/current baseline | `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95` |

## Independent test review

The complete 494-line new spec, relevant page handlers/effects/modal/public controls, real document-format helper and author evidence were reviewed. Tests mount the actual exported page with the real module/session gate, real dispatcher, real Next Image and real latest-visura card. API/auth/navigation/URL boundaries and Mammoth/XLSX conversion adapters plus unrelated layout/domain children are isolated. Real Blob objects and selected Blob-method spies bind literal buffers, text and failures. No copied dispatcher/reference mapping algorithm, synthetic handler probes, extracted compiled functions, source-string assertions, invalid DTO property deletion or fake coverage was found. Old tests are unchanged; no skips/todo or weakened assertions.

Authentication uses actual enabled-module gating with viewer and empty permission keys; existing immutable anonymous/module-denied cases remain in the union. Preview is characterized in the current read-only mode, without changing permissions or visura request policy.

Meaningful public assertions include:

- Utenze and Catasto nested Preview, row click, Enter and Space each download exactly once with literal token/document id; nonactivation Utenze key does nothing. The public null-id guard produces exact error text and no download/URL/modal. The real Visualizza visura control downloads an existing Catasto document without creating a visura request.
- Deferred Blob shows filename/loading/close while delaying URL and download link; createObjectURL receives the exact Blob. Real helper precedence/case/null filename fallback chooses PDF/image/DOCX/XLS/XLSX/text/download. Explicit empty extension and MIME independence remain boundary characterization, not changed validation behavior.
- DOCX uses the exact ArrayBuffer and literal converted HTML or empty-content message. XLS/XLSX verify exact read/sheet-to-json options and worksheet order, first three sheets and 25 rows through omitted fourth/26th sentinels, empty workbook/sheet messages, and independently literal keep/0/false/em-dash/em-dash cell output. TXT/CSV/EML use real Blob.text with literal escaped markup, empty versus whitespace content and no adapter conversion.
- Error and primitive download/ArrayBuffer/Mammoth/URL failures plus XLSX read/row and text-read failures preserve exact error/fallback, loading release, link presence/absence and suppressed body. Created URLs remain downloadable through conversion failure; a subsequent public open resets an old URL error. Binary converter correctness is outside these mocked adapter-contract tests.
- Loaded close/Escape revokes twice; loaded unmount alone revokes once; close/reopen/unmount preserves exact duplicate/cleanup counts. Closing before late Blob resolution/rejection or during DOCX conversion keeps the modal closed while retaining current late URL/cleanup behavior.
- Replacement is reached through a genuinely focused public row: activeElement is asserted before and after the loaded modal and second Enter. No pointer clicks are forced through the overlay. Exact download invocation precedes old URL revoke; passive cleanup duplicates revoke before the replacement URL is created.
- Window keydown callback identity is removed/reinstalled with URL changes and removed on close/unmount. Non-Escape and backdrop clicks preserve the modal.
- Late old Blob can replace the newer URL while the newer selected filename remains; late old DOCX content/kind can contaminate the newer PDF while its URL/filename stays; old rejection can clear newer loading and remain as error after the newer Blob succeeds. Tests preserve these races without introducing cancellation/latest-wins semantics.

### Eleven independent native traces

Fresh plain and coverage logs each emitted eleven unique scenarios. Reviewer `trace-audit.json` independently matches both new executions to both frozen author trace artifacts using ordered textual events and semantic boundary `(kind, call index)` tuples. Absolute invocation ids were not treated as semantic scheduling proof. Listener add/remove ranks were normalized separately; callback identity assertions passed in native tests. The focused replacement trace retains `publicFocusProven: true`.

| Scenario family | Observed native boundary order |
| --- | --- |
| Loaded Chiudi/Escape, reopen, unmount | downloadA → create1 → revoke1 → revoke1 → downloadA → create2 → revoke2 |
| Loaded unmount | downloadA → create1 → revoke1 |
| Close before late Blob resolve/reject | resolve: downloadA → create1 → revoke1 on unmount; reject: downloadA only |
| Close during DOCX conversion | downloadA → create1 → Mammoth → revoke1 → revoke1 |
| Focused public replacement | downloadA → create1 → downloadA → revoke1 → revoke1 → create2 → revoke2 |
| Late first Blob after second | downloadA → downloadB → createB → createA → revokeB → revokeA on unmount |
| Old conversion after new PDF | downloadA → createA → Mammoth → revokeA → revokeA → downloadB → createB → revokeB on unmount |
| Old error while newer loading | downloadA → downloadB → createB → revokeB on unmount; stale error persists |

Listener identity scenario is retained separately in raw/normalized traces. Deferred mocks sometimes omit download from textual events; boundary-order instrumentation still records the actual download. No missing event was invented.

## Fresh native gates — no retry

Each command, cwd/env, native log/exit, test JSON and raw coverage was freshly captured in reviewer private evidence. The existing author evidence was used for comparison, not substituted for execution.

| Evidence stem / gate | Native result |
| --- | --- |
| `union`: Vitest exact old detail + NAS R22 + NEW preview specs, one worker/no file parallelism, default + JSON results | exit 0; three specs **21 + 45 + 55 = 121/121 PASS**, zero failures/skips/pending/todo |
| `coverage-union`: same exact union, actual full original page, text + JSON reporters | **121/121 PASS**, native exit **1**, ONLY four unchanged 100% threshold errors |
| `project-types`: `npm run typecheck -- --incremental false` | exit 0 |
| `new-spec-types`: actual project compiler options, new spec/next-env/jest-dom roots, noEmit/incremental false | exit 0; **95 actual runtime imports, 0 diagnostics**, actual page present |
| `new-spec-lint`: eslint NEW spec only, `--max-warnings=0` | exit 0 |
| `native55a`: actual `make complexity-ratchet BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2 QUALITY_PYTHON=backend/.venv/bin/python` | exit 0; decoded **base_ref = baseline_commit = exact 55a**, **findings: []** |

No unexpected native test/type/lint/coverage/ratchet failure occurred. An initial read-only exploration command used frontend-prefixed paths from the frontend working directory and guessed a nonexistent helper filename; the diagnostic is preserved in `preflight-read-path-diagnostic.json`. Correct source locations were read before gates; no input or native gate was corrected/retried.

The author's earlier auxiliary Make JSON reader failure remains preserved and disclosed. It selected the brace in Make's echoed shell parameter, after native Make exit 0. Coordinator resolved only JSON reading from the standalone JSON line. Reviewer independently decoded that original native log and verified its full payload equals the coordinator resolution, with exact baseline/findings and no author native rerun. `author-ratchet-resolution-audit.json` binds the immutable root artifact. Reviewer's own fresh Make run and standalone-line decoding both succeeded; no failure evidence was removed or relabeled as a passing reader.

## Genuine full-file coverage — still FAIL100

Coverage include exactly `src/app/utenze/\[id\]/page.tsx`; full original runtime, no threshold overrides or exclusion changes. Raw JSON has exactly one absolute actual page key/internal path with positive nonempty full denominators. All statement/branch/function maps and covered/missing locations independently match frozen author evidence; zero synthetic skip flags. `coverage-audit.json` records every uncovered statement/function/branch and line; `coverage-region-audit.json` binds actual regional counters.

| Dimension | Published R22 | Fresh R23 | Gain | Missing | Required |
| --- | ---: | ---: | ---: | ---: | ---: |
| Statements | 253/576 (43.92%) | 370/576 (**64.23%**) | 117 | 206 | 100% |
| Branch arms | 273/610 (44.75%) | 408/610 (**66.88%**) | 135 | 202 | 100% |
| Functions | 49/176 (27.84%) | 80/176 (**45.45%**) | 31 | 96 | 100% |
| Lines | 251/536 (46.82%) | 364/536 (**67.91%**) | 113 | 172 | 100% |

| Preview region | Statements | Arms |
| --- | ---: | ---: |
| Close 747–759 | 11/11 | 2/2 |
| Open 761–866 | 50/50 | 26/30 |
| Utenze handler 868–874 | 4/4 | 2/2 |
| Catasto handler 876–887 | 1/1 | 0/0 |
| URL cleanup 896–902 | 4/4 | 2/2 |
| Escape 904–926 | 11/13 | 7/10 |
| Modal 1394–1493 | 3/3 | 51/51 |
| Document controls 1853–1936 | 7/12 | 14/20 |
| Catasto controls 2000–2038 | 7/7 | 5/8 |

Four open-preview missing arms at 775/776/777/809 are nullish `is_pdf`, `doc_type` and `classification_source` defaults not reached through the tested valid public DTOs; no impossible default was forced by deleting required fields or probing a handler. Manual-upload Escape statements 919–920 and three related arms remain outside this preview slice. Catasto nonactivation key/subalterno/CF fallbacks and adjacent document selection/classification remain disclosed. Incidental real fixture coverage of document/list/visura presentation is not a separately accepted responsibility.

Whole-page residual still includes ANPR/visura, personal-save branches, classification, upload/deletion, queue/drop/files, manual-upload modal, personal fields, select/classification/deletion controls, list expansion, audit/metadata and helper/display branches. This review does not certify every format extension/permutation, adapter internals, browser behavior or full-page equivalence. Regional body coverage and passing characterization do not replace whole-file 100%.

## Complete context, custody and unchanged metrics

Before native activation all **1,673** official frozen-report runtime paths, including worker tests, were independently present and byte-exact to integration and reviewer Git index. Reviewer has **2,645** hydrated tracked files and **945** authorized skip-worktree absences outside that complete runtime inventory. Sparse omission of unrelated assets/docs did not reduce scanner scope or alter policy/exclusions. Native Make used the actual complete runtime context.

Custody before gates, before ratchet and after gates is exactly equal. All hydrated tracked inputs, source/helper/specs/config/baseline, eighteen author protected paths, author report/private evidence, main and previous R21/R22 reports/evidence remain unchanged. Main's **3,341** tracked-file manifest and concurrent changes are preserved; binary diff SHA remains `9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`, status SHA remains `0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`. Combined frozen custody records **206** prior/input artifacts.

All 124 previous R21 evidence-manifest entries and all 36 previous R22 evidence-manifest entries were independently revalidated. R21 final report remains `83c3d8e2667f49428300ecb96475ca1dec5621ece14e3cfa94094a75646a129d`; R22 final report remains `6e55808c0a5bee605c94d95bec54f1bfbe6db9a639299541390565a74514f979`. Terminal custody allows only the imported untracked spec and this NEW report.

| Runtime unit | Before = after cognitive | Before = after cyclomatic | Before = after LOC |
| --- | ---: | ---: | ---: |
| `DetailContent` | 391 | 304 | 1908 |
| Whole page | 729 | 723 | 2118 |
| Four primary preview callables | 20 | 22 | 130 |
| `openPreviewFromBlob` | 18 | 17 | 98 |
| Real document-preview helper file | 10 | 12 | 34 |

Whole page still has 176 callables and official 28 useState/10 useEffect; supplemental raw AST 50 state calls is distinct. Open-preview cyclomatic/LOC legacy violations remain. No whole report regeneration was needed because frozen runtime scanner inputs are exact and unchanged; fresh global Make ratchet supplies authoritative nonregression proof. Global frozen inventory remains 1,673 files / 20,322 callables / 1,925 errors / 2,741 warnings / 4,666 findings, five >300 / seventeen >200 / fifty-five >100. Historical finding 30 is unchanged, not a fresh acceptance result.

Pre-ratchet available space was **5,323,370,496 bytes**. Only bounded text/JSON evidence, no HTML/build/full suite/Graphify refresh. Runtime structure, routing, services and workflow remain unchanged. Coordinator retains integration/governance and any publication Graphify obligations.

## Verdict and release

**ACCEPT_CHARACTERIZATION_ONLY** for exact spec SHA `1fbcb0d529097bd4775daf09b661306dfd959d4bf57dd869dd11d2247c6d99b5`. Full original coverage remains native **FAIL100 / BLOCKED_COVERAGE**. **CHARACTERIZED_ONLY / NO_CHANGE**, campaign **ACTIVE/INCOMPLETE**; strategic-tail reduction and final application suites remain unmet.

New report/evidence hashes and terminal custody are frozen in the reviewer private manifest. **STOP / HEAVY RELEASED**. Coordinator alone controls test-only integration/publication. No runtime refactor or additional responsibility follows from this review.
