# R27 — Inactive Vehicle Anomalies: Analysis and Admission Proposal

## Ownership

- Author worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261011-r27-inactive-vehicle`.
- Branch: `refactor/complexity-r27-inactive-vehicle-anomalies`.
- HEAD: `6ab78dc42f33948d00410242e8a6a49f67a1eb90`.
- Merge-base with main: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Initial status: clean. Coordinator registered exclusive ownership before activation.
- Initial admission authorized only this report and small private static evidence.
- Coordinator subsequently admitted implementation of the new characterization
  spec and a small private candidate shape, not runtime or author native gates.
- Runtime and existing tests remain read-only. The new spec
  `backend/tests/test_operazioni_inactive_vehicle_r27.py` is now frozen for the
  Coordinator's first native gates; its successful execution remains unproven.
- Frozen R19 author tree, main, shared files and baseline are outside ownership.

## Baseline

Runtime: `backend/app/modules/operazioni/routes/analytics.py`.
SHA-256: `e877a34cc20b570306939f9f527048bf77584f6b1d3e78f9b4addf557fc46279`.

Coordinator-supplied accepted metrics, not remeasured by this analysis:

| Scope | Cognitive | Cyclomatic | Effective LOC |
| --- | ---: | ---: | ---: |
| `anomalies_analytics` | 239 | 112 | 320 |
| Whole analytics file | Not remeasured | Not remeasured | 1204 |

The original inactive-vehicle block occupies physical lines 1245–1295 and
49 nonempty, noncomment lines. Each source-specific projection loop occupies
12 such lines. A source-only `ast.parse` confirmed these spans; it is not a
native complexity measurement.

Coordinator reports a fresh original gate in
`~/.cache/gaia-campaign/20261011-r27-original/`: exact 276 real-only tests,
10 specs, no skips, analytics 634 statements/264 branch outcomes full 100%,
unchanged driver 49/16 and orphan 27/10 full 100%; raw audit and custody pass.
The author did not execute, reproduce or independently certify that native gate.

## Target Callable and Responsibility

Only family 6, `inactive_vehicle`: find logs and usage sessions on inactive
vehicles, and project them into high-severity anomalies. Other families, date
parsing, authorization and response aggregation are not refactoring targets.

The duplicated responsibility is the common anomaly envelope and label
fallback, not the two distinct database sources. Reaching cognitive 200 is a
preference, not permission to extract additional families or change lifetimes.

## Behavioral Invariants

### Query sequence and gates

1. Enter only when `anomaly_type` is falsy or exactly `inactive_vehicle`.
2. Always query complete `Vehicle` entities with `is_active IS FALSE`; collect
   their IDs with the original comprehension. Do not retain these vehicles in
   a new loader/context, or replace the entity query with scalar IDs.
3. With no inactive IDs, issue no logs, sessions or second vehicle query.
4. With inactive IDs, issue the fuel query first, then usage-session query.
   Each uses the existing inclusive lower/upper timestamps and `IN` IDs;
   neither has status constraints, sorting, limit, pagination or deduplication.
5. Compute `all_vids` as the existing union, without filtering falsy IDs.
6. Issue the second full `Vehicle` query even if both source lists are empty
   and `all_vids` is empty. Preserve the original SQL predicate and parameters.
7. Preserve both query-result lists, vehicle map, and route-scope `v`, `log`
   and `s` assignments. No loader extraction, eager mapped objects or generator
   lifetime changes are proposed. The map-construction loop is not replaced
   by a comprehension: that changes the outer `v` binding.
8. Preserve autoflush and transaction boundaries. This block performs no
   explicit mutation, flush, commit, rollback or external call.

### Projection and evaluation

Process every fuel row in returned order, then every session in returned
order. Do not interleave by date or vehicle, or deduplicate. Resolve `v` before
constructing each item. Keep the existing field evaluation order:

| Field | Fuel | Session |
| --- | --- | --- |
| `id` | `inact_v_log_` plus row ID | `inact_v_sess_` plus row ID |
| `type` / `severity` | `inactive_vehicle` / `high` | Same |
| `description` | `Rifornimento registrato su mezzo dismesso` | `Sessione d'uso registrata su mezzo dismesso` |
| `entity_id` | String vehicle ID | String vehicle ID |
| `entity_label` | Plate, otherwise code, otherwise string vehicle ID | Same |
| `detected_at` | `fueled_at.isoformat()` | `started_at.isoformat()` |
| `details` | Liters first (`float(liters or 0)`), then vehicle code | Vehicle code only |

