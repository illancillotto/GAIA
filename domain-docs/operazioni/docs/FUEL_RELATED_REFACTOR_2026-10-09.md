# Fuel analytics — related response mapping

The fuel route keeps query execution, entity identity, grouping and ranking in
the existing orchestration. A small typed adapter now owns the three nullable
average response fields, shared by top vehicles, top operators and both related
entity lists. A local related-usage builder removes duplicate count/net-total
response construction without introducing a generic processor or context.

## Preserved contract

- Average price uses positive-liter records and rounds to four decimals;
  average cost/liters round to two. Missing cost remains excluded from the
  cost mean, but its liters remain in the price denominator. Explicit zero
  and negative cost are not treated as missing.
- Net liters/cost sums include storno and zero-liter entries in original
  order. Refuel counts include all entries. Means retain the existing raw
  calculation and evaluation points, before ordered related net-total sums.
- Related entities rank by net liters with stable ties and the existing
  five-item limit. Vehicle plate/name/id fallback and operator UUID/name/
  unknown identities remain unchanged; related operator keys are not newly
  consolidated merely because top operator groups are consolidated.
- All database statements, parameters, order and response fields remain
  unchanged. No authorization, transaction, schema, external call, UI or
  anomaly logic is modified. No writes are introduced.

Characterization uses real persisted SQLAlchemy records; full-file analytics
statement/branch coverage is 100% before/after under existing coverage policy.
The legacy defensive exclusions are unchanged, not new exemptions.
The new mapping helpers are below all warning thresholds. Cognitive reduction
is real across the full analytics file, while file LOC grows by 15; this is not
a claim that all metrics or finding counts decrease.

Detailed commands, attempts, counters and independent integration gates live
in `reports/code-quality/SLICE_R4_FUEL_RELATED_2026-10-09.md` and the matching
integration/verification reports. Production PostgreSQL behavior is not
certified solely by the isolated SQLite characterization.
