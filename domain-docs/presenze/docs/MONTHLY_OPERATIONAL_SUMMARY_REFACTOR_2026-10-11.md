# Monthly operational summary — R34

## Responsibility

The collaborator grid and dialog in `PresenzeGiornalierePage` share one private
`buildMonthlyOperationalSummary` projection. It owns strictly-positive Extra
eligibility, Saturday display text, descending stable absence ordering and the
two layouts' summary styles. Rendering remains local, not a moved mega component.
No new file, hook, state, effect, authorization, API or identity mapping.

Supplement descriptors remain separate from cause-keyed absence rows. Grid
supplements use keyed Fragments without DOM wrappers; absence rows keep their
original `div.contents`. Exact classes/borders/text remain, including Extra-only
bottom border and grid emerald700 versus dialog emerald800.

## Observable equivalence

The existing Saturday array is still sorted IN PLACE per grid/dialog render;
this projection is not generally pure. Its mutation sequence is preserved.
Absences are copied from the same Map and sorted by descending minutes, keeping
insertion order on ties. Each absence evaluates tone, label, value in that order.
No memoization, copied Saturday sort or changed aggregation.

Some deterministic formatting and collaborator-policy lookups commute with
unrelated header computations. Their absolute invocation trace changes, not
observable output/effects: schema-valid DTO fields and locally allocated totals
are primitives/plain objects, helpers are total and headers do not inspect the
sorted array. This bounded source proof does not authorize reordering external
calls, exceptions, async transitions or user actions.

## Evidence and limits

Author and static independent review: principal cognitive385→367/cyclomatic
341→323/LOC2023→1988; whole-file cognitiveSUM1093→1062/cyclomaticSUM1231→1201/
effectiveLOC2812→2809. Helper6/7/32/nesting0/params1, no finding.
Existing496 mounted tests in seven immutable specs pass before/after with
full-file statements/branches/functions/lines100. Types/lint/actual-main ratchet
pass; no new test needed beyond existing R26 public summary characterization.
Independent native verification and integration evidence are recorded separately
in the R34 reports. No baseline/scope/threshold update or main merge.

The principal still exceeds300 cognitive; this is a coherent IMPROVED slice,
not completion of P1's strategic50% target or the global campaign. Historical30
global findings and final whole-project suite certification remain separate.
