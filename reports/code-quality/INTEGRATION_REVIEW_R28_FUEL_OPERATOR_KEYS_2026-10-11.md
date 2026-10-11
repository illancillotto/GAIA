# R28 — Fuel operator keys integration review

## Scope and status

Final verdict: STATIC_ACCEPT_IMPROVED / READY_FOR_FINAL_VERIFICATION. Acceptance
is of exact frozen bounded diff and retained author evidence, not independent
native certification or integration. Whole campaign remains ACTIVE / INCOMPLETE.
One responsibility only: repeated UUID/name/sentinel identity selection in
fuel_analytics primary grouping and per-vehicle related grouping.

## Ownership and preflight

Dedicated review tree GAIA-campaign-20261011-r28-fuel-operator-keys-review,
branch review/complexity-r28-fuel-operator-keys, clean starting HEAD
fed2cc7d0f2ee1dd128b6d11f68655179b9711d7, merge-base/main
55a1b1d35911451e018b662c2acc450bf5994ea2. Authoritative R28 registry read from
Coordinator's pending integration-tree ownership file before review writing.
Sole writable repository path is this NEW report. Runtime/tests/configuration
and other reports are read-only. Coordinator owns publications; no reviewer
commit, import, cleanup, dependency installation or main modification.

Original analytics SHA
e877a34cc20b570306939f9f527048bf77584f6b1d3e78f9b4addf557fc46279 confirmed.
The original owned runtime has no local diff. Native tests, metrics, ratchet,
lint, Graphify and builds NOT RUN by this static reviewer; author owns the sole
native token, followed by a separately admitted independent final verifier.

## Baseline

Inherited accepted R27/R24 evidence, not freshly measured by this reviewer:
fuel_analytics cognitive250/cyclomatic160/LOC348; whole analytics file
LOC1204,28callables,cognitive sum757/cyclomatic sum513. Full-file analytics
coverage634statements264branch outcomes100 in preceding accepted checkpoint.
These overlapping nested/parent metric sums are not independent decisions.

## Original behavioral invariants

- UUID precedence is `is not None`, never UUID truthiness. The selected UUID
  branch reads wc_operator_id twice; it never reads operator_name.
- Only the None branch reads operator_name for truthiness; a truthy name is
  read again for the key. Null/empty names return the closure sentinel without
  a second name read. No attribute caching, trimming, conversion or parsing.
- A zero UUID is still identified. A UUID-shaped legacy string stays a string.
  Whitespace and case remain exact. A literal __no_operator__ legacy name
  deliberately collides with missing/empty names and displays as unknown.
- UUIDs missing from the queried operator map retain UUID identity/display
  fallback, not name fallback. No new exceptions are caught or transformed.
- Only primary grouping consolidates legacy name variants into a loaded UUID;
  per-vehicle related grouping stays unconsolidated. Existing variant collision
  precedence, pop/extend ordering and initial insertion-order ties stay exact.
- Sorting uses net liters, is stable for ties, and related lists retain [:5].
  Top operators currently have NO top10 slice despite an explanatory comment;
  correcting that behavior would be an unauthorized functional change.
- Queries, SQL parameters/order, date bounds, authorization, write behavior,
  response fields and all non-selector analytics phases remain unchanged.
- A nested helper may transiently retain its argument but must not replace
  route-scope log/list/map/operator/vehicle locals. Both original loop variables
  remain live. No query relocation or ORM identity/lifetime shortening.
- The selector is a small typed local responsibility, not a generic manager or
  a renamed mega-function. Exactly two callsite branch replacements, no new
  module/import/layer boundary/cycle, no parameter inflation or LOC growth.

## Characterization review matrix

| Behavior | Existing evidence inspected | Missing/fresh requirement | Review status |
| --- | --- | --- | --- |
| Primary-only consolidation | analytics_characterization and fuel_related_r4 | Frozen NEW real-ORM spec and both-source exact outputs | Pending |
| Related net rank/ties/limit5 | fuel_related_r4 | Keep unchanged and run real-only union | Pending final native verifier |
| SQL order/no writes | fuel_related_r4 | Frozen NEW query expectations including selected key families | Pending |
| UUID/name/sentinel precedence | Existing fuel response and consolidation cases | Null, empty, whitespace, case, UUID-shaped string, zero UUID, sentinel collision, nonmatching UUID/name | Pending |
| Attribute read order | Two original branch copies directly inspected | Exact candidate source comparison; fake getter models not coverage evidence | Original invariant established |
| ORM lifetime/races | Existing r2 deletion snapshot tests inspected | Keep live original locals and run immutable real tests | Pending candidate |
| Auth/date boundaries | Existing public endpoints inspected | Genuine public fuel endpoint verification in frozen NEW spec | Pending |
| Full-file100/runtime custody | R27 report only | Author and distinct verifier fresh raw full-file evidence | NOT RUN by reviewer |

