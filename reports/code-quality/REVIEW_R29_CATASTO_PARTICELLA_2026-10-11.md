# R29 — Independent Catasto Particella review

## Status and ownership

Final disposition, 2026-10-11: **ACCEPT_ORIGINAL_CHARACTERIZATION_ONLY** after
the distinct independent native admission documented below. Runtime admission
remains **BLOCKED_COVERAGE**, with **NO_CHANGE** and no complexity reduction
credit. Full global campaign ACTIVE / INCOMPLETE. The initial static preparation
and its historical pending matrix are preserved below, not retroactively
represented as native verification.

Exclusive reviewer repository ownership: this new report only. Worktree
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r29/review-worktree`,
branch `review/complexity-r29-catasto-particella`, HEAD
`f3598577ddb8d681fa30ea4ed984a2fc4209f826`, actual main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Preflight working tree clean.
Registry read before work: `MULTI_AGENT_OWNERSHIP_R29_CATASTO_PARTICELLA_2026-10-11.md`
in the integration worktree. Author holds the sole heavy native token.

No runtime/test/config/tooling/baseline edits, imports, test runs, complexity
commands, Graphify invocation, install/build/cleanup or commits are authorized
in this preparation. Existing source/test hashes independently read below.
The evolving author NEWspec is deliberately not used as frozen evidence.

## Original custody and baseline

| Input | SHA-256 |
| --- | --- |
| `frontend/src/app/catasto/anomalie/page.tsx` | `855e3ef09296d8024f894118ef6e9c0d6bf13dc63b4f653c6ce6202407a732f7` |
| `frontend/tests/unit/catasto-anomalie.test.ts` | `99ab392a3bf6955514b41a2185b85017b9d5e4d01028bce4c0d6b7c34c6b0947` |
| `frontend/tests/unit/campaign-catasto-anomalie-page.test.tsx` | `7f2ae75982efaec902bc584fe6435034d426e0ac231b7fab5b7f13aa0137de23` |
| `frontend/tests/unit/campaign-catasto-cf-wizard-r17.test.tsx` | `e4b97fcc3460641482b01f8d6b55b804b1c7f1d374f11b6cb0f60417e98840a2` |
| `frontend/tests/unit/campaign-catasto-comune-wizard-r18.test.tsx` | `63e29633a3733258395e8760739240b1e5c0ca3ce1fa40cf4b7e79a81359273b` |

Coordinator-admitted baseline, not independently rerun here: old four specs
196 PASS, page coverage 522/643 statements, 427/645 branches, 148/194 functions.
Full-page 100% FAIL remains open. Registered source target is
`CatastoAnomaliePageContent`: cognitive390, cyclomatic342, callableLOC2109;
fileLOC2267, useState24, useEffect10. No new measurement or reduction credit.

## Independently reconstructed public contracts

Source references below identify the original unchanged page.

### Loading, query, pagination and selection

- Initial `tab=particella`, or compatible `workspace=particella` when no explicit
  valid tab is supplied, selects the wizard. Other tabs keep its loader idle.
  Wizard starts at page1 independently of overview URL `page` (page.tsx:215).
- `loadParticellaWizard` returns before state/API changes on inactive tab or
  missing token. Request is `{status:"aperta", anno:Number(value) or undefined,
  distretto:raw string or undefined, page, pageSize:25}`; overview status/type/
  severity/search/sort are not forwarded to the Particella API (page.tsx:403).
- Returned item and candidate order is authoritative. The first candidate is
  automatically selected for a falsey draft; match score does not reorder it.
  Functional draft merge preserves the latest truthy edit and off-page keys.
  It does not validate retained IDs against new candidate arrays (page.tsx:428).
- Empty positive-total page>1 resets page1 without first replacing old rows,
  total or drafts. Empty page1 is accepted without a recovery loop. Failure
  retains old rows/total/drafts and surfaces Error.message or literal fallback.
  Finally releases the shared boolean load busy flag (page.tsx:422).
- Local `without_candidates` filters rendering only, not fetched data, count
  of selected current rows or batch payload. Its change causes no API request
  and does not reset pagination or drafts (page.tsx:759, page.tsx:1800).
- Clear removes the complete draft dictionary. Top selection overwrites every
  current candidate-bearing row with its first candidate, retaining off-page
  keys and stale draft keys for rows now without candidates (page.tsx:778).
- Radios have independent per-anomaly groups. Preview/single action exists
  only if the draft matches a current candidate. A truthy stale draft still
  increments batch count and can be submitted although no preview exists.
  Preserve this observed behavior; do not invent validation (page.tsx:1883,
  page.tsx:1908).
- Year/district edits and context reset return pagination to1. Tab selection
  also resets overview/CF/Comune/Particella page counters and clears wizard
  messages/errors, but not drafts, local view or batch note (page.tsx:895,
  page.tsx:1258). Particella page is not serialized as overview URL page.

### Mutation and refresh ordering

- Token loss before individual/batch apply returns without API/state changes.
  Individual apply captures candidate ID and trimmed note at click time;
  blank note fallback is `Collegamento particella da console anomalie`.
  The initially nonblank batch note is used for single apply too (page.tsx:645).
- Batch iterates all current items in response order, maps each retained draft,
  drops falsey IDs and attaches a trimmed note with the distinct batch fallback.
  It includes selected rows hidden by local view; excludes off-page drafts.
  No extra candidate-existence validation is performed (page.tsx:673).
- Starting apply sets one scalar applying ID, clears prior message/error,
  awaits API, publishes response counts literally, then awaits overview and
  the captured wizard loaders concurrently. Inactive wizard loaders are idle.
  Busy release waits for these loaders to finish, not merely mutation success.
  Both numeric zero and partial counts remain literal; no rollback is claimed
  for a partial response or refresh failure (page.tsx:651, page.tsx:692).
- Apply failure shows Error.message or the separate single/batch fallback,
  makes no successful refresh, and releases applying ID. Reload errors are
  caught within loaders, so a successful mutation message can coexist with
  Particella reload error and retained previous rows (page.tsx:667).
- Initial/reload busy disables batch/top/clear; candidate radio, note and local
  view remain editable. A selected single action is not disabled merely by
  load busy. During batch mutation, single actions/batch are disabled but
  top/clear remain enabled until actual loading begins (page.tsx:1789,
  page.tsx:1946). Do not normalize these asymmetries in characterization.

### Race-sensitive original behavior

- No cancellation/version token/cleanup rejects older loads. An older response
  may replace newer rows and merge drafts; either load's finally can release
  the shared boolean busy flag while another remains outstanding.
- Mutation captures the loaders from its render. A pending apply can refresh
  its old Particella tab/year after navigation/context edit; latest note/radio
  edits are not retroactively substituted into the captured API payload.
- Single apply does not globally lock batch or other rows. Single→batch and
  distinct single calls can overlap. The original scalar applying ID permits
  one completion to release controls for another pending mutation. This is an
  invariant to record, not a functional concurrency fix in R29.
- No Particella-wizard modal exists in this rendering. Manual linked-parcel
  modal behavior is already covered by the original manual spec and must not
  be inferred as a candidate-detail modal or expanded here.

## Independent characterization matrix before author freeze

| Behavior | Existing test | Missing for Particella | Added | Result |
| --- | --- | --- | --- | --- |
| Loader activation, literal request, independent page/URL | CF/Comune analogous; manual verifies inactive wizard | Yes | Pending frozen NEWspec review | Not executed |
| First-candidate auto-fill, explicit radio/preview | Comune analogous | Yes | Pending | Not executed |
| Local hidden rows still counted/submitted | No equivalent Particella lifecycle | Yes, distinct Particella risk | Pending | Not executed |
| Clear/top and draft merge/off-page preservation | Comune analogous | Yes | Pending | Not executed |
| Stale IDs without current candidate still batch-eligible | Comune analogous | Yes | Pending | Not executed |
| Pagination/reset and empty positive-total recovery | Comune analogous | Yes | Pending | Not executed |
| Load Error/non-Error, retained previous state, token loss | CF/Comune analogous | Yes | Pending | Not executed |
| Single/batch payload, note trimming/distinct fallback | No executed Particella mutation | Yes | Pending | Not executed |
| Captured payload and refresh busy ordering | CF/Comune analogous | Yes | Pending | Not executed |
| Partial/zero counts and successful apply + failed refresh | Comune analogous | Yes | Pending | Not executed |
| Overlapping late loads, captured old context/tab refresh | Comune analogous | Yes | Pending | Not executed |
| Original shared scalar applying-ID race | Comune analogous | Yes | Pending | Not executed |
| Manual parcel navigation/modal | Original manual mounted spec | No, preserve unchanged input | None | Historical result only |

Analogous Comune/CF assertions do not prove the independently implemented
Particella paths. Pure explainer tests cover VAL-05 text, not wizard lifecycle.

## Admission conditions and residual risks

1. Receive exact frozen NEWspec/report hashes and raw author evidence from
   Coordinator. Check diff is exclusively admitted tests/report, no existing
   assertion weakening, skips or runtime changes.
2. Inspect actual mounted-route tests, typed external API boundary fixtures,
   public actions and awaited deferred responses. No copied runtime logic,
   generated branch executions or private handler invocation.
3. Review native old+new union outcome and raw page coverage against unchanged
   denominator, source custody and actual55a ratchet. Never accept aggregate
   average as full-page100 or call expected incomplete100 PASS.
4. A separate independent native verification admission is required before
   certification; this static preparation has no token and runs none.
5. Only characterize original behavior. Any desired concurrency/validation
   improvement is a separate functional decision, not an R29 refactor.

One read-only observation searched the nonexistent legacy `frontend/src/lib/api.ts`;
it returned an IO error. Correct API path was located from the runtime import
as `frontend/src/lib/api/catasto.ts`. No native command/process was launched
or restarted because of this observation error.

Root free space at independent preflight was about205MiB; archive SSD336GiB.
All new reviewer outputs stay in its admitted SSD worktree/evidence. No cleanup,
moving prior evidence or deleting other project resources was performed.

## Classification and next action

Initial disposition: **NO_CHANGE — STATIC_PREPARATION_ONLY.** No complexity reduction credit and
no acceptance of a draft test candidate. Runtime full-file100 remains blocked.
Next action: wait for Coordinator's frozen author inputs and review them
without native activity unless explicitly admitted separately.

## Separate final independent admission

Coordinator granted independent native verification after author termination,
updated ownership before activation and imported only the exact frozen new spec.
No import was performed by this reviewer. Frozen author inputs independently
verified against all80 manifest members:

| Frozen input | SHA-256 |
| --- | --- |
| New `campaign-catasto-particella-wizard-r29.test.tsx` | `add0937db9d0397153d5385df1a89b929da6dad2222345548d3865a629fb03a7` |
| Author characterization report | `e4529d7c7187f18a9421a0f33d44f3153f59b6f62ef3317485830ceab899deca` |
| Author `FREEZE.json` | `ed09d55c44f3edf43ad35c39d6b95ad19bc69b58716d611eed39c5e826713cf5` |

All new independent evidence lives at
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r29/review-evidence/`.
Temporary files, bytecode and coverage outputs route to its SSD directories.
Existing dependencies are read-only linked; no install, build, browser,
cleanup, application/config/baseline change or commit occurred.

