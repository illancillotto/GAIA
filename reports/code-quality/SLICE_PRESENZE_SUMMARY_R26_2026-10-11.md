# R26 Presenze monthly operational summary — Analysis Gate

## Ownership

ANALYZE ONLY. Dedicated worktree
`/home/cbo/CursorProjects/GAIA-campaign-20261009-r9-presenze-mutations`, branch
`refactor/complexity-r26-presenze-summary`; clean starting HEAD
`de76117a6ad9405fd013c3c7114d18625c2b8620`, merge-base/main
`55a1b1d35911451e018b662c2acc450bf5994ea2`.

Coordinator registered ownership before delegation. Potential runtime ownership
is only `frontend/src/app/presenze/giornaliere/page.tsx`; potential new tests only
`frontend/tests/unit/presenze-giornaliere-summary-r26.test.tsx`. Neither runtime
nor tests are admitted. This new report is the only tracked write authorized.
Existing extracted models, shared UI/lib/hooks, old tests, backend, identity,
tooling, baseline and configuration are read-only.

## Baseline

Preflight commands: `git status --short`, `git rev-parse HEAD`,
`git merge-base HEAD main`, owned-path history and SHA256. Starting tree clean.
Page SHA256:
`d362df3199fbf65dc4566b56d4029fe72135c910f3e39e691b3e3535516fa940`.
Last page commits are accepted campaign work: `c51b6038` mutations,
`ecdcc93c` label policy, `bee3fd53` anomaly ordering, `cdfb8f96` daily presentation,
`fbd4172d` monthly insights. No uncommitted page work in this author checkout.
Coordinator separately controls main/user-worktree concurrent custody.

Coordinator-provided actual R24 report records:

| Scope | Cognitive | Cyclomatic | LOC | Callables | useState | useEffect |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Principal | 385 | 341 | 2023 | 1 | — | — |
| Whole page | 1093 | 1231 | 2812 | 308 | 21 | 13 |

These are original metrics, not newly executed measurements. No native scanner,
test, lint, typecheck, ratchet, build or Graphify process was started by this
agent. Existing frontend Graphify query supplied by Coordinator provides
orientation only; absent backend corpus is not complexity evidence.

## Target callable and coherent responsibility

`PresenzeGiornalierePage`: duplicated **monthly operational-summary projection**
for the collaborator grid heading and collaborator modal. Exactly two existing
sites: grid preparation lines2084–2091 and rendering2121–2159; modal
preparation2753–2760 and rendering2908–2938.

Both compute sorted absences, sort Saturday entries in place, format the same
Saturday string and display ordered Extra / Sabati mese / absence rows with the
same eligibility rules. Their layouts and grid-border rules intentionally differ.
This is more than badge tidying: the complete repeated selection, ordering and
summary-value policy can have a single owner while both layouts stay local.

Existing models were inspected: `monthly-record-insights.ts` owns aggregation,
`collaborator-rows.ts` selection, `daily-cell-model.ts` daily indicators/input
projection, `anomaly-panel-model.ts` anomaly ordering. None owns this monthly
display policy. No change to any existing model is proposed or authorized.

## Behavioral invariants

- Inputs remain the existing `CollaboratorMonthTotals`; no recomputation of
  ordinary/extra/absence/Saturday facts or collaborator identity.
- Absences remain `Array.from(map.entries()).sort((a,b) => b[1]-a[1])`, preserving
  stable insertion order on equal minutes. No alphabetical secondary sort.
- Saturday entries continue to be sorted **in place** by ordinal before exact
  `ordinal + "° " + label` formatting and `" · "` joining. Do not introduce a
  copied sort, Set, deduplication or new fallback.
- Current non-null totals assumption remains: both sites dereference
  `totals!.absencesByCause` before optional Saturday handling. Do not mask an
  invariant violation with empty totals or optional absence access.
