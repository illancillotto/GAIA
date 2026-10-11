# R31 — Independent session distance review

## Ownership and admission

Reviewer owns ONLY this NEW report. Original application/test files are
read-only. Registry established before activation:
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R31_SESSION_DISTANCE_2026-10-11.md`
in the integration checkout.

Review worktree:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r31-session-distance/review-worktree`.
Branch `review/complexity-r31-session-distance`; HEAD
`6089b05e1c047f388badf8f9b53caa18a1babf6e`; actual main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Initial tree and source diff clean.
Original analytics SHA256:
`49b9ffeef7851e12aa4e8a309fb63356d226a6526cffbdaef052d4c9d3fde0d7`.

Initial stage: STATIC_PREPARATION_ONLY; NO HEAVY TOKEN. No native certificate
was issued at that stage. Final status: **IMPROVED / ACCEPT** after separate
Coordinator native admission and the independent gates below. Reviewer never
mutated/imported source or tests, committed, installed dependencies, invoked
browsers, cleaned caches or delegated children.

## Baseline and target callable

Two identical nested policy implementations appear at original analytics
lines452 and794, respectively in fuel_analytics and km_analytics. Fuel calls
its local helper twice per selected session. Km calls its helper for period,
vehicle, attributed operator, total and duration-extreme presentation; counts
depend on attribution and eligible extremes. Preserve every call site and its
execution position, not just the final numeric result.

Registry baseline (NOT a fresh reviewer native measurement): each nested helper
cognitive5/cyclomatic5/LOC7/params1/nesting1; fuel240/158/344 and km44/37/137.
Fresh author's native before report is frozen and independently revalidated.
Reviewer independently generated the whole candidate report after admission;
it exactly reproduces every candidate file/callable object and the aggregates
below. Reviewer did not substitute original source into the read-only tree.

Single allowed change: one typed pure session-distance policy in SAME file,
replace the two implementations and their original calls. No endpoint-wide
refactor, memoization, parameter pre-evaluation, query or domain-rule change.

## Behavioral invariants reconstructed independently

1. Evaluate route_distance_km by truthiness, NOT by non-None or positivity.
   A truthy positive or negative route value wins over odometers. Return its
   float conversion unchanged; no negative clamp on the route path.
2. Truthy route reads the route attribute TWICE: truthiness read, return read.
   Neither odometer is accessed. Coercion exceptions propagate unchanged.
3. Falsey route (including numeric zero and None) falls back to odometers.
   Read end first; if end is None, skip the start attribute entirely and
   return0.0. Present end reads start for its None check; start None returns0.0.
4. If both checks succeed, read/convert end AGAIN, then read/convert start
   AGAIN, subtract in that order and return max(0.0, difference). Do not move
   coercion into the checks, snapshot both attributes or reverse conversions.
   End conversion failure must prevent the second start read/conversion.
5. Negative odometer delta returns0.0; zero start remains a valid odometer,
   unlike a truthiness guard. Fractional Decimal arithmetic is converted to
   float BEFORE subtraction, preserving existing rounding behavior.
6. No new fallback for malformed values, defensive exception swallowing,
   finiteness validation, normalization or route-distance flooring. Unusual
   in-memory conversion/attribute behavior remains the same by body/order
   equivalence; public fixtures must obey actual persisted model constraints.
7. Original Numeric(12,3) route/end are nullable; start Numeric(12,3) is
   NONNULL. A missing-start public persisted fixture is therefore not a valid
   native HTTP characterization. Such helper probes can supplement proof,
   never justify faking route data or replacing real-route coverage.
8. Fuel selects logs first and closed/non-open usage sessions second using
   inclusive from/to timestamps. Its distance contributes to vehicle totals
   and GAIA-user/legacy-name attribution, downstream consumption and existing
   nonpositive-distance semantics. No query/call/order/rounding mutation.
9. Km selects non-open sessions within the same inclusive window, sorts
   period keys and vehicle/operator distance rankings as before, retains
   zero-distance session counts and original top10 truncation. Total/average
   and longest/shortest km use the same policy. Duration logic is untouched.
