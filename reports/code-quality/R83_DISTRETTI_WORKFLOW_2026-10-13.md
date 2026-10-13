# R83 — Distretti test-workflow slice report

## Ownership and snapshot

Exclusive spec/docs Coordinator ownership in R83registry, independent reviewer
owns only external review/. Integration HEAD2d9236e61e8479bae93566137e2fb26eaae0d4ab,
branch refactor/complexity-campaign-20261008, actual main/basea51a48dc.
Main concurrent config/Bonifica test untouched, historical55a1b1d not BASE_REF.
Native/runtime/refactoring is not authorized by this test-only responsibility.

## Baseline and behavioral invariants

Original whole-file two drill-down cases skipped in historical E2E due empty
private district dataset. Source frozen on SSD before modification, SHA256
f720a46e44b46e3b3d40ea10074da56968debd7708873daa15decdb2781896d6.
Static R82diagnosis shows existing parent-URL waits incompatible with current
iframe detail and an obsolete Apri link replaced by runtime row-click navigation.
These are source observations, not native failures or proof of a runtime bug.

User independently authorizes iframe workflow and the first-row action change.
Preserve real login, first district choice, district/detail/parcel/anomaly URL
patterns, content/visibility assertions, close-or-empty branch, original skips,
config/timeouts/retries and real backend dataset. No runtime or response mock.

## Changes

Resolve the real district iframe content Frame after row selection. All subsequent
detail/parcel/anomaly interactions, checks and URL waits use that same Frame.
First parcel row must be visible before click, replacing the separately authorized
obsolete Apri-link visibility/action. All remaining old assertion arguments and
URL patterns are unchanged. Parent login/list assertions are untouched.
Candidate SHA25692fae5dc66f7372f0a587c310b1ea05117de8ad2c1233ad83f2f7acd1f2d5dbb.

## Characterization matrix

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Real login and first district | Original two cases | Genuine private dataset | None | Native NOT_RUN |
| District detail opens in iframe | Original intent; separate existing iframe smoke | Full original-case execution | Context resolution only | Static review accepted, native NOT_RUN |
| First parcel visibility/open/URL/tabs | Original first case | Real associated current parcel | Authorized visible-row selector | Native NOT_RUN |
| Anomalies navigation/filters/close-or-empty | Original second case | Private dataset and browser run | Frame context only | Native NOT_RUN |
| Lifecycle/containment/cleanup | Reviewed private E2E lifecycle | Dataset extension/readiness review | None | NOT_RUN |

## Metric before / after / delta

Runtime unchanged: NO_CHANGE, no complexity reduction credit. Callable/file
runtime metrics and full-file runtime coverage are not remeasured by this
test-only preparation. No baseline, thresholds, ignore, exclusions or coverage
policy changed. Whole-AST current report NOT_RUN under heavy-process constraint.

## Tests / coverage / ratchet / review

Diff-check PASS. No native collection, test, build, scanner or Graphify launched
for R83 at preparation; ratchet then NOT_RUN, coverage NOT_MEASURED_UNCHANGED_RUNTIME.
Private dataset is not prepared. Independent source review subsequently accepts
STATIC_WORKFLOW_ONLY_ACCEPTED:59checksPASS/16frozen consumed inputs, exact
reconstruction of the authorized diff, unchanged runtime/login/22assertions and
URL/skip/timeout counts. Reviewer stopped; this is not native/readiness acceptance.
R81guarded publication continuation ended exit3/NOT_RUN after240s external Jest;
an earlier continuation launcher guard rejected missing cold pycache_prefix
before any imports/test/gate, preserved separately. Correct invocation was
distinct and did not rerun a native suite. These are not native case failures.

Fresh continuation2 later obtained a quiet slot: actual-main ratchetPASS0findings,
merge-basea51a48dc, driver/ratchet/Graphifyexit0. Graphifyplatform-docs completed
chunk1/1 with no semantic warning,958nodes/1228edges/162communities; graph outputs
ignored. It covers pre-terminal documentary input, not a new runtime graph or
the later receipt-only status annotations. Previous NOT_RUN entries above are
historical, not an inherited current PASS. Full native suites are not replayed.
Receipts in R81root/publication-continuation-2/, old attempts remain separate.