- Extra is present strictly when `totals.extra > 0`, not truthiness. Zero,
  negative and NaN totals are not displayed as extra rows.
- Summary order stays Extra, Saturday, then descending absence minutes. A
  Saturday without a fact remains absent. Unknown absence causes continue
  through existing formatter/tone fallback unchanged, including prototype-like
  strings; do not repair those helpers inside this slice.
- `formatHoursCompact` null/zero/NaN/rounding behavior is unchanged. Existing
  helpers remain the sole formatters, rather than copied implementations.
- Grid Extra always has bottom border, including Extra-only summary. Saturday
  has bottom border iff Extra is positive OR absence entries exist. Absences
  have bottom border except the last absence. Grid Extra value remains emerald700,
  modal Extra value emerald800; all exact layout/class strings remain intentional.
- Existing absence React keys remain the original cause. Supplement keys can
  live in a separate nested array, so a cause `extra` or `saturday` cannot collide.
  No combined list requiring replacement of original absence keys is proposed.
- DOM element order, text, wrappers, profile badges and modal open/close remain
  exact. No stateful child component, new hook/effect, lifecycle change, API,
  permissions, mutation, transaction, mapping or async workflow is in scope.

## Characterization test matrix

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Aggregated amounts and both summary views | page1724 / regressions1649 | Exact row order/classes | None yet | Not rerun |
| Saturday ordering and all absence causes | page1803 / regressions1674 | Equal-ordinal stability and repeated entries | None yet | Not rerun |
| Unknown cause fallback | page1311 / regressions1260 | Exact label/value tones in both layouts | None yet | Not rerun |
| No Saturday fact | page1344 / regressions1293 | Modal absence and empty summary wrapper | None yet | Not rerun |
| Extra/absence/Saturday combinations | Partial existing | Eight combinations, original border oracle | None yet | Not run |
| Equal absence totals | Not found | Insertion-order assertion both views | None yet | Not run |
| Extra zero/negative/NaN | Existing numeric page cases | Summary eligibility comparison | None yet | Not run |
| Keys and retained DOM identity | Existing input lifecycle tests | Cause collision and modal close/reopen | None yet | Not run |
| Async successful record update | R9 mutations | Summary refresh with same input node and untouched payload | None yet | Not run |

Tests, if admitted, must mount the actual public page with native React and mock
only API/protection/irrelevant external controls in the established pattern.
No compiled-handler extraction or synthetic runtime coverage credit.

## Proposed design for Coordinator decision

One bounded local typed projection in the owned page, not a new mega component:
`buildMonthlyOperationalSummary(totals: CollaboratorMonthTotals)`.

1. Read the same absence entries and same optional Saturday entries in the same
   order, preserving in-place sort.
2. Produce `supplements` from two declarative descriptors (Extra and Saturday)
   with original eligibility, formatted value, label/value tone and grid border.
   Filter descriptors once by their eligibility; no duplicated imperative switch.
3. Produce `absences` with unchanged cause key, label/value formatter/tone and one
   computed grid-border token per entry. Existing cause helpers stay unchanged.
4. Each site checks `supplements.length + absences.length > 0`, renders its
   existing wrapper, then the supplement array followed by the absence array.
   Layout remains in each original site; no state/events are moved. Grid strings
   are parameterized only by the already projected tone/border token.

Separate supplement/absence arrays are required to preserve original cause keys
without cross-category collisions. A single combined-row list with renamed cause
keys is explicitly not the admitted design. Helper body should remain bounded
(roughly35–45 effective lines) and below cognitive/cyclomatic warning thresholds;
exact metrics cannot be asserted before a real candidate exists.

## Physical simplification proof plan

The two original policy/render copies contain22 relevant explicit decision sites:
6 for optional Saturday selection,8 for the two compound summary gates,
2 Extra-render gates,2 Saturday-render gates,2 repeated Saturday border ORs,
2 repeated absence border conditions. Sort/map callbacks are also duplicated.