10. Route decorators, signatures, Depends(require_active_user), module access,
    DB reads, transaction/lifetime semantics, response schemas and exceptions
    must remain exact. No schema, migration or mutable global state.

## Static characterization matrix — historical preparation

This preparation matrix records the initial NOT RUN state, not final results.
Its named old tests and all NEW cases have subsequently run in the independent
complete union. The terminal native matrix below supersedes pending cells.
Missing originally meant focused evidence was required, not that the old suite
had never covered the behavior.

| Behavior | Existing test inspected | Missing evidence | Added | Result |
| --- | --- | --- | --- | --- |
| Positive route overrides odometers | test_km_uses_route_distance_over_odometer_and_retains_duration (r2) | Both public endpoints, full outputs | PENDING frozen spec | NOT RUN |
| Numeric zero route falls back | Existing positive odometer HTTP cases | Explicit persisted zero route in both endpoints | PENDING | NOT RUN |
| None route falls back | test_km_time_series_uses_odometer_diff | Explicit public fuel/km policy matrix | PENDING | NOT RUN |
| Truthy negative route stays negative | R14 negative operator-distance cases inspected | Both endpoints and downstream nonpositive behavior | PENDING | NOT RUN |
| Negative odometer delta clamps | No dedicated persisted public distance case verified | Both endpoints plus zero retained count | PENDING | NOT RUN |
| End None returns0 | test_fuel_storno_only_group_has_null_positive_means; missing-duration km case | Focused persisted endpoints with ordinary duration | PENDING | NOT RUN |
| Fractional Decimal/coercion/rounding | Existing fuel and km decimal fixtures | Deliberate route-vs-odometer fractional case | PENDING | NOT RUN |
| Start None/attribute read/float error order | No real persisted case possible for start None | Supplemental helper probes and exact body/call-site diff | PENDING | NOT RUN |
| Inclusive dates and status filtering | R28 public fuel query/auth test; existing km period HTTP | New policy fixtures exclude open/out-of-window data | PENDING | NOT RUN |
| Query sequence/no DB mutations | R28 full-response/query recorder | New spec query snapshots before/after, source review | PENDING | NOT RUN |
| Public auth/permission/validation | R28 anonymous401/module403 fuel; km invalid422 | Retained real login, km permission review | PENDING | NOT RUN |
| Attribution/ranking/extremes | Existing km linked-driver/top/extremes and fuel attribution | Assert affected distance-bearing public fields | PENDING | NOT RUN |
| Entire runtime coverage | Historical R28 real-only12spec342 union | Fresh original/candidate independent native full-file100 | PENDING | NOT RUN |

The original union command is retained at
`/home/cbo/.cache/gaia-campaign/20261011-r28-final/union-candidate.command`.
Its report config includes ENTIRE analytics.py, _driver_mismatch.py and
_orphan_session_operators.py with branch measurement; threshold100 unchanged.
Preserve all12 original test bytes and real-only selection. No copied runtime,
fake auth, synthetic fixtures, private route-handler execution solely for
coverage, new ignore/exclusion/pragma/skip or weakened assertions permitted.
Pure helper tests are supplementary, not substitutes for persisted HTTP cases.

## Frozen admission and independently reviewed changes

Author terminal FREEZE SHA256
`f33d8a4040d055fa0d3c30402c814d3433eed9c06d29ea0e5a3bf38adae08281`,
140members independently rehashed BEFORE native gates. Author heavy token
RELEASED; Coordinator imported exact source/spec/author report into the review
tree and granted reviewer the exclusive serial token. Root remained static.

Inputs exact before/after:

- analytics `dd7a8bcd259efc1ef9853bef07a69b2123eb1cedfbcf78aa1eb0a8b645b48a2e`;
- NEWspec `51ce977a2da5059c75493bf7f05550f7788265a3e8dc7c6980759f4a807ae174`;
- author report `c74aacf70f4fa2c9a7a6be6e6a4a389d9e233fe187a7ef4b55ac24417bf4a0f8`.