### Explained private-auditor recovery

First independent custody gate failed with ENOENT because the private reviewer
auditor assumed `tools/code_quality/complexity-baseline.json`. The canonical
path is `config/code-quality/complexity-baseline.json`, explicitly defined by
`tools/code_quality/complexity.py:28`. Reviewer stopped before all application
gates. Coordinator granted a distinct bounded recovery after validating the
canonical path and baseline hash in both trees.

Original `custody.cjs`, `custody-before.command`, `.log`, `.exit` and
`OBSERVATION_ERRORS.md` remain byte-exact. A separate `custody-corrected.cjs`
changes only that path; separately named `custody-before-corrected` exits0.
No failed evidence was overwritten or native process restarted. The prior
read-only freeze-key TypeError is also recorded in the original observations.

### Independent native results

Exact arguments/environment are in each `<gate>.command`, bounded raw output
in `<gate>.log`, native result in `<gate>.exit`, storage snapshots in
`<gate>.disk-before` and `.disk-after`. Gates ran serially with the reviewer's
sole heavy token, with root free storage above100MiB at every launch.

| Gate | Independent evidence | Result |
| --- | --- | --- |
| Frozen author80, runtime1673, old4, main and baseline custody | `custody-before-corrected.*` | Native0, exact |
| New mounted-route focus | `focused.*`, `focused.junit.xml` | Native0,39 PASS,0 failure/skip,0 act warnings |
| Full five-spec page V8 union | `union.*`, `union.junit.xml`, `coverage/` |235 PASS,0 failure/skip; native1 solely four unchanged100 coverage deficits |
| Strict project source plus explicitly included NEWspec | `type-test-inclusive.*`, `tsconfig.test-inclusive.json` | Native0; entire src and NEWspec included, incremental false/noEmit |
| New-spec ESLint | `scoped-lint.*` | Native0 |
| Actual whole Make complexity report | `report.*`, `complexity-after.{json,md}` | Native0; exact1673 file/20323 callable objects versus R28 |
| Actual Make ratchet `BASE_REF=main` | `ratchet.*`, `ratchet-raw.json` | Native0; actual baseline commit55a, findings[] |
| Independent JUnit/raw coverage/maps/metrics/gate audit | `audit-independent.*` | Native0 |
| Final runtime/main/baseline/old4/frozen-author custody | `custody-final-corrected.*` | Native0, exact; freeze manifest records terminal result |

