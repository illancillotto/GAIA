# R29 author — Original Catasto Particella Wizard Characterization

## Ownership

Single responsibility: public-mounted Particella wizard candidate selection,
individual and current-page batch correction lifecycle. New files only:
`frontend/tests/unit/campaign-catasto-particella-wizard-r29.test.tsx` and this
report. Runtime, old tests, configuration, baseline and shared governance are
immutable. Coordinator registry:
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R29_CATASTO_PARTICELLA_2026-10-11.md`
in the integration checkout. No commit, merge, publication or runtime change.

Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261011-r29-catasto-particella`.
Branch: `refactor/complexity-r29-catasto-particella-characterization`.
HEAD: `f3598577ddb8d681fa30ea4ed984a2fc4209f826`.
Actual main and merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Initial working tree clean; only the two owned new files are added.

## Baseline and target callable

The original runtime source is
`frontend/src/app/catasto/anomalie/page.tsx`, SHA256
`855e3ef09296d8024f894118ef6e9c0d6bf13dc63b4f653c6ce6202407a732f7`.
The genuine existing four-spec union was executed before new tests:
196 PASS, zero failure/skip, exit0. Those four specs remain byte-exact:

| Existing input | SHA256 |
| --- | --- |
| campaign-catasto-anomalie-page.test.tsx | 7f2ae75982efaec902bc584fe6435034d426e0ac231b7fab5b7f13aa0137de23 |
| catasto-anomalie.test.ts | 99ab392a3bf6955514b41a2185b85017b9d5e4d01028bce4c0d6b7c34c6b0947 |
| campaign-catasto-cf-wizard-r17.test.tsx | e4b97fcc3460641482b01f8d6b55b804b1c7f1d374f11b6cb0f60417e98840a2 |
| campaign-catasto-comune-wizard-r18.test.tsx | 63e29633a3733258395e8760739240b1e5c0ca3ce1fa40cf4b7e79a81359273b |

R18's accepted original full-page coverage is the before coverage measurement;
its source SHA is identical. R28's accepted whole native report is the before
metrics measurement. New native whole-report validation proves exact equality
of all 1673 file objects and all 20323 callable objects, including source spans,
fingerprints, metrics and violations. No measurement is taken from October7.

## Behavioral invariants

- Public route mounts the original component. Next navigation, token and API
  boundaries are mocked using the accepted existing fixture pattern. The
  Catasto authorization wrapper is replaced with a passthrough recording its
  props; module/role propagation is checked, actual authorization is not proved.
- URL tab takes precedence over workspace fallback. Particella always requests
  status `aperta`, pageSize25; only year and raw district affect its query. Its
  pagination is independent from overview URL pagination. Empty later pages
  with positive totals return to page1 before replacing displayed candidates.
- Response order controls top candidate and batch serialization, not score.
  Radio groups are independent. Clear removes drafts; top explicitly overwrites
  current candidate choices. Reload preserves truthy drafts and off-page drafts,
  and fills absent/empty drafts from the first response candidate.
- Without-candidates filtering is local display filtering only. Batch includes
  all selected current-page rows, including hidden selected rows and truthy
  stale IDs no longer present in the candidate list. Stale IDs have no preview
  or individual button. These legacy semantics are characterized, not fixed.
- Individual/batch notes use their exact trimmed-or-default fallback. Payloads
  snapshot the selected IDs and note at action time. Success uses backend
  updated/closed counters verbatim, even for partial counts; applied_count is
  not interpreted as an all-or-nothing success condition in the UI.
- Apply clears old status/error, sets scalar applying ID, invokes mutation,
  publishes success before parallel overview/active-wizard refresh, then clears
  applying ID. Loaders catch their own failures: success can coexist with a
  refresh error. Rejected mutation does not trigger refresh and retains drafts.
- Initial/reload busy disables batch/top/clear but permits radio/note changes.
  Individual apply disables only that row and allows batch/another row. Batch
  disables individual buttons. Selection controls remain usable during apply.
  A single then batch overlap shares one scalar busy ID; earlier completion
  releases it while the second mutation is pending. No mutex is added.
- Context responses are applied in completion order: an older response can
  overwrite a newer response, and a completed request can clear busy while
  another is pending. Mutation retains its captured old year/tab loaders after
  navigation. Leaving/reopening tab clears status/page but retains draft/note/
  local filter. No cancellation or latest-request protection is invented.
- Missing token prevents initial load or action without error/status mutation.
  Error objects expose message; non-Error rejections use literal UI fallbacks.