Read-only immutable-URI inspection of the original private SQLite DB confirms
cat_distretti/cat_particelle/cat_utenze_irrigue/cat_import_batches each0rows.
Original SHAebc902bd5479951f0e3971c85fd21423bee368a21f6c2b0c02eea3fa0a71524d
identical before/after; no application imports/seed/schema mutation. A separate
new-copy synthetic dataset preparation was requested; no approval is presumed.

## Separate authorized private fixture preparation

The user subsequently authorizes only a new isolated copy with one synthetic
district and one parcel. Preparation completed once: exit0, existing282table
schemas unchanged, all280other tables/counts/row hashes exact, only two Catasto
tables0→1. The source DB SHA remains identical before/after. Actual fixture
SHA529e7aa4fa4e929581ff70d2e3bf9fb622d925bef8d5c8213baf0d3a4f58a44f;
explicit private UUIDs, district-code join, required/current fields and closed
contained positive-area WKT geometries. No production/schema/runtime/auth or
existing synthetic user/session/device modification. Raw dataset never staged.

Independent raw fixture review616checksPASS, all282schema/index/trigger metadata
identical,280other tables exact, foreign-key0violations and quick-checkOK. The
source SQLite read-only immutable URI and fixture checks leave both DB hashes
unchanged. Classification RAW_PRIVATE_FIXTURE_ACCEPTED_NOT_EXECUTION_READY;
no application/API/ORM/geometry/browser/coverage/native certification. Reviewer
stopped; custody in external private-fixture/ and review/fixture/.

Reviewed lifecycle runner adaptation assigned separately to a preparer owning
only external runner-preparation/. No native launch, source/app imports or
fixture mutation by preparer. Existing private cgroup/namespace/read-only source
and byte custody rules, workers1/retry0/original identities/assertions/timeouts,
quiescent synthetic cleanup and bounded resources remain mandatory. Independent
runner preparation review is required before launch; heavy external Vitest was
confirmed live in this goal turn. No test/scanner overlapping that work.

Runner preparer subsequently completed external source-only adapter and stopped.
ManifestSHA d40ac331dc2c8e23fb468a6f888ca5c5786cc24c19f5ee26a52a15431b6026ea,
adapterSHA0db382ded0282d3e1c97160aba33aea45423a35ab830160f974042c624b3305e.
V4guard copies unchanged; parent-owned cgroup bounds3GiB/512pids/two-core budget,
bwrap network/PID/read-only root+repo/build with isolated/run+private/tmp, real
backend/Next/proxy, original two identities21:5/60:5 and private-copy-only cleanup.
Each case gets a separate once-only invocation; failed or skipped result stops
remaining identities, retains DB/log/trace, never admits campaign source itself.
Current protected2732files and V4serving1405/NFT253/browser8 custody pinned; this
is source preparation, not executed containment/readiness. Coordinator10module
hash/ASTsyntax checks exact, explicitly non-independent and no application import.
Independent runner review owns external review/runner/, currently active.
No native candidate directory/server/browser/cgroup created by preparation.

## Independent runner review and guarded execution disposition

Independent runner review subsequently accepts1775/1775static/hash checks,
17consumed inputs frozen,20sealed files checksum verified. No DB/app import or
launch; reviewer stopped. Cold prefix, exact V4guards, current2732protected and
1405build/253NFT/8browser custody, two original identities21:5/60:5, isolation,
bounded resources and fail-closed lifecycle inspected. This is preparation
acceptance only, not execution readiness, source admission or native PASS.

Coordinator attempts only the finite launch-slot waiter, once, after source/review
checksum checks. It ends exit3 after240s with external Jest/Vitest active;
native driver is never invoked. No native-launch.json, workingDB, native-r83,
server/browser/cgroup or case attempt exists. Both original cases NOT_RUN;
this guard refusal is not a GIS/test failure or retry. Source remains partial,
unstaged and uncommitted. All owned preparer/reviewer/waiter work terminal.
Receipts in external execution-coordinator/, current source/docs checkpoint in
runner-reviewed-stop/. Goal ACTIVE/INCOMPLETE. No new scanner/Graphify attempted
over external jobs; last recorded ratchetPASS0 and docs graph remain historical.

Resume from verified immutable runner/review/fixture and same candidate only
after fresh free-heavy observation and current source/main/HEAD/base custody.
Do not restart on polling timeout or alter pinned HEAD to hide drift. No old
native execution has to be retried: none began. Preserve any future real failure
without repair or source admission until its separate decision and verification.