Live handles were reported to Coordinator: focus18144, union17027,
project/test-inclusive types6022, whole report58380, ratchet56434. Each was
observed terminal before the next heavy gate; observation waits caused no retry.
No fresh global complexity-check, complete project suites, build or E2E ran.
Global30 provenance is not claimed independently recertified by this slice;
the exact runtime/baseline custody and zero metric delta preserve its inputs.

### Actual full-file coverage — still FAIL100

Native V8 file entry is only the complete original page, not a helper or scoped
line subset. The statement/function/branch maps and all counters match the
frozen author's raw coverage exactly after root-path normalization. All
denominators are unchanged from accepted R18, with no skipped entries.

| Metric | Accepted R18 before | Independent R29 after | Covered delta |
| --- | ---: | ---: | ---: |
| Statements |522/643|598/643 (93.00%)|+76|
| Branches |427/645|521/645 (80.77%)|+94|
| Functions |148/194|174/194 (89.69%)|+26|
| Lines |484/595|554/595 (93.10%)|+70|

Remaining45 statements,124 branches,20 functions and41 lines are real deficits.
Raw missing statement/branch locations are in `audit-independent.json`; the
unreachable public empty-selection validation at page.tsx:687 remains uncovered.
Disabled zero-selection click genuinely verifies no API invocation but does not
execute that handler branch. No synthetic private-handler execution, runtime
ignore or reduced threshold disguises this. Runtime refactoring is not admitted.