One typed pure `_session_distance_km(session: VehicleUsageSession) -> float`
replaces both original nested bodies in SAME file. Seven original call names
changed; their arguments, call positions, loops and query/response paths remain
exact. No import, service, schema, query, auth, mutation or cache added.

Reviewer independently normalized ONLY new parameter/local identifiers
session→s/distance→diff and proved the shared definition's complete signature
and body AST identical to EACH original. Removing the two original nested
definitions and the new shared definition, and normalizing ONLY the changed
call names, proves COMPLETE module AST equality. Thus queries, coercion/read
order, short-circuiting, API decorators, auth, transactions and all untouched
analytics behavior are preserved, beyond the public test projections.

## Metric before / after / delta

Fresh author before report, frozen before edits; fresh independent candidate
native report. All1672other file objects and all their callable objects exact,
same scope/engines, no parse/exception errors. Candidate objects exactly match
the independently rehashed author after report.

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| fuel cognitive / cyclomatic / LOC |240 /158 /344 |235 /154 /337 |-5 /-4 /-7 |
| km cognitive / cyclomatic / LOC |44 /37 /137 |39 /33 /130 |-5 /-4 /-7 |
| Policy implementations |2 |1 |-1 |
| Policy cognitive / cyclomatic / LOC sum |10 /10 /14 |5 /5 /7 |-5 /-5 /-7 |
| Whole file cognitive sum / max |749 /240 |734 /239 |-15 /-1 |
| Whole file cyclomatic sum / max |514 /158 |501 /154 |-13 /-4 |
| Whole file sum(cyclomatic-1) |485 |473 |-12 |
| File effective LOC / callable LOC |1200 /1266 |1193 /1245 |-7 /-21 |
| File callable count |29 |28 |-1 |
| Native statements / branch outcomes |632 /260 |625 /256 |-7 /-4 |
| Global file / callable count |1673 /20323 |1673 /20322 |0 /-1 |
| Global error / warning / findings |1924 /2740 /4664 |1924 /2740 /4664 |0 |

New helper5cognitive/5cyclomatic/7LOC/nesting1/params1, no violation.
File cognition falls2.00%, LOC0.58%; dependencies/import counts21 unchanged.
Nested decisions are counted inside parents AND nested callable records:
aggregate -15cognitive/-12normalized decisions is NOT15independent rules or
12physical branches removed. Physical duplicate policy removal is one7LOC body;
native branch-outcomes decrease4. This is genuine duplication reduction, not
simply moving both copies or exporting a mega-function. Extreme tail remains
5>300/17>200/55>100, not solved by this small slice.

## Independent native tests and coverage

| Gate | Native result | Scope |
| --- | --- | --- |
| union-persisted |0,366PASS,0failure/error/skip,18deselected |Old12 + NEW persisted20/auth4; `-k 'not synthetic and not unflushed'` |
| union-complete |0,374PASS,0failure/error/skip,10deselected |Old12 + allNEW32; `-k 'not synthetic'` |
| Scoped Ruff |0 |Owned runtime and NEWspec |
| NEWspec format-check |0 |Read-only Ruff format-check |
| make lint-backend |0 |Actualmain55a changed Python scope |
| make style-ratchet |0 |Actualmain55a |
| Whole complexity-report |0 |1673runtime files,20322callables |
| make complexity-ratchet BASE_REF=main |0/findings[] |Actual baseline_commit55a |
| Independent raw audit |0 |JUnit identities/counts, coverage maps, AST report, metrics, Graphify |
| Admission/final custody and diff-check |0 |2073protected paths,140author members, main/baseline/input exact |

Each genuine persisted-only AND complete union measures ENTIRE analytics.py:
625/625statements and256/256branch outcomes,100% each,0missing/partial. Existing
_driver_mismatch49/49statements16/16branches and _orphan_session_operators27/27
statements10/10branches also100. All three runtime summary/line/branch maps
exactly match frozen author candidate evidence; both reviewer union counters
equal, proving the8unflushed supplemental HTTP cases add NO coverage.

