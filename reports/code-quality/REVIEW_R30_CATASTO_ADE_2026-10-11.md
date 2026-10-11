# R30 — Independent Catasto AdE workflow review

## Status and ownership

Final disposition after separate native admission: **ACCEPT_ORIGINAL_CHARACTERIZATION_ONLY**.
Classification **NO_CHANGE — ORIGINAL_CHARACTERIZED**; original runtime remains
**BLOCKED_COVERAGE**. No complexity reduction or global completion is claimed.
The historical preparation and pending matrix below are preserved, not
retroactively represented as native results. Final evidence is appended below.

Initial 2026-10-11 allocation: **STATIC_PREPARATION_ONLY**. This is an independent reconstruction
of the unchanged original public workflow, not acceptance of the evolving R30
spec, not native independent verification and not a complexity improvement.
Original runtime admission remains **BLOCKED_COVERAGE**. Whole campaign
ACTIVE / INCOMPLETE; no narrower definition of global completion.

Exclusive reviewer repository ownership: this NEW report only. Worktree
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r30-catasto-ade/review-worktree`,
branch `review/complexity-r30-catasto-ade`, initial HEAD
`3b99dea5981dabf2feac1611366ea7405f3a2bcc`, main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Initial working tree clean.
Coordinator registry in the integration worktree read before preparation:
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R30_CATASTO_ADE_2026-10-11.md`.
Author holds the sole heavy token; reviewer holds none.

No runtime/test/config/tooling/baseline mutations, source/spec imports, native
tests/types/coverage/complexity/Graphify commands, installs, builds, cleanup,
browser activity, commits, push, merge or child agents were executed here.
Context checkpoint/project/complexity/reference/Graphify rules and the
user-provided global objective were consulted. Graphify execution remains
reserved to Coordinator publication; no dependency boundary changed here.

## Original inputs and accepted evidence

| Input | SHA-256 independently read |
| --- | --- |
| `frontend/src/app/catasto/anomalie/page.tsx` | `855e3ef09296d8024f894118ef6e9c0d6bf13dc63b4f653c6ce6202407a732f7` |
| `frontend/tests/unit/catasto-anomalie.test.ts` | `99ab392a3bf6955514b41a2185b85017b9d5e4d01028bce4c0d6b7c34c6b0947` |
| `frontend/tests/unit/campaign-catasto-anomalie-page.test.tsx` | `7f2ae75982efaec902bc584fe6435034d426e0ac231b7fab5b7f13aa0137de23` |
| `frontend/tests/unit/campaign-catasto-cf-wizard-r17.test.tsx` | `e4b97fcc3460641482b01f8d6b55b804b1c7f1d374f11b6cb0f60417e98840a2` |
| `frontend/tests/unit/campaign-catasto-comune-wizard-r18.test.tsx` | `63e29633a3733258395e8760739240b1e5c0ca3ce1fa40cf4b7e79a81359273b` |
| `frontend/tests/unit/campaign-catasto-particella-wizard-r29.test.tsx` | `add0937db9d0397153d5385df1a89b929da6dad2222345548d3865a629fb03a7` |
| `frontend/vitest.config.ts` | `01e2dab469c1a961df5d2aa70efcb79e2e6a732be47808f5640a80d77ad61c68` |
| `reports/code-quality/INTEGRATION_R29_CATASTO_PARTICELLA_2026-10-11.md` | `75df3de23b7140257ca5854d1b4abb665501c4d0a8d7150cf45320d12fd22bec` |
| Prior root `FREEZE.json` | `58e3d24cee941fea01b6e23e4547cade1c3aefe71bb2abe9348635d73be47c6a` |