Synthetic extracted-function/getter tests must not count toward full-file
coverage. Source inspection can establish identical attribute expressions but
cannot substitute for genuine public-route/ORM execution or native metrics.

## Integration checks required before verdict

Coordinator admitted frozen source/spec static inspection. Cross-tree hashes:
candidate49b9ffeef7851e12aa4e8a309fb63356d226a6526cffbdaef052d4c9d3fde0d7,
specf899cf78f3842663108e624dc79658d36b5645de03676cab161ad36f21638163.
Exact diff is a6effective-line typed nested helper plus exactly two6→1line
branch replacements; ordinary blank separation, no packing/unrelated edits.
Effective owned span12→8lines, physical branch decisions4→2. No cosmetic
compression or transferred mega-function; genuinely removes duplicated domain
selection. Native parent/helper/aggregate metrics still pending at this point.

Both selected attributes are read twice in original order, None checked before
name truthiness, closure sentinel returned unchanged. New argument log is local
to helper and does not overwrite caller log. Route still retains logs/vlogs,
maps and both loop variables at every external-query boundary. Helper frame
exists only during selection, with no moved DB operation; no callbacks are
introduced. Sentinel becomes a captured local cell but retains same immutable
value and assignment-before-use. Postponed annotations from existing future
import avoid eager _uuid evaluation/side effects; no annotation introspection
or new public signature exists. UUID/name result contract matches ORM model.
No imports/module relationships/cycles/layers/component boundaries change.