## Subsequent once-only driver: environmental failure, native NOT_RUN

New evidence directory `execution-coordinator-20261013T165729Z/` preserves its
own guard observations, exact coordinator source copy, invocation and terminal
exit1. Earlier sealed waiter receipts remain unchanged. A fresh quiet slot was
obtained; immutable reviewed driver was invoked once, with a new cold prefix.

The driver created only the private working DB and initial owned scope. Initial
authorized synthetic cleanup completed; case0 resource-limit preparation then
raised `PermissionError(13, 'Permission denied')`. No namespace command, backend,
Next, proxy, browser or native test was launched. `terminal.json` records zero
native attempts, zero namespace launches and both original identities NOT_RUN.
This is an environmental driver failure, not a test FAIL/SKIP; no retry occurred.

Original DB SHAebc902bd and fixture SHA529e7aa4 remain unchanged. Working DB
SHA4cb230cb is preserved after the initial cleanup, not falsely equal to the raw
fixture. Current input custody before/after exact; both owned scopes terminal
with populated0 and no process handles. Read-only diagnosis observes an empty
parent `cgroup.subtree_control`, `memory pids` available and no parent `cpu.max`.
The partial stat diagnostic failure is preserved, with a separate supplement.
No cgroup controller/delegation/permission changes or relaxed bounds applied.

Independent terminal review requested in `review/terminal-20261013T165729Z/`.
Source remains excluded and uncommitted. Before any new native attempt, isolate
and independently review a suitable delegated resource-bound execution scope;
do not reuse exclusive attempt paths, weaken isolation or auto-retry this run.
No current ratchet/Graphify claim follows from this failed environment setup.
Global campaign remains ACTIVE/INCOMPLETE.

Independent terminal review subsequently accepts66/66checks,32sealed files
checksum verified. Classification ENVIRONMENT_RESOURCE_DELEGATION_BLOCKED_NOT_TEST_FAIL.
ReviewSHA2ad4102058a52b5f7995ed9e9fafc01d8098f2c8f5dab1e549f45f87adde224a.
Both original identities NOT_RUN; original/fixture unchanged, working DB exactly
matches initial-cleanup afterimage; driver/coordinator terminal, scopes removed.
The first failing controller filename is an ordering inference, not proven by
the repr-only exception. CPU is available higher in app.slice but not enabled
below it. A dedicated properly delegated CPU/memory/pids hierarchy with suitable
empty parent is a separate prerequisite; no shared-cgroup writes or retries.
Reviewer stopped. This acceptance certifies environmental disposition only.

Separate publication preflight verified quiet guard and prepared custody exact.
`make complexity-ratchet BASE_REF=main` then completed exit0/findings[] against
actual merge-basea51a48dc. It is a change gate, not proof of native execution,
coverage or global baseline freshness. Before Graphify, a new guard refused on
live external Jest/pytest; `make graphify-platform-docs` NOT_RUN, not FAIL/PASS.
No retry or overlapping graph workload launched. Logs/exit receipts preserved
in `publication-environment-stop-20261013T165729Z/`. Updated documentary files
remain uncommitted pending required graph maintenance; partial spec unadmitted.
No new commit/main merge/push or modified baseline/threshold/policy this turn.

## Classification / files changed / commit

PARZIALE_NOT_ADMITTED; source workflow candidate only, not IMPROVED or PASS.
Changed spec plus R83registry/report/PROGRESS. Spec remains uncommitted/excluded;
only documentary evidence is eligible for a separate local checkpoint commit,
whose SHA is recorded externally. No push or main merge.
External r82-distretti-readiness source freeze binds static diagnosis; R83
source-before/current-candidate records preserve authorized bytes and history.

## Residual risks and next slice

No iframe/frame readiness, real data geometry/query, full browser assertion,
auth/device/provider or final-suite certification from static review alone.
Exact source delta independently reviewed, but candidate remains unverified.
Following the separate dataset decision, prepare and independently review a genuine
isolated district/parcel dataset using the private lifecycle. Native two-case
execution requires a fresh free-heavy slot, same assertion/timeouts and retry0.
Preserve failures without automatic repair or admission. Other original skips,
queued R74, workercoverageFAIL, global baseline ambiguity and extreme hotspots
remain open. Global goal ACTIVE/INCOMPLETE, not COMPLETE.