Proposed projection retains one optional Saturday decision chain, one Extra
eligibility comparison, one Saturday border OR and one absence border condition;
the two layouts retain two length gates. This is a projected reduction from22
to8 sites before accounting for new filter/map callable baselines. This count is
a source-design estimate, **not measured evidence** and not a claim of14 cognitive
points: the native engine counts branches/nesting differently and nested parent
metrics overlap. The final proof must enumerate actual AST decision nodes,
including every new callback, and expand descriptors to show DOM equivalence.

Expected direction: principal cognitive and cyclomatic fall materially, whole-page
cognitive/physical decisions fall, no transferred helper violation. The exact
principal delta, file/callable LOC, callback count, findings and native gate are
UNKNOWN until admitted characterization and a frozen real candidate exist.
If the design only produces neutral relocation or insufficient actual reduction,
stop as `NO_SAFE_CHANGE`; do not broaden to other UI workflows.

## Tests and coverage prerequisite

Historical accepted six Presenze UI suites:472PASS and page full100 across1035
statements,1139 branch outcomes,306 functions,847 lines. That historical result
is **not fresh original admission**. Coordinator is acquiring fresh original
full-file evidence serially. New mounted characterization must also PASS against
the unchanged original before runtime authorization. Candidate then requires
full-file100 in all four dimensions without changing coverage gates, exclusions,
timeouts, skips or tests. All significant behaviors above need explicit assertions.

## Ratchet and stop condition

No ratchet executed by this analysis agent. Actual immutable55a gate is required
after any future admitted candidate and again after independent integration.
R25's proven generic-callback matching failure does not authorize application
reshaping, symbol renaming, baseline/tooling modifications or a different base.
First unexpected failure or ambiguous matching freezes candidate/evidence and
stops the slice for Coordinator decision.

## Classification

`ANALYZE_ONLY / DESIGN_PENDING`: no runtime reduction claimed. A coherent real
deduplication appears possible, contingent on characterization, actual metrics,
coverage, ratchet and independent review. This does not satisfy original P1's
50% reduction stop condition or eliminate the extreme tail.

## Files changed and commit

Only this newly created analysis report. Runtime/tests/models untouched; no
commit, branch manipulation, install, cache cleanup or native process launched.

## Residual risks and next decision

The main risk is unintentionally normalizing intentional layout/border, sort
mutation, key or fallback behavior while consolidating policy. Descriptor-driven
markup must be reviewed against real original mounted DOM, not only snapshots
or aggregate numbers. Callback matcher provenance remains an independent risk.

Coordinator decides whether to admit new original characterization tests after
fresh original full100. Runtime remains unauthorized until that separate gate.

## Characterization draft admission — subsequent Coordinator decision

Coordinator recorded separate characterization admission in the integration
registry before reactivating this agent. Fresh actual original evidence supplied:
472PASS /6 specs, original page1035statements1139branch outcomes306functions847
lines all100%, raw audit/input SHA checks exit0. Evidence directory:
`~/.cache/gaia-campaign/20261011-r26-presenze-original/`.

Agent subsequently authored exactly one new spec, with24 mounted-page tests:
8 summary-presence combinations,8 known/unknown absence tone/label cases,
stable aggregate absence ties,Saturday chronology,unworked Saturday absence,
3 extra eligibility values, supplement-like absence key close/reopen lifecycle,
and async KM-response refresh/input identity. Every combination verifies complete
ordered label/value nodes and **exact original classes** in both layouts,
including Extra-only grid bottom border and intentional emerald700/800 difference.
Models/calculation/formatters/components are real; only established API and
unrelated protection/external controls are mocked. Existing six specs untouched.

