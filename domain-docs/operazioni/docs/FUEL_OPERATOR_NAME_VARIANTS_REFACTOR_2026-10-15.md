# Fuel operator ordered name variants — R100

## Responsibility

Deduplicate only the ordered WCOperator name policy shared by orphan fuel-group
consolidation and distance attribution in `fuel_analytics`. Both consumers use
the same local `_operator_name_variants` tuple builder; their subsequent guards,
maps, aggregation and response construction remain unchanged.

## Preserved contract

- First-last display name, then last-first, then raw username; display strings
  are stripped only at their outside boundaries. No case or internal whitespace
  normalization, canonical identity mapping or username stripping.
- Preserve empty variants, eager left-to-right evaluation and repeated property
  reads. First and last names are intentionally not bound once before formatting.
- Consolidation retains last-query-owner collisions, dictionary insertion order
  and empty-name filtering. Vehicle-related keys remain raw and unconsolidated.
- Distance attribution retains positive linked GAIA-user precedence, first
  existing name fallback, exceptions and fresh shallow vehicle-map copies.
- SQL, authorization, date/status filtering, API, read-only behavior and database
  transaction boundaries do not change.

## Characterization and accounting

Twelve added persisted public-route cases cover exact formatting/nonmatches,
nullable names, empty/raw username, related keys and query-order collisions.
Existing R14 assertions remain byte-exact outside their AST factory. The factory
now compiles the actual live helper dependency with its real annotation type;
it does not substitute an implementation or inflate runtime coverage.

Original-source focused characterization99PASS; candidate genuine428PASS and
supplemental78PASS. Two external mutation probes show original assertions reject
reversed name priority and bind-once property reads. Genuine full-file analytics
coverage627/627statements and252/252branches100%, unchanged defensive pragmas.
Independent verification supplies a new terminal receipt; the recovered original
run's missing terminal receipt and external overlap remain documented.

Fuel cognitive217→192, cyclomatic148→138; `_op_km` cognitive33→18. New helper
cognitive10/cyclomatic11 has an explicit cyclomatic warning. File cognitive
sum706→676; unique source OR nodes68→63. Nested scanner spans overlap: these
are five removed duplicated source decisions, not ten independent decisions.
File error18→16, warning10→13, total findings28→29; no reduced finding-total
claim. This is a bounded improvement, not resolution of fuel orchestration or
completion of the campaign. Final admission/gates belong to the R100 report in
`reports/code-quality/`.