Two union React act warnings belong exclusively to the unchanged manual spec:
`without-wizard filter is local and recovers selection when a selected row
disappears` and `unworked view excludes notes, assignment and non-open status
but accepts whitespace notes`. Both names reproduce in the initial196 baseline;
the independent39-spec focus has no act warnings. Console output is not suppressed.

### Final independent matrix

| Behavior | Existing test | Missing before R29 | Added public assertions | Result |
| --- | --- | --- | --- | --- |
| Tab/workspace precedence, query, independent page/URL | Other wizard analogues | Particella-specific | Literal25 query, tab precedence, URL and wrapper props | PASS |
| Response-first selection and preview/radio/nullish fields | Other wizard analogues | Particella-specific | Score-order distinction, independent groups, literal before/after and0 | PASS |
| Hidden selected rows/local empty view batch scope | None | Yes | No fetch on view change, hidden IDs in exact response-order payload | PASS |
| Draft edits, clear/top, off-page/stale IDs | Comune analogues | Particella-specific | Deferred edit merge, top overwrite, stale ID/no preview, current-page batch | PASS |
| Page recovery and context resets | Other wizard analogues | Particella-specific | Page2 empty positive-total recovery and year/district/reset page1 | PASS |
| Single/batch notes and partial/zero counters | None | Yes | Exact trim/default/ID/order and literal response counts | PASS |
| Mutation snapshots, control asymmetry, refresh/failure | Other wizard analogues | Particella-specific | Genuine deferred API completion, intended locks, successful apply+load failure | PASS |
| Missing token, Error/non-Error fallback | Other wizard analogues | Particella-specific | Genuine public no-op and literal load/apply failures | PASS |
| Late/captured loads and original scalar busy race | Comune analogues | Particella-specific | Out-of-order replacement, old year/tab refresh, overlapping single→batch | PASS |
| Zero-selection handler validation branch | Public disabled control | Not publicly executable | Disabled click/no API only | NOT COVERED |
| Manual linked-parcel modal | Original manual spec | No | Original input preserved |235-union PASS, unchanged legacy warnings|