## Characterization test matrix

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Wizard URL activation, query, module/roles | General manual/CF/Comune contracts | Particella requests/activation | R29 URL, exact query and wrapper props | PASS |
| Candidate order, before/after, nullish values | Other wizards only | Particella presentation and radio groups | R29 first/score, nullable0, independent radio preview | PASS |
| Draft precedence, clear/top, stale/off-page drafts | Comune analogous behavior | Particella lifecycle | R29 reload edit, top overwrite, current page order, stale ID | PASS |
| Local filter versus batch scope | No Particella mounted test | Hidden selected rows and empty local view | R29 exact batch order and no extra request | PASS |
| Pagination, filter resets and empty-page recovery | Other wizards only | Particella25 pagination | R29 next/previous, year/district/reset, positive-total recovery | PASS |
| Individual/batch payload and partial counters | No Particella mounted test | Mutations and refresh | R29 trim/default, exact ID/order, partial counters | PASS |
| Deferred busy/status order and failure paths | Other wizards only | Particella errors, refresh failure, overlap | R29 apply/load failures and two deferred mutations | PASS |
| Missing token and late responses | Other wizards only | Particella no-op/captured loader behavior | R29 no-token, old/new response order, tab leave | PASS |
| Empty-batch validation private branch | Analogous Comune blocker documented | Public UI cannot invoke zero-selection handler | Genuine disabled click proves no API call; no private invocation | NOT COVERED |

## Changes

39 coherent public-mounted tests added. No copied runtime, private handler
invocation, AST replay, fabricated coverage execution, fake timers, skipped
test, weakened assertion, runtime extraction or shared config change.

Initial focus was37 PASS with two React act warnings from the missing-token
mount: token-free report lookups still resolve asynchronously. A test-only
async `act` around mounting drains those genuine lookup transitions. Two public
overlap/captured-loader tests were added before freeze. Final focus39 PASS,
zero warnings. Initial focus log/XML/input hash are retained; final strict
types/lint and coverage union run against the final spec. The union's two act
warnings belong exclusively to the unchanged old manual spec and reproduce in
the initial196 baseline; no console suppression is used.

## Metrics before, after and delta

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| CatastoAnomaliePageContent cognitive | 390 | 390 | 0 |
| CatastoAnomaliePageContent cyclomatic | 342 | 342 | 0 |
| CatastoAnomaliePageContent callable LOC | 2109 | 2109 | 0 |
| CatastoAnomaliePageContent nesting / params | 2 / 0 | 2 / 0 | 0 |
| File effective LOC | 2267 | 2267 | 0 |
| File useState / useEffect | 24 / 10 | 24 / 10 | 0 |
| File cognitive sum / cyclomatic sum | 794 / 868 | 794 / 868 | 0 |
| File callable count | 197 | 197 | 0 |
| Whole files / callables | 1673 / 20323 | 1673 / 20323 | 0 |
| Whole error / warning / finding | 1924 / 2740 / 4664 | 1924 / 2740 / 4664 | 0 |

No complexity reduction claimed. Finding counts are overlapping metric signals,
not independent problem counts. All whole-report runtime objects are identical.

## Coverage

Actual native V8 full-file measurement of the complete page, repository's four
thresholds unchanged100; output reporters selected JSON/text/cobertura via CLI,
not gate/config changes. No runtime exclusion or coverage ignore added.

| Metric | R18 accepted before | R29 five-spec union | Newly covered |
| --- | ---: | ---: | ---: |
| Statements | 522/643 (81.18%) | 598/643 (93.00%) | +76 |
| Branches | 427/645 (66.20%) | 521/645 (80.77%) | +94 |
| Functions | 148/194 (76.28%) | 174/194 (89.69%) | +26 |
| Lines | 484/595 (81.34%) | 554/595 (93.10%) | +70 |

Full-page coverage gate **FAIL**, native exit1, four100-threshold errors only.
235 tests PASS, zero failure/skip. This known original deficit is not waived;
no runtime change is authorized by this result. Remaining45 statements,
124 branches,20 functions and41 lines are recorded with raw locations in
`audit.json`. Remaining uncovered Particella empty-batch validation
lines687–689 is publicly inaccessible because zero selection disables its
button. The analogous Comune branch lines618–620 remains uncovered. No
private-handler workaround is used. Other remaining work spans untouched
AdE/manual/lookup/render branches and requires separate ownership admission.

## Test gates and reproducibility