The fallback short-circuits: do not eagerly read code when the plate is truthy,
or stringify the vehicle ID for a label when an earlier fallback succeeds.
Do not cache label/code per vehicle: multiple rows can observe different ORM
attribute states. Do not read timestamp, liters or code before their original
field position. Null/empty plate and code, zero/negative liters and missing map
entries retain their original semantics; nullable liters/code outside the
persisted schema are not manufactured as runtime-coverage proof.

The existing route collects all counts before stable severity sorting. All
inactive-vehicle items are high, so ties retain family/source/query-row order.
The response remains the original Pydantic construction, fields and count maps.

### ORM lifetime is observable

`test_operazioni_driver_mismatch_lifetime.py` uses actual SQLAlchemy readers,
weak references and a distinct committed writer. It proves unfiltered queries
reuse a retained driver vehicle (`BEFORE`) whereas inactive-only queries can
read the newly committed plate (`AFTER`). Moving the entire inactive block into
a helper changes route-scope strong-reference lifetimes and is not justified
merely because ordinary JSON/coverage tests pass.

## Characterization Test Matrix

Results below distinguish source evidence from execution. Existing behavior
was inspected in tests; only the Coordinator gate is freshly executed evidence.

| Behavior | Existing test | Missing | Proposed new real/public cases | Result |
| --- | --- | --- | --- | --- |
| Fuel then session, IDs/details/counts and older fuel exclusion | `test_inactive_entity_anomalies_include_fuel_and_sessions_in_period` in R2 | Full literal session payload; exact descriptions/labels | One literal two-source response with all fields | Existing source inspected; new not admitted |
| Four queries when IDs and matching session exist | Inactive-only lifetime control | Empty-source SQL and bound params | No inactive IDs: one query; inactive IDs/no matches: four queries including empty second vehicle SELECT | Existing source inspected; new not admitted |
| Inclusive date endpoints, source-specific timestamp | General date tests concern driver mismatch | Both inactive source boundaries, just outside edges | Both sources at min/max of selected day, plus one microsecond outside; compare literal IDs and SQL params | Not executed |
| Only inactive vehicles; any usage status | R2 covers one inactive vehicle | Active control and open/closed/cancelled status matrix | Persist active/inactive vehicles and session statuses, asserting no invented status filter | Not executed |
| Exact fallback priority | Driver-mismatch fallback tests are a different family | Both source kinds, plate/code/UUID and empty strings | Real vehicles with truthy/empty/null plate and truthy/empty code; exact response labels | Not executed |
| Numeric details and their ordering | R2 positive liters | Zero/negative Decimal values and session key absence | Persist supported values, assert float numeric values, fuel key order and no session liters key | Not executed |
| Preserve source iteration order | R19 ordering test covers driver mismatch | More than one row per inactive source | Observer delegates real `scalars` and controls returned persisted-row order; assert logs before sessions and no timestamp re-sort | Not executed |
| Stable ties across families | `test_original_unfiltered_high_severity_ties_keep_family_order` in R19 | Fuel and session of same inactive vehicle amid several high families | Public unfiltered route with real persisted rows; assert exact family/source order and count-map insertion order | Existing source inspected; new not admitted |
| ORM retained/reloaded plate across writer commit | Three lifetime tests | Reload/lifetime boundaries of the two inactive queries | Keep all existing lifetime tests; add distinct writer before second vehicle load and later inactive-operator query with weakref boundary assertions | Existing source inspected; new not admitted |
| Public auth/type filtering and unsupported/empty type | Endpoint tests + R2 unsupported type | Specific endpoint controls for new slice | Existing login/client helpers; inactive filter, unfiltered empty type, unsupported type, unauthenticated and inactive auth user | Not executed |