Two proposed matrix cases cannot be produced with a legitimate DTO/database:
duplicate Saturday facts/equal ordinals for one collaborator require duplicate
`collaborator_id,work_date`, forbidden by
`uq_presenze_daily_records_collaborator_date` (`models.py:395`). NaN effective
extra cannot come from the integer `effective_extra_minutes` response schema
(`schemas.py:679`) over JSON. They were not fabricated through aggregation mocks
or invalid synthetic DTOs. In-place sorting and no deduplication remain source
review invariants; three distinct valid Saturday dates characterize public order.
Negative integer effective extra is representable by the existing optional int
schema and is checked through the real page aggregation.

Frozen draft spec SHA256:
`4abd9f8e199fa32d80f840f6ed3c1075ea3f34bc2d8e0e9e9f2c52c1fedd1440`.
Page remains exact
`d362df3199fbf65dc4566b56d4029fe72135c910f3e39e691b3e3535516fa940`.
No agent native commands were run. These24 tests are **NOT YET PASS**; root owns
the serial native token and must review/run the frozen draft. Static
`git diff --check` exit0, status contains only the new spec and this report.

Proposed commands, from the author worktree `frontend/` directory:

```bash
./node_modules/.bin/vitest run tests/unit/presenze-giornaliere-summary-r26.test.tsx \
  --maxWorkers=1 --minWorkers=1 --reporter=json \
  --outputFile=/home/cbo/.cache/gaia-campaign/20261011-r26-presenze-summary/focused.json

VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx \
./node_modules/.bin/vitest run \
  tests/unit/presenze-giornaliere-page.test.tsx \
  tests/unit/presenze-giornaliere-regressions.test.tsx \
  tests/unit/presenze-giornaliere-r6.test.tsx \
  tests/unit/presenze-giornaliere-r7.test.tsx \
  tests/unit/presenze-giornaliere-r8.test.tsx \
  tests/unit/presenze-giornaliere-r9.test.tsx \
  tests/unit/presenze-giornaliere-summary-r26.test.tsx \
  --maxWorkers=1 --minWorkers=1 --coverage --reporter=json \
  --outputFile=/home/cbo/.cache/gaia-campaign/20261011-r26-presenze-summary/union.json \
  --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261011-r26-presenze-summary/coverage
```

Expected counts if all pass: focused24, union496/7specs, zero skips/failures.
Commands retain configured100% coverage thresholds. Root may select its existing
equivalent serial harness/logging convention; this spec does not alter policy.
Runtime remains forbidden until original characterization independent review
and fresh coverage gates complete. First failure freezes evidence for explanation.

## Root original gate and strict-type diagnostic

Coordinator executed frozen original24case draft: focused24PASS, then
496PASS/7specs, no skip/todo, original full1001035statements1139branch outcomes
306functions847lines. Raw audit and complete input custody checks exit0;
project-native `npm run typecheck -- --incremental false` exit0.
No runtime change authorized by those results alone.

First private strict new-spec type invocation failed20diagnostics (exit1), so
lint was not run. Evidence preserved in
`20261011-r26-presenze-characterization/new-spec-types.log`. Eighteen GeoJSON
diagnostics stem from omitted project root declarations in the private program;
two errors concern unsupported ByRoleOptions `exact:true` in this NEW spec.
Coordinator explicitly removed only those two redundant role options (string
accessible-name matching defaults exact), including read-only reviewer input;
new spec SHA `ea775e5ca3a1356a3b59be9a70ca3daf13abb9b4b886e46128bd9746f95c666e`.
Original source, old six tests, config, baseline and all assertions unchanged.

Corrected private verifier includes COMPLETE parsed project roots plus new spec
and Jest DOM declarations, not exclusions, mocked ambient types or diagnostic
ignores. Separate result log is required; original native failure is not erased.
Runtime remains unauthorized pending strict types/lint and independent review.
An attempted root report append with nonexistent `Custody` anchor failed before
editing; this explicit append records the actual evidence, no native retry.

## Refined implementation plan — still ANALYZE ONLY