Prior root evidence directory:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r29/root-evidence/`.
All 80 entries of its actual embedded `manifest` map were hashed read-only:
zero mismatches. `union.command`, `union.exit`, bounded `union.log` and native
`coverage/coverage-final.json` were inspected. This verifies existing artifact
custody, not a new execution of R29 or R30 tests. Previous native union:
235 PASS, zero failure/skip, exit1 exclusively for unchanged full-file100.

| Prior accepted page coverage | Covered/total | Percentage |
| --- | ---: | ---: |
| Statements | 598/643 | 93.00% |
| Branches | 521/645 | 80.77% |
| Functions | 174/194 | 89.69% |
| Lines | 554/595 | 93.10% |

The genuine V8 map has no execution of the AdE article conditional branch at
page.tsx:1313, run command at714, batch opener at795 or modal close at2381.
Old specs protect other queues and the unconditional initial AdE request, but
do not establish AdE render/command behavior. No new coverage result is claimed.

## Independently reconstructed public contracts

References below are to the unchanged original page.

### Loading and context

- `loadAdeScan` runs from its stable mount effect on every initial tab, not
  only `ade` (page.tsx:445, page.tsx:521). Explicit `tab=ade` is valid and wins
  over workspace fallback. AdE does not become a wizard mode (page.tsx:215).
- Missing token returns before any request or state change. Existing data,
  message and error remain as they were; absent initial data stays absent.
  Auth enforcement itself belongs to the unmodified wrapper/API, not a mocked
  token or wrapper test.
- Valid token starts shared AdE busy, then requests summary(token),
  candidates(token,{limit:8}) and batches(token) in one Promise.all. Year,
  district, overview filters/page and selected tab are not forwarded. Context
  edits do not recreate the empty-dependency AdE loader.
- With ordinary typed responses, no returned summary/candidate/batch state
  is replaced before all three resolve. Rejection of any participant leaves
  prior data intact and stores Error.message or the literal non-Error fallback
  `Errore caricamento scansione AdE`. Other promises are not cancelled.
  This is not a DB transaction or proof of atomic handling of malformed data.
- Success replaces summary and candidate items, filters batches, sorts and
  truncates them, then clears AdE error. Loading does not clear a prior message
  or an existing error at start; finally releases busy (page.tsx:458).
- Batch name filtering is case-sensitive startsWith of exactly
  `Visure storiche AdE particelle non collegate`. Null names become empty
  strings and are excluded. Sorting is descending Date.parse(created_at),
  followed by slice(0,6); ties preserve native stable ordering. Invalid dates
  use the actual comparator semantics, not a new validation/fallback policy.
- First pending or processing in the retained six is the active batch, not
  first in the API response and not first globally before truncation
  (page.tsx:774). An active batch ranked seventh creates no active CTA.
- AdE navigation passes undefined tipo, leaving the current overview type
  filter unchanged. Navigation resets other queue pages/feedback but does not
  clear AdE state/error/message/workspace (page.tsx:895, page.tsx:1076).

### Presentation

- AdE tab count is absent while summary is null, but literal zero is shown
  when total_unmatched=0. Active workspace count falls back to zero. Statistic
  cards use em-dash only for nullish totals/pending, preserving zeros.
- Truthy last_checked_at uses the original formatDateTime; null/empty values
  display `Mai eseguita`. The imported formatter displays invalid strings
  unchanged; do not introduce locale/time-zone assumptions in assertions.
- Summary buckets retain response order, capped at six. A loaded empty bucket
  array displays `Nessun esito AdE salvato.`; absent summary does not show that
  loaded-empty message (page.tsx:1363). Initial fixture must not pass `{}` as a
  valid summary when rendering this tab: buckets is required in the real type.
- Candidates retain all returned items and order: limit8 is requested from
  API, but rendering does not impose a second client-side limit or use total.
  Truthy sezione/subalterno add their labels, falsey match_reason/status use
  em-dash/`non scansionata`, truthy document ID adds `PDF acquisito`
  (page.tsx:1377). Empty candidates have the literal empty message.
- Retained batch rows preserve sorted order, completed/failed counts, and
  display not_found/skipped badges only for values greater than zero.
  Operation/status rendering uses existing child components, not copied
  implementation. Batch absence displays the current-user empty message.
- Load/run controls are disabled by adeScanBusy; run label is
  `Preparazione...` while busy. Tab/context controls and batch workspace open
  are not disabled by this flag. Error and success message can coexist.

### Queue command, refresh and late responses

- `handleRunAdeScan` returns before feedback changes on missing token. With
  a token it sets busy and clears both error and prior message, then calls
  `catastoRunAdeStatusScan(token,{})` (page.tsx:714). No year/district/limit,
  match reasons or selected candidates are added to the payload.
- created>0 yields literal created count plus skipped suffix only for a truthy
  skipped count; created<=0 yields `Nessuna nuova particella da mettere in
  coda.` regardless of skipped. Returned batch_id does not auto-open a modal.
- After success the message appears before awaiting loadAdeScan. That loader
  reacquires the current token, not the token captured for the mutation, and
  waits on all three requests. Its error is swallowed locally: a failed refresh
  leaves the queue success visible alongside reload error, not a queue failure.
- Queue rejection uses Error.message or `Errore avvio scansione AdE`, does not
  refresh and retains prior data. Finally releases the same busy boolean.
- Losing token during mutation prevents subsequent refresh requests while
  preserving queue result. Switching tab/context during pending mutation does
  not cancel it or change the empty AdE refresh payload. Results remain in
  AdE state when returning to the tab. A deferred older Promise.all participant
  after rejection cannot trigger another data commit on its own.
- A scalar boolean is not a reference counter. However source inspection alone
  does not establish a publicly reachable overlap of two AdE commands: both
  triggers are disabled while it is true, and mount loader has no context
  dependency. Do not invoke private handlers, bypass disabled DOM, or create
  impossible double-click races to claim branch coverage. Genuine tab/context
  transitions and outstanding promises are suitable async contracts.

### Batch workspace and inaccessible fallback

- Row-name button, row `Apri batch` and `Apri batch attivo` open identical
  boundary props: `/elaborazioni/batches/${batch.id}`, batch.name and the
  literal operative description (page.tsx:795). The mounted original page
  owns state; a minimal child modal adapter may observe props and invoke its
  public close callback.
- Modal close clears workspace; closed props are open=false, href=null,
  title=`Dettaglio batch`, description=null (page.tsx:2377). Workspace remains
  across tab changes; opening is not navigation through router.replace.
- The batch.name nullish fallback in handleOpenAdeScanBatch at798 and table
  fallback at1435 are not reachable through the loader's accepted batch set:
  null and empty names fail the mandatory prefix. Do not inject private state,
  mutate a retained fixture object after render, or cast an invalid mock merely
  to execute them. Closed-modal fallback is reachable and distinct.
- Existing empty-selection validation guards618–620/687–689 remain separately
  inaccessible and outside R30. Disabled clicks prove no API mutation, not
  execution of those guards. Full-page100 must not be waived or simulated.

## Public boundary test matrix proposed before author freeze

Every row below is a proposal, not an added or passing R30 test. No unfrozen
author spec was imported or treated as acceptance evidence.

| Behavior | Existing evidence | Missing | Added here | Result here |
| --- | --- | --- | --- | --- |
| Initial load regardless of tab; literal API args | Old manual initialization | AdE public render/no-token | No | Static only |
| All three awaited; initial placeholders/busy | Existing request invocation | Deferred participants and each rejection | No | Static only |
| Prefix/null name, stable dates, top6, active first | Original loader source | Mixed real-shaped batches, rank7 active | No | Static only |
| Summary zero/null/date/bucket order/top6/empty | V8 original article branch0 | Real-shaped summary fixtures | No | Static only |
| Candidate order and truthy metadata fallbacks | Original article source | Mixed candidates and empty items | No | Static only |
| Batch row counts, status/operation, modal close | Original source, close0 | Public name/row/active clicks and adapter props | No | Static only |
| Queue positive/zero/skipped and exact payload | Run handler V8 counters0 | Click with typed responses; no auto-open | No | Static only |
| Queue failure and missing/lost token | Source only | Error/non-Error, token loss before/during | No | Static only |
| Reload preserves old data/feedback until resolution | Source only | Failed participants, success, pending state | No | Static only |
| Successful queue plus failed refresh | Source only | Deferred message then reload error | No | Static only |
| Leave/change context during pending load/queue | Source only | Public transitions, late settle/reentry | No | Static only |
| Private nullable batch-name/empty selection branches | Inaccessible original source | Explicit decision, not synthetic tests | No | BLOCKED |

API/auth/router/component boundary mocks are permitted, not source copies,
reimplemented business logic or private handler access. Use async act and
observable UI/API completion conditions, not arbitrary timers or warning
suppression. Preserve old assertions and record old versus new act warnings.

## Measurements, tests, gates and classification

No fresh native metrics, coverage, tests, types, lint, ratchet or Graphify
executed in this static allocation. Registered original target remains
CatastoAnomaliePageContent390 cognitive/342 cyclomatic/2109 callableLOC,
file2267LOC/24useState/10useEffect. These are accepted previous metrics, not
a new measurement. No reduction delta or complexity improvement is claimed.

Only this report changes in the reviewer repository. Next final admission
requires author terminal/frozen hashes, root byte-exact NEWspec import and
separate native token. Final independent review must verify tests, full-page
coverage100 still enforced, native types/lint, current whole AST report,
actual main55a ratchet, original five specs/runtime/main/baseline custody,
exact commands/exits and evidence freeze. Unknown new failures mean STOP.

### Observation errors retained

Two read-only artifact-path mistakes occurred in this preparation, neither a
native test/gate failure: guessed standalone R29 `manifest.sha256` was absent
(`ls` diagnostic), and guessed `coverage-summary.json` was absent (Node
ENOENT, exit1 for that Node process). The actual FREEZE embeds the manifest,
and the original union used text/json/cobertura, not json-summary. Root was
notified. Original evidence remained unchanged; no native command restarted,
no failed log overwritten. Later reads used the actual manifest-present
coverage-final.json. These observations do not convert native coverage FAIL
to PASS. Bounded details retained in private STATIC_OBSERVATIONS.md on SSD.

Initial static storage measurement: root159MiB available, separate SSD343509MiB.
No caches, browser, dependencies, worktrees, prior evidence or other project
directories were moved/deleted. Heavy-token admission must recheck space.

## Residual risks and next step

Static preparation complete; final R30 acceptance PENDING. Original page100
coverage remains FAIL/BLOCKED, no runtime refactor admitted. Existing R25
matcher misattribution and historical30 global divergences are separate;
this report makes no provenance repair or global PASS claim. Broad final
backend/frontend/worker/build/E2E suites and extreme-tail reduction remain
open. Do not classify test-only characterization as IMPROVED.

## Separate final independent admission and frozen review

Coordinator followup explicitly admitted native independent verification only
after author TERMINAL/token RELEASED, freeze verification and root byte-exact
NEWspec import. Reviewer owns this report only; root-imported spec/source/old
five specs/shared eight are read-only. No author auditor copied blindly.
Private reviewer scripts inspect the actual manifest and schema paths and
record commands/logs/exits/storage; all new temp/bytecode/output stays on SSD.

Frozen author inputs independently verified before and after reviewer gates:

| Frozen input | SHA-256 |
| --- | --- |
| Author `evidence/FREEZE.json` | `7a9be0fe6064af4801a8c94f8e09b43ad514aeb70da33b59e1c15afdf894516b` |
| Exact root-imported NEWspec | `55b72cb05aeb0381c6d9e98640326a729901db4daf34c2f8a1f6842aff57cc23` |
| Frozen author report | `2b0190cbce2431cc1270e3edc13e3b8081c381fc9c0c15020f5227eb9adaef7b` |

All92 frozen raw members and source/spec/report hashes exact. Fresh custody
checks all1673runtime, five old specs, eight shared files, actual HEAD3b99 /
main55a, protected main diff/status and canonical baseline hash38e6b794. Both
before/final native custody0. Only NEWspec and NEWreview are untracked in this
tree; spec imported exclusively by root, no reviewer test/runtime edits.

### Frozen failure recovery review

Independent byte comparison proves SPEC_TYPE_FAILURE -> SPEC_FOCUS_FAILURE
removes ONLY five unsupported `, exact: true` options. Role string names are
already exact; role/payload/count/aria assertions remain unchanged. Native
initial type log has exactly five TS2769 failures at97/223/247twice/440.
Initial lint0 before interpreting types2 is disclosed sequencing deviation,
not a passed type check or erased failure. Failure input/logs preserved.

SPEC_FOCUS_FAILURE -> final frozen spec removes ONLY three spaces in exact
literal names `Scansione AdE 31/77` -> `Scansione AdE31/77`. Source adjacent
spans and original native role diagnostics confirm those actual names. Initial
focus31PASS3FAIL and raw failed XML/log remain immutable. No regex relaxation,
assertion removal, test skipping, runtime accessibility change or baseline
change occurred. Separate bounded Coordinator recovery is recorded in registry.

### Final test design review

Read all frozen34 tests and actual original route. Genuine render/public API
boundary, deferred loading/command completion, tab/context transitions and
public child-close controls execute original runtime. Coverage is native V8,
not copied source/private handlers/synthetic branch execution. Tests preserve
prefix/sort/top6/first-active behavior, exact empty command payload, response
ordering, legacy token/refresh/hidden-tab/unmount semantics and modal boundary
props. Stand-ins do not prove auth, backend transaction, SISTER/worker or iframe
behavior. formatDateTime expectation calls the unmodified imported formatter;
this protects its use, not independent formatter correctness.

The proposed static matrix was a review checklist, not proof every imagined
case was added. Final tests do not claim exhaustive race coverage or execute
nullable retained-batch names/inaccessible empty-selection guards. No scope
expansion or desired-behavior bug fix is hidden in characterization. Author
`Promise.all makes publication atomic` is accepted only for ordinary typed
responses with all participants successful, not malformed inputs/DB atomicity.

## Fresh independent native results

Evidence:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r30-catasto-ade/review-evidence/`.
Exact argv/environment, terminal exit and before/after storage are recorded
per gate by private gate.sh. Each command ran once, serially; live report and
ratchet handles were polled to terminal, never restarted after observation wait.
Root available142MiB initially,136MiB near ratchet; guard100MiB maintained.

