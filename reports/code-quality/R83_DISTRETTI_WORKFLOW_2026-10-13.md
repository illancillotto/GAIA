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