Root reports complete-project-plus-new-spec strict types0, scoped lint0 with
three unchanged page warnings. Independent reviewer currently owns original
native verification; this author has no native token and no runtime admission.
Current spec `ea775e5c` and original source `d362df31` were rechecked unchanged.

Use the actual imported `CollaboratorMonthTotals` from
`./monthly-record-insights` as the sole helper argument type. The proposed local
name remains `buildMonthlyOperationalSummary`; inferred return shape only, no
new row interface, mega context, component or hook. Add `Fragment` to the existing
React import; extend the existing local type import. No new runtime path.

Projection preparation:

- `absenceEntries` retains exact `Array.from(totals.absencesByCause.entries())`
  and descending-minute stable sort before Saturday access.
- `saturdaySummary` retains exact optional access/ternary/in-place sort/map/join,
  called anew by **each** original render site. No `useMemo` or precomputed cache.
- Compute one `saturdayBorder` string using the original Extra/absence predicate;
  compute each absence border once in the absence projection.
- Two supplemental descriptor objects carry existing label/value, eligibility,
  key, exact grid label/value class, exact modal wrapper/value class. Use one
  shared `tone` pair to drive modal labels/value tones, with the Extra grid value
  class explicitly remaining700 while its modal value remains800. Never derive
  Extra grid class by concatenating Saturday border tokens: its original exact
  order is `border-b border-l border-slate-100`, not the duplicated Saturday form.
- `.filter((entry) => entry.present)` preserves descriptor order Extra/Saturday.
  The ordinary comparison `totals.extra > 0` occurs once in eligibility; the
  independent original Saturday border comparison remains intentional.
- Separate `absences` preserve `cause`, formatted label/value, existing tone
  lookup and the single border token. Never rename or prefix the cause key.

Supplemental descriptor class strings are presentation data, not an additional
conditional renderer. One bounded helper should contain about38–43 effective
lines; original helpers remain intact. There is no justification for packing
unrelated statements or minifying source to pass the LOC gate.

Exact rendering plan:

1. Replace each duplicated preparation with one destructuring call on its
   existing `totals!`; preserve nearby policy-label/schedule/record declarations.
2. Replace each outer compound summary gate by positive combined array lengths.
   Original wrappers and modal heading remain byte-equivalent.
3. Grid supplemental map returns **keyed `<Fragment key={entry.key}>`**, containing
   exactly two existing direct-grid divs with projected exact class strings.
   No additional DOM div. Separate grid absence map retains `<div key={cause}
   className="contents">` and its two original child divs with projected tone and
   border. Empty border concatenation keeps the original leading space.
4. Modal supplemental map retains its original single card div and two spans;
   projected wrapper/value strings retain Saturday `gap-3`/`text-right` and Extra
   emerald800. Modal absence map retains original cause-key card/spans.

## Corrected complete static decision census

The initial22-site estimate had incorrectly distributed optional-chain versus
Saturday-border counts. The following **syntactic branch-site** census is the
refined plan (comparisons, array traversal and callable entry baselines are not
silently counted as branch syntax):

| Original syntax | Sites before | Planned after | Where |
| --- | ---: | ---: | --- |
| Optional-chain Saturday access + ternary | 4 | 2 | Two preparations → one projection |
| Outer summary AND/two ORs/ternary | 8 | 2 | Two original wrappers, simple length gates |
| Extra render ternary | 2 | 0 | Descriptor eligibility then shared filter |
| Saturday render ternary | 2 | 0 | Descriptor eligibility then shared filter |
| Saturday border OR/ternary, duplicated for label/value | 4 | 2 | One projected border |
| Absence border ternary, duplicated for label/value | 2 | 1 | One projection-map border |
| Total branch syntax | 22 | 7 | Planned genuine deduplication, not measured |