| Gate | Native command / raw evidence | Result |
| --- | --- | --- |
| Admission/final custody | node private custody.cjs before/final; custody-before.*, custody-final.* | 0, original/shared/main/baseline exact |
| NEWspec focus | npm run test:unit -- tests/unit/campaign-catasto-ade-scan-r30.test.tsx --maxWorkers=2; focus.* | 0,34PASS,0failure/skip/warning |
| Complete-page six-spec union | unchanged VITEST_COVERAGE_INCLUDE page, npm run test:coverage; union.command/log/exit/XML, coverage/coverage-final.json | 1 ONLY full100 deficit;269PASS,0failure/skip |
| Strict project+NEWspec types | node_modules/.bin/tsc -p private tsconfig.test-inclusive.json --noEmit --incremental false | 0 |
| NEWspec lint | node_modules/.bin/eslint tests/unit/campaign-catasto-ade-scan-r30.test.tsx | 0 |
| Whole native report | make complexity-report REPORT_JSON=SSD/complexity-after.json REPORT_MD=SSD/complexity-after.md | 0 |
| Actual authoritative ratchet | make complexity-ratchet BASE_REF=main; ratchet.* | 0, actual55a/findings[] |
| Raw independent audit | node private audit.cjs; audit.* | 0, XML/counters/maps/warnings/objects checked |

