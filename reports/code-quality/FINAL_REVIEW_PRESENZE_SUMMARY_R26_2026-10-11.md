# R26 Presenze monthly operational summary — Independent review

## Ownership and admission

Reviewer owns only this NEW report and small private evidence. Dedicated tree:
`GAIA-campaign-20261011-r26-presenze-review`, branch
`review/complexity-r26-presenze-summary`. Initial tree clean; HEAD
`de76117a6ad9405fd013c3c7114d18625c2b8620`, merge-base/main
`55a1b1d35911451e018b662c2acc450bf5994ea2`.

Registry recorded ACTIVE before delegation. This phase is STATIC DESIGN ONLY:
no source/test import, native test, scanner, lint, typecheck, build, dependency,
cleanup, Graphify, commit or integration performed. Original six specs, models,
configuration, tooling and baseline remain immutable. Main checkout untouched.

Original page independently hashed:
`d362df3199fbf65dc4566b56d4029fe72135c910f3e39e691b3e3535516fa940`.
Objective, context checkpoint skill, project complexity rules/references and
identity contract read. Canonical identity, authorization, INAZ refresh and
business calculations are outside this display-policy responsibility.

## Evidence inspected

- Author design: `SLICE_PRESENZE_SUMMARY_R26_2026-10-11.md`; specifically the
  two existing monthly Extra/Saturday/absence projections, not other workflows.
- Original page: grid preparation2083–2091/render2121–2156; modal
  preparation2751–2759/render2908–2935; formatters155,321,582,596.
- Existing `monthly-record-insights.ts`: aggregation, Map insertion order,
  shared mutable Saturday-entry arrays and non-null totals assumptions.
- Original native Coordinator evidence in
  `~/.cache/gaia-campaign/20261011-r26-presenze-original/`: tests.exit0,
  audit.exit0, input-check-frontend-cwd.exit0, report.exit0; audit.json reports
  1035/1035 statements,1139/1139 branch outcomes,306/306 functions,847/847 lines,
  all100%, no skipped counters. This is inspected Coordinator evidence,
  **not an independently executed reviewer gate**.

Principal baseline385 cognitive/341 cyclomatic/2023LOC; page aggregate1093
cognitive/1231 cyclomatic/2812LOC/308callables/21useState/13useEffect are supplied
native baseline metrics. Candidate metrics and gates remain NOT RUN.

## Source-backed invariant checklist

| Invariant | Original source | Requirement for candidate |
| --- | --- | --- |
| Absence ordering |2084,2753 descending numeric comparator|Same copied Map entries and stable insertion ties; no alphabetical tie-breaker|
| Saturday sorting side effect |2087–2090,2755–2758|Sort the SAME array in place at both render call-sites; no copy/useMemo/deduplication|
| Saturday text |155,2089,2757|Exact ordinal formatter, one space and middle-dot join separator|
| Null totals assumption |2084,2753 dereference before optional Saturday chain|Do not add empty fallback that hides an invalid invariant|
| Extra eligibility |2124,2912 strictly greater than zero|Not truthiness; zero/negative/NaN remain absent|
| Summary presence/order |2121,2908|Empty wrapper absent; Extra then Saturday then absences|
| Extra border |2126–2127 unconditional bottom border|Retain bottom border even when Extra is sole summary row|
| Saturday border |2134,2137 Extra-positive OR any absence|Retain both conditions, including Saturday last with Extra present|
| Absence border |2146,2149 index less than last|No bottom border on final absence; both cells match|
| Layout/tone |2122–2152 versus2909–2932|Keep intentional different wrappers/classes; Extra value700 grid versus800 modal|
| Cause policy |582–613|Reuse exact format/tone helpers; no prototype-key/fallback repairs|
| Keys |2145,2927 raw cause|Separate absence key domain from supplement keys; no cause renaming|
| Lifecycle |Existing local React rendering|No new component state/effect, handler, asynchronous flow or authorization change|

The proposed shared typed projection is a coherent responsibility: duplicated
selection, ordering, formatting and visibility become a single policy owner,
while grid/modal layout stays local. It is not inherently a mega-JSX move.
However, source equivalence and aggregate improvement are still unproven.

## Actionable design conditions

1. Grid Extra/Saturday currently use fragments, not DOM wrappers. A mapped
   supplement needs a keyed React Fragment, not a new `div.contents` or component
   wrapper. Preserve absence wrappers exactly.
2. Separate supplement and absence arrays must stay separate React child key
   domains. Raw absence causes `extra` and `saturday` must not collide with
   supplement identifiers or receive artificial renamed keys.
3. Exact class assertions must include the leading space produced by empty
   border interpolation and modal Saturday `gap-3`/`text-right` distinctions;
   truthy visual equivalence alone is weaker than the behavior-preserving scope.