Four existing analytics pragma lines remain unchanged; no new exclusions,
skips, ignore or threshold reduction. Branch100 does not imply all boolean
condition combinations: unpersistable start-None and malformed Numeric probes
remain explicitly supplemental, not valid stored data. They use actual login
and actual public routes with unflushed ORM state, never fake auth or copied
runtime. Persisted coverage reaches100 independently without those8cases.

Public persisted cases check truthy/negative route, zero fallback, None end,
zero/negative/fractional odometers and all km period/vehicle/operator/total/
extreme fields; fuel affected distances and nonpositive operator semantics.
They observe exact attribute trace:2fuel/6km policy evaluations for each
single-session fixture. Four genuine login cases retain401/403/200 behavior.
Legacy query/filter/order/attribution tests remain byte-exact and run in unions;
complete-module AST equality independently protects every query and call site.

JWT21-byte-key warnings remain visible, not suppressed. No new unexplained
native failure. Live sessions40834/87105/23793/77503/56035 were polled to native
terminal, never restarted because observation yielded. Immutable private
runner/union scripts were never edited while live. All logs/argv/cwd/exits/
JUnit/coverage/report/custody/storage live on new isolated SSD review-evidence;
minimum100MiB root checked before each gate. No install/build/browser/cleanup.

## Ratchet and baseline provenance

Actual `make complexity-ratchet BASE_REF=main` PASS0/findings[], baseline_commit
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Canonical baseline38e6b794 exact;
no baseline command, threshold, exception, scope or shared tooling change.
Global historical30findings are separate and NOT rerun or certified here.

Original author's native374 passed0/full100 while its outer observer failed2
after editing a LIVE wrapper. Reviewer verified retained PROCESS_DEVIATION,
native/log/XML/maps and Coordinator's separate immutable recovery. Outer2
remains a disclosed failure, not reclassified PASS. Author persisted-before366
completed0/full100 before runtime admission. No equivalent reviewer deviation.

## Graphify

Reviewer verified author's frozen native0 `make graphify-operazioni-code`
artifacts: parseable module graph535nodes1534edges, shared helper node and
EXTRACTED calls from BOTH route nodes. All graph bytes are members of the
140-member author freeze checked before/after gates. Reviewer did NOT claim
to regenerate this graph; Coordinator's integration maintenance remains
separate. Graph is impact evidence, never proof of coverage or complexity.

## Classification and disposition

**IMPROVED / ACCEPT** for this SINGLE duplicate policy consolidation.
Real whole-file/policy cognition and LOC reductions, behavior preserved by
public native tests plus exact AST transformation, genuine persisted full100,
actualmain ratchet0, no debt transfer or baseline inflation.
Coordinator fresh root gates/publication still required. Whole original
backend/frontend/worker campaign ACTIVE / INCOMPLETE; this is not global closure.

## Files changed / commit

Only `reports/code-quality/REVIEW_R31_SESSION_DISTANCE_2026-10-11.md`.
No commit, source/test import or application modification by reviewer. Frozen
input imports were performed by Coordinator before native admission, not review.

## Residual risks and recommended next step

- Truthiness vs None, negative route clamp and repeated attribute reads are
  easy accidental behavior changes despite the tiny duplicate body.
- Persisted database limits must not be bypassed to manufacture coverage.
- A single shared helper removes duplication, not the endpoints' broader debt.
- Native backend scope is13pertinent specs with genuine SQLite/auth; complete
  backend/frontend/worker/build/E2E/production/PostgreSQL behavior is not certified.
- No blocking review finding remains. Coordinator may rehash final review
  freeze and publish only after fresh serial root gates. Do not extend this
  accepted responsibility to another hotspot without new ownership/admission.

## Final evidence and token release

Independent raw audit `../review-evidence/audit.json`, admission/final custody,
original frozen author manifest and final reviewer manifest
`../review-evidence/FREEZE.json`. All native reviewer gates terminal0 before
freeze. Final source/spec/report bytes preserved; heavy token RELEASED after
manifest publication. Reviewer stops here; no further runtime work or commit.