These are real mounted original route actions; APIs/navigation/auth-token are
boundary mocks and authorization-wrapper props are observed, not enforcement.
The fixtures do not copy handlers/domain algorithms; no AST/private execution,
fake timers, skipped tests, source import substitution or weakening old tests.
Current test counts are39 new and235 union, not39 distinct runtime problems.

### Metrics, debt and disposition

Whole report independently compares exactly to accepted R28: all1673 file and
20323 callable objects, spans, fingerprints, metric tuples, violations and
summary unchanged. Global1924 Error,2740 Warning,4664 overlapping findings.
`CatastoAnomaliePageContent` cognitive390,cyclomatic342,LOC2109,nesting2,params0;
fileLOC2267,useState24,useEffect10,197callables,cognitive sum794,cyclomatic sum868.
Before/after delta0 and0%. No responsibility/dpendency change, debt relocation
or Graphify code relationship update is introduced by test-only characterization.
Documentation Graphify publication workflow belongs to Coordinator.

**ACCEPT_ORIGINAL_CHARACTERIZATION_ONLY — NO_CHANGE.** Stronger original
behavioral protection is independently reproducible. Full-file100 remains
**FAIL / BLOCKED_COVERAGE**, with no runtime admission or complexity credit.
No merge/commit/publication is performed by reviewer. Coordinator may publish
only the exact frozen new spec/author report/independent review after its own
integration gates. Sole heavy token is **RELEASED**, agent **TERMINAL**, with
no native process outstanding after final custody/freeze.

Residual risks: public stale ID submission, captured old context, out-of-order
loads and scalar apply busy semantics remain intentional characterization
boundaries, not repaired behavior. Real HTTP/DB/provider/auth enforcement and
global final suites remain uncertified. Further runtime change requires actual
full-file100 or a separate explicit policy decision; no workaround is inferred.
Recommended next admission is coherent remaining original AdE/manual-flow
characterization, not a second refactor in this allocation. Global campaign
ACTIVE / INCOMPLETE; no claim to achieved strategic targets.