4. Descriptor construction must not normalize numeric/fallback behavior or
   introduce another local switch/table that merely duplicates domain policy.
   Existing formatters stay authoritative. No generic mega context object.
5. File LOC already violates error threshold. The helper/projection must replace
   enough duplication to prevent native fileLOC growth; readability does not
   waive the ratchet. Any new helper/callback must remain below error thresholds.
6. Verify actual AST decision sites including new filtering/mapping callbacks.
   The author's22→8 physical-site estimate is not native cognitive credit and
   cannot substitute for full-file aggregate measurement. Border predicates
   occur twice per grid row in original source and need explicit enumeration.
7. Preserve sort execution during each render at both sites. Hoisting into
   memoized/global monthly preparation changes timing/mutation and is outside
   the admitted design. No identity or aggregation rewrites are permitted.

## Independent needed characterization checklist

| Behavior | Required evidence before candidate admission | Current reviewer status |
| --- | --- | --- |
| Eight Extra/Saturday/absence combinations|Public mounted page; exact wrapper presence, label/value order/classes in BOTH views|Spec not yet admitted to reviewer|
| Known and unknown causes|All seven known tones plus legitimate underscore fallback; exact values in both layouts|Spec not yet reviewed|
| Equal absence totals|Real distinct-date records establish Map insertion tie order in both views|Spec not yet reviewed|
| Saturday chronology|Valid distinct-date records supplied out of order, actual ordinal text in both layouts|Spec not yet reviewed|
| Saturday without working fact|Saturday date alone does not create a summary row|Spec not yet reviewed|
| Extra eligibility/format|Positive,zero,negative legitimate integer DTO values and fractional-hour formatting|Spec not yet reviewed|
| Key domains/lifecycle|Cause identifiers equal supplement keys; close/reopen and public updates preserve unrelated input identity|Spec not yet reviewed|
| Async response refresh|Real mounted mutation response changes both projections without changing API payload/order|Spec not yet reviewed|
| Whole-file coverage|Original plus candidate four dimensions100%, raw counters audited, immutable existing tests|Only Coordinator original evidence inspected|

Equal Saturday ordinals/duplicate Saturday facts for one collaborator cannot
be generated with valid monthly dates and the database constraint
`uq_presenze_daily_records_collaborator_date` (`models.py:395`). NaN effective
extra cannot cross the optional integer JSON response schema (`schemas.py:679`).
Do not manufacture invalid DTOs or mock aggregation for coverage. Preserve
these defensive source semantics in candidate diff review; valid public
chronology/zero/negative cases are still required. Prototype-like absence
strings expose existing dictionary lookup behavior; they must not become
an unrelated bug fix here.

## Gates and acceptance

Independent focused/union native tests, raw coverage audit, lint/types,
candidate report/physical proof and actual immutable55a ratchet NOT RUN.
No candidate imported or reviewed. A passing original coverage prerequisite
does not authorize runtime. First unexplained native failure or matcher
ambiguity must freeze the candidate/evidence; no silent retry or waiver.

R25 frozen FAIL14 is a separate blocked candidate. Its provenance does not
authorize reshaping this application code, changing matcher/tooling, adjusting
baseline or changing BASE_REF. Global historical FAIL30 is also separate.

## Classification and decision

`STATIC_DESIGN_REVIEW_ONLY`: coherent deduplication appears feasible with the
above explicit conditions. No ACCEPT_IMPROVED, runtime approval or reduction
credit. This slice alone does not satisfy P1's50% principal reduction condition
and does not eliminate the385-cognitive extreme hotspot.

## Residual risk and next step

Highest risks: class/border normalization, wrapper/key-domain changes, sort
mutation timing, legacy fileLOC growth and anonymous callback matcher identity.
Coordinator must freeze/admit the exact new spec and reviewer import separately;
native gates only after explicit exclusive token. Reviewer stops at this static
checkpoint until that admission. No commit performed.

## Original admission — native STOP checkpoint

Coordinator explicitly admitted original-only independent verification and
transferred the exclusive native token. Corrected spec independently read in
full and hashed `ea775e5ca3a1356a3b59be9a70ca3daf13abb9b4b886e46128bd9746f95c666e`;
original page stilld362. The24 mounted cases meaningfully assert both layouts,
all combinations, exact classes/order, seven causes plus fallback, stable ties,
chronology, strict extra eligibility, supplement-like absence keys and genuine
async KM response/input identity. No handler extraction or fabricated coverage.