All callbacks are included in the planned aggregate accounting: original scope
has8 callbacks (two absence sorts, two Saturday sorts, two Saturday format maps,
two absence JSX maps). Planned scope has9 callbacks (one absence sort, one
Saturday sort, one Saturday format map, one descriptor filter, one absence
projection map, **four** JSX maps across the two layouts), plus one new helper.
Net callable-entry change is therefore+2, not a fictitious negative count.
Every introduced JSX map is decision-free; projection-map keeps the one genuine
border decision. All other page callbacks remain untouched. Engine metrics may
include nested contributions more than once;22→7 is not a15-point cognitive claim.

Static nonblank source counts identify the replacement budget: preparation7+8,
grid policy body30 (`2124–2153`), modal policy body21 (`2912–2932`), total66lines.
Wrapper gates replace in place. Projected new render bodies about24–28lines total,
two destructuring calls2lines, helper38–43lines:64–73lines. This is an honest
LOC risk band, not a passing promise: the wide end would grow legacy file LOC
and is unacceptable. Full explicit descriptor structure must be reviewed against
the native file count; if readable consolidation does not keep fileLOC<=2812,
STOP rather than compress text or hide classes in unrelated existing helpers.
The lower end plausibly removes2lines while eliminating15 branch-syntax sites.

Future admission, if granted, must require actual aggregate/physical reduction,
full100 and actual55a ratchet. No baseline/tooling, test weakening or symbol-name
adjustment is proposed. No candidate source has been written. Stop pending
independent original review and Coordinator runtime decision.

## Code-only candidate freeze — STOP, no native admission

Coordinator separately admitted CODE ONLY after independent original review
`ACCEPT_ORIGINAL_CHARACTERIZATION6d569ca7`,24focused/496union/full100/types/lint/
custody0. Agent implemented only the owned page; no tests/models/config touched.

Candidate SHA256:
`3e68dbf4ffd19bcb1e971b3d3685cd948dee90b04fea86b55fd576a6a0685d9d`.
Original `d362df31` and corrected spec `ea775e5c` remain the comparison/input
authority. Candidate diff68insertions66deletions,134changed physical lines;
the helper has40nonblank lines. No minification, unrelated edits or naming trick.

The candidate uses actual `CollaboratorMonthTotals`, inferred typed return,
keyed `Fragment` supplements with two direct grid divs, separate original cause
keys, same-array Saturday sort at both render invocations and unchanged exact
class strings. Source branch census matches the previously planned22→7 syntax
sites; complete new callbacks9+helper versus old8, net callable-entry+2.
This static count is **NOT measured cognitive/cyclomatic evidence**.

Read-only awk reproducing the existing native scanner's `effectiveLoc` predicate
(nonempty trimmed lines excluding comment-prefix lines) gives **2812→2813**.
The+1 line exceeds the explicit legacy file budget. Native scanner/test/type/
lint/ratchet have not been invoked by this agent; no PASS is claimed. The prior
66line estimate omitted the closing-line accounting in modal preparation,
which actually contributes7lines. Final readable40line helper and render maps
therefore exceed the budget despite genuine policy deduplication.

Root also noted original absence tone lookup precedes label/value formatting.
The frozen projection evaluates label/value before tone; the current helpers
are plain-data readers on typed primitive input, but this altered evaluation
order has not earned invariant acceptance and is an additional review issue.
It is recorded rather than silently repaired or claimed equivalent.

Classification for this frozen candidate: **`NO_SAFE_CHANGE / NOT_ADMITTED`**.
Stop under Coordinator's explicit LOC condition. No full100/native gate or
integration attempted. Existing six specs and new corrected spec are immutable;
candidate remains uncommitted in dedicated author tree, not integration.
Do not publish/cherry-pick it or claim IMPROVED. Readable descriptor redundancy
does not currently give a demonstrated compliant reduction; do not compress
statements, remove unrelated lines or relocate presentation data to manufacture
the missing line. Coordinator may decide a separately justified revised design,
but this agent does not continue unilaterally.