Six-spec union uses unchanged five original spec arguments plus NEWspec,
--maxWorkers=2, V8 text/json/cobertura and native JUnit. Four threshold failure
messages at100 are present. Native test success and coverage failure are
separate. Focus has0warning; union has exactly2old manual DataTable act warnings
with identical test names to original author235 baseline and author269 union.
No suppression or unexplained new failure occurred during reviewer natives.

### Actual coverage retained FAIL

| Whole original page | Before | Independent after | Covered delta |
| --- | ---: | ---: | ---: |
| Statements |598/643 (93.00%)|624/643 (97.04%)|+26|
| Branches |521/645 (80.77%)|580/645 (89.92%)|+59|
| Functions |174/194 (89.69%)|188/194 (96.90%)|+14|
| Lines |554/595 (93.10%)|579/595 (97.31%)|+25|

Every statement/function/branch map and counter equals the frozen author union,
not merely rounded percentage equality. Zero skipped coverage. Residual19
statements/65branches/6functions/16lines, exact locations in audit.json. Runtime
admission remains BLOCKED_COVERAGE; nullable batch-name arms798/1435 and public
zero-selection guards remain unexecuted, not waived/fake-covered. Further
reachable manual residuals and any inaccessible-source decision are separate.

### Complexity, policy and limits

Whole1673file/20323callable objects, scope, engines, summary and violation
arrays exactly equal accepted R29 root. Parser/exception errors empty. Target
390cognitive/342cyclomatic/2109LOC unchanged; file2267LOC/24useState/10useEffect,
global1924errors2740warnings4664overlapping findings unchanged. Delta0/0%.
Ratchet parses the actual JSON delimiter after Make command, baseline_commit
55a and findings[]; no BASE_REF trick. Baseline/scope/threshold/ignore/tooling
unchanged; no global-check rerun or assertion historical30 disappeared.

No fresh broad backend/frontend/worker/build/E2E or Graphify executed by this
reviewer. Docs graph publication remains Coordinator responsibility. No commit,
push, merge, cleanup, install, browser or movement/deletion of prior data.
Final native gates and frozen author custody qualify ONLY this original
test/report characterization for publication, not a runtime change or closure
of the global mission. Reviewer TERMINAL, native token RELEASED after freeze.