FIRST native focused command exited1 before tests: installed Vitest rejects
the author's proposed `--minWorkers=1` option with `CACError: Unknown option
--minWorkers`. Command retained `--maxWorkers=1`, default/json reporters and
the exact new spec. Evidence private
`~/.cache/gaia-campaign/20261011-r26-presenze-review/focused.log` and
`focused.exit`. No test JSON or coverage exists from this invocation.

STOP immediately; no retry, option workaround, spec edit, union/audit/types/
lint invocation, candidate import, commit or acceptance. This is an explained
CLI compatibility failure, not a failed test assertion; any corrected command
requires separate Coordinator admission. Exclusive token released.

Earlier read-only preparation diagnostic used an incorrect baseline path in
a custody command; partial `inputs.sha256` retained. Correct authoritative
`config/code-quality/complexity-baseline.json` was then recorded separately in
`inputs-complete.sha256` before the native invocation, without changing bytes.
Private-directory inventory also returned absent-directory before creation;
neither preparation diagnostic was represented as a native PASS.

Current decision: `STOP_NATIVE_CLI_FAILURE`; no
`ACCEPT_ORIGINAL_CHARACTERIZATION` and no runtime credit.

## Explicit corrected-command admission and independent original verification

Coordinator recorded the invalid CLI invocation and separately admitted new
commands omitting ONLY unsupported `--minWorkers`. The valid worker cap remains
`--maxWorkers=1`; exact source/spec and all assertions unchanged. Original failed
command/log/exit remain untouched. Corrected command list:
`~/.cache/gaia-campaign/20261011-r26-presenze-review/corrected-commands.txt`.
Each native command executed serially after its predecessor completed:

| Independent command | Exit | Actual result |
| --- | ---: | --- |
| Corrected focused Vitest |0|24PASS,one spec,no skip/todo|
| Corrected original union Vitest/V8 |0|496PASS,seven exact specs,no skip/todo|
| Private raw results/coverage auditor |0|Four dimensions full100; all positive hits; exact single page path; no skip markers|
| Full project plus new spec TypeScript |0|662 configured roots,661 actual runtime files,zero diagnostics|
| Scoped ESLint page/new spec |0|Zero errors;three unchanged original page warnings;new spec no warning|
| Custody SHA check |0|Page,new spec,original six specs,Vitest/TS/lint configs and baseline unchanged|
| git diff --check |0|No tracked whitespace errors|

Raw page coverage matches original:1035/1035 statements,1139/1139 branch arms,
306/306 functions,847/847 lines. Auditor independently validates all496 results,
the exact seven spec names and full raw statement/function/branch counters,
not just rounded percentages. Actual fresh native outputs and auditor source
remain in the private directory with distinct `*-corrected` names. No broad
suite/build/E2E gate or runtime-candidate ratchet was executed or claimed.

The strict verifier was independently read: it retains ALL parsed project
roots plus the new spec and Jest DOM declaration and uses actual TypeScript
configuration. It does not use fake GeoJSON ambient declarations, narrowed
imports, diagnostic suppression or coverage exclusions. Page warnings remain
unused `isLoadingRecordDetail` and two existing effect dependencies; no repairs
are part of this characterization.

## Refined design assessment

Author refined design frozen at
`d10d24b0ff003548deebe077364fb1e380687a916ca0dc453d3a133092c1d70c`
was independently read. Explicit Fragment/no-DOM-wrapper plan, separate key
domains, unchanged classes/formatters, repeated in-place sort timing and single
local typed projection answer earlier design conditions. Revised22→7 syntactic
branch-site census includes both grid border expressions and accurately
discloses nine new-scope callbacks versus eight original plus one helper.
That estimate still does not prove native metrics or functional equivalence.

Honest source-size budget64–73lines versus66original indicates a real LOC risk;
native pageLOC must stay<=2812 without minification or unrelated changes.
Candidate admission must require actual aggregate/physical improvement, full100
and immutable55a ratchet, not the forecast.

The public mounted tests provide meaningful original characterization of this
bounded responsibility. One limitation remains: grid assertion flattens
`div.contents` children, so it does not itself reject an added supplement DOM
wrapper. A candidate reviewer must inspect AST/markup for keyed Fragment and
direct grid divs. This is not permission to weaken the exact-wrapper invariant.
Impossible duplicate-Saturday/NaN JSON cases stay source-review obligations,
not synthetic coverage. Existing six specs are preserved byte-for-byte.

## Independent original decision

`ACCEPT_ORIGINAL_CHARACTERIZATION`: explicit fresh independent native evidence
supports the immutable original and new mounted spec. Runtime still NOT
ADMITTED; no `ACCEPT_IMPROVED`, no candidate metric credit, no baseline/tooling
change and no commit/integration performed. Whole campaign remains
ACTIVE/INCOMPLETE and P1 extreme reduction is unmet.

All native processes terminal; exclusive heavy token RELEASED to Coordinator.
Reviewer stops until separate exact candidate import/admission. Original source
SHA remainsd362df31, corrected spec ea775e5c and baseline38e6b794.