Author's actual original union command explicitly names12specs with `-k not
synthetic`, branch coverage and unchanged100threshold. Raw original XML root
342tests/errors0/failures0/skips0; original coverage JSON analytics634/264,
driver49/16, orphan27/10 with empty missing arrays. Existing4excluded analytics
lines are unchanged inherited defensive branches, not newly introduced.
Original raw audit exit0. No extracted-source/getter model credited. Independent
reviewer has NOT executed tests or gate commands and has NOT imported inputs.

Await frozen author report, terminal candidate native evidence and actual
main55a ratchet before final static verdict; distinct final verifier is still
mandatory. Check complete metrics and custody rather than infer from this diff.

Candidate raw XML independently read:342tests/errors0/failures0/skips0; actual
candidate union/audit exit0. Whole coverage raw summaries and empty missing
arrays show analytics632statements260branch outcomes100, driver49/16 and
orphan27/10unchanged100. Four inherited exclusions shift to394/395/889/890,
same source text/semantics, no new exclusion. Source/spec hashes remain frozen.
Native complexity/style/actual-ratchet results still pending here; full campaign
suite/build/E2E completion is not implied by this12spec analytics union.

## Native metric evidence and aggregate interpretation

Author native whole report exit0, raw report independently inspected:

| Metric | Original | Candidate | Delta |
| --- | ---: | ---: | ---: |
| fuel cognitive |250|240|-10|
| fuel cyclomatic |160|158|-2|
| fuel LOC |348|344|-4|
| file cognitive sum |757|749|-8|
| file cyclomatic sum |513|514|+1|
| file LOC |1204|1200|-4|
| file callable count |28|29|+1|

Selector cognitive2/cyclomatic3/LOC6/nesting1/params1, no violations. Parent
nesting4/params5 unchanged, dependency/import counts21 unchanged. Global
1673files20323callables1924errors2740warnings4664findings; no finding-count
reduction claimed. Parent/native file cognitive genuinely reduces, but nested
parent/helper sums overlap and must not be described as physical decisions.

Author's first private metric audit incorrectly required strict reduction of
sum(cyclomatic−1), observed485→485, and STOPped exit1. Failed audit script/log/
inputs preserved; no ratchet was run yet. The flat sum +1 is the new callable
entry: two physical if decisions counted once by parent and again by nested
helper replace four old parent decisions. Normalized aggregate is unchanged
because of this nested overlap, while physical if sites4→2 and actual branch
outcomes264→260 decrease. This is explicit compensated accounting, not an
assertion that every aggregate fell. Gate/audit correction needs separately
recorded Coordinator admission and no runtime/test/baseline change.

## Diagnostic note

Separately authorized non-growth metric audit terminal0, source/spec/report
inputs unchanged; strict cognitive/file-LOC reductions retained, normalized
cyclomatic non-growth plus raw increase limited to callable entry increase.
Native Make complexity-ratchet BASE_REF=main raw command/log/exit0 inspected:
baseline_commit55a1b1d35911451e018b662c2acc450bf5994ea2,findings[]. Ruff check0
and NEWspec format-check0, no source reformat/suppression. Dedicated Operazioni
code Graphify0 rebuilt534nodes1533edges26communities, ignored/uncommitted,
not complexity proof. Original/candidate custody manifests1673paths differ
ONLY analytics; baseline SHA38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95
confirmed. Author SLICE not yet present at last observation; final report freeze
and distinct final verifier gates still pending, no publication authorized here.

Author's first original focus terminated exit1,29PASS/2FAIL, source e877
unchanged. Read-only failure inspection identifies sqlite missing
application_users during real login in both public cases: NEWspec's get_db
override originally began after _auth_headers. Failed spec3bd9358a retained as
focused-original-failed-spec.py with diff/hash/log/XML/exit. Coordinator registry
separately authorized ONLY the fixture correction before a new labeled run.
Independent exact diff inspection of current UNFROZEN spec
f899cf78f3842663108e624dc79658d36b5645de03676cab161ad36f21638163 shows just
one moved line: real _auth_headers now inside try after get_db override.
Finally restoration and all401/403/date/literal assertions are unchanged.
Corrected focus exit file is0; native execution belongs author, not reviewer.
This evidence explains the harness failure without weakening behavior/gates or
changing runtime. Frozen revalidation remains required before final acceptance.

Current UNFROZEN NEWspec contains31cases:24UUID/name cross-products,3name
variants, sentinel collision,12equal-ranking names (one case),2public auth/date
cases. Persisted records and genuine Session.scalars delegation, no fake
response/getter/AST runtime execution; full literal payloads in key matrix,
primary-vs-related distinctions and exact query expressions/parameters.
Existing SQL event-based tests cover actual compiled statement order and
parameters independently. No pending mutable input is treated as accepted.

A read-only status query using this review-tree absolute report path while CWD
was the integration tree returned Git128/outside-repository. This is a static
observation invocation error, not an application/native failure. No gate was
run or retried and no input changed because of it.
A reviewer tool wait with invalid handle returned not-found; it did not observe,
restart or alter author's native session. No command/input changed.
A read-only JSON diagnostic assumed callables were nested under file stats,
returned TypeError, and was corrected to the actual top-level callables array.
No native report/test/gate rerun or input edit followed this observation error.
A no-op report patch failed on unmatched context; the actual evidence addition
was applied against the existing Diagnostic note header. No runtime input changed.

## Verdict

STATIC_ACCEPT_IMPROVED / READY_FOR_FINAL_VERIFICATION. Frozen author report
44ea04529737754c28e9fc53bf9ce62b06c7d4a5c6dfef897401324157e073a6 read completely
after terminal notice and verified against raw retained evidence. Source49b9 and
specf899 hashes unchanged; author only source/NEWspec/NEWreport dirty, no commit.
Earlier pending/unfrozen observations in this report describe review chronology,
not the final outcome. No additional behavioral assertion deficit was found
for these two replaced branches; immutable lifetime/SQL/other-domain tests remain
required and present in both actual342case runs.

Real improvement: duplicated identity policy2→1, physical if sites4→2, parent
cognitive250→240 and file cognitive757→749, file LOC1204→1200. Raw cyclomatic
sum513→514 is explicitly compensated new-callable entry, not a hidden reduction;
normalized485→485 remains unchanged. Small helper2/3/6 below thresholds, no
debt shift, other callables unchanged, no baseline/config/threshold inflation.

Author explained original fixture and private-audit failures are retained and
separately admitted corrections do not weaken behavior or change runtime
inputs. Tests public/persisted with real queries, whole-runtime full100, actual
main55a ratchet0/findings[], style0 and dedicated code graph0 were read as
author evidence only. Reviewer ran NO native gates or import and wrote ONLY this
report. Independent final verifier fresh original/candidate gates and Coordinator
per-publication ratchets remain mandatory. No merge/commit/main/push performed.

Residual debt remains fuel240/anomalies239, full campaign5>300/17>200/55>100
before this bounded change. Global Error/Warning/finding counts unchanged;
historical globalFAIL30 separate unresolved provenance. Broad final suites,
coverage for other domains, frontend build and deployed E2E still uncertified.
Stop this reviewer after frozen verdict; no second responsibility authorized.