Initial root evidence:
`/home/cbo/.cache/gaia-campaign/20261011-r29-catasto-particella/`.
New SSD evidence:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r29/evidence/`.
Coordinator explicitly admitted new isolated SSD evidence/tmp/bytecode paths;
existing evidence/dependencies/worktrees were not moved or deleted. Root was
checked above100MiB before each native gate. No install, build, browser or
cleanup. Native heavy gates ran serially under author's sole token.

Exact argv/env is retained in `<gate>.command`, logs in `<gate>.log`, terminal
code in `<gate>.exit`, storage before/after in `<gate>.disk-*`:

| Gate | Evidence name | Result |
| --- | --- | --- |
| Existing four-spec original baseline | root `baseline.*` | native0,196 PASS |
| New initial focus | SSD `focused.*` | native0,37 PASS; warnings preserved |
| Final new focus | SSD `focused-final.*` | native0,39 PASS, no warnings |
| Five-spec complete-page V8 coverage union | SSD `union.*`, `coverage/` |235 PASS; native1 solely known unchanged100 coverage deficit |
| New-spec strict TypeScript | SSD `type-new-spec-final.*`, `tsconfig.new-spec.json` | native0; tests explicitly included, incremental false/noEmit |
| Scoped ESLint | SSD `scoped-lint-final.*` | native0 |
| Actual whole `make complexity-report` | SSD `report.*`, `complexity-after.{json,md}` | native0; parse/exception errors0 |
| Whole object/coverage/JUnit audit | SSD `audit.{cjs,json,log,exit}` |0; exact1673 file and20323 callable objects |
| Actual `make complexity-ratchet BASE_REF=main` | SSD `ratchet.*` | native0, findings[]; actual merge-base55a |
| Runtime/main/baseline/four-test custody | root `custody-before.json`, SSD `custody-final.*` |0; runtime1673 exact, old tests/main/baseline intact |

Reproduction from the author tree frontend, using existing dependencies:

```bash
npm run test:unit -- tests/unit/campaign-catasto-particella-wizard-r29.test.tsx --maxWorkers=2
VITEST_COVERAGE_INCLUDE=src/app/catasto/anomalie/page.tsx npm run test:coverage -- tests/unit/campaign-catasto-anomalie-page.test.tsx tests/unit/catasto-anomalie.test.ts tests/unit/campaign-catasto-cf-wizard-r17.test.tsx tests/unit/campaign-catasto-comune-wizard-r18.test.tsx tests/unit/campaign-catasto-particella-wizard-r29.test.tsx --maxWorkers=2 --coverage.reporter=text --coverage.reporter=json
node_modules/.bin/tsc -p /media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r29/evidence/tsconfig.new-spec.json --noEmit --incremental false
node_modules/.bin/eslint tests/unit/campaign-catasto-particella-wizard-r29.test.tsx
```

Coverage reproduction is expected exit1, not PASS. Exact SSD routing/XML output
flags are in command evidence. From root, report and ratchet commands are the
actual native Make targets, with BASE_REF=main. No baseline-repair/baseline
command run. Global baseline30 provenance is unchanged by custody and exact
runtime/metric equality; no fresh global-check or final-suite certificate is
claimed in this test-only slice. Project-wide build/E2E/backend/worker suites
are not run here. Graphify runtime relationships unchanged: no code graph
update needed for this test-only responsibility; report publication belongs
to Coordinator's dedicated documentation workflow.

## Classification

**NO_CHANGE — ORIGINAL_CHARACTERIZED**.
Runtime refactor status: **BLOCKED_COVERAGE**. Stronger genuine behavioral
protection is achieved; the target hotspot remains390 cognitive and342
cyclomatic, with no artificial reduction/relocation. This is preparation for
decomposition, not a runtime improvement or completion of the global campaign.

## Files changed and hashes

- New `frontend/tests/unit/campaign-catasto-particella-wizard-r29.test.tsx`:
  `add0937db9d0397153d5385df1a89b929da6dad2222345548d3865a629fb03a7`.
- New report (this file): exact hash recorded after freeze in `FREEZE.json`.
- All1673 runtime hashes in `custody-final.json`; all equal to integrated R28.
- Main diff SHA `9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`;
  main status SHA `0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`.
- Baseline SHA `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.

## Commit

None: author has no publication/commit authorization. Frozen files require
independent review before Coordinator decides exact-path publication.

## Residual risks and recommended next slice

The public component has stale draft, response-order, captured-loader and
scalar busy semantics that a later decomposition must preserve unless a
separate functional correction is explicitly requested. API boundary mocks do
not verify actual HTTP/DB/provider behavior or authorization enforcement.
Independent replay/review remains required. Coverage is not100; its publicly
inaccessible validation branches cannot be certified by fabricated tests.
Next admission should address a coherent remaining original public-flow
characterization responsibility (AdE orchestration or manual-state transitions)
without changing existing tests or runtime. Any inability to reach policy100
through real public behavior requires an explicit Coordinator/user decision,
not a lowered threshold, ignore or runtime change hidden inside tests.

Global campaign remains ACTIVE / INCOMPLETE; no second hotspot/refactor started.