Use the original database/driver fixtures and persisted model factories.
Observer wrappers must delegate to actual SQLAlchemy queries; no fabricated
scalar lists, source execution, injected globals or test-only ORM objects.
Descriptor access tracing, if necessary to supplement source review, must be
reported separately from real persisted coverage evidence. Public API tests
must preserve the route's current auth behavior rather than impose a new module
permission rule. Fixed dates are safe only with explicit fixed query dates.

Minimum prerequisite batch: exact empty-query contracts, both-source literal
payload/fallback/date boundaries, multi-row ordering, and existing three ORM
lifetime tests. Remaining cases can be parametrized in the same single spec;
do not consolidate or weaken existing specs. Full-file coverage must continue
to be obtained from the entire real-only union, not the new spec alone.

## Changes Proposed, Not Admitted

Keep all queries, guards, map construction and both projection loops in the
parent exactly as above. Consider one domain-specific small common item mapper,
not a generic dispatch engine, context or new module. The parent must still bind
`v`, `log` and `s`; only its two `AnomalyItem` constructions become calls.

One possible mapper receives a typed record union, optional vehicle, and a
literal source discriminator. It shares type/severity/entity ID/label and emits
source-specific identifier, description, timestamp and details. Attribute
selection must occur lazily at its original field position. Merging a fuel
liters dictionary with the common vehicle-code dictionary is allowed only in
that order; reading vehicle code first is not equivalent.

An alternative receives the original already-evaluated item identifier and
description, plus record and vehicle (four parameters). This avoids duplicate
description/ID decisions but still needs timestamp/details discrimination.
Identifier evaluation must remain immediately after `v` resolution and before
any remaining record/vehicle attribute evaluation.

Neither alternative is an implementation admission. Exact AST/source budgets
must first establish that the chosen shape is genuinely simpler and fits the
non-growth constraint. No wrapper merely containing the old 49-line block is
acceptable. No additional responsibility may be extracted to recover a target.

## LOC and Decision Budget — Important Limitation

- Original two projection loops: exactly 24 effective lines total.
- Preserve the two loops, two `v` assignments and two appends: minimum six
  ordinary effective lines, leaving at most 18 lines for the entire new mapper
  and any needed imports/type aliases/constants.
- The existing typing import can be extended without adding a physical line;
  separate aliases/metadata constants consume the same 18-line budget.
- A readable typed mapper with four parameters, named fields, lazy timestamp
  selection and ordered details tends to consume 19 or more lines before
  multiline call sites. A three-parameter discriminator reduces duplication,
  but adds source selection decisions. Exact formatting is not yet implemented.
- Do not join unrelated statements, remove unrelated lines, suppress formatting,
  delete behavior, move helpers into another file or subtract comments to make
  this arithmetic appear green. Even +1 effective file LOC fails admission.
- Sharing label fallback removes one physical copy of that decision chain.
  Timestamp/details/description discrimination adds decisions back. The entire
  candidate's physical decisions and aggregate metrics must be counted; label
  deduplication alone is not proof that aggregate branching decreased.
- The mapper-only shape cannot honestly promise parent cognitive <=200: query,
  comprehension and loop decisions remain. A coherent reduction above 200 can
  still be useful, but it cannot be claimed before the native report.

**Recommendation:** admit missing characterization first, then permit a bounded
private source-only draft for this exact projection responsibility. Before any
runtime edit/native gate, review its effective LOC and physical decision count.
If no readable shape fits <=1204 file LOC with nonincreasing aggregate debt,
classify the runtime attempt `NO_SAFE_CHANGE` and retain characterization only.
Do not relax the LOC condition or widen the slice silently.

## Metric Before / After / Delta

No runtime candidate was written. Runtime SHA and working copy remain original.
After metrics and delta are therefore unchanged, with no new measurement or
complexity-reduction credit. The supplied 239/112/320 parent and 1204 file
baseline remain the admission references, not an inferred improvement.

## Tests / Coverage / Ratchet

Author executed no pytest, coverage, native report, ratchet, lint, Graphify,
dependency installation, commit or branch changes. Coordinator original gate
is recorded separately above. No threshold, baseline, ignore, exclusion,
coverage configuration or existing test was changed.

Required sequence after explicit admission: new-spec characterization on original,
real-only full-file union/100%, source-only candidate budget review, runtime
refactor, same tests/100%, native before/after/aggregate report, Ruff, exact55a
ratchet, independent review and dedicated `make graphify-operazioni-code` under
the Coordinator's exclusive heavy token. Stop on the first unexplained failure.

## Classification

`ANALYZED_NOT_ADMITTED`. This is an analysis report, not `IMPROVED` or a completed
slice. Current evidence does not establish a runtime shape satisfying all
constraints. The full campaign remains active/incomplete.

## Files Changed / Commit

This report and the new characterization spec. A small private candidate is
outside the repository. No commit authorized or created by the author.

## Residual Risks and Recommended Next Slice

Highest risks are ORM lifetime changes hidden by fixture-held models, empty-set
SELECT elimination, fallback/timestamp/details eagerness, and positive file-LOC
delta disguised as formatting. Reaching an extreme-tail target requires another
separately owned responsibility only after this slice's review; it is not part
of the present proposal.

Next action for Coordinator: review the missing characterization admission and
the 18-line shared-projection budget, or explicitly reject the runtime shape.

## Phase 2 — Characterization Implemented, Runtime Shape Rejected Statically

Coordinator explicitly admitted the new spec after reviewing report SHA
`5564996c89e6ee2bab2d7481d4e8b12bf88e9cf1205dab7ef3160b9f0c4cbf5f`.
The earlier test matrix's `not admitted` entries describe the initial proposal,
not the current spec-write permission. No test result is upgraded to PASS.

### Frozen spec

- File: `backend/tests/test_operazioni_inactive_vehicle_r27.py`.
- SHA-256: `d4790f9121ec81f198804557ed06f47b49d24ec94642dec2be7b67e90beb021b`.
- Static AST: 14 test functions, 35 expanded parametrized cases. This is not
  pytest collection or execution evidence.
- Database/driver fixtures and persisted factories are the existing canonical
  analytics fixtures. All direct tests call the actual registered route function.
- Cases cover the complete literal two-source response, SQL query order and
  parameters, one-query empty/active-only control, four-query empty source result
  including empty second vehicle SELECT, five plate/code fallback variants,
  three supported Decimal values, four inclusive/outside timestamp cases,
  three usage statuses, active-vehicle exclusions, three inclusive type guards,
  eight unrelated/unsupported type guards, controlled real-row iteration order,
  cross-family high-severity ties/count insertion order, authenticated public
  endpoint payload/type alias, and unauthenticated endpoint rejection.
- Query observers delegate every scalar query to the original real Session.
  The ordering observer only sorts actual persisted result rows; it never
  substitutes fabricated source entities or evaluates copied route code.
- Existing three distinct-writer ORM lifetime tests are untouched and remain
  required in the union. Fixture-held models in the new tests do not replace
  those no-strong-reference lifetime controls.
- No new missing-map/nonnullable-null synthetic coverage is claimed. Per-field
  descriptor access count is protected by source review and existing lifetime
  controls, not inferred from ordinary fixture-held entity results.

### Private candidate and exact source budget

Private shape:
`~/.cache/gaia-campaign/20261011-r27-author/projection-candidate.py`.
SHA-256: `2c486e7c2fa08e446f9dd5869d382c5ec9b961ebbf8ae98af92ea629b510b257`.
It was parsed, never imported/executed or copied into runtime.

The four-parameter typed mapper shares the common envelope and lazy label
fallback. Identifier is evaluated in the original parent position. Timestamp
selects the original attribute at its original field position. The ordered
details expression constructs optional fuel liters first and unions the common
vehicle-code dictionary afterwards. Python primitive string-key dict union
preserves the original fuel `liters, vehicle_code` and session-only code order.

Actual static accounting with ordinary readable multiline arguments:

| Budget | Original | Private draft | Delta |
| --- | ---: | ---: | ---: |
| Two source loops | 24 | 16 | -8 |
| New mapper | 0 | 23 | +23 |
| Total noncomment lines in touched responsibility | 24 | 39 | **+15** |
| Decision increments, including retained loops | 10 | 9 | -1 |

Decision accounting explicitly includes the source discrimination: original
two `For`, two three-value `or`, one two-value `or`; draft retains two `For`,
one three-value `or`, one two-value `or`, and adds two conditional expressions.
Each `or` contributes its value count, matching the current scanner's syntactic
decision weighting. These are static syntax counts, not native cognitive,
cyclomatic or ratchet results.

The mapper preserves parent locals and query phases. New `isinstance` calls
inspect type where the old code did not. Current mapped classes have no custom
instance-check behavior or subclass mapping in this source. Nevertheless,
future/custom class observation would need review; a static type-selection
argument is not automatically equivalent for arbitrary synthetic objects.

**Decision: do not admit this candidate.** File LOC would become 1219 if no
other lines changed, violating <=1204. A formatter can add further wrapping;
it cannot cure the positive delta. No one-line packing, unrelated subtraction,
comment deletion, helper relocation or ownership/query changes were used to
hide the 15 lines. Native metric or coverage execution on this candidate is not
requested. Runtime outcome is `NO_SAFE_CHANGE` for this shape, not `IMPROVED`.

### Proposed native argv (Coordinator only)

From the author worktree's `backend` directory, with the integration venv Python
and private isolated environment/output paths selected by Coordinator:

```text
<integration>/backend/.venv/bin/python -m pytest -q -p no:cacheprovider
  tests/test_operazioni_inactive_vehicle_r27.py
  tests/test_operazioni_driver_mismatch_lifetime.py
```

Expected static case count is 38 (35 new plus existing three lifetime cases),
not an assertion that this count has been collected or passed. If this first
gate succeeds, rerun the exact frozen original ten-spec real-only union plus
the new spec: expected 311 cases, selector `-k "not synthetic"`, original
full-file coverage configuration and unchanged 100% threshold. Record actual
statement/branch totals and native exit; do not infer union success from focus.

Run Ruff check and new-spec format check under the same serial ownership.
No author lint/format, pytest, coverage, complexity command or Graphify was run.
On first unexplained failure stop and retain the frozen source/results; a
specific test-only correction needs Coordinator authorization before rerun.

### Current outcome

`CHARACTERIZATION_FROZEN_NOT_VERIFIED`; private runtime shape
`NO_SAFE_CHANGE / NOT_ADMITTED` for demonstrated +15 LOC. Runtime SHA remains
`e877a34cc20b570306939f9f527048bf77584f6b1d3e78f9b4addf557fc46279`.
Whole campaign active/incomplete. Next action is the Coordinator original-code
characterization gate, not a runtime commit or broader refactor.

## Coordinator verified original characterization — publication admission

Later native results supersede the earlier unexecuted admission notes; the
runtime projection draft remains rejected and no runtime delta is credited.

Root exact frozen specd4790/sourcee877:38focused PASS (35NEW+3unchanged ORM
lifetime cases); union311PASS/11spec real-only, no skips/synthetic credit.
Whole original analytics634statements264branch outcomes100%, driver49/16 and
orphan27/10full100. Raw audit/input manifests/Ruffcheck/new-spec format all0;
all1673runtime/main/baseline custody exact. Root evidence20261011-r27-characterization.

Distinct fresh reviewer independently reran exact original38/311/full100 and
Ruff/format/raw audit. First actual ratchet Make2 was explained missing
@babel/parser in fresh tree, not a finding or matching ambiguity. STOP/frozen
evidence preserved. Coordinator authorized only ignored dependency symlink to
existing unchanged integration graph; no install/config/scanner/baseline change.
Explicit corrected SAME actual55a ratchet with new log labels0/findings[];
post-input/custody0. No tests rerun for that environment correction. Independent
final ACCEPT_CHARACTERIZATION_ONLY report4b96ba861f5a149da664af9c82eb27a271c3160e4e2bc349ce7fcb6a627a88fd.

Both root and reviewer retained inherited private short-JWT-key warnings.
Source/spec/test configs unchanged, no fake coverage/skip weakening. Private
actual draft remains NO_SAFE_CHANGE/NOT_ADMITTED (+15effectiveLOC), never copied
into runtime or natively measured. Characterization classification NO_CHANGE
complexity; no IMPROVED claim. Whole campaign ACTIVE/INCOMPLETE.

Coordinator alone is now authorized exact-path TEST/REPORTONLY publication:
this report and NEWspec; separately independent report. Original analytics
runtime must never be staged, main not changed, no push. Publication commit and
post-integration ratchet recorded in R27 integration checkpoint/private evidence.
